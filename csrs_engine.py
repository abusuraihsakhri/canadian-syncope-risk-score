#!/usr/bin/env python3
"""
Canadian Syncope Risk Score (CSRS) engine.

Published predictor weights (Thiruganasambandamoorthy et al., Ann Emerg Med /
JAMA Netw Open validation cohorts) for 30-day serious adverse cardiovascular
events after emergency-department syncope:

    Predisposition to vasovagal symptoms            -1
    History of cardiovascular disease               +1
    Systolic BP < 90 mmHg                           +2   (90-140 reference = 0)
    Troponin above local 99th percentile            +2
    Abnormal Q-wave axis (Q waves in III/aVF)       +1
    Bradycardia in ED (HR < 50 bpm)                 +1
    Rectal tone loss or focal neurological deficit  +2

Risk tiers map to published 30-day serious-adverse-event rates:
    <= -1  low        ~0.7%
     0.. 2 medium     ~2.4%
     3.. 5 high       ~6.9%
    >= 6   very high ~25.8%

Disposition guidance: score <= -1 -> ED discharge with primary-care follow-up;
0-2 -> observation unit / shared decision-making; >= 3 -> admission with
telemetry and cardiology involvement.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CSRSPresentation:
    predisposition_vasovagal: bool = False
    cardiac_history: bool = False          # CAD, arrhythmia, CHF, valve disease
    systolic_bp_mmhg: float = 120.0
    troponin_elevated: bool = False
    q_axis_abnormal: bool = False          # Q waves in inferior leads III/aVF
    ed_heart_rate_bpm: float = 75.0
    rectal_tone_loss_or_focal_deficit: bool = False


COMPONENT_WEIGHTS = {
    "predisposition_to_vasovagal_symptoms": -1,
    "history_of_cardiovascular_disease": +1,
    "systolic_bp_below_90": +2,
    "troponin_above_99th_percentile": +2,
    "abnormal_q_axis": +1,
    "bradycardia_in_ed": +1,
    "rectal_tone_loss_or_focal_deficit": +2,
}

TIER_TABLE = [
    # (score_min_inclusive, score_max_inclusive, label, published_rate)
    (-99, -1, "low", 0.007),
    (0, 2, "medium", 0.024),
    (3, 5, "high", 0.069),
    (6, 99, "very high", 0.258),
]


def active_components(p: CSRSPresentation) -> List[str]:
    comps = []
    if p.predisposition_vasovagal:
        comps.append("predisposition_to_vasovagal_symptoms")
    if p.cardiac_history:
        comps.append("history_of_cardiovascular_disease")
    if p.systolic_bp_mmhg < 90:
        comps.append("systolic_bp_below_90")
    if p.troponin_elevated:
        comps.append("troponin_above_99th_percentile")
    if p.q_axis_abnormal:
        comps.append("abnormal_q_axis")
    if p.ed_heart_rate_bpm < 50:
        comps.append("bradycardia_in_ed")
    if p.rectal_tone_loss_or_focal_deficit:
        comps.append("rectal_tone_loss_or_focal_deficit")
    return comps


def compute_csrs(p: CSRSPresentation) -> Dict[str, Any]:
    """Score a presentation and return tier, event probability, disposition."""
    active = active_components(p)
    score = sum(COMPONENT_WEIGHTS[c] for c in active)

    tier_label, rate = next(
        ((lbl, r) for lo, hi, lbl, r in TIER_TABLE if lo <= score <= hi),
        ("medium", 0.024))

    if score <= -1:
        disposition = ("ED discharge with primary care follow-up; no further "
                       "testing indicated for most patients")
    elif score <= 2:
        disposition = ("Observation unit or shared decision-making; consider "
                       "prolonged rhythm monitoring before discharge")
    else:
        disposition = ("Admit with telemetry; expedited cardiology evaluation "
                       "and echocardiography")

    return {
        "csrs_score": score,
        "active_components": {c: COMPONENT_WEIGHTS[c] for c in active},
        "risk_tier": tier_label,
        "published_30day_sae_rate": rate,
        "disposition_recommendation": disposition,
        "score_range_note": "theoretical range -1 to +11 with this component set",
    }


if __name__ == "__main__":
    cases = [
        ("classic vasovagal", CSRSPresentation(predisposition_vasovagal=True)),
        ("cardiac history only",
         CSRSPresentation(cardiac_history=True, ed_heart_rate_bpm=78)),
        ("high risk", CSRSPresentation(cardiac_history=True,
                                       systolic_bp_mmhg=85,
                                       troponin_elevated=True,
                                       ed_heart_rate_bpm=44)),
        ("neuro deficit", CSRSPresentation(rectal_tone_loss_or_focal_deficit=True)),
        ("mixed very-high",
         CSRSPresentation(troponin_elevated=True, q_axis_abnormal=True,
                          systolic_bp_mmhg=88, ed_heart_rate_bpm=48,
                          cardiac_history=True)),
    ]
    print(f"{'case':20s} {'score':>5} {'tier':10s} {'30d SAE':>8}")
    print("-" * 50)
    for name, pres in cases:
        r = compute_csrs(pres)
        print(f"{name:20s} {r['csrs_score']:>5} {r['risk_tier']:10s} "
              f"{r['published_30day_sae_rate']:>7.1%}")
    print("\nHigh-risk disposition:")
    print(compute_csrs(cases[4][1])["disposition_recommendation"])
