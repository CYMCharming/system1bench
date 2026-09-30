"""Greedy one-code generation on two frozen natural domains, without prompt search."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.strong_baseline import model_fingerprint, parse_response  # noqa: E402
from system1bench.common import digest, read, request, sha, write  # noqa: E402
from system1bench.llm_adapter import messages  # noqa: E402
from system1bench.run import read_run  # noqa: E402
from freeze import HERE, MODELS, SOURCES, source_cases  # noqa: E402

BATCH = 4
MAX_NEW_TOKENS = 16


def validate() -> tuple[dict, dict, dict[str, list[dict]]]:
    manifest = read(HERE / "manifest.json")
    if (sha(HERE / "frozen.json") != manifest["frozen_sha256"]
        or sha(HERE / "PROTOCOL.md") != manifest["protocol_sha256"]
        or sha(ROOT / "benchmarks/strong_baseline.py") != manifest["parser_code_sha256"]
        or sha(ROOT / "system1bench/llm_adapter.py") != manifest["adapter_code_sha256"]):
        raise ValueError("Frozen protocol, cases or parser changed")
    for domain, (directory, _) in SOURCES.items():
        if (sha(directory / "frozen.json") != manifest["source_frozen_sha256"][domain]
            or sha(directory / "manifest.json") != manifest["source_manifest_sha256"][domain]):
            raise ValueError("Source freeze/manifest changed")
    frozen = read(HERE / "frozen.json")
    if len(frozen["cases"]) != 324:
        raise ValueError("Case count changed")
    cases = source_cases()
    selected = {(domain, case["id"]): case for domain, domain_cases in cases.items()
                for case in domain_cases}
    if len(selected) != len(frozen["cases"]):
        raise ValueError("Source case IDs not unique")
    for row in frozen["cases"]:
        case = selected[row["domain"], row["id"]]
        question = case["questions"]["answer"]
        if (row["group"] != case["group"] or row["gold"] != case["gold"]["answer"]["label"]
            or row["request_sha256"] != case["request_sha256"]
            or row["question_sha256"] != digest(question)
            or row["messages_sha256"] != digest(messages(case["state"], question))
            or digest(request(case)) != case["request_sha256"]):
            raise ValueError("Frozen semantic request/prompt changed")
    return frozen, manifest, cases


def prompts_for_model(model: str, tokenizer, context_limit: int, frozen: dict,
                      manifest: dict, cases_by_domain: dict) -> tuple[list[dict], dict]:
    selected = {(domain, case["id"]): case for domain, cases in cases_by_domain.items()
                for case in cases}
    old = {}
    old_model_signatures = {}
    for domain, (directory, suite) in SOURCES.items():
        metadata_path = directory / "results/local" / model / "metadata.json"
        if sha(metadata_path) != manifest["old_metadata_sha256"][f"{domain}/{model}"]:
            raise ValueError("Historical metadata changed")
        metadata = read(metadata_path)
        if metadata["signature"]["batch_size"] != BATCH:
            raise ValueError("Historical batch size mismatch")
        old_model_signatures[domain] = metadata["signature"]["model"]
        path = directory / "results/local" / model / f"{suite}.json.gz"
        if sha(path) != manifest["old_output_sha256"][f"{domain}/{model}"]:
            raise ValueError("Historical output changed")
        saved = read_run(path)
        for row in saved["rows"]:
            key = (domain, row["id"])
            if key in old:
                raise ValueError("Duplicate historical result")
            old[key] = row
    if len(old) != len(frozen["cases"]):
        raise ValueError("Historical result count mismatch")
    prompts = []
    for spec in frozen["cases"]:
        domain, case_id = spec["domain"], spec["id"]
        case = selected[domain, case_id]
        old_row = old[domain, case_id]
        question = case["questions"]["answer"]
        msgs = messages(case["state"], question)
        rendered = tokenizer.apply_chat_template(msgs, tokenize=False,
                                                 add_generation_prompt=True,
                                                 enable_thinking=False)
        token_ids = tokenizer.encode(rendered, add_special_tokens=False)
        prompt_hash = digest(token_ids)
        if len(token_ids) + MAX_NEW_TOKENS > context_limit:
            raise ValueError("Context budget exceeded; no truncation allowed")
        if (prompt_hash != old_row["audit"]["prompt_token_sha256"]
            or len(token_ids) != old_row["audit"]["prompt_tokens"]
            or spec["request_sha256"] != old_row["request_sha256"]
            or spec["gold"] != old_row["gold"]):
            raise ValueError("Direct prompt/reference differs from code-logit comparator")
        prompts.append(dict(domain=domain, suite=spec["suite"], id=case_id,
                            group=spec["group"], gold=spec["gold"],
                            request_sha256=spec["request_sha256"],
                            question_sha256=spec["question_sha256"],
                            messages_sha256=spec["messages_sha256"],
                            prompt_token_sha256=prompt_hash,
                            token_ids=token_ids, allowed=spec["labels"], codes=spec["codes"]))
    return prompts, old_model_signatures


def read_existing(path: Path, expected: dict) -> dict:
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        key = (row["domain"], row["id"])
        if key not in expected or key in rows:
            raise ValueError("Unexpected/duplicate saved raw output")
        source = expected[key]
        for field in ("suite", "group", "gold", "request_sha256", "question_sha256",
                      "messages_sha256", "prompt_token_sha256"):
            if row[field] != source[field]:
                raise ValueError(f"Saved raw output {field} mismatch")
        rows[key] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--paths", default=".aris/compute/performance_paths.json")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    frozen, manifest, cases = validate()

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(4)
    torch.manual_seed(0)
    checkpoint = Path(read(ROOT / args.paths)[args.model])
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True,
                                              trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    context_limit = min(32768, int(read(checkpoint / "config.json").get(
        "max_position_embeddings", 32768)))
    prompts, historical = prompts_for_model(args.model, tokenizer, context_limit,
                                            frozen, manifest, cases)
    if len(prompts) != 324:
        raise ValueError("Prompt count changed")
    lengths = sorted(len(prompt["token_ids"]) for prompt in prompts)
    print(args.model, "historical token hashes matched", len(prompts),
          "min/median/max", lengths[0], lengths[len(lengths)//2], lengths[-1], flush=True)
    if args.audit_only:
        return

    model_files = model_fingerprint(checkpoint)
    template_hash = digest(tokenizer.chat_template)
    for domain in SOURCES:
        if (model_files != historical[domain]["model_files_sha256"]
            or template_hash != historical[domain]["chat_template_sha256"]):
            raise ValueError("Checkpoint/chat template differs from old code-logit run")
    signature = dict(model=args.model, model_files_sha256=model_files,
                     chat_template_sha256=template_hash,
                     frozen_sha256=manifest["frozen_sha256"],
                     protocol_sha256=manifest["protocol_sha256"],
                     runner_sha256=sha(__file__),
                     parser_code_sha256=manifest["parser_code_sha256"],
                     adapter_code_sha256=manifest["adapter_code_sha256"],
                     old_output_sha256=manifest["old_output_sha256"],
                     decoding="greedy_direct_code", parser="whole_response_exact_code",
                     batch_size=BATCH, max_new_tokens=MAX_NEW_TOKENS,
                     dtype="bfloat16", attention="sdpa", seed=0,
                     torch=torch.__version__, transformers=transformers.__version__,
                     python=platform.python_version(), gpu=torch.cuda.get_device_name(0))
    output = HERE / "results" / args.model
    metadata_path = output / "metadata.json"
    raw_path = output / "raw.jsonl"
    expected = {(p["domain"], p["id"]): p for p in prompts}
    if output.exists():
        if not args.resume:
            raise ValueError("Output already exists; use --resume with identical signature")
        metadata = read(metadata_path)
        if metadata["signature"] != signature:
            raise ValueError("Cannot resume changed run")
    else:
        output.mkdir(parents=True)
        metadata = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(),
                        expected=len(prompts), signature=signature)
        write(metadata_path, metadata)
    existing = read_existing(raw_path, expected)
    if metadata["status"] == "DONE":
        if len(existing) != len(prompts):
            raise ValueError("Completed run missing rows")
        print("Verified existing complete run", args.model, len(existing), flush=True)
        return

    model = AutoModelForCausalLM.from_pretrained(
        checkpoint, local_files_only=True, trust_remote_code=False,
        dtype=torch.bfloat16, attn_implementation="sdpa"
    ).to("cuda").eval()
    for domain in SOURCES:
        pending = [p for p in prompts if p["domain"] == domain
                   and (domain, p["id"]) not in existing]
        for start in range(0, len(pending), BATCH):
            batch = pending[start:start + BATCH]
            encoded = tokenizer.pad({"input_ids": [p["token_ids"] for p in batch]},
                                    padding=True, return_tensors="pt").to("cuda")
            input_width = encoded["input_ids"].shape[1]
            torch.cuda.synchronize()
            begun = time.perf_counter()
            batch_error = None
            try:
                with torch.inference_mode():
                    generated = model.generate(**encoded, do_sample=False,
                                               max_new_tokens=MAX_NEW_TOKENS,
                                               pad_token_id=tokenizer.pad_token_id,
                                               eos_token_id=tokenizer.eos_token_id,
                                               use_cache=True)
                generated_ids = generated[:, input_width:].cpu().tolist()
            except Exception as exc:
                batch_error = type(exc).__name__
                generated_ids = [[] for _ in batch]
            torch.cuda.synchronize()
            seconds = time.perf_counter() - begun
            records = []
            for item, ids in zip(batch, generated_ids):
                raw = tokenizer.decode(ids, skip_special_tokens=True)
                code, prediction, parse_error = parse_response("direct", raw,
                                                                 item["codes"], item["allowed"])
                ended = tokenizer.eos_token_id in ids
                error = batch_error or parse_error
                if not ended and error is not None and batch_error is None:
                    error = "max_tokens_without_valid_code"
                row = {key: item[key] for key in (
                    "domain", "suite", "id", "group", "gold", "request_sha256",
                    "question_sha256", "messages_sha256", "prompt_token_sha256"
                )}
                row.update(code=code, prediction=prediction, error=error,
                           raw_text=raw, generated_ids=ids,
                           prompt_tokens=len(item["token_ids"]),
                           completion_tokens=(ids.index(tokenizer.eos_token_id) + 1
                                              if ended else len(ids)),
                           stopped_at_eos=ended,
                           batch_seconds=seconds, batch_requests=len(batch),
                           batch_id=f"{domain}:{start // BATCH}")
                records.append(row)
            with raw_path.open("a", encoding="utf-8") as handle:
                for row in records:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        print(args.model, domain, len(pending), "new generations", flush=True)
    rows = read_existing(raw_path, expected)
    if len(rows) != len(prompts):
        raise ValueError("Incomplete raw output")
    batch_times = {}
    for row in rows.values():
        batch_id = row["batch_id"]
        if batch_id in batch_times and batch_times[batch_id] != row["batch_seconds"]:
            raise ValueError("Inconsistent batch timing")
        batch_times[batch_id] = row["batch_seconds"]
    metadata.update(status="DONE", finished_at=datetime.now(timezone.utc).isoformat(),
                    raw_sha256=sha(raw_path), count=len(rows),
                    invalid=sum(row["error"] is not None for row in rows.values()),
                    generated_tokens=sum(row["completion_tokens"] for row in rows.values()),
                    prompt_tokens=sum(row["prompt_tokens"] for row in rows.values()),
                    synchronized_inference_seconds=sum(batch_times.values()))
    write(metadata_path, metadata)
    print(args.model, "DONE", metadata["count"], "invalid", metadata["invalid"], flush=True)


if __name__ == "__main__":
    main()
