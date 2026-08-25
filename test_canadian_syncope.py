#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for Canadian Syncope Risk Score (CSRS) Engine
===========================================================================
Tests cover:
  - Component point assignment and additive score correctness
  - All risk tiers (Very Low, Low, Medium, High, Very High)
  - Blood pressure thresholds (<90, 90-180, >180 mmHg)
  - ECG features (abnormal axis, prolonged QRS, prolonged QTc)
  - ED presumptive diagnoses (vasovagal, cardiac, other/unknown)
  - Red flag symptom detection and alerting
  - Boundary conditions and invalid parameter exceptions
  - CCS angina classification modifiers
  - CSV batch processing and JSON serialization
  - CLI subcommand execution
"""

import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from canadian_syncope import (
    CSRSInput,
    CSRSResult,
    EDPresumptiveDiagnosis,
    RiskTier,
    calculate_metrics,
    evaluate_csrs,
    process_batch,
    CSRS_SCORE_TABLE,
)
import cli


class TestCanadianSyncopeRiskScore(unittest.TestCase):

    def test_baseline_neutral_presentation(self):
        """Neutral baseline: score 0, medium risk."""
        inp = CSRSInput(systolic_bp=120.0)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 0)
        self.assertEqual(res.risk_tier, RiskTier.MEDIUM.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 2.9, places=1)
        self.assertEqual(len(res.active_components), 0)

    def test_maximum_negative_score(self):
        """Vasovagal predisposition (-2) + ED dx vasovagal (-2) = -4 -> clamped to -3."""
        inp = CSRSInput(
            predisposition_vasovagal=True,
            ed_diagnosis=EDPresumptiveDiagnosis.VASOVAGAL,
            systolic_bp=115.0,
        )
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, -4)
        self.assertEqual(res.risk_tier, RiskTier.VERY_LOW.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 0.4, places=1)
        self.assertIn("predisposition_vasovagal", res.active_components)
        self.assertIn("ed_dx_vasovagal", res.active_components)

    def test_score_minus_one_low_risk(self):
        """Vasovagal predisposition (-2) + History of heart disease (+1) = -1."""
        inp = CSRSInput(
            predisposition_vasovagal=True,
            history_heart_disease=True,
            systolic_bp=125.0,
        )
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, -1)
        self.assertEqual(res.risk_tier, RiskTier.LOW.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 1.4, places=1)

    def test_score_plus_one_medium_risk(self):
        """History of heart disease only (+1) = +1 -> Medium risk."""
        inp = CSRSInput(history_heart_disease=True, systolic_bp=130.0)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 1)
        self.assertEqual(res.risk_tier, RiskTier.MEDIUM.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 5.3, places=1)

    def test_score_plus_two_high_risk(self):
        """Elevated troponin (+2) only = +2 -> High risk."""
        inp = CSRSInput(troponin_elevated=True, systolic_bp=120.0)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 2)
        self.assertEqual(res.risk_tier, RiskTier.HIGH.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 8.4, places=1)

    def test_score_plus_three_high_risk(self):
        """Troponin (+2) + History (+1) = +3 -> High risk."""
        inp = CSRSInput(
            history_heart_disease=True,
            troponin_elevated=True,
            systolic_bp=120.0,
        )
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 3)
        self.assertEqual(res.risk_tier, RiskTier.HIGH.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 13.2, places=1)

    def test_very_high_risk_score_four(self):
        """Troponin (+2) + Hypotension (+2) = +4 -> Very High risk."""
        inp = CSRSInput(
            troponin_elevated=True,
            systolic_bp=85.0,
        )
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 4)
        self.assertEqual(res.risk_tier, RiskTier.VERY_HIGH.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 21.4, places=1)

    def test_maximum_positive_score(self):
        """All positive components active -> score = 11."""
        inp = CSRSInput(
            predisposition_vasovagal=False,
            history_heart_disease=True,    # +1
            systolic_bp=80.0,              # +2 (<90)
            troponin_elevated=True,        # +2
            ecg_abnormal_axis=True,        # +1
            ecg_prolonged_qrs=True,        # +1
            ecg_prolonged_qtc=True,        # +2
            ed_diagnosis="cardiac",        # +2
        )
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 11)
        self.assertEqual(res.risk_tier, RiskTier.VERY_HIGH.value)
        self.assertAlmostEqual(res.sae_30day_probability_pct, 95.0, places=1)
        self.assertEqual(len(res.active_components), 7)

    def test_systolic_bp_hypertension_threshold(self):
        """Systolic BP > 180 mmHg adds +2."""
        inp = CSRSInput(systolic_bp=195.0)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 2)
        self.assertIn("systolic_bp_hypertension", res.active_components)
        self.assertEqual(res.active_components["systolic_bp_hypertension"], 2)

    def test_systolic_bp_normal_range_no_points(self):
        """Systolic BP within 90-180 mmHg gets 0 points."""
        for sbp in [90.0, 120.0, 150.0, 180.0]:
            inp = CSRSInput(systolic_bp=sbp)
            res = evaluate_csrs(inp)
            self.assertEqual(res.score, 0)

    def test_ecg_abnormal_axis(self):
        inp = CSRSInput(ecg_abnormal_axis=True)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 1)
        self.assertIn("ecg_abnormal_axis", res.active_components)

    def test_ecg_prolonged_qrs(self):
        inp = CSRSInput(ecg_prolonged_qrs=True)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 1)
        self.assertIn("ecg_prolonged_qrs", res.active_components)

    def test_ecg_prolonged_qtc(self):
        inp = CSRSInput(ecg_prolonged_qtc=True)
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 2)
        self.assertIn("ecg_prolonged_qtc", res.active_components)

    def test_red_flag_exertional_syncope(self):
        inp = CSRSInput(exertional_syncope=True)
        res = evaluate_csrs(inp)
        self.assertTrue(any("Exertional syncope" in rf for rf in res.red_flag_alerts))

    def test_red_flag_supine_syncope(self):
        inp = CSRSInput(supine_syncope=True)
        res = evaluate_csrs(inp)
        self.assertTrue(any("supine" in rf for rf in res.red_flag_alerts))

    def test_red_flag_palpitations(self):
        inp = CSRSInput(palpitations_preceding=True)
        res = evaluate_csrs(inp)
        self.assertTrue(any("Palpitations" in rf for rf in res.red_flag_alerts))

    def test_red_flag_family_history_scd(self):
        inp = CSRSInput(family_history_sudden_death=True)
        res = evaluate_csrs(inp)
        self.assertTrue(any("sudden cardiac death" in rf for rf in res.red_flag_alerts))

    def test_severe_bradycardia_alert(self):
        inp = CSRSInput(heart_rate_bpm=38.0)
        res = evaluate_csrs(inp)
        self.assertTrue(any("Severe bradycardia" in rf for rf in res.red_flag_alerts))

    def test_tachycardia_alert(self):
        inp = CSRSInput(heart_rate_bpm=135.0)
        res = evaluate_csrs(inp)
        self.assertTrue(any("Tachycardia" in rf for rf in res.red_flag_alerts))

    def test_ccs_angina_modifier(self):
        inp = CSRSInput(history_heart_disease=True, troponin_elevated=True, ccs_angina_class="class_IV")
        res = evaluate_csrs(inp)
        self.assertEqual(res.score, 3)
        self.assertAlmostEqual(res.ccs_adjusted_score, 3.0 * 1.6, places=2)

    def test_out_of_bounds_blood_pressure_low(self):
        inp = CSRSInput(systolic_bp=30.0)
        with self.assertRaises(ValueError):
            evaluate_csrs(inp)

    def test_out_of_bounds_blood_pressure_high(self):
        inp = CSRSInput(systolic_bp=320.0)
        with self.assertRaises(ValueError):
            evaluate_csrs(inp)

    def test_calculate_metrics_wrapper_string_inputs(self):
        res = calculate_metrics(
            predisposition_vasovagal="yes",
            cardiac_history="no",
            systolic_bp="110",
            troponin_elevated="0",
        )
        self.assertEqual(res["score"], -2)
        self.assertEqual(res["risk_tier"], "Very Low")
        self.assertEqual(res["tool"], "canadian-syncope-risk-score")

    def test_calculate_metrics_wrapper_aliases(self):
        res = calculate_metrics(
            v1="1",   # predisposition
            v2="1",   # cardiac history
            v3="85",  # hypotension
            v4="1",   # troponin
        )
        # -2 + 1 + 2 + 2 = 3
        self.assertEqual(res["score"], 3)
        self.assertEqual(res["risk_tier"], "High")

    def test_to_dict_and_json_serializability(self):
        inp = CSRSInput(
            patient_id="SYN-991",
            predisposition_vasovagal=True,
            ed_diagnosis="vasovagal",
        )
        res = evaluate_csrs(inp)
        d = res.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["patient_id"], "SYN-991")
        self.assertEqual(deserialized["risk_tier"], "Very Low")

    def test_batch_processing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_csv = os.path.join(tmpdir, "syncope_input.csv")
            out_csv = os.path.join(tmpdir, "syncope_output.csv")

            with open(in_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["patient_id", "predisposition_vasovagal", "history_heart_disease", "systolic_bp", "troponin_elevated"])
                writer.writeheader()
                writer.writerow({"patient_id": "P001", "predisposition_vasovagal": "true", "history_heart_disease": "false", "systolic_bp": "120", "troponin_elevated": "false"})
                writer.writerow({"patient_id": "P002", "predisposition_vasovagal": "false", "history_heart_disease": "true", "systolic_bp": "82", "troponin_elevated": "true"})

            count = process_batch(in_csv, out_csv)
            self.assertEqual(count, 2)
            self.assertTrue(os.path.exists(out_csv))

            with open(out_csv, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                self.assertEqual(len(reader), 2)
                self.assertEqual(reader[0]["patient_id"], "P001")
                self.assertEqual(reader[0]["risk_tier"], "Very Low")
                self.assertEqual(reader[1]["patient_id"], "P002")
                self.assertEqual(reader[1]["risk_tier"], "Very High")

    def test_cli_evaluate_command(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["evaluate", "--patient-id", "CLI-01", "--cardiac-history", "--sbp", "85", "--troponin-elevated"])
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            self.assertIn("CSRS Total Score", output)
            self.assertIn("CLI-01", output)

    def test_cli_evaluate_json_flag(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["evaluate", "--cardiac-history", "--json"])
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            data = json.loads(output)
            self.assertEqual(data["score"], 1)
            self.assertEqual(data["risk_tier"], "Medium")

    def test_cli_table_command(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["table"])
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            self.assertIn("30d SAE %", output)
            self.assertIn("Very High", output)


if __name__ == "__main__":
    unittest.main()
