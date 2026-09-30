"""Real inference, per-suite atomic outputs, input-bound verified resumption."""
import argparse
import gzip
import importlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from system1bench.common import ROOT, decode, digest, labels, read, request, sha, write


def read_run(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def save_run(path, obj):
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    temp = path.with_suffix(".tmp")
    temp.write_bytes(gzip.compress(raw, mtime=0))
    temp.replace(path)


def validate_saved(saved, suite, signature):
    if saved["signature"] != signature:
        raise ValueError("Run fingerprint mismatch; use a new output directory")
    wanted = {(c["id"], qid): c for c in suite["cases"] for qid in c["questions"]}
    actual = [(r["id"], r["qid"]) for r in saved["rows"]]
    if len(set(actual)) != len(actual) or set(actual) != set(wanted):
        raise ValueError("Missing, duplicate or unexpected result IDs")
    for r in saved["rows"]:
        c = wanted[r["id"], r["qid"]]
        if r["request_sha256"] != c["request_sha256"] or r["gold"] != str(c["gold"][r["qid"]]["label"]):
            raise ValueError("Saved request/gold mismatch")


def validate_complete_files(out, suites, metadata):
    # A completed run is immutable: do not regenerate a missing file under stale
    # timing/hash metadata. Recovery must use a fresh output directory.
    for suite in suites:
        name = suite["name"]
        path = out / (name + ".json.gz")
        expected = metadata["suites"].get(name)
        if not path.is_file() or expected is None or sha(path) != expected["sha256"]:
            raise ValueError("Completed run has missing/corrupt files; use a new output directory")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--checkpoint")
    p.add_argument("--adapter", default="system1bench.laya_adapter:LayaAdapter")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--output", default="results")
    p.add_argument("--frozen", required=True, help="Repository-relative frozen input file")
    p.add_argument("--manifest", required=True, help="Repository-relative pre-inference manifest")
    args = p.parse_args()
    frozen_path, manifest_path = ROOT / args.frozen, ROOT / args.manifest
    frozen = read(frozen_path)
    if sha(frozen_path) != read(manifest_path)["prepared_sha256"]:
        raise ValueError("Prepared data is not bound to the published manifest")
    module, cls = args.adapter.split(":")
    adapter = getattr(importlib.import_module(module), cls)(args.model, args.checkpoint)
    code = {str(f.relative_to(ROOT)): sha(f) for f in sorted((ROOT / "system1bench").glob("*.py")) if f.name not in ["report.py", "metrics.py"]}
    code["benchmarks/run_frozen.py"] = sha(Path(__file__))
    signature = dict(protocol_sha256=sha(manifest_path), prepared_sha256=sha(frozen_path),
                     source_code_sha256=code, model=adapter.metadata, batch_size=args.batch_size, budget=frozen["budget"])
    out = ROOT / args.output / args.model
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "metadata.json"
    if meta_path.exists():
        meta = read(meta_path)
        if meta["signature"] != signature:
            raise ValueError("Metadata signature changed; use a new output directory")
    else:
        meta = dict(signature=signature, status="RUNNING", started_at=datetime.now(timezone.utc).isoformat(), suites={})
        write(meta_path, meta)
    was_complete = meta["status"] == "DONE"
    if was_complete:
        validate_complete_files(out, frozen["suites"], meta)
    for suite in frozen["suites"]:
        name = suite["name"]
        path = out / (name + ".json.gz")
        if path.exists():
            if name in meta["suites"] and sha(path) != meta["suites"][name]["sha256"]:
                raise ValueError("Saved output hash mismatch")
            saved = read_run(path)
            validate_saved(saved, suite, signature)
            print("VERIFIED", args.model, name, flush=True)
        else:
            groups = defaultdict(list)
            for c in suite["cases"]:
                groups[(digest(c["questions"]), c["language"])].append(c)
            records, batches = [], []
            for (_, lang), cases in groups.items():
                q = cases[0]["questions"]
                for start in range(0, len(cases), args.batch_size):
                    batch = cases[start:start + args.batch_size]
                    audits = [adapter.audit(c["state"], q, frozen["budget"]) for c in batch]
                    adapter.synchronize()
                    t = time.perf_counter()
                    error = None
                    try:
                        # Construct the payload through an explicit whitelist, not raw source rows.
                        outputs = adapter.predict([request(c)["state"] for c in batch], q, lang, frozen["budget"], len(batch))
                        if len(outputs) != len(batch):
                            raise ValueError("Wrong output count")
                    except Exception as e:
                        error = type(e).__name__  # avoid private paths / source text in public error messages
                        outputs = [None] * len(batch)
                    adapter.synchronize()
                    seconds = time.perf_counter() - t
                    bid = len(batches)
                    batches.append(dict(id=bid, requests=len(batch), decisions=sum(len(c["questions"]) for c in batch), seconds=seconds))
                    for c, output, audit in zip(batch, outputs, audits):
                        answers = output.get("answers", {}) if output else {}
                        for qid, question in q.items():
                            err = error
                            answer = answers.get(qid)
                            pred, probabilities = None, None
                            try:
                                pred, probabilities = decode(question, answer)
                            except Exception as e:
                                err = err or type(e).__name__
                            records.append(dict(id=c["id"], qid=qid, group=c["group"], family=c["family"], language=c["language"],
                                                request_sha256=c["request_sha256"], questions_sha256=digest(q), type=question["type"],
                                                labels=labels(question), gold=str(c["gold"][qid]["label"]),
                                                answer=answer, prediction=pred, probabilities=probabilities, error=err,
                                                audit=audit[qid], batch_id=bid, length_target=c.get("length_target"), position=c.get("position")))
            saved = dict(signature=signature, suite={k: v for k, v in suite.items() if k != "cases"}, rows=records, batches=batches,
                         completed_at=datetime.now(timezone.utc).isoformat())
            validate_saved(saved, suite, signature)
            save_run(path, saved)
        meta["suites"][name] = dict(sha256=sha(path), requests=len(suite["cases"]), decisions=len(saved["rows"]),
                                    errors=sum(r["error"] is not None for r in saved["rows"]),
                                    inference_seconds=sum(b["seconds"] for b in saved["batches"]))
        if not was_complete:
            write(meta_path, meta)
        print("DONE", args.model, name, meta["suites"][name], flush=True)
    if not was_complete:
        meta.update(status="DONE", finished_at=datetime.now(timezone.utc).isoformat())
        write(meta_path, meta)


if __name__ == "__main__":
    main()
