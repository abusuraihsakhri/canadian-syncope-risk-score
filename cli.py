#!/usr/bin/env python3
"""
Canadian Syncope Risk Score (CSRS) CLI
======================================
Command line interface for evaluating 30-day serious adverse cardiovascular event risks
in emergency department syncope presentations.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from canadian_syncope import (
    CSRSInput,
    EDPresumptiveDiagnosis,
    calculate_metrics,
    evaluate_csrs,
    process_batch,
)


def format_table_report(result: dict) -> str:
    """Format single result into an ASCII table."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"  CANADIAN SYNCOPE RISK SCORE (CSRS) CLINICAL EVALUATION")
    lines.append("=" * 72)
    lines.append(f"  Patient ID            : {result.get('patient_id') or 'N/A'}")
    lines.append(f"  CSRS Total Score      : {result['score']:+d}")
    lines.append(f"  Risk Category         : {result['risk_tier']}")
    lines.append(f"  30-Day SAE Probability: {result['sae_30day_probability_pct']:.1f}% (95% CI: {result['sae_95ci_pct'][0]:.1f}% - {result['sae_95ci_pct'][1]:.1f}%)")
    lines.append(f"  Arrhythmic Event Risk : {result['arrhythmic_risk_probability_pct']:.1f}%")
    lines.append(f"  Non-Arrhythmic Risk   : {result['non_arrhythmic_risk_probability_pct']:.1f}%")
    lines.append("-" * 72)
    lines.append(f"  Active Components:")
    comps = result.get("active_components", {})
    if comps:
        for k, v in comps.items():
            lines.append(f"    - {k:35s}: {v:+d} pts")
    else:
        lines.append("    (No points assigned / baseline reference)")
    lines.append("-" * 72)
    lines.append(f"  Disposition Guidance  : {result['disposition_recommendation']}")
    lines.append(f"  Monitoring Guidance   : {result['monitoring_recommendation']}")
    if result.get("ccs_adjusted_score") is not None:
        lines.append(f"  CCS-Adjusted Score    : {result['ccs_adjusted_score']:.2f}")
    if result.get("red_flag_alerts"):
        lines.append("-" * 72)
        lines.append("  RED FLAG WARNINGS:")
        for alert in result["red_flag_alerts"]:
            lines.append(f"    * {alert}")
    lines.append("=" * 72)
    return "\n".join(lines)


def interactive_wizard() -> CSRSInput:
    """Run interactive question prompt to gather clinical variables."""
    print("\n--- Canadian Syncope Risk Score Interactive Assessment ---")
    patient_id = input("Patient ID / MRN (optional): ").strip() or None

    def ask_bool(prompt: str) -> bool:
        resp = input(f"{prompt} (y/n): ").strip().lower()
        return resp in ("y", "yes", "true", "1")

    def ask_float(prompt: str, default: float) -> float:
        resp = input(f"{prompt} [{default}]: ").strip()
        if not resp:
            return default
        try:
            return float(resp)
        except ValueError:
            print(f"Invalid number, defaulting to {default}")
            return default

    predisposition = ask_bool("1. Predisposition to vasovagal symptoms (warm place, prolonged standing, fear/pain)?")
    cardiac_history = ask_bool("2. History of heart disease (CAD, CHF, arrhythmia, valve)?")
    sbp = ask_float("3. Systolic BP on triage (mmHg)", 120.0)
    troponin = ask_bool("4. Elevated cardiac troponin (>99th percentile URL)?")
    axis = ask_bool("5. ECG abnormal axis (<-30 deg or >+100 deg)?")
    qrs = ask_bool("6. ECG prolonged QRS duration (>120 ms)?")
    qtc = ask_bool("7. ECG prolonged corrected QT interval (QTc > 480 ms)?")
    
    print("8. ED presumptive diagnosis:")
    print("   [1] Vasovagal syncope (-2)")
    print("   [2] Cardiac syncope (+2)")
    print("   [3] Other / Unknown / Unspecified (0)")
    dx_choice = input("   Select (1/2/3) [3]: ").strip()
    dx_map = {"1": "vasovagal", "2": "cardiac", "3": "unknown"}
    ed_dx = dx_map.get(dx_choice, "unknown")

    exertional = ask_bool("9. Exertional syncope (occurred during physical effort)?")
    supine = ask_bool("10. Supine syncope (occurred while lying down)?")
    palpitations = ask_bool("11. Palpitations immediately preceding syncope?")

    return CSRSInput(
        patient_id=patient_id,
        predisposition_vasovagal=predisposition,
        history_heart_disease=cardiac_history,
        systolic_bp=sbp,
        troponin_elevated=troponin,
        ecg_abnormal_axis=axis,
        ecg_prolonged_qrs=qrs,
        ecg_prolonged_qtc=qtc,
        ed_diagnosis=ed_dx,
        exertional_syncope=exertional,
        supine_syncope=supine,
        palpitations_preceding=palpitations,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="canadian-syncope",
        description="Canadian Syncope Risk Score (CSRS) Decision Support Tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Evaluate single case via arguments
    single_parser = subparsers.add_parser("evaluate", help="Evaluate a single syncope presentation")
    single_parser.add_argument("--patient-id", type=str, default=None, help="Patient identifier")
    single_parser.add_argument("--vasovagal-predisposition", action="store_true", help="Predisposition to vasovagal syncope (-2)")
    single_parser.add_argument("--cardiac-history", action="store_true", help="History of heart disease (+1)")
    single_parser.add_argument("--sbp", type=float, default=120.0, help="Systolic blood pressure in mmHg (<90 or >180 adds +2)")
    single_parser.add_argument("--troponin-elevated", action="store_true", help="Troponin above 99th percentile (+2)")
    single_parser.add_argument("--ecg-axis-abnormal", action="store_true", help="ECG QRS axis <-30 or >+100 deg (+1)")
    single_parser.add_argument("--ecg-qrs-prolonged", action="store_true", help="ECG QRS duration > 120 ms (+1)")
    single_parser.add_argument("--ecg-qtc-prolonged", action="store_true", help="ECG QTc > 480 ms (+2)")
    single_parser.add_argument("--ed-diagnosis", choices=["vasovagal", "cardiac", "other", "unknown"], default="unknown", help="ED presumptive diagnosis")
    single_parser.add_argument("--exertional", action="store_true", help="Syncope occurred during exertion")
    single_parser.add_argument("--supine", action="store_true", help="Syncope occurred in supine position")
    single_parser.add_argument("--palpitations", action="store_true", help="Preceding palpitations")
    single_parser.add_argument("--family-history-scd", action="store_true", help="Family history of sudden cardiac death")
    single_parser.add_argument("--ccs-class", choices=["class_I", "class_II", "class_III", "class_IV"], default=None, help="CCS angina classification")
    single_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # Interactive mode
    interactive_parser = subparsers.add_parser("interactive", help="Interactive question wizard")
    interactive_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # Batch processing
    batch_parser = subparsers.add_parser("batch", help="Batch process a CSV file of presentations")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch_parser.add_argument("-o", "--output", default="csrs_batch_results.csv", help="Output CSV path")

    # Score lookup table
    table_parser = subparsers.add_parser("table", help="Print the validated CSRS score and risk probability table")

    args = parser.parse_args(argv)

    if args.command == "evaluate":
        inp = CSRSInput(
            patient_id=args.patient_id,
            predisposition_vasovagal=args.vasovagal_predisposition,
            history_heart_disease=args.cardiac_history,
            systolic_bp=args.sbp,
            troponin_elevated=args.troponin_elevated,
            ecg_abnormal_axis=args.ecg_axis_abnormal,
            ecg_prolonged_qrs=args.ecg_qrs_prolonged,
            ecg_prolonged_qtc=args.ecg_qtc_prolonged,
            ed_diagnosis=args.ed_diagnosis,
            exertional_syncope=args.exertional,
            supine_syncope=args.supine,
            palpitations_preceding=args.palpitations,
            family_history_sudden_death=args.family_history_scd,
            ccs_angina_class=args.ccs_class,
        )
        res = evaluate_csrs(inp)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(format_table_report(res.to_dict()))
        return 0

    elif args.command == "interactive":
        inp = interactive_wizard()
        res = evaluate_csrs(inp)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(format_table_report(res.to_dict()))
        return 0

    elif args.command == "batch":
        count = process_batch(args.input, args.output)
        print(f"Successfully processed {count} records into '{args.output}'.")
        return 0

    elif args.command == "table":
        from canadian_syncope import CSRS_SCORE_TABLE
        print("=" * 64)
        print(f"{'Score':>6} | {'Risk Tier':<10} | {'30d SAE %':>10} | {'95% CI':>15} | {'Arrhythmic %':>12}")
        print("=" * 64)
        for sc, (rate, lo, hi, arr, non_arr) in CSRS_SCORE_TABLE.items():
            if sc <= -2:
                tier = "Very Low"
            elif sc == -1:
                tier = "Low"
            elif sc in (0, 1):
                tier = "Medium"
            elif sc in (2, 3):
                tier = "High"
            else:
                tier = "Very High"
            print(f"{sc:+6d} | {tier:<10} | {rate:>9.1f}% | {lo:>6.1f}% - {hi:>5.1f}% | {arr:>11.1f}%")
        print("=" * 64)
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
