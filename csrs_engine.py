"""Compatibility layer for the canonical :mod:`canadian_syncope` engine.

Older repository versions exposed a second, clinically inconsistent CSRS engine.
This module now delegates to the validated nine-component implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from canadian_syncope import CSRSInput, evaluate_csrs


@dataclass(frozen=True)
class CSRSPresentation:
    predisposition_vasovagal: bool = False
    cardiac_history: bool = False
    systolic_bp_mmhg: float = 120.0
    troponin_elevated: bool = False
    q_axis_abnormal: bool = False
    qrs_duration_over_130ms: bool = False
    qtc_over_480ms: bool = False
    ed_diagnosis: str = "unknown"


def compute_csrs(p: CSRSPresentation) -> Dict[str, Any]:
    result = evaluate_csrs(CSRSInput(
        predisposition_vasovagal=p.predisposition_vasovagal,
        history_heart_disease=p.cardiac_history,
        systolic_bp=p.systolic_bp_mmhg,
        troponin_elevated=p.troponin_elevated,
        ecg_abnormal_axis=p.q_axis_abnormal,
        ecg_prolonged_qrs=p.qrs_duration_over_130ms,
        ecg_prolonged_qtc=p.qtc_over_480ms,
        ed_diagnosis=p.ed_diagnosis,
    ))
    return {
        "csrs_score": result.score,
        "active_components": result.active_components,
        "risk_tier": result.risk_tier.lower(),
        "validation_category_outcome_rate_pct": result.validation_category_outcome_rate_pct,
        "disposition_recommendation": result.management_context,
        "score_range_note": "validated range -3 to 11",
    }
