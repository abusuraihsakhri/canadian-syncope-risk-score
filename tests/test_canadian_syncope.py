import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import cli
from canadian_syncope import CSRSInput, RiskTier, calculate_metrics, evaluate_csrs, process_batch


class TestCanadianSyncopeRiskScore(unittest.TestCase):
    def test_published_component_weights(self):
        cases = [
            (CSRSInput(predisposition_vasovagal=True), -1),
            (CSRSInput(history_heart_disease=True), 1),
            (CSRSInput(systolic_bp=89), 2),
            (CSRSInput(systolic_bp=181), 2),
            (CSRSInput(troponin_elevated=True), 2),
            (CSRSInput(ecg_abnormal_axis=True), 1),
            (CSRSInput(ecg_prolonged_qrs=True), 1),
            (CSRSInput(ecg_prolonged_qtc=True), 2),
            (CSRSInput(ed_diagnosis="vasovagal"), -2),
            (CSRSInput(ed_diagnosis="cardiac"), 2),
        ]
        for inp, expected in cases:
            with self.subTest(inp=inp):
                self.assertEqual(evaluate_csrs(inp).score, expected)

    def test_score_range_minimum_and_maximum(self):
        minimum = evaluate_csrs(CSRSInput(
            predisposition_vasovagal=True,
            ed_diagnosis="vasovagal",
        ))
        maximum = evaluate_csrs(CSRSInput(
            history_heart_disease=True,
            systolic_bp=80,
            troponin_elevated=True,
            ecg_abnormal_axis=True,
            ecg_prolonged_qrs=True,
            ecg_prolonged_qtc=True,
            ed_diagnosis="cardiac",
        ))
        self.assertEqual(minimum.score, -3)
        self.assertEqual(maximum.score, 11)

    def test_validated_risk_category_boundaries(self):
        # Construct representative scores spanning each boundary.
        fixtures = [
            (CSRSInput(predisposition_vasovagal=True, ed_diagnosis="vasovagal"), -3, RiskTier.VERY_LOW, 0.2),
            (CSRSInput(predisposition_vasovagal=True), -1, RiskTier.LOW, 0.7),
            (CSRSInput(), 0, RiskTier.LOW, 0.7),
            (CSRSInput(history_heart_disease=True), 1, RiskTier.MEDIUM, 8.0),
            (CSRSInput(history_heart_disease=True, troponin_elevated=True), 3, RiskTier.MEDIUM, 8.0),
            (CSRSInput(troponin_elevated=True, ed_diagnosis="cardiac"), 4, RiskTier.HIGH, 19.2),
            (CSRSInput(history_heart_disease=True, troponin_elevated=True, ed_diagnosis="cardiac"), 5, RiskTier.HIGH, 19.2),
            (CSRSInput(systolic_bp=80, troponin_elevated=True, ed_diagnosis="cardiac"), 6, RiskTier.VERY_HIGH, 51.3),
        ]
        for inp, score, tier, rate in fixtures:
            with self.subTest(score=score):
                result = evaluate_csrs(inp)
                self.assertEqual(result.score, score)
                self.assertEqual(result.risk_tier, tier.value)
                self.assertEqual(result.validation_category_outcome_rate_pct, rate)

    def test_thresholds_are_strict(self):
        self.assertEqual(evaluate_csrs(CSRSInput(systolic_bp=90)).score, 0)
        self.assertEqual(evaluate_csrs(CSRSInput(systolic_bp=180)).score, 0)
        self.assertEqual(evaluate_csrs(CSRSInput(systolic_bp=89.9)).score, 2)
        self.assertEqual(evaluate_csrs(CSRSInput(systolic_bp=180.1)).score, 2)

    def test_invalid_inputs_raise(self):
        for value in [0, -1, float("nan"), float("inf"), "abc"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_csrs(CSRSInput(systolic_bp=value))
        with self.assertRaises(ValueError):
            evaluate_csrs(CSRSInput(ed_diagnosis="definitely-not-valid"))
        with self.assertRaises(ValueError):
            calculate_metrics(troponin_elevated="maybe")

    def test_alias_wrapper_does_not_override_explicit_false(self):
        result = calculate_metrics(predisposition_vasovagal=False, v1=True)
        self.assertEqual(result["score"], 0)

    def test_json_serializable(self):
        payload = evaluate_csrs(CSRSInput(patient_id="P-1")).to_dict()
        self.assertEqual(json.loads(json.dumps(payload))["patient_id"], "P-1")

    def test_batch_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "input.csv")
            target = os.path.join(tmp, "output.csv")
            with open(source, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["patient_id", "predisposition_vasovagal", "systolic_bp"])
                writer.writeheader()
                writer.writerow({"patient_id": "P1", "predisposition_vasovagal": "true", "systolic_bp": "120"})
                writer.writerow({"patient_id": "P2", "predisposition_vasovagal": "false", "systolic_bp": "80"})
            self.assertEqual(process_batch(source, target), 2)
            with open(target, encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["csrs_score"], "-1")
            self.assertEqual(rows[1]["csrs_score"], "2")

    def test_cli_json(self):
        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(cli.main(["evaluate", "--vasovagal-predisposition", "--json"]), 0)
            payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["score"], -1)
        self.assertEqual(payload["risk_tier"], "Low")

    def test_cli_invalid_value_returns_nonzero(self):
        with patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(cli.main(["evaluate", "--sbp", "0"]), 2)


if __name__ == "__main__":
    unittest.main()
