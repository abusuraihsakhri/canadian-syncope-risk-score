#!/usr/bin/env python3
"""Command-line interface for the Canadian Syncope Risk Score."""

from __future__ import annotations

import argparse
import json
import sys

from canadian_syncope import CSRSInput, RISK_CATEGORIES, evaluate_csrs, process_batch


def format_report(result: dict) -> str:
    lines = [
        "Canadian Syncope Risk Score",
        "=" * 50,
        f"Patient ID: {result.get('patient_id') or 'N/A'}",
        f"Score: {result['score']:+d}",
        f"Risk category: {result['risk_tier']}",
        (
            "Observed 30-day serious-outcome rate in validation category: "
            f"{result['validation_category_outcome_rate_pct']:.1f}%"
        ),
        "",
        "Active score components:",
    ]
    components = result.get("active_components", {})
    if components:
        lines.extend(f"  - {name}: {points:+d}" for name, points in components.items())
    else:
        lines.append("  - none")
    lines.extend([
        "",
        result["management_context"],
        "",
        "Educational/research implementation; not a substitute for clinical judgment.",
    ])
    return "\n".join(lines)


def interactive_wizard() -> CSRSInput:
    print("\nCanadian Syncope Risk Score interactive assessment")
    patient_id = input("Patient ID (optional): ").strip() or None

    def ask_bool(prompt: str) -> bool:
        return input(f"{prompt} (y/n): ").strip().lower() in {"y", "yes", "1", "true"}

    def ask_float(prompt: str, default: float) -> float:
        raw = input(f"{prompt} [{default:g}]: ").strip()
        return default if not raw else float(raw)

    predisposition = ask_bool("Predisposition to vasovagal symptoms")
    cardiac_history = ask_bool("History of heart disease")
    sbp = ask_float("Any ED systolic BP reading to evaluate (mm Hg)", 120.0)
    troponin = ask_bool("Troponin above the local 99th percentile")
    axis = ask_bool("QRS axis < -30° or > 100°")
    qrs = ask_bool("QRS duration > 130 ms")
    qtc = ask_bool("QTc > 480 ms")
    print("ED diagnosis: 1=vasovagal, 2=cardiac, 3=other/unknown")
    diagnosis = {"1": "vasovagal", "2": "cardiac", "3": "unknown"}.get(
        input("Selection [3]: ").strip() or "3", "unknown"
    )
    return CSRSInput(
        patient_id=patient_id,
        predisposition_vasovagal=predisposition,
        history_heart_disease=cardiac_history,
        systolic_bp=sbp,
        troponin_elevated=troponin,
        ecg_abnormal_axis=axis,
        ecg_prolonged_qrs=qrs,
        ecg_prolonged_qtc=qtc,
        ed_diagnosis=diagnosis,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Canadian Syncope Risk Score calculator")
    subparsers = parser.add_subparsers(dest="command")

    single = subparsers.add_parser("evaluate", help="Evaluate one presentation")
    single.add_argument("--patient-id")
    single.add_argument("--vasovagal-predisposition", action="store_true")
    single.add_argument("--cardiac-history", action="store_true")
    single.add_argument("--sbp", type=float, default=120.0)
    single.add_argument("--troponin-elevated", action="store_true")
    single.add_argument("--ecg-axis-abnormal", action="store_true")
    single.add_argument("--ecg-qrs-prolonged", action="store_true", help="QRS duration >130 ms")
    single.add_argument("--ecg-qtc-prolonged", action="store_true", help="QTc >480 ms")
    single.add_argument(
        "--ed-diagnosis", choices=["vasovagal", "cardiac", "other", "unknown"], default="unknown"
    )
    single.add_argument("--json", action="store_true")

    interactive = subparsers.add_parser("interactive", help="Interactive assessment")
    interactive.add_argument("--json", action="store_true")

    batch = subparsers.add_parser("batch", help="Process a CSV cohort")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="csrs_batch_results.csv")

    subparsers.add_parser("table", help="Show validated risk categories")
    args = parser.parse_args(argv)

    try:
        if args.command == "evaluate":
            result = evaluate_csrs(CSRSInput(
                patient_id=args.patient_id,
                predisposition_vasovagal=args.vasovagal_predisposition,
                history_heart_disease=args.cardiac_history,
                systolic_bp=args.sbp,
                troponin_elevated=args.troponin_elevated,
                ecg_abnormal_axis=args.ecg_axis_abnormal,
                ecg_prolonged_qrs=args.ecg_qrs_prolonged,
                ecg_prolonged_qtc=args.ecg_qtc_prolonged,
                ed_diagnosis=args.ed_diagnosis,
            ))
            print(json.dumps(result.to_dict(), indent=2) if args.json else format_report(result.to_dict()))
            return 0
        if args.command == "interactive":
            result = evaluate_csrs(interactive_wizard())
            print(json.dumps(result.to_dict(), indent=2) if args.json else format_report(result.to_dict()))
            return 0
        if args.command == "batch":
            count = process_batch(args.input, args.output)
            print(f"Processed {count} records into '{args.output}'.")
            return 0
        if args.command == "table":
            print("Score range | Risk category | Validation 30-day serious outcome rate")
            print("-" * 68)
            for lo, hi, tier, rate in RISK_CATEGORIES:
                print(f"{lo:+d} to {hi:+d} | {tier.value:<11} | {rate:.1f}%")
            return 0
        parser.print_help()
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
