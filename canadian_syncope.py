#!/usr/bin/env python3
"""Canadian Syncope Risk Score (CSRS) calculator.

Implements the nine-component score published by Thiruganasambandamoorthy et al.
and prospectively validated in JAMA Internal Medicine (2020).

This module calculates the score and its validated risk category. The reported
30-day outcome rate is the *observed category-level rate* from the 2020
validation cohort, not an individualized probability estimate.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class RiskTier(str, Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class EDPresumptiveDiagnosis(str, Enum):
    VASOVAGAL = "vasovagal"
    CARDIAC = "cardiac"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CSRSInput:
    """Inputs used by the validated Canadian Syncope Risk Score."""

    predisposition_vasovagal: bool = False
    history_heart_disease: bool = False
    systolic_bp: float = 120.0
    troponin_elevated: bool = False
    ecg_abnormal_axis: bool = False
    ecg_prolonged_qrs: bool = False
    ecg_prolonged_qtc: bool = False
    ed_diagnosis: Union[EDPresumptiveDiagnosis, str] = EDPresumptiveDiagnosis.UNKNOWN
    patient_id: Optional[str] = None


@dataclass(frozen=True)
class CSRSResult:
    """Result of a Canadian Syncope Risk Score calculation."""

    score: int
    risk_tier: str
    validation_category_outcome_rate_pct: float
    active_components: Dict[str, int]
    management_context: str
    patient_id: Optional[str] = None
    evidence_note: str = (
        "Observed 30-day serious-outcome rate for this risk category in the "
        "2020 prospective multicenter validation cohort; not an individualized probability."
    )
    # Compatibility fields retained without inventing unsupported precision.
    sae_30day_probability_pct: float = 0.0
    sae_95ci_pct: Optional[List[float]] = None
    arrhythmic_risk_probability_pct: Optional[float] = None
    non_arrhythmic_risk_probability_pct: Optional[float] = None
    disposition_recommendation: str = ""
    monitoring_recommendation: str = (
        "The CSRS score alone does not encode a patient-specific monitoring protocol."
    )
    red_flag_alerts: List[str] = field(default_factory=list)
    ccs_adjusted_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "score": self.score,
            "risk_tier": self.risk_tier,
            "validation_category_outcome_rate_pct": self.validation_category_outcome_rate_pct,
            "evidence_note": self.evidence_note,
            "active_components": dict(self.active_components),
            "management_context": self.management_context,
            "sae_30day_probability_pct": self.sae_30day_probability_pct,
            "sae_95ci_pct": self.sae_95ci_pct,
            "arrhythmic_risk_probability_pct": self.arrhythmic_risk_probability_pct,
            "non_arrhythmic_risk_probability_pct": self.non_arrhythmic_risk_probability_pct,
            "disposition_recommendation": self.disposition_recommendation,
            "monitoring_recommendation": self.monitoring_recommendation,
            "red_flag_alerts": list(self.red_flag_alerts),
            "ccs_adjusted_score": self.ccs_adjusted_score,
        }


# Published score weights (JAMA Intern Med. 2020;180(5):737-744, Table 1).
COMPONENT_WEIGHTS: Dict[str, int] = {
    "predisposition_vasovagal": -1,
    "history_heart_disease": 1,
    "abnormal_systolic_bp": 2,
    "troponin_elevated": 2,
    "ecg_abnormal_axis": 1,
    "ecg_prolonged_qrs": 1,
    "ecg_prolonged_qtc": 2,
    "ed_dx_vasovagal": -2,
    "ed_dx_cardiac": 2,
}

# Risk strata and observed 30-day serious-outcome rates in the 2020 validation cohort.
# (score_min, score_max, tier, observed_rate_pct)
RISK_CATEGORIES = (
    (-3, -2, RiskTier.VERY_LOW, 0.2),
    (-1, 0, RiskTier.LOW, 0.7),
    (1, 3, RiskTier.MEDIUM, 8.0),
    (4, 5, RiskTier.HIGH, 19.2),
    (6, 11, RiskTier.VERY_HIGH, 51.3),
)

# Backward-compatible mapping. Values are category-level observed rates.
CSRS_SCORE_TABLE: Dict[int, float] = {
    score: rate
    for lo, hi, _tier, rate in RISK_CATEGORIES
    for score in range(lo, hi + 1)
}


def _normalize_ed_diagnosis(value: Union[EDPresumptiveDiagnosis, str]) -> str:
    if isinstance(value, EDPresumptiveDiagnosis):
        return value.value
    normalized = str(value).strip().lower()
    allowed = {item.value for item in EDPresumptiveDiagnosis}
    if normalized not in allowed:
        raise ValueError(
            f"Unsupported ED diagnosis {value!r}; expected one of {sorted(allowed)}."
        )
    return normalized


def _validate_systolic_bp(value: float) -> float:
    try:
        sbp = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Systolic BP must be numeric, got {value!r}.") from exc
    if not math.isfinite(sbp) or sbp <= 0:
        raise ValueError("Systolic BP must be a finite positive number.")
    return sbp


def _risk_category(score: int) -> tuple[RiskTier, float]:
    for lo, hi, tier, rate in RISK_CATEGORIES:
        if lo <= score <= hi:
            return tier, rate
    raise ValueError(f"CSRS score {score} is outside the validated range -3 to 11.")


def _management_context(tier: RiskTier) -> str:
    if tier in (RiskTier.VERY_LOW, RiskTier.LOW):
        return (
            "In the 2020 validation report, very-low- and low-risk patients could "
            "generally be discharged after the ED evaluation when no serious cause "
            "was identified. Apply clinical judgment and local protocols."
        )
    if tier is RiskTier.MEDIUM:
        return (
            "The 2020 validation report describes shared decision-making regarding "
            "disposition for medium-risk patients. Apply clinical judgment and local protocols."
        )
    return (
        "The 2020 validation report describes a short course of hospitalization as a "
        "reasonable option for higher-risk patients. Apply clinical judgment and local protocols."
    )


def evaluate_csrs(inp: CSRSInput) -> CSRSResult:
    """Calculate the validated nine-component Canadian Syncope Risk Score."""

    sbp = _validate_systolic_bp(inp.systolic_bp)
    ed_dx = _normalize_ed_diagnosis(inp.ed_diagnosis)

    components: Dict[str, int] = {}
    if inp.predisposition_vasovagal:
        components["predisposition_vasovagal"] = -1
    if inp.history_heart_disease:
        components["history_heart_disease"] = 1
    if sbp < 90.0 or sbp > 180.0:
        components["abnormal_systolic_bp"] = 2
    if inp.troponin_elevated:
        components["troponin_elevated"] = 2
    if inp.ecg_abnormal_axis:
        components["ecg_abnormal_axis"] = 1
    if inp.ecg_prolonged_qrs:
        components["ecg_prolonged_qrs"] = 1
    if inp.ecg_prolonged_qtc:
        components["ecg_prolonged_qtc"] = 2
    if ed_dx == EDPresumptiveDiagnosis.VASOVAGAL.value:
        components["ed_dx_vasovagal"] = -2
    elif ed_dx == EDPresumptiveDiagnosis.CARDIAC.value:
        components["ed_dx_cardiac"] = 2

    score = sum(components.values())
    tier, observed_rate = _risk_category(score)
    context = _management_context(tier)

    return CSRSResult(
        patient_id=inp.patient_id,
        score=score,
        risk_tier=tier.value,
        validation_category_outcome_rate_pct=observed_rate,
        sae_30day_probability_pct=observed_rate,
        active_components=components,
        management_context=context,
        disposition_recommendation=context,
    )


def _first_present(kwargs: Dict[str, Any], names: tuple[str, ...], default: Any) -> Any:
    for name in names:
        if name in kwargs and kwargs[name] not in (None, ""):
            return kwargs[name]
    return default


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value in (0, 0.0):
            return False
        if value in (1, 1.0):
            return True
        raise ValueError(f"Boolean numeric values must be 0 or 1, got {value!r}.")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "t", "positive", "+"}:
            return True
        if normalized in {"false", "0", "no", "n", "f", "negative", "-", ""}:
            return False
    raise ValueError(f"Cannot parse boolean value {value!r}.")


def calculate_metrics(**kwargs: Any) -> Dict[str, Any]:
    """Compatibility wrapper accepting common aliases used by prior versions."""

    predisposition = _parse_bool(_first_present(
        kwargs, ("predisposition_vasovagal", "vasovagal_predisposition", "v1"), False
    ))
    cardiac_history = _parse_bool(_first_present(
        kwargs, ("history_heart_disease", "cardiac_history", "v2"), False
    ))
    sbp = _first_present(kwargs, ("systolic_bp", "sbp", "systolic_bp_mmhg", "v3"), 120.0)
    troponin = _parse_bool(_first_present(
        kwargs, ("troponin_elevated", "troponin_positive", "v4"), False
    ))
    axis = _parse_bool(_first_present(
        kwargs, ("ecg_abnormal_axis", "q_axis_abnormal", "v5"), False
    ))
    qrs = _parse_bool(_first_present(
        kwargs, ("ecg_prolonged_qrs", "qrs_prolonged", "v6"), False
    ))
    qtc = _parse_bool(_first_present(
        kwargs, ("ecg_prolonged_qtc", "qtc_prolonged", "v7"), False
    ))
    ed_dx = _first_present(kwargs, ("ed_diagnosis", "diagnosis"), "unknown")
    patient_id = _first_present(kwargs, ("patient_id", "Patient", "id"), None)

    result = evaluate_csrs(CSRSInput(
        patient_id=str(patient_id) if patient_id is not None else None,
        predisposition_vasovagal=predisposition,
        history_heart_disease=cardiac_history,
        systolic_bp=sbp,
        troponin_elevated=troponin,
        ecg_abnormal_axis=axis,
        ecg_prolonged_qrs=qrs,
        ecg_prolonged_qtc=qtc,
        ed_diagnosis=ed_dx,
    ))
    out = result.to_dict()
    out["classification"] = result.risk_tier
    out["clinical_recommendation"] = result.management_context
    out["tool"] = "canadian-syncope-risk-score"
    return out


def process_batch(input_csv: str, output_csv: str) -> int:
    """Process a CSV cohort. Invalid rows raise a row-numbered ``ValueError``."""

    with open(input_csv, "r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    output_fields = fieldnames + [
        "csrs_score",
        "risk_tier",
        "validation_category_outcome_rate_pct",
        "management_context",
    ]
    deduped_fields = list(dict.fromkeys(output_fields))
    output_rows: List[Dict[str, Any]] = []

    for row_number, row in enumerate(rows, start=2):
        try:
            calculated = calculate_metrics(**row)
        except ValueError as exc:
            raise ValueError(f"Invalid data on CSV row {row_number}: {exc}") from exc
        enriched = dict(row)
        enriched["csrs_score"] = calculated["score"]
        enriched["risk_tier"] = calculated["risk_tier"]
        enriched["validation_category_outcome_rate_pct"] = calculated[
            "validation_category_outcome_rate_pct"
        ]
        enriched["management_context"] = calculated["management_context"]
        output_rows.append(enriched)

    with open(output_csv, "w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=deduped_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows)
