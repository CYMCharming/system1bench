"""Corrected two-cell ContractNLI inference using the historical batch size."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, read, sha, write  # noqa: E402
from system1bench.llm_adapter import LLMAdapter, answer_from_logits  # noqa: E402
from system1bench.run import read_run, save_run  # noqa: E402
from freeze import HERE, SOURCE  # noqa: E402
from run import MODES, audit_prompts, validate_files  # noqa: E402

BATCH = 4


def check_amendment(model: str, manifest: dict, frozen: dict) -> dict:
    amended = read(HERE / "batch4_manifest.json")
    expected = {
        "amendment_sha256": sha(HERE / "AMENDMENT.md"),
        "corrected_runner_sha256": sha(__file__),
        "base_protocol_sha256": manifest["protocol_sha256"],
        "frozen_sha256": manifest["frozen_sha256"],
        "source_frozen_sha256": manifest["source_frozen_sha256"],
        "original_batch_size": BATCH,
        "corrected_batch_size": BATCH,
        "cases": len(frozen["rows"]),
        "document_groups": len({r["group"] for r in frozen["rows"]}),
    }
    for key, value in expected.items():
        if amended[key] != value:
            raise ValueError(f"Batch-four amendment mismatch: {key}")
    source_meta_path = SOURCE / "results" / "local" / model / "metadata.json"
    if sha(source_meta_path) != amended["source_metadata_sha256"][model]:
        raise ValueError("Original metadata changed")
    source_meta = read(source_meta_path)
    if source_meta["signature"]["batch_size"] != BATCH:
        raise ValueError("Historical batch size changed")
    for mode, suite in (("base", "contractnli_base"),
                        ("both", "contractnli_reversed_option_order")):
        path = SOURCE / "results" / "local" / model / f"{suite}.json.gz"
        if sha(path) != manifest["existing_output_sha256"][f"{model}/{mode}"]:
            raise ValueError("Historical output changed")
        saved = read_run(path)
        for index, (old, frozen_row) in enumerate(zip(saved["rows"], frozen["rows"])):
            if old["id"] != frozen_row["id"] or old["batch_id"] != index // BATCH:
                raise ValueError("Historical case ordering/batch grouping differs")
    return source_meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=("llama31_8b_instruct", "qwen3_8b"))
    parser.add_argument("--paths", default=".aris/compute/performance_paths.json")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    frozen, manifest, base, both = validate_files()
    source_meta = check_amendment(args.model, manifest, frozen)
    if args.audit_only:
        from transformers import AutoTokenizer

        checkpoint = Path(read(ROOT / args.paths)[args.model])
        tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True,
                                                  trust_remote_code=False)
        tokenizer.padding_side = "left"
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        audit = audit_prompts(args.model, tokenizer, 32768, frozen, manifest, base, both)
        print(args.model, audit["lengths"], "original token hashes matched", flush=True)
        return

    import torch

    adapter = LLMAdapter(args.model, read(ROOT / args.paths)[args.model])
    if source_meta["signature"]["model"]["model_files_sha256"] != adapter.metadata["model_files_sha256"]:
        raise ValueError("Checkpoint changed")
    if source_meta["signature"]["model"]["chat_template_sha256"] != adapter.metadata["chat_template_sha256"]:
        raise ValueError("Chat template changed")
    if source_meta["signature"]["source_code_sha256"]["system1bench/llm_adapter.py"] != sha(ROOT / "system1bench/llm_adapter.py"):
        raise ValueError("Adapter source changed")
    audit = audit_prompts(args.model, adapter.tok, adapter.limit, frozen, manifest, base, both)
    print(args.model, audit["lengths"], "original token hashes matched", flush=True)
    directory = HERE / "results_batch4" / args.model
    if directory.exists():
        raise ValueError("Corrected output already exists; never overwrite")
    directory.mkdir(parents=True)
    signature = dict(model=adapter.metadata,
                     source_frozen_sha256=manifest["source_frozen_sha256"],
                     codebook_frozen_sha256=manifest["frozen_sha256"],
                     protocol_sha256=manifest["protocol_sha256"],
                     amendment_manifest_sha256=sha(HERE / "batch4_manifest.json"),
                     amendment_sha256=sha(HERE / "AMENDMENT.md"),
                     runner_sha256=sha(__file__),
                     adapter_sha256=sha(ROOT / "system1bench/llm_adapter.py"),
                     existing_output_sha256=manifest["existing_output_sha256"],
                     batch_size=BATCH, modes=list(MODES), context_limit=adapter.limit)
    metadata = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                    signature=signature, audit_lengths=audit["lengths"], modes={})
    write(directory / "metadata.json", metadata)
    for mode in MODES:
        rows = []
        batches = []
        prompts = audit["prepared"][mode]
        for start in range(0, len(prompts), BATCH):
            group = prompts[start:start + BATCH]
            padded = adapter.tok.pad({"input_ids": [p["token_ids"] for p in group]},
                                     padding=True, return_tensors="pt").to("cuda")
            position = padded["attention_mask"].long().cumsum(-1) - 1
            position.masked_fill_(padded["attention_mask"] == 0, 0)
            adapter.synchronize()
            begun = time.perf_counter()
            error = None
            try:
                with torch.inference_mode():
                    logits = adapter.model(**padded, position_ids=position,
                                           use_cache=False, logits_to_keep=1).logits[:, -1]
                selected = [logits[i].index_select(-1, adapter.code_ids[p["code_indices"]])
                            .float().cpu().tolist() for i, p in enumerate(group)]
            except Exception as exc:
                error = type(exc).__name__
                selected = [None] * len(group)
            adapter.synchronize()
            seconds = time.perf_counter() - begun
            batches.append(dict(id=len(batches), requests=len(group), seconds=seconds, error=error))
            for prompt, z in zip(group, selected):
                answer = None
                prediction = None
                probabilities = None
                row_error = error
                if z is not None:
                    try:
                        answer = answer_from_logits(prompt["question"], z)
                        prediction, probabilities = decode(prompt["question"], answer)
                    except Exception as exc:
                        row_error = type(exc).__name__
                rows.append(dict(id=prompt["id"], group=prompt["group"], qid="answer", mode=mode,
                                 gold=prompt["gold"], prediction=prediction, answer=answer,
                                 probabilities=probabilities, candidate_logits=z, error=row_error,
                                 request_sha256=prompt["request_sha256"],
                                 messages_sha256=prompt["messages_sha256"],
                                 candidate_assignment_sha256=prompt["candidate_assignment_sha256"],
                                 prompt_token_sha256=prompt["prompt_token_sha256"],
                                 prompt_tokens=len(prompt["token_ids"]),
                                 canonical_code_indices=prompt["code_indices"],
                                 batch_id=batches[-1]["id"]))
        if len(rows) != 144 or {r["id"] for r in rows} != {p["id"] for p in prompts}:
            raise ValueError("Incomplete mode output")
        path = directory / f"{mode}.json.gz"
        save_run(path, dict(signature=signature, mode=mode, rows=rows, batches=batches,
                            completed_at=datetime.now(timezone.utc).isoformat()))
        metadata["modes"][mode] = dict(sha256=sha(path), decisions=len(rows),
                                       invalid=sum(r["error"] is not None for r in rows),
                                       inference_seconds=sum(b["seconds"] for b in batches))
        write(directory / "metadata.json", metadata)
        print(args.model, mode, metadata["modes"][mode], flush=True)
    metadata.update(status="DONE", finished_at=datetime.now(timezone.utc).isoformat())
    write(directory / "metadata.json", metadata)


if __name__ == "__main__":
    main()
