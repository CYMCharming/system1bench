"""Run the two missing SciFact3 codebook cells at the historical batch size."""

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
from freeze import HERE, MODEL_NAMES, MODES, SOURCE, render, selected_source  # noqa: E402

BATCH = 4
NEW_MODES = ("display_only", "code_only")
EXISTING = {"base": "scifact3_base", "both": "scifact3_reversed_option_order"}


def validate() -> tuple[dict, dict, list[dict], list[dict]]:
    manifest = read(HERE / "manifest.json")
    if (sha(HERE / "frozen.json") != manifest["frozen_sha256"]
        or sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]
        or sha(SOURCE / "frozen.json") != manifest["source_frozen_sha256"]
        or sha(SOURCE / "manifest.json") != manifest["source_manifest_sha256"]
        or manifest["batch_size"] != BATCH):
        raise ValueError("Source/codebook freeze or protocol changed")
    base, both = selected_source(read(SOURCE / "frozen.json"))
    frozen = read(HERE / "frozen.json")
    if len(frozen["rows"]) != 180:
        raise ValueError("Frozen row count changed")
    for case, rev, spec in zip(base, both, frozen["rows"]):
        if (case["id"] != spec["id"] or rev["id"] != spec["id"]
            or case["group"] != spec["group"]
            or case["request_sha256"] != spec["base_request_sha256"]
            or rev["request_sha256"] != spec["both_request_sha256"]):
            raise ValueError("Frozen paired cases differ from source")
        for mode in MODES:
            msgs, codes, options = render(case["state"], case["questions"]["answer"], mode)
            expected = spec["modes"][mode]
            if (digest(msgs) != expected["messages_sha256"]
                or digest(options) != expected["candidate_assignment_sha256"]
                or codes != expected["canonical_code_indices"]):
                raise ValueError("Frozen prompt/code assignment mismatch")
    return frozen, manifest, base, both


def audit(model: str, tokenizer, limit: int, frozen: dict, manifest: dict,
          base: list[dict], both: list[dict]) -> tuple[dict, dict]:
    source_meta_path = SOURCE / "results/local" / model / "metadata.json"
    if sha(source_meta_path) != manifest["source_metadata_sha256"][model]:
        raise ValueError("Original run metadata changed")
    source_meta = read(source_meta_path)
    if source_meta["status"] != "DONE" or source_meta["signature"]["batch_size"] != BATCH:
        raise ValueError("Original run was not complete batch four")
    historical = {}
    for mode, suite in EXISTING.items():
        path = SOURCE / "results/local" / model / f"{suite}.json.gz"
        if sha(path) != manifest["existing_output_sha256"][f"{model}/{mode}"]:
            raise ValueError("Original comparator changed")
        saved = read_run(path)
        rows = {row["id"]: row for row in saved["rows"]}
        if len(rows) != 180:
            raise ValueError("Original comparator incomplete")
        historical[mode] = rows
    prepared = {mode: [] for mode in NEW_MODES}
    lengths = {mode: [] for mode in MODES}
    for case, rev, spec in zip(base, both, frozen["rows"]):
        question = case["questions"]["answer"]
        for mode in MODES:
            msgs, code_indices, _ = render(case["state"], question, mode)
            rendered = tokenizer.apply_chat_template(msgs, tokenize=False,
                                                     add_generation_prompt=True,
                                                     enable_thinking=False)
            token_ids = tokenizer.encode(rendered, add_special_tokens=False)
            if len(token_ids) > limit:
                raise ValueError("Context limit exceeded; no truncation")
            lengths[mode].append(len(token_ids))
            token_hash = digest(token_ids)
            if mode in EXISTING:
                original = historical[mode][case["id"]]
                original_case = case if mode == "base" else rev
                if (original["request_sha256"] != original_case["request_sha256"]
                    or original["gold"] != spec["gold"]
                    or original["audit"]["prompt_token_sha256"] != token_hash
                    or original["audit"]["prompt_tokens"] != len(token_ids)):
                    raise ValueError("Original prompt token/reference mismatch")
            else:
                mode_spec = spec["modes"][mode]
                prepared[mode].append(dict(id=case["id"], group=case["group"],
                                           gold=spec["gold"],
                                           request_sha256=case["request_sha256"],
                                           messages_sha256=mode_spec["messages_sha256"],
                                           candidate_assignment_sha256=mode_spec["candidate_assignment_sha256"],
                                           code_indices=code_indices, token_ids=token_ids,
                                           prompt_token_sha256=token_hash, question=question))
    stats = {mode: dict(min=min(values), median=sorted(values)[len(values)//2],
                        max=max(values)) for mode, values in lengths.items()}
    return dict(prepared=prepared, lengths=stats), source_meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=MODEL_NAMES)
    parser.add_argument("--paths", default=".aris/compute/performance_paths.json")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    frozen, manifest, base, both = validate()
    if args.audit_only:
        from transformers import AutoTokenizer

        checkpoint = Path(read(ROOT / args.paths)[args.model])
        tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True,
                                                  trust_remote_code=False)
        tokenizer.padding_side = "left"
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        checked, _ = audit(args.model, tokenizer, 32768, frozen, manifest, base, both)
        print(args.model, checked["lengths"], "base/both token hashes matched", flush=True)
        return

    import torch

    adapter = LLMAdapter(args.model, read(ROOT / args.paths)[args.model])
    checked, old_meta = audit(args.model, adapter.tok, adapter.limit,
                              frozen, manifest, base, both)
    if (old_meta["signature"]["model"]["model_files_sha256"]
            != adapter.metadata["model_files_sha256"]
        or old_meta["signature"]["model"]["chat_template_sha256"]
            != adapter.metadata["chat_template_sha256"]
        or old_meta["signature"]["source_code_sha256"]["system1bench/llm_adapter.py"]
            != sha(ROOT / "system1bench/llm_adapter.py")):
        raise ValueError("Original model/template/adapter source differs")
    print(args.model, checked["lengths"], "base/both token hashes matched", flush=True)
    directory = HERE / "results" / args.model
    if directory.exists():
        raise ValueError("New results already exist; never overwrite")
    directory.mkdir(parents=True)
    signature = dict(model=adapter.metadata,
                     source_frozen_sha256=manifest["source_frozen_sha256"],
                     codebook_frozen_sha256=manifest["frozen_sha256"],
                     protocol_sha256=manifest["protocol_sha256"],
                     runner_sha256=sha(__file__),
                     adapter_sha256=sha(ROOT / "system1bench/llm_adapter.py"),
                     existing_output_sha256=manifest["existing_output_sha256"],
                     batch_size=BATCH, new_modes=list(NEW_MODES), context_limit=adapter.limit)
    metadata = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                    signature=signature, audit_lengths=checked["lengths"], modes={})
    write(directory / "metadata.json", metadata)
    for mode in NEW_MODES:
        prompts = checked["prepared"][mode]
        rows = []
        batches = []
        for start in range(0, len(prompts), BATCH):
            batch = prompts[start:start+BATCH]
            padded = adapter.tok.pad({"input_ids": [p["token_ids"] for p in batch]},
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
                            .float().cpu().tolist() for i, p in enumerate(batch)]
            except Exception as exc:
                error = type(exc).__name__
                selected = [None] * len(batch)
            adapter.synchronize()
            seconds = time.perf_counter() - begun
            batches.append(dict(id=len(batches), requests=len(batch), seconds=seconds,
                                error=error))
            for item, values in zip(batch, selected):
                answer = None
                prediction = None
                probabilities = None
                row_error = error
                if values is not None:
                    try:
                        answer = answer_from_logits(item["question"], values)
                        prediction, probabilities = decode(item["question"], answer)
                    except Exception as exc:
                        row_error = type(exc).__name__
                rows.append(dict(id=item["id"], group=item["group"], qid="answer",
                                 mode=mode, gold=item["gold"], prediction=prediction,
                                 answer=answer, probabilities=probabilities,
                                 candidate_logits=values, error=row_error,
                                 request_sha256=item["request_sha256"],
                                 messages_sha256=item["messages_sha256"],
                                 candidate_assignment_sha256=item["candidate_assignment_sha256"],
                                 prompt_token_sha256=item["prompt_token_sha256"],
                                 prompt_tokens=len(item["token_ids"]),
                                 canonical_code_indices=item["code_indices"],
                                 batch_id=batches[-1]["id"]))
        if len(rows) != 180 or {row["id"] for row in rows} != {p["id"] for p in prompts}:
            raise ValueError("Incomplete new mode")
        path = directory / f"{mode}.json.gz"
        save_run(path, dict(signature=signature, mode=mode, rows=rows,
                            batches=batches,
                            completed_at=datetime.now(timezone.utc).isoformat()))
        metadata["modes"][mode] = dict(sha256=sha(path), decisions=len(rows),
                                       invalid=sum(row["error"] is not None for row in rows),
                                       inference_seconds=sum(batch["seconds"] for batch in batches))
        write(directory / "metadata.json", metadata)
        print(args.model, mode, metadata["modes"][mode], flush=True)
    metadata.update(status="DONE", finished_at=datetime.now(timezone.utc).isoformat())
    write(directory / "metadata.json", metadata)


if __name__ == "__main__":
    main()
