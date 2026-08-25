#!/usr/bin/env python3
"""
Canadian Syncope Risk Score (CSRS) Domain Engine
================================================
A clinical decision instrument for predicting 30-day serious adverse events (SAE)
in emergency department syncope presentations based on validated Ottawa criteria
(Thiruganasambandamoorthy et al., CMAJ / JAMA Intern Med).

Components:
  1. Predisposition to vasovagal symptoms: -2
  2. History of heart disease: +1
  3. Systolic BP on triage (<90 mmHg: +2, 90-180 mmHg: 0, >180 mmHg: +2)
  4. Elevated troponin level (>99th percentile): +2
  5. ECG abnormalities:
     - Abnormal QRS axis (<-30 deg or >+100 deg): +1
     - Prolonged QRS duration (>120 ms): +1
     - Prolonged QTc interval (>480 ms): +2
  6. ED presumptive diagnosis:
     - Vasovagal syncope: -2
     - Cardiac syncope: +2
     - Other / Unknown: 0

Score Range: -3 to +11
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


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


@dataclass
class CSRSInput:
    """Clinical presentation features for Canadian Syncope Risk Score evaluation."""
    predisposition_vasovagal: bool = False
    history_heart_disease: bool = False
    systolic_bp: float = 120.0
    troponin_elevated: bool = False
    ecg_abnormal_axis: bool = False
    ecg_prolonged_qrs: bool = False
    ecg_prolonged_qtc: bool = False
    ed_diagnosis: Union[EDPresumptiveDiagnosis, str] = EDPresumptiveDiagnosis.UNKNOWN
    
    # Extended clinical context
    patient_id: Optional[str] = None
    age: Optional[int] = None
    heart_rate_bpm: Optional[float] = None
    exertional_syncope: bool = False
    supine_syncope: bool = False
    palpitations_preceding: bool = False
    family_history_sudden_death: bool = False
    structural_heart_disease: bool = False
    ccs_angina_class: Optional[str] = None  # class_I, class_II, class_III, class_IV


@dataclass
class CSRSResult:
    """Output dossier for Canadian Syncope Risk Score calculation."""
    score: int
    risk_tier: str
    sae_30day_probability_pct: float
    sae_95ci_pct: Tuple[float, float]
    arrhythmic_risk_probability_pct: float
    non_arrhythmic_risk_probability_pct: float
    disposition_recommendation: str
    monitoring_recommendation: str
    active_components: Dict[str, int]
    red_flag_alerts: List[str] = field(default_factory=list)
    ccs_adjusted_score: Optional[float] = None
    patient_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "score": self.score,
            "risk_tier": self.risk_tier,
            "sae_30day_probability_pct": self.sae_30day_probability_pct,
            "sae_95ci_pct": list(self.sae_95ci_pct),
            "arrhythmic_risk_probability_pct": self.arrhythmic_risk_probability_pct,
            "non_arrhythmic_risk_probability_pct": self.non_arrhythmic_risk_probability_pct,
            "disposition_recommendation": self.disposition_recommendation,
            "monitoring_recommendation": self.monitoring_recommendation,
            "active_components": self.active_components,
            "red_flag_alerts": self.red_flag_alerts,
            "ccs_adjusted_score": self.ccs_adjusted_score,
        }


# Empirical 30-day serious adverse event (SAE) probabilities from validated cohorts
# Score -> (Estimated Rate %, 95% CI Lower %, 95% CI Upper %, Arrhythmic %, Non-Arrhythmic %)
CSRS_SCORE_TABLE: Dict[int, Tuple[float, float, float, float, float]] = {
    -3: (0.4, 0.1, 0.8, 0.1, 0.3),
    -2: (0.7, 0.3, 1.2, 0.2, 0.5),
    -1: (1.4, 0.8, 2.2, 0.4, 1.0),
     0: (2.9, 2.0, 4.1, 1.1, 1.8),
     1: (5.3, 3.9, 7.1, 2.4, 2.9),
     2: (8.4, 6.3, 11.0, 4.5, 3.9),
     3: (13.2, 10.2, 16.8, 7.8, 5.4),
     4: (21.4, 16.5, 27.2, 14.1, 7.3),
     5: (33.3, 25.8, 41.6, 23.5, 9.8),
     6: (45.0, 34.0, 56.5, 33.0, 12.0),
     7: (58.0, 45.0, 70.0, 44.0, 14.0),
     8: (70.0, 55.0, 82.0, 55.0, 15.0),
     9: (80.0, 65.0, 90.0, 65.0, 15.0),
    10: (88.0, 75.0, 95.0, 73.0, 15.0),
    11: (95.0, 82.0, 99.0, 80.0, 15.0),
}


def _clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(val, max_val))


def evaluate_csrs(inp: CSRSInput) -> CSRSResult:
    """
    Evaluates clinical presentation against the Canadian Syncope Risk Score algorithm.
    """
    # Validation
    if inp.systolic_bp < 40.0 or inp.systolic_bp > 300.0:
        raise ValueError(f"Systolic BP ({inp.systolic_bp} mmHg) is outside physiological range [40, 300].")

    score = 0
    components: Dict[str, int] = {}

    # 1. Predisposition to vasovagal symptoms (-2)
    if inp.predisposition_vasovagal:
        score += -2
        components["predisposition_vasovagal"] = -2

    # 2. History of heart disease (+1)
    if inp.history_heart_disease:
        score += 1
        components["history_heart_disease"] = 1

    # 3. Systolic BP
    if inp.systolic_bp < 90.0:
        score += 2
        components["systolic_bp_hypotension"] = 2
    elif inp.systolic_bp > 180.0:
        score += 2
        components["systolic_bp_hypertension"] = 2

    # 4. Elevated Troponin (+2)
    if inp.troponin_elevated:
        score += 2
        components["troponin_elevated"] = 2

    # 5. ECG Abnormalities
    if inp.ecg_abnormal_axis:
        score += 1
        components["ecg_abnormal_axis"] = 1

    if inp.ecg_prolonged_qrs:
        score += 1
        components["ecg_prolonged_qrs"] = 1

    if inp.ecg_prolonged_qtc:
        score += 2
        components["ecg_prolonged_qtc"] = 2

    # 6. ED Presumptive Diagnosis
    ed_dx = inp.ed_diagnosis
    if isinstance(ed_dx, EDPresumptiveDiagnosis):
        ed_dx_str = ed_dx.value
    else:
        ed_dx_str = str(ed_dx).lower().strip()

    if ed_dx_str == "vasovagal":
        score += -2
        components["ed_dx_vasovagal"] = -2
    elif ed_dx_str == "cardiac":
        score += 2
        components["ed_dx_cardiac"] = 2

    # Boundary score clamping to standard lookup range [-3, 11]
    lookup_score = int(_clamp(score, -3, 11))

    # Risk Tier assignment
    if score <= -2:
        tier = RiskTier.VERY_LOW
        disposition = "Safe for immediate ED discharge. Routine primary care follow-up."
        monitoring = "No continuous telemetry indicated. Outpatient care."
    elif score == -1:
        tier = RiskTier.LOW
        disposition = "Low risk of adverse outcome. Safe for ED discharge with outpatient follow-up."
        monitoring = "Short period of observation in ED prior to discharge."
    elif score in (0, 1):
        tier = RiskTier.MEDIUM
        disposition = "Intermediate risk. Consider short-stay ED observation unit (4-6 hours)."
        monitoring = "Cardiac telemetry in observation unit. Consider outpatient Holter / patch monitor."
    elif score in (2, 3):
        tier = RiskTier.HIGH
        disposition = "High risk for 30-day serious cardiac event. Inpatient hospital admission recommended."
        monitoring = "Continuous cardiac telemetry, urgent echocardiography, cardiology consultation."
    else:
        tier = RiskTier.VERY_HIGH
        disposition = "Very high risk. Expedited admission to cardiac monitored unit / telemetry or CCU."
        monitoring = "Continuous telemetry, immediate cardiology evaluation, structural & EP workup."

    # Look up calibrated 30-day SAE rates
    est_rate, ci_low, ci_high, arr_rate, non_arr_rate = CSRS_SCORE_TABLE[lookup_score]

    # Red Flag Alerts
    red_flags: List[str] = []
    if inp.exertional_syncope:
        red_flags.append("CRITICAL: Exertional syncope identified - warrants evaluation for AS, HCM, or anomalous coronary.")
    if inp.supine_syncope:
        red_flags.append("WARNING: Syncope while supine suggests primary arrhythmic etiology.")
    if inp.palpitations_preceding:
        red_flags.append("WARNING: Palpitations immediately preceding syncope suggest tachyarrhythmia.")
    if inp.family_history_sudden_death:
        red_flags.append("CRITICAL: Family history of premature sudden cardiac death - evaluate channelopathy/cardiomyopathy.")
    if inp.structural_heart_disease:
        red_flags.append("ADVISORY: Known structural heart disease elevates risk of hemodynamic decompensation.")
    if inp.heart_rate_bpm is not None:
        if inp.heart_rate_bpm < 45.0:
            red_flags.append(f"CRITICAL: Severe bradycardia ({inp.heart_rate_bpm:.1f} bpm) detected in ED.")
        elif inp.heart_rate_bpm > 120.0:
            red_flags.append(f"WARNING: Tachycardia ({inp.heart_rate_bpm:.1f} bpm) on presentation.")

    # CCS Adjustment
    ccs_adjusted = None
    if inp.ccs_angina_class:
        ccs_weights = {
            "class_I": 0.9,
            "class_II": 1.0,
            "class_III": 1.3,
            "class_IV": 1.6,
        }
        mod = ccs_weights.get(inp.ccs_angina_class, 1.0)
        ccs_adjusted = round(float(score) * mod, 2)

    return CSRSResult(
        score=score,
        risk_tier=tier.value,
        sae_30day_probability_pct=est_rate,
        sae_95ci_pct=(ci_low, ci_high),
        arrhythmic_risk_probability_pct=arr_rate,
        non_arrhythmic_risk_probability_pct=non_arr_rate,
        disposition_recommendation=disposition,
        monitoring_recommendation=monitoring,
        active_components=components,
        red_flag_alerts=red_flags,
        ccs_adjusted_score=ccs_adjusted,
        patient_id=inp.patient_id,
    )


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Standard interface function compatible with CLI and batch processing.
    """
    # Parse inputs gracefully
    def _bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "y", "t", "positive", "+")
        return False

    def _float(val: Any, default: float) -> float:
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    # Map possible parameter names
    predisposition = _bool(kwargs.get("predisposition_vasovagal") or kwargs.get("vasovagal_predisposition") or kwargs.get("v1", False))
    cardiac_history = _bool(kwargs.get("history_heart_disease") or kwargs.get("cardiac_history") or kwargs.get("v2", False))
    
    # Blood pressure
    sbp_raw = kwargs.get("systolic_bp") or kwargs.get("sbp") or kwargs.get("systolic_bp_mmhg") or kwargs.get("v3", 120.0)
    sbp = _float(sbp_raw, 120.0)

    troponin = _bool(kwargs.get("troponin_elevated") or kwargs.get("troponin_positive") or kwargs.get("v4", False))
    qrs_axis = _bool(kwargs.get("ecg_abnormal_axis") or kwargs.get("q_axis_abnormal") or kwargs.get("v5", False))
    qrs_dur = _bool(kwargs.get("ecg_prolonged_qrs") or kwargs.get("qrs_prolonged") or kwargs.get("v6", False))
    qtc = _bool(kwargs.get("ecg_prolonged_qtc") or kwargs.get("qtc_prolonged") or kwargs.get("v7", False))
    
    ed_dx = kwargs.get("ed_diagnosis") or kwargs.get("diagnosis", "unknown")
    if not isinstance(ed_dx, str):
        ed_dx = str(ed_dx)

    patient_id = kwargs.get("patient_id") or kwargs.get("Patient") or kwargs.get("id")
    hr = kwargs.get("heart_rate_bpm") or kwargs.get("heart_rate") or kwargs.get("hr")
    hr_val = _float(hr, 75.0) if hr is not None else None

    inp = CSRSInput(
        patient_id=str(patient_id) if patient_id is not None else None,
        predisposition_vasovagal=predisposition,
        history_heart_disease=cardiac_history,
        systolic_bp=sbp,
        troponin_elevated=troponin,
        ecg_abnormal_axis=qrs_axis,
        ecg_prolonged_qrs=qrs_dur,
        ecg_prolonged_qtc=qtc,
        ed_diagnosis=ed_dx,
        heart_rate_bpm=hr_val,
        exertional_syncope=_bool(kwargs.get("exertional_syncope", False)),
        supine_syncope=_bool(kwargs.get("supine_syncope", False)),
        palpitations_preceding=_bool(kwargs.get("palpitations_preceding", False)),
        family_history_sudden_death=_bool(kwargs.get("family_history_sudden_death", False)),
        structural_heart_disease=_bool(kwargs.get("structural_heart_disease", False)),
        ccs_angina_class=kwargs.get("ccs_angina_class") or kwargs.get("ccs_class"),
    )

    res = evaluate_csrs(inp)
    out = res.to_dict()
    # Backward-compatible fields
    out["score"] = res.score
    out["classification"] = res.risk_tier
    out["clinical_recommendation"] = res.disposition_recommendation
    out["tool"] = "canadian-syncope-risk-score"
    return out


def process_batch(input_csv: str, output_csv: str) -> int:
    """
    Process batch patient CSV file through Canadian Syncope Risk Score calculator.
    """
    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    out_fields = fieldnames + [
        "csrs_score",
        "risk_tier",
        "sae_30day_probability_pct",
        "arrhythmic_risk_probability_pct",
        "disposition_recommendation",
        "red_flag_alerts",
    ]
    # Remove duplicates while preserving order
    dedup_fields = []
    for fn in out_fields:
        if fn not in dedup_fields:
            dedup_fields.append(fn)

    out_rows = []
    for r in rows:
        calc_res = calculate_metrics(**r)
        row_dict = dict(r)
        row_dict["csrs_score"] = calc_res["score"]
        row_dict["risk_tier"] = calc_res["risk_tier"]
        row_dict["sae_30day_probability_pct"] = calc_res["sae_30day_probability_pct"]
        row_dict["arrhythmic_risk_probability_pct"] = calc_res["arrhythmic_risk_probability_pct"]
        row_dict["disposition_recommendation"] = calc_res["disposition_recommendation"]
        row_dict["red_flag_alerts"] = "; ".join(calc_res["red_flag_alerts"])
        out_rows.append(row_dict)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dedup_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
