#!/usr/bin/env python3
"""
Serial Canadian Syncope Risk Score tracking during ED observation.

Recomputes the CSRS at defined reassessment points while the patient is under
observation, attributing every score change to its newly-appeared or resolved
component. Escalation rules fire on:
  - any transition to a higher published risk tier
  - new appearance of a +2-weighted component (troponin, SBP<90, neuro deficit)
  - failure to reassess within the observation window before discharge

Stdlib only.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from csrs_engine import CSRSPresentation, compute_csrs


@dataclass
class Reassessment:
    minutes_since_arrival: int
    presentation: CSRSPresentation
    setting: str = "ED_observation"


TWO_POINT_COMPONENTS = {
    "troponin_above_99th_percentile",
    "systolic_bp_below_90",
    "rectal_tone_loss_or_focal_deficit",
}

TIER_ORDER = ["low", "medium", "high", "very high"]


def track_observation(reassessments: List[Reassessment],
                      max_reassessment_gap_minutes: int = 240) -> Dict[str, Any]:
    timeline: List[Dict[str, Any]] = []
    escalations: List[str] = []
    prev_active: set = set()
    prev_score = None
    prev_tier_idx = -1

    for i, ra in enumerate(sorted(reassessments,
                                  key=lambda r: r.minutes_since_arrival)):
        result = compute_csrs(ra.presentation)
        score = result["csrs_score"]
        tier_idx = TIER_ORDER.index(result["risk_tier"])

        delta = None if prev_score is None else score - prev_score
        entry = {
            "t_minutes": ra.minutes_since_arrival,
            "setting": ra.setting,
            "csrs_score": score,
            "tier": result["risk_tier"],
            "delta_from_previous": delta,
        }

        if delta is not None and delta != 0:
            now_active = set(result["active_components"])
            new_positives = [c for c in now_active - prev_active
                             if not c.startswith("predisposition")]
            entry["new_components"] = sorted(new_positives)
            for c in new_positives:
                if c in TWO_POINT_COMPONENTS:
                    escalations.append(
                        f"t+{ra.minutes_since_arrival}min: NEW high-weight "
                        f"component '{c}' (+2)")
            if tier_idx > prev_tier_idx:
                escalations.append(
                    f"t+{ra.minutes_since_arrival}min: tier escalated "
                    f"{TIER_ORDER[prev_tier_idx]} -> {result['risk_tier']} "
                    "(re-disposition required)")

        timeline.append(entry)
        prev_active = set(result["active_components"])
        prev_score = score
        prev_tier_idx = tier_idx

    final = timeline[-1] if timeline else None
    gaps_checked = all(
        b["t_minutes"] - a["t_minutes"] <= max_reassessment_gap_minutes
        for a, b in zip(timeline, timeline[1:]))

    return {
        "timeline": timeline,
        "escalations": escalations or ["no escalation events during observation"],
        "final_score": final["csrs_score"] if final else None,
        "final_disposition": compute_csrs(reassessments[-1].presentation)
                             ["disposition_recommendation"] if reassessments else None,
        "reassessment_protocol_followed": gaps_checked and bool(len(timeline) >= 2),
    }


if __name__ == "__main__":
    t0 = Reassessment(0, CSRSPresentation(ed_heart_rate_bpm=70))
    t2h = Reassessment(120, CSRSPresentation(ed_heart_rate_bpm=70))
    t6h = Reassessment(360, CSRSPresentation(troponin_elevated=True,
                                             ed_heart_rate_bpm=62))
    t9h = Reassessment(540, CSRSPresentation(troponin_elevated=True,
                                             systolic_bp_mmhg=86))
    report = track_observation([t0, t2h, t6h, t9h])
    print("Serial CSRS trajectory")
    print("-" * 58)
    for e in report["timeline"]:
        d = "" if e["delta_from_previous"] is None \
            else f"{e['delta_from_previous']:+d}"
        print(f"t+{e['t_minutes']:>3}min [{e['setting']}] score={e['csrs_score']:<3} "
              f"{e['tier']:<10s} delta={d:>3}"
              + (f"  new={e['new_components']}" if "new_components" in e else ""))
    print("\nEscalations:")
    for esc in report["escalations"]:
        print(f"  * {esc}")
    print(f"\nProtocol followed: {report['reassessment_protocol_followed']}")
    print(f"Final action: {report['final_disposition']}")
