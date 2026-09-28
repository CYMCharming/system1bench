import unittest
import tempfile
from pathlib import Path

from system1bench.common import ROOT, decode, digest, read, request
from system1bench.run import validate_complete_files, validate_saved
from system1bench.metrics import auc, metrics, cluster_ci
from system1bench.prepare import order_control


class IntegrityTests(unittest.TestCase):
    def test_reversal_with_shared_question_objects(self):
        questions = {"q": {"type": "choice", "criteria": {"A": "first", "B": "second", "C": "third"}}}
        cases = [dict(id=str(i), state={"text": str(i)}, questions=questions, gold={"q": {"label": "B"}}) for i in range(100)]
        reversed_cases = order_control(cases, "reversed")
        for before, after in zip(cases, reversed_cases):
            self.assertEqual(list(before["questions"]["q"]["criteria"]), ["A", "B", "C"])
            self.assertEqual(list(after["questions"]["q"]["criteria"]), ["C", "B", "A"])
            self.assertEqual(before["state"], after["state"])
            self.assertEqual(before["gold"], after["gold"])
            self.assertNotEqual(digest(request(before)), digest(request(after)))

    def test_release_keeps_simplified_chinese_as_chinese(self):
        manifest = read(ROOT / "protocol_manifest.json")
        suite = next(s for s in manifest["suites"] if s["name"] == "jev_laya_multilingual")
        self.assertEqual(suite["languages"]["zh"], 16)
        self.assertNotIn("en", suite["languages"])
        self.assertEqual(sum(suite["languages"].values()), 128)

    def test_metrics_known_confusion_matrix(self):
        rows = []
        for i, (g, p) in enumerate([("A", "A"), ("A", "B"), ("B", "B"), ("B", None)]):
            rows.append(dict(gold=g, prediction=p, error="failure" if p is None else None,
                             group=str(i), labels=["A", "B"], type="choice",
                             probabilities=[0.8, 0.2] if p == "A" else [0.2, 0.8]))
        m = metrics(rows)
        self.assertEqual(m["accuracy"], 0.5)
        self.assertEqual(m["failures"], 1)
        self.assertAlmostEqual(m["macro_f1"], ((2/3) + 0.5)/2)
        self.assertAlmostEqual(m["brier"], (0.08 + 1.28 + 0.08)/3)
        self.assertAlmostEqual(m["ece10"], 0.8 - 2/3)

    def test_auc_ties_and_clustered_interval(self):
        self.assertEqual(auc([0, 1], [0.5, 0.5]), 0.5)
        self.assertEqual(auc([0, 1], [0.1, 0.9]), 1.0)
        rows = [dict(group="one", gold="A", prediction=p, error=None) for p in ["A", "B"]]
        self.assertEqual(cluster_ci(rows, 100), [0.5, 0.5])

    def test_payload_whitelist(self):
        c = dict(state={"text": "hello"}, questions={}, gold="secret", factors="reason", verifier="answer")
        self.assertEqual(request(c), {"state": {"text": "hello"}, "questions": {}})

    def test_order_changes_fingerprint(self):
        self.assertNotEqual(digest({"A": None, "B": None}), digest({"B": None, "A": None}))

    def test_probability_validation(self):
        q = {"type": "choice", "criteria": {"A": None, "B": None}}
        for probs in [{"A": 1}, {"A": float("nan"), "B": 0}, {"A": 0.2, "B": 0.2}]:
            with self.assertRaises((ValueError, KeyError)):
                decode(q, {"choice": "A", "probabilities": probs})
        with self.assertRaises(ValueError):
            decode(q, {"choice": "A", "probabilities": {"A": 0.2, "B": 0.8}})
        self.assertEqual(decode(q, {"choice": "B", "probabilities": {"A": 0.5, "B": 0.5}})[0], "B")

    def test_completed_run_missing_file_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            with self.assertRaises(ValueError):
                validate_complete_files(out, [{"name": "x"}], {"suites": {"x": {"sha256": "unused"}}})
            self.assertEqual(list(out.iterdir()), [])

    def test_score_uses_mode_not_rounded_mean(self):
        pred, _ = decode({"type": "score", "criteria": ["low", "mid", "high"]},
                         {"score": 0.98, "probabilities": {"0": 0.5, "1": 0.02, "2": 0.48}})
        self.assertEqual(pred, "0")

    def test_resume_rejects_duplicates_and_gold_changes(self):
        c = dict(id="x", questions={"q": {}}, request_sha256="a", gold={"q": {"label": "yes"}})
        row = dict(id="x", qid="q", request_sha256="a", gold="yes")
        suite = {"cases": [c]}
        validate_saved({"signature": {}, "rows": [row]}, suite, {})
        for rows in [[row, row], [row | {"gold": "no"}], [row | {"request_sha256": "b"}]]:
            with self.assertRaises(ValueError):
                validate_saved({"signature": {}, "rows": rows}, suite, {})


if __name__ == "__main__":
    unittest.main()
