"""CPU-only exact token-completeness audit of SciFact cited-pair census."""

import collections
import json
from pathlib import Path

from transformers import AutoTokenizer

from laya.common import build_sequence, encode_text, render_options, serialize_state

from system1bench.common import digest, read, request, sha, write
from system1bench.llm_adapter import messages

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/scifact3_census_v1"
Laya_CHECKPOINT = (Path("/home/cym/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots") /
                   "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851")


def laya_one(tok, case, budget):
    q = case["questions"]["answer"]
    internal = {"t": q["type"], "ins": q["instructions"], "crit": q["criteria"]}
    state_text = serialize_state(case["state"])
    state_ids = encode_text(tok, state_text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
    head, markers = build_sequence(tok, "", internal, state_ids=[], **budget)
    opts = render_options(internal)
    original = [encode_text(tok, " " + s.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
                for s in opts]
    actual = [head[p + 1:(markers[i + 1] if i + 1 < len(markers) else len(head) - 2)]
              for i, p in enumerate(markers)]
    ins = encode_text(tok, "%s question: %s" % (internal["t"], internal["ins"].replace(tok.mask_token, " ")),
                      add_special_tokens=False)["input_ids"]
    actual_ins = head[1:markers[0] - 1]
    state_shortened = len(state_ids) > budget["max_len"] - len(head)
    option_shortened = actual != original
    instruction_shortened = actual_ins != ins
    mask_sanitized = tok.mask_token in state_text or tok.mask_token in str(q)
    return dict(state_tokens=len(state_ids), head_tokens=len(head), complete=not (
        state_shortened or option_shortened or instruction_shortened or mask_sanitized),
        state_shortened=state_shortened, option_shortened=option_shortened,
        instruction_shortened=instruction_shortened, mask_sanitized=mask_sanitized,
        prompt_token_sha256=digest(head + state_ids))


def main():
    target = OUT / "input_audit.json"
    if target.exists():
        raise FileExistsError("Input audit exists: refusing overwrite")
    frozen = read(OUT / "frozen.json")
    manifest = read(OUT / "manifest.json")
    if sha(OUT / "frozen.json") != manifest["prepared_sha256"]:
        raise ValueError("Frozen input hash changed")
    cases = [c for suite in frozen["suites"] for c in suite["cases"]]
    if any(c["request_sha256"] != digest(request(c)) for c in cases):
        raise ValueError("Request hash mismatch")
    result = dict(frozen_sha256=manifest["prepared_sha256"], requests=len(cases), systems={})
    for variant, path in [("laya_en", Laya_CHECKPOINT / "tokenizer"),
                          ("laya_multilingual", Laya_CHECKPOINT / "multilingual/tokenizer")]:
        tok = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        rows = [laya_one(tok, c, frozen["budget"]) for c in cases]
        result["systems"][variant] = dict(complete=sum(r["complete"] for r in rows),
                                          state_shortened=sum(r["state_shortened"] for r in rows),
                                          option_shortened=sum(r["option_shortened"] for r in rows),
                                          instruction_shortened=sum(r["instruction_shortened"] for r in rows),
                                          mask_sanitized=sum(r["mask_sanitized"] for r in rows),
                                          max_state_tokens=max(r["state_tokens"] for r in rows),
                                          max_head_tokens=max(r["head_tokens"] for r in rows))
    paths = read(ROOT / ".aris/compute/performance_paths.json")
    for variant in ["llama31_8b_instruct", "qwen3_8b"]:
        tok = AutoTokenizer.from_pretrained(paths[variant], local_files_only=True, trust_remote_code=False)
        lengths = []
        for c in cases:
            rendered = tok.apply_chat_template(messages(c["state"], c["questions"]["answer"]),
                                               tokenize=False, add_generation_prompt=True,
                                               enable_thinking=False)
            lengths.append(len(tok.encode(rendered, add_special_tokens=False)))
        limit = min(32768, read(Path(paths[variant]) / "config.json").get("max_position_embeddings", 32768))
        result["systems"][variant] = dict(complete=sum(n <= limit for n in lengths),
                                          over_limit=sum(n > limit for n in lengths),
                                          max_prompt_tokens=max(lengths), context_limit=limit)
    write(target, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
