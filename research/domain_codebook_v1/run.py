"""Run only the two missing ContractNLI display/code cells on pinned 8B LLMs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import decode, digest, read, sha, write  # noqa: E402
from system1bench.llm_adapter import LLMAdapter, answer_from_logits  # noqa: E402
from system1bench.run import read_run, save_run  # noqa: E402
from freeze import HERE, SOURCE, render, selected_source  # noqa: E402

MODES = ("display_only", "code_only")
EXISTING = {"base": "contractnli_base", "both": "contractnli_reversed_option_order"}
BATCH = 8


def validate_files() -> tuple[dict, dict, list[dict], list[dict]]:
    manifest = read(HERE / "manifest.json")
    if sha(HERE / "frozen.json") != manifest["frozen_sha256"]:
        raise ValueError("Codebook freeze changed")
    if sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]:
        raise ValueError("Codebook protocol changed")
    if sha(SOURCE / "frozen.json") != manifest["source_frozen_sha256"]:
        raise ValueError("Original domain cases changed")
    if sha(SOURCE / "manifest.json") != manifest["source_manifest_sha256"]:
        raise ValueError("Original domain manifest changed")
    base, both = selected_source(read(SOURCE / "frozen.json"))
    frozen = read(HERE / "frozen.json")
    if len(frozen["rows"]) != 144 or {r["id"] for r in frozen["rows"]} != {c["id"] for c in base}:
        raise ValueError("Selected case IDs changed")
    for case, row in zip(base, frozen["rows"]):
        if case["id"] != row["id"] or case["group"] != row["group"]:
            raise ValueError("Frozen case order/group changed")
        for mode in ("base", *MODES, "both"):
            msgs, indices, options = render(case["state"], case["questions"]["answer"], mode)
            spec = row["modes"][mode]
            if digest(msgs) != spec["messages_sha256"] or digest(options) != spec["candidate_assignment_sha256"] or indices != spec["canonical_code_indices"]:
                raise ValueError("Frozen prompt/code assignment changed")
    return frozen, manifest, base, both


def audit_prompts(model: str, tokenizer, limit: int, frozen: dict, manifest: dict,
                  base: list[dict], both: list[dict]) -> dict:
    orig = {}
    for mode, suite in EXISTING.items():
        path = SOURCE / "results/local" / model / f"{suite}.json.gz"
        if sha(path) != manifest["existing_output_sha256"][f"{model}/{mode}"]:
            raise ValueError("Existing comparator output changed")
        saved = read_run(path)
        orig[mode] = {r["id"]: r for r in saved["rows"]}
        if len(orig[mode]) != 144:
            raise ValueError("Original result missing IDs")
    prepared = {mode: [] for mode in MODES}
    stats = {mode: [] for mode in ("base", *MODES, "both")}
    for case, rev, spec in zip(base, both, frozen["rows"]):
        for mode in ("base", *MODES, "both"):
            msgs, code_indices, options = render(case["state"], case["questions"]["answer"], mode)
            rendered = tokenizer.apply_chat_template(msgs, tokenize=False,
                                                     add_generation_prompt=True, enable_thinking=False)
            ids = tokenizer.encode(rendered, add_special_tokens=False)
            if len(ids) > limit:
                raise ValueError("Context limit exceeded; no truncation")
            stats[mode].append(len(ids))
            fingerprint = digest(ids)
            if mode in EXISTING:
                original = orig[mode][case["id"]]
                source = case if mode == "base" else rev
                if original["request_sha256"] != source["request_sha256"] or original["gold"] != spec["gold"]:
                    raise ValueError("Existing semantic request/gold mismatch")
                if original["audit"]["prompt_token_sha256"] != fingerprint or original["audit"]["prompt_tokens"] != len(ids):
                    raise ValueError("Existing token-level prompt mismatch")
            else:
                prepared[mode].append(dict(id=case["id"], group=case["group"], gold=spec["gold"],
                                           request_sha256=case["request_sha256"],
                                           messages_sha256=spec["modes"][mode]["messages_sha256"],
                                           candidate_assignment_sha256=spec["modes"][mode]["candidate_assignment_sha256"],
                                           code_indices=code_indices, token_ids=ids,
                                           prompt_token_sha256=fingerprint,
                                           question=case["questions"]["answer"]))
    return dict(prepared=prepared, lengths={mode: dict(min=min(v), max=max(v),
                   median=sorted(v)[len(v)//2]) for mode, v in stats.items()})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=("llama31_8b_instruct", "qwen3_8b"))
    parser.add_argument("--paths", default=".aris/compute/performance_paths.json")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    frozen, manifest, base, both = validate_files()
    if args.audit_only:
        from transformers import AutoTokenizer
        checkpoint = Path(read(ROOT / args.paths)[args.model])
        tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True, trust_remote_code=False)
        tokenizer.padding_side = "left"
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        audit = audit_prompts(args.model, tokenizer, 32768, frozen, manifest, base, both)
        print(args.model, audit["lengths"], "base/both matched existing token hashes", flush=True)
        return

    import torch

    adapter = LLMAdapter(args.model, read(ROOT / args.paths)[args.model])
    original_meta = read(SOURCE / "results/local" / args.model / "metadata.json")
    if original_meta["signature"]["model"]["model_files_sha256"] != adapter.metadata["model_files_sha256"]:
        raise ValueError("Checkpoint differs from existing legal results")
    if original_meta["signature"]["model"]["chat_template_sha256"] != adapter.metadata["chat_template_sha256"]:
        raise ValueError("Chat template differs from existing legal results")
    audit = audit_prompts(args.model, adapter.tok, adapter.limit, frozen, manifest, base, both)
    print(args.model, audit["lengths"], "base/both matched existing token hashes", flush=True)
    output = HERE / "results" / args.model
    if output.exists():
        raise ValueError("Existing output directory; do not overwrite")
    output.mkdir(parents=True)
    signature = dict(model=adapter.metadata, source_frozen_sha256=manifest["source_frozen_sha256"],
                     codebook_frozen_sha256=manifest["frozen_sha256"],
                     protocol_sha256=manifest["protocol_sha256"],
                     runner_sha256=sha(__file__), freeze_code_sha256=manifest["freeze_code_sha256"],
                     adapter_sha256=sha(ROOT / "system1bench/llm_adapter.py"),
                     existing_output_sha256=manifest["existing_output_sha256"],
                     batch_size=BATCH, new_modes=list(MODES), context_limit=adapter.limit)
    metadata = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                    signature=signature, audit_lengths=audit["lengths"], modes={})
    write(output / "metadata.json", metadata)
    for mode in MODES:
        rows = []
        batches = []
        prompts = audit["prepared"][mode]
        for start in range(0, len(prompts), BATCH):
            group = prompts[start:start+BATCH]
            padded = adapter.tok.pad({"input_ids": [p["token_ids"] for p in group]},
                                     padding=True, return_tensors="pt").to("cuda")
            position = padded["attention_mask"].long().cumsum(-1) - 1
            position.masked_fill_(padded["attention_mask"] == 0, 0)
            adapter.synchronize()
            begun = time.perf_counter()
            error = None
            try:
                with torch.inference_mode():
                    output_logits = adapter.model(**padded, position_ids=position,
                                                  use_cache=False, logits_to_keep=1).logits[:, -1]
                selected = [output_logits[i].index_select(-1, adapter.code_ids[p["code_indices"]])
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
        path = output / f"{mode}.json.gz"
        save_run(path, dict(signature=signature, mode=mode, rows=rows, batches=batches,
                            completed_at=datetime.now(timezone.utc).isoformat()))
        metadata["modes"][mode] = dict(sha256=sha(path), decisions=len(rows),
                                        invalid=sum(r["error"] is not None for r in rows),
                                        inference_seconds=sum(b["seconds"] for b in batches))
        write(output / "metadata.json", metadata)
        print(args.model, mode, metadata["modes"][mode], flush=True)
    metadata.update(status="DONE", finished_at=datetime.now(timezone.utc).isoformat())
    write(output / "metadata.json", metadata)


if __name__ == "__main__":
    main()
