"""Read-only, independent audit of frozen data. No inference or source mutation.

Run: python audit_existing.py /mnt/sata2/cym/system1bench
The JSON is printed to stdout; no input/output file is overwritten.
Uses only the Python standard library and does not execute benchmark code.
"""
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import gzip
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(s) for s in (ROOT / path).read_text(encoding="utf-8").splitlines() if s.strip()]


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def request(c):
    return {"state": c["state"], "questions": c["questions"]}


def duplicates(items):
    counts = Counter(items)
    return sum(n - 1 for n in counts.values() if n > 1)


def profile(cases):
    valid_gold = 0
    forbidden = 0
    for c in cases:
        for qid, q in c["questions"].items():
            allowed = list(q["criteria"]) if q["type"] == "choice" else ["true", "false"] if q["type"] == "noul" else [str(i) for i in range(len(q["criteria"]))]
            valid_gold += str(c["gold"][qid]["label"]) in allowed
        state = c["state"]
        if isinstance(state, dict):
            forbidden += len(set(state) & {"gold", "answer", "expected", "label", "rationale", "derivation", "correct_answer", "target_tools", "original_tools"})
    return dict(cases=len(cases), decisions=sum(len(c["gold"]) for c in cases),
                groups=len({c["group"] for c in cases}), duplicate_ids=duplicates(c["id"] for c in cases),
                duplicate_requests=duplicates(digest(request(c)) for c in cases),
                request_hash_mismatches=sum(digest(request(c)) != c["request_sha256"] for c in cases),
                valid_gold_fields=valid_gold, forbidden_state_fields=forbidden)


def policy_oracle(family, facts, p):
    # Independent priority scan; never imports the generator or its oracle.
    if family == "refund":
        order = [(facts["suspected_fraud"], "hold"), (facts["elapsed_days"] <= p["return_window"] and facts["damaged"], "replace"), (facts["elapsed_days"] <= p["return_window"], "refund"), (True, "deny")]
        review = bool(facts["suspected_fraud"] or facts["amount"] >= p["review_threshold"])
        severity = sum([facts["urgent"], facts["damaged"]])
    elif family == "access":
        order = [(facts["disabled"] or facts["expired"], "deny"), (facts["mfa_required"] and not facts["mfa_verified"], "challenge"), (facts["role"] in p["permitted_roles"], "allow"), (True, "deny")]
        review = bool(facts["anomalous"] and facts["attempts"] >= p["review_threshold"])
        severity = sum(facts["attempts"] >= p[k] for k in ("low_threshold", "high_threshold"))
    else:
        order = [(facts["outage"] and facts["paying"], "urgent_support"), (facts["category"] == "billing", "billing"), (facts["category"] == "technical", "technical"), (True, "general")]
        review = bool(facts["outage"] or (facts["vip"] and facts["age_hours"] >= p["review_threshold"]))
        severity = sum(facts["age_hours"] >= p[k] for k in ("low_threshold", "high_threshold"))
    return {"action": next(label for cond, label in order if cond), "review": str(review).lower(), "severity": str(severity)}


def event_distribution(family, p, options):
    """Independent finite-event/Bayes calculation; not the vendor derivation."""
    F = Fraction
    def binary(yes): return {"yes": yes, "no": 1 - yes}
    if family == "uniform_support": return {k: F(int(k) <= p["faces"], p["faces"]) for k in options}
    if family == "weighted_inventory": return {k: F(p[k], sum(p.values())) for k in options}
    if family == "deterministic_support": return {k: F(k == p["only_color"]) for k in options}
    if family == "rare_event": return binary(F(1, p["tickets"]))
    if family == "sum_of_dice":
        n = p["sides"]; counts = Counter(a + b for a in range(1, n + 1) for b in range(1, n + 1))
        return {k: F(counts[int(k)], n * n) for k in options}
    if family == "independent_hits":
        n = p["shots"]; hit = F(p["hit_probability"])
        return {k: F(math.comb(n, int(k))) * hit ** int(k) * (1-hit) ** (n-int(k)) for k in options}
    if family == "backup_reliability": return binary(1 - (1-F(p["a"])) * (1-F(p["b"])))
    if family == "delivery_mixture": return binary(F(p["route_a"]) * F(p["on_time_a"]) + (1-F(p["route_a"])) * F(p["on_time_b"]))
    if family == "independent_streak": return {"heads": F(1, 2), "tails": F(1, 2)}
    if family == "without_replacement":
        red = p["red"] - p["removed_red"]
        return {"red": F(red, red + p["blue"]), "blue": F(p["blue"], red + p["blue"])}
    if family == "restricted_observation": return {k: F(int(k) in p["allowed"], len(p["allowed"])) for k in options}
    if family == "hidden_state_sensor":
        busy = F(p["initial_busy"]); stay = F(p["persistence"]); accuracy = F(p["sensor_accuracy"])
        for i, obs in enumerate(p["observations"]):
            if i: busy = busy * stay + (1-busy) * (1-stay)
            likelihood_busy = accuracy if obs else 1 - accuracy
            likelihood_clear = 1 - likelihood_busy
            busy = busy * likelihood_busy / (busy * likelihood_busy + (1-busy) * likelihood_clear)
        return binary(busy)
    if family == "defect_screening":
        prior = F(p["defect_prior"]); yes = prior * F(p["sensitivity"])
        return binary(yes / (yes + (1-prior) * F(p["false_positive"])))
    if family in {"independent_repeated_tests", "copied_correlated_tests"}:
        n = p["tests"] if family == "independent_repeated_tests" else 1
        yes = F(1, 10) * F(4, 5) ** n
        return binary(yes / (yes + F(9, 10) * F(1, 5) ** n))
    if family == "random_time_waiting": return {"short_gap": F(p["short_minutes"], p["short_minutes"] + p["long_minutes"]), "long_gap": F(p["long_minutes"], p["short_minutes"] + p["long_minutes"])}
    if family == "monty_informed_host": return {"initial_door": F(1, p["doors"]), "other_unopened_door": 1-F(1, p["doors"])}
    if family == "monty_uninformed_host": return {"initial_door": F(1, 2), "other_unopened_door": F(1, 2)}
    if family == "monty_selective_offer":
        a = F(p["offer_if_initial_correct"]); b = 2 * F(p["offer_if_initial_wrong"])
        return {"initial_door": a / (a+b), "other_unopened_door": b / (a+b)}
    if family == "two_child_selection":
        protocol = p["observation_protocol"]
        if protocol == "at_least_one": return binary(F(1, 3))
        if protocol == "random_child": return binary(F(1, 2))
        raise ValueError("unreviewed two-child observation protocol " + protocol)
    if family == "coupon_collection":
        states = {0: F(1)}; types = p["types"]
        for _ in range(p["purchases"]):
            new = defaultdict(F)
            for k, prob in states.items():
                new[k] += prob * F(k, types)
                new[k+1] += prob * F(types-k, types)
            states = new
        return {k: states.get(int(k), F(0)) for k in options}
    if family == "birthday_collision":
        none = F(1)
        for i in range(p["people"]): none *= F(max(0, p["possible_dates"]-i), p["possible_dates"])
        return binary(1-none)
    if family == "gambler_ruin":
        win = F(p["win"]); ratio = (1-win)/win
        yes = F(p["start"], p["goal"]) if win == F(1, 2) else (1-ratio ** p["start"])/(1-ratio ** p["goal"])
        return binary(yes)
    if family == "guaranteed_reward":
        hit = F(p["natural_success"]); last = p["guarantee_attempt"]
        return {k: (1-hit) ** (int(k)-1) * (hit if int(k) < last else 1) for k in options}
    raise ValueError("unreviewed family " + family)


def science_sensitivity():
    """Sidecar bootstrap experiment on frozen predictions; no published CI edits."""
    import numpy as np
    frozen = next(s["cases"] for s in read("research/scifact3_census_v1/frozen.json")["suites"] if s["name"] == "scifact3_base")
    cases = {c["id"]: c for c in frozen}
    published = read("research/model_expansion_v3/scores.json")["models"]
    historical = read("research/model_expansion_v1/historical_context.json")["models"]
    readings = {}; receipts = {}
    for model in published:
        if model in historical:
            receipt = next(r for r in historical[model]["source_receipts"] if r["path"].endswith("scifact3_base.json.gz"))
            path = ROOT / receipt["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"]
            rows = json.loads(gzip.decompress(path.read_bytes()))["rows"]
            declared_hash = receipt["sha256"]
        else:
            candidates = [ROOT / folder / model / "raw.jsonl" for folder in ("research/model_expansion_v1/results", "research/model_expansion_v2/results", "research/startlux_transfer_v1/results/main", "research/model_expansion_v3/results/main")]
            found = [p for p in candidates if p.exists()]
            assert len(found) == 1, (model, found)
            path = found[0]; meta = json.loads((path.parent / "metadata.json").read_text())
            assert meta["status"] == "DONE" and meta["errors"] == 0
            assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["raw_sha256"]
            rows = [r for r in map(json.loads, path.read_text().splitlines()) if r["suite"] == "scifact3_base"]
            declared_hash = meta["raw_sha256"]
        assert len(rows) == len({r["id"] for r in rows}) == 339
        mapping = {}
        for row in rows:
            c = cases[row["id"]]
            assert row["qid"] == "answer" and row["error"] is None
            assert row["request_sha256"] == c["request_sha256"] and row["gold"] == c["gold"]["answer"]["label"] and row["group"] == c["group"]
            mapping[row["id"]] = int(row["gold"] == row["prediction"])
        vals = [mapping[c["id"]] for c in frozen]
        metric = published[model]["metrics"]["science"]
        assert metric["n"] == 339 and metric["correct"] == sum(vals) and abs(metric["score"] - sum(vals)/339) < 1e-12
        readings[model] = vals
        receipts[model] = {"path": str(path.relative_to(ROOT)), "raw_sha256": declared_hash, "validated_rows": 339}
    model_names = list(readings)
    y = np.array([readings[m] for m in model_names], dtype=float).T
    claims = sorted({c["group"] for c in frozen}); docs = sorted({c["document_group"] for c in frozen})
    ci = np.array([claims.index(c["group"]) for c in frozen]); di = np.array([docs.index(c["document_group"]) for c in frozen])
    draws = 5000; seed = 20261006; rng = np.random.default_rng(seed)
    claim_counts = rng.multinomial(len(claims), np.ones(len(claims))/len(claims), size=draws)
    doc_counts = rng.multinomial(len(docs), np.ones(len(docs))/len(docs), size=draws)
    weightings = {"claim_only": claim_counts[:, ci], "document_only": doc_counts[:, di], "crossed_pigeonhole": claim_counts[:, ci] * doc_counts[:, di]}
    output = {"design": "post-hoc pointwise percentile bootstrap sensitivity; not historical CI replacement", "n": 339,
              "claims": len(claims), "documents": len(docs), "draws": draws, "seed": seed, "numpy": np.__version__,
              "crossed_method": "Independently resample claim IDs and document IDs, retaining observed pairs with product multiplicity; no nonexistent claim-document rows are created.",
              "caveat": "Claim-only, document-only and crossed intervals are model-dependent sensitivity analyses, not proof that any estimator is universally optimal or a causal architecture effect.",
              "models": {}, "raw_receipts": receipts}
    intervals = {name: np.quantile((w @ y)/(w.sum(axis=1)[:, None]), [.025, .975], axis=0) for name, w in weightings.items()}
    for i, model in enumerate(model_names):
        result = dict(correct=sum(readings[model]), n=339, score=sum(readings[model])/339)
        for name, limits in intervals.items():
            lower, upper = limits[:, i]
            result[name] = dict(ci95=[float(lower), float(upper)], width=float(upper-lower))
        result["crossed_to_claim_width_ratio"] = result["crossed_pigeonhole"]["width"] / result["claim_only"]["width"]
        output["models"][model] = result
    return output


def main():
    out = {"audit_version": 1, "scope": "frozen rows and pinned source files; not a human semantic annotation audit", "root": str(ROOT), "datasets": {}}
    policy = read("research/confirmation_v1/frozen.json")
    frozen_paths = ["research/confirmation_v1/frozen.json", "research/domain_expansion_v1/frozen.json", "research/scifact3_census_v1/frozen.json", "data/startlux_transfer_v1/frozen.json", "research/model_expansion_v1/frozen.json"]
    out["frozen_integrity"] = {}
    for path in frozen_paths:
        suites = read(path)["suites"]
        all_cases = [c for s in suites for c in s["cases"]]
        out["frozen_integrity"][path] = profile(all_cases) | dict(suite_duplicate_ids=sum(duplicates(c["id"] for c in s["cases"]) for s in suites))
    for suite in policy["suites"]:
        cases = suite["cases"]
        bases = [c for c in cases if c["condition"] == "original"]
        pairs = defaultdict(dict)
        for c in cases:
            pairs[c["group"]][c["condition"]] = c
        mismatch = sum(any(policy_oracle(c["family"], c["state"]["facts"], c["state"]["parameters"])[k] != str(c["gold"][k]["label"]) for k in c["gold"]) for c in cases)
        nonrepeat_by_request = defaultdict(list)
        for c in cases:
            if c["condition"] != "repeat": nonrepeat_by_request[digest(request(c))].append(c["id"])
        out["datasets"][suite["name"]] = profile(bases) | dict(all_variants=len(cases), oracle_mismatches=mismatch,
            labels=dict(Counter(c["gold"]["action"]["label"] for c in bases)),
            malformed_counterfactuals=sum(sum(a != p["counterfactual"]["state"]["facts"][k] for k, a in p["original"]["state"]["facts"].items()) != 1 or p["counterfactual"]["gold"]["action"] == p["original"]["gold"]["action"] for p in pairs.values()),
            nonrepeat_duplicate_request_groups=[ids for ids in nonrepeat_by_request.values() if len(ids) > 1],
            identical_repeat_pairs=sum(request(p["original"]) == request(p["repeat"]) for p in pairs.values()))
    domain = read("research/domain_expansion_v1/frozen.json")
    domain_manifest = read("research/domain_expansion_v1/manifest.json")
    out["domain_source_hashes"] = {name: hashlib.sha256((ROOT / "data/external/domain_expansion_v1" / name).read_bytes()).hexdigest() == expected for name, expected in domain_manifest["source_sha256"].items()}
    legal = next(s["cases"] for s in domain["suites"] if s["name"] == "contractnli_base")
    source = read("data/external/domain_expansion_v1/test.json")
    docs = {str(d["id"]): d for d in source["documents"]}
    source_mismatch = 0
    for c in legal:
        ids = c["source_id"]; d = docs[str(ids["document_id"])]; h = ids["hypothesis_id"]
        source_mismatch += c["state"]["contract_text"] != d["text"] or c["state"]["hypothesis"] != source["labels"][h]["hypothesis"] or c["gold"]["answer"]["label"] != d["annotation_sets"][0]["annotations"][h]["choice"]
    archive = zipfile.ZipFile(ROOT / "data/external/domain_expansion_v1/contract-nli.zip")
    train_files = [n for n in archive.namelist() if n.endswith("/train.json") or n == "train.json"]
    train_texts = set()
    for name in train_files:
        train_texts |= {d["text"] for d in json.loads(archive.read(name))["documents"]}
    out["datasets"]["contractnli"] = profile(legal) | dict(source_pairs_mismatch=source_mismatch, source_test_documents=len(docs),
        selected_labels=dict(Counter(c["gold"]["answer"]["label"] for c in legal)),
        excluded_length_documents=sum(len(d["text"]) > 16000 for d in docs.values()),
        document_cluster_sizes=dict(Counter(Counter(c["group"] for c in legal).values())),
        distinct_selected_texts=len({c["state"]["contract_text"] for c in legal}),
        train_archive_members=train_files, selected_exact_texts_in_train=len({c["state"]["contract_text"] for c in legal} & train_texts))
    science = next(s["cases"] for s in read("research/scifact3_census_v1/frozen.json")["suites"] if s["name"] == "scifact3_base")
    science_path = "data/external/domain_expansion_v1/scifact/data/"
    claims = {r["id"]: r for r in lines(science_path + "claims_dev.jsonl")}
    corpus = {r["doc_id"]: r for r in lines(science_path + "corpus.jsonl")}
    mismatch = 0; unannotated = []; source_pairs = set()
    for c in science:
        ids = c["source_id"]; claim = claims[ids["claim_id"]]; doc = corpus[ids["doc_id"]]
        annotations = claim["evidence"].get(str(ids["doc_id"]), [])
        gold = annotations[0]["label"] if annotations else "NOINFO"
        mismatch += c["state"] != dict(claim=claim["claim"], paper_title=doc["title"], paper_abstract="\n".join(doc["abstract"])) or gold != c["gold"]["answer"]["label"]
        if not annotations: unannotated.append(c["id"])
        source_pairs.add((ids["claim_id"], ids["doc_id"]))
    expected = {(r["id"], doc) for r in claims.values() for doc in set(r["cited_doc_ids"])}
    out["datasets"]["scifact3"] = profile(science) | dict(source_pairs_mismatch=mismatch, missing_source_pairs=len(expected - source_pairs), extra_source_pairs=len(source_pairs - expected),
        labels=dict(Counter(c["gold"]["answer"]["label"] for c in science)), distinct_documents=len({c["source_id"]["doc_id"] for c in science}),
        duplicated_citation_occurrences=sum(len(r["cited_doc_ids"]) - len(set(r["cited_doc_ids"])) for r in claims.values()),
        claim_cluster_sizes=dict(Counter(Counter(c["group"] for c in science).values())),
        document_cluster_sizes=dict(Counter(Counter(c["source_id"]["doc_id"] for c in science).values())),
        noinfo_from_annotation_absence=len(unannotated), noinfo_example_ids=unannotated[:3])
    raw = "data/startlux_transfer_v1/raw/"
    receipt = read(raw + "source_receipt.json")
    out["pinned_source_hashes"] = {name: hashlib.sha256((ROOT / raw / name).read_bytes()).hexdigest() == item["sha256"] for name, item in receipt.items()}
    transfer = read("data/startlux_transfer_v1/frozen.json")
    source_cladder = {str(r["question_id"]): r for r in json.loads(zipfile.ZipFile(ROOT / raw / "cladder.zip").read("cladder-v1-q-balanced.json"))}
    cladder_models = {r["model_id"]: r for r in json.loads(zipfile.ZipFile(ROOT / raw / "cladder.zip").read("cladder-v1-meta-models.json"))}
    source_crux = {r["id"]: r for r in lines(raw + "cruxeval.jsonl")}
    source_fin = {hashlib.sha256(d["content"].encode()).hexdigest(): d for d in read(raw + "finentity.json")}
    source_when = {r["uuid"]: r for r in lines(raw + "when2call.jsonl")}
    # Recompute eligibility without importing the preparation code.
    fin_issues = Counter(); eligible_spans = 0
    for d in read(raw + "finentity.json"):
        span_labels = defaultdict(set)
        for a in d["annotations"]: span_labels[a["start"], a["end"]].add(a["tag"])
        seen = set()
        for a in d["annotations"]:
            span = a["start"], a["end"]
            if len(span_labels[span]) != 1: fin_issues["conflicting_span"] += 1; continue
            if span in seen: fin_issues["duplicate_span"] += 1; continue
            seen.add(span)
            if d["content"][a["start"]:a["end"]] != a["value"] or a["tag"] != a["label"]: fin_issues["invalid_span_or_label"] += 1; continue
            eligible_spans += 1
    generations = read(raw + "crux_generations.json")
    flags = read(raw + "crux_flags.json")["raw_scored_generations"]
    crux_exclusions = Counter(); crux_eligible = 0
    for q in source_crux.values():
        correct = ast.literal_eval(q["output"]); values = [correct]
        if q["id"] not in generations: crux_exclusions["no_published_distractors"] += 1; continue
        for text, ok in zip(generations[q["id"]], flags[q["id"]]):
            if ok: continue
            try: value = ast.literal_eval(text)
            except (SyntaxError, ValueError): continue
            if not any(value == v for v in values): values.append(value)
        if len(values) > 1: crux_eligible += 1
        else: crux_exclusions["no_distinct_literal_distractor"] += 1
    out["source_eligibility"] = dict(finentity_eligible_spans=eligible_spans, finentity_issues=dict(fin_issues), cruxeval_source=len(source_crux), cruxeval_eligible=crux_eligible, cruxeval_exclusions=dict(crux_exclusions))
    for suite in transfer["suites"]:
        name = suite["name"]
        if name == "known_distribution": continue
        cases = [c for c in suite["cases"] if c["expansion_condition"] == "original"]
        report = profile(cases)
        report["gold_option_ids"] = dict(Counter(c["gold"]["decision"]["label"] for c in cases))
        report["gold_display_positions"] = dict(Counter(list(c["questions"]["decision"]["criteria"]).index(c["gold"]["decision"]["label"]) for c in cases))
        mismatch = 0
        for c in cases:
            sid = c["base_id"].split("/", 1)[1]; answer = c["questions"]["decision"]["criteria"][c["gold"]["decision"]["label"]]
            if name == "cladder":
                q = source_cladder[sid]
                mismatch += answer.lower() != q["answer"] or c["state"] != {"background": cladder_models[q["meta"]["model_id"]]["background"], "given_information": q["given_info"]} or c["questions"]["decision"]["instructions"] != q["question"]
            elif name == "cruxeval":
                q = source_crux[sid]
                mismatch += ast.literal_eval(answer) != ast.literal_eval(q["output"]) or c["state"] != {"code": q["code"], "input_arguments": q["input"]}
            elif name == "finentity":
                d = source_fin[c["group"]]; st = c["state"]
                labels = {a["tag"] for a in d["annotations"] if a["start"] == st["span_start"] and a["end"] == st["span_end"]}
                mismatch += labels != {answer} or st["entity"] != d["content"][st["span_start"]:st["span_end"]]
            else:
                q = source_when[sid]
                mismatch += answer != q["answers"][q["correct_answer"]] or c["state"] != {"tools": [json.loads(t) for t in q["tools"]], "user_question": q["question"]}
        report["source_binding_mismatches"] = mismatch
        if name == "cruxeval":
            report["candidate_counts"] = dict(Counter(len(c["questions"]["decision"]["criteria"]) for c in cases))
            report["uniform_choice_chance"] = sum(1 / len(c["questions"]["decision"]["criteria"]) for c in cases) / len(cases)
        if name == "when2call": report["source_gold_classes"] = dict(Counter(q["correct_answer"] for q in source_when.values()))
        out["datasets"][name] = report
    pilot = next(s["cases"] for s in transfer["suites"] if s["name"] == "known_distribution")
    refs = {r["id"]: r for r in lines(raw + "pilot_references.jsonl")}
    inputs = {r["id"]: r for r in lines(raw + "pilot_inputs.jsonl")}
    errors = 0; derivation_errors = []; derivation_unverified = []
    families = {}; settings = defaultdict(list)
    for c in pilot:
        ref = refs[c["id"]]; frac = {k: Fraction(v) for k, v in ref["gold_fractions"].items()}
        errors += sum(frac.values()) != 1 or any(float(frac[k]) != c["gold"]["decision"]["distribution"][k] for k in frac) or request(c) != request(inputs[c["id"]])
        settings[c["group"]].append(c)
        try:
            independently_derived = event_distribution(ref["family"], ref["parameters"], frac)
            if independently_derived != frac: derivation_errors.append(c["id"])
        except ValueError as exc: derivation_unverified.append(dict(id=c["id"], reason=str(exc)))
        if ref["variant"] == "canonical": families.setdefault(ref["family"], {"parameters": ref["parameters"], "fractions": ref["gold_fractions"]})
    out["datasets"]["known_distribution"] = profile(pilot) | dict(exact_fraction_or_payload_mismatches=errors,
        settings=len(settings), paired_setting_sizes=dict(Counter(len(v) for v in settings.values())),
        categories=dict(Counter(c["metadata"]["category"] for c in pilot)),
        paired_distribution_mismatches=sum(v[0]["gold"]["decision"]["distribution"] != v[1]["gold"]["decision"]["distribution"] for v in settings.values()),
        independently_derived_fraction_mismatch_ids=derivation_errors,
        independent_derivation_unverified=derivation_unverified,
        families_first_examples=families)
    out["unverified"] = ["Independent human semantic review of ContractNLI/SciFact/FinEntity labels", "All models' complete training corpora and contamination", "CRUXEval outputs reexecuted in a secured execution environment", "CLadder probabilities/answers independently rederived from causal graph", "Pilot natural-language-to-parameter binding exhaustively reread (first instance of each family inspected only)", "FinEntity and Intern-pilot standalone dataset redistribution license", "Two-way claim/document clustered uncertainty for SciFact"]
    if "--science-sensitivity" in sys.argv:
        out["science_uncertainty_sensitivity"] = science_sensitivity()
        out["unverified"].remove("Two-way claim/document clustered uncertainty for SciFact")
    print(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
