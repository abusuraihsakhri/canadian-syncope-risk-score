#!/usr/bin/env python3
"""
Syncope Outcomes Prediction for Canadian Syncope Risk Score.
Predicts 30-day adverse outcomes (death, MI, arrhythmia) using clinical features.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class SyncopePatient:
    """Patient presenting with syncope."""
    age: float
    sex: str
    syncope_risk_score: float
    ecg_normal: bool
    heart_failure: bool
    sbp: float
    hct: float
    troponin: float = 0.0
    bnp: float = 0.0
    family_history_scd: bool = False
    prior_syncope: bool = False


def predict_outcomes(patient: SyncopePatient) -> Dict[str, Any]:
    """Predict 30-day adverse outcomes for syncope patient."""
    risk_score = patient.syncope_risk_score
    risk_factors = []

    if patient.age > 65:
        risk_score += 2.0
        risk_factors.append(f"Age >65 ({patient.age:.0f})")

    if patient.sex == "M":
        risk_score += 0.5

    if not patient.ecg_normal:
        risk_score += 3.0
        risk_factors.append("Abnormal ECG")

    if patient.heart_failure:
        risk_score += 3.0
        risk_factors.append("Heart failure history")

    if patient.sbp < 90:
        risk_score += 2.0
        risk_factors.append(f"Hypotension (SBP {patient.sbp:.0f})")
    elif patient.sbp < 100:
        risk_score += 1.0
        risk_factors.append(f"Borderline BP (SBP {patient.sbp:.0f})")

    if patient.hct < 30:
        risk_score += 1.5
        risk_factors.append(f"Anemia (Hct {patient.hct:.0f})")

    if patient.troponin > 0.04:
        risk_score += 4.0
        risk_factors.append(f"Elevated troponin ({patient.troponin:.2f})")

    if patient.bnp > 400:
        risk_score += 2.0
        risk_factors.append(f"Elevated BNP ({patient.bnp:.0f})")

    if patient.family_history_scd:
        risk_score += 2.0
        risk_factors.append("Family history of SCD")

    if patient.prior_syncope:
        risk_score += 1.0
        risk_factors.append("Prior syncope episode")

    death_risk_pct = min(25.0, risk_score * 1.2)
    mi_risk_pct = min(15.0, risk_score * 0.8)
    arrhythmia_risk_pct = min(20.0, risk_score * 1.0)
    composite_risk_pct = min(35.0, risk_score * 1.5)

    if composite_risk_pct >= 20:
        risk_category = "HIGH"
        disposition = "Admit. Continuous telemetry. Urgent cardiology consult."
        followup = "Cardiology within 48 hours"
    elif composite_risk_pct >= 10:
        risk_category = "MODERATE"
        disposition = "Observation unit with telemetry for 24 hours."
        followup = "Cardiology within 1 week"
    elif composite_risk_pct >= 5:
        risk_category = "LOW"
        disposition = "ED observation. Discharge with close follow-up."
        followup = "Primary care within 1 week"
    else:
        risk_category = "VERY_LOW"
        disposition = "Discharge. Outpatient follow-up."
        followup = "As needed"

    return {
        "risk_score_final": round(risk_score, 2),
        "risk_category": risk_category,
        "outcomes": {
            "death_30d_risk_pct": round(death_risk_pct, 1),
            "mi_30d_risk_pct": round(mi_risk_pct, 1),
            "arrhythmia_30d_risk_pct": round(arrhythmia_risk_pct, 1),
            "composite_risk_pct": round(composite_risk_pct, 1),
        },
        "risk_factors": risk_factors,
        "disposition": disposition,
        "followup": followup,
    }


class SyncopeOutcomeAgent:
    """Sub-agent for syncope outcomes prediction."""

    def __init__(self):
        self.agent_name = "SyncopeOutcomeAgent"

    def evaluate(self, patient: SyncopePatient) -> Dict[str, Any]:
        """Evaluate syncope outcomes."""
        result = predict_outcomes(patient)
        alerts = []

        if result["risk_category"] in ("HIGH", "MODERATE"):
            alerts.append({
                "type": "ADVERSE_OUTCOME_RISK", "severity": "WARNING" if result["risk_category"] == "MODERATE" else "CRITICAL",
                "message": f"30-day composite risk: {result['outcomes']['composite_risk_pct']:.1f}% "
                           f"({result['risk_category']} risk).",
                "recommendation": result["disposition"]
            })

        if patient.troponin > 0.04:
            alerts.append({
                "type": "ELEVATED_TROPONIN", "severity": "CRITICAL",
                "message": f"Troponin {patient.troponin:.2f} ng/mL. Evaluate for acute coronary syndrome.",
                "recommendation": "Serial troponins. Cardiology consultation. Consider catheterization."
            })

        return {"outcome_result": result, "alerts": alerts}
