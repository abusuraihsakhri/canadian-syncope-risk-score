#!/usr/bin/env python3
"""
CCS Pre-Screening Score for Canadian Syncope Risk Score.
Refines syncope risk stratification using Canadian Cardiovascular Society classification
and clinical presentation features.
"""

from typing import Dict, Any, Optional, List


CCS_CLASSIFICATIONS = {
    "class_I": {"description": "Ordinary physical activity does not cause angina",
                "syncope_risk_modifier": 0.8},
    "class_II": {"description": "Slight limitation of ordinary physical activity",
                 "syncope_risk_modifier": 1.0},
    "class_III": {"description": "Marked limitation of physical activity",
                 "syncope_risk_modifier": 1.3},
    "class_IV": {"description": "Inability to carry on any physical activity without discomfort",
                 "syncope_risk_modifier": 1.6},
}


def calculate_ccs_syncope_score(syncope_risk_score: float, ccs_class: str,
                                  syncope_circumstances: Optional[List[str]] = None,
                                  cardiac_history: Optional[List[str]] = None) -> Dict[str, Any]:
    """Calculate CCS pre-screening score for syncope."""
    syncope_circumstances = syncope_circumstances or []
    cardiac_history = cardiac_history or []

    ccs_info = CCS_CLASSIFICATIONS.get(ccs_class, CCS_CLASSIFICATIONS["class_I"])
    ccs_modifier = ccs_info["syncope_risk_modifier"]

    adjusted_risk = syncope_risk_score * ccs_modifier
    risk_factors = []

    if "exertional_syncope" in syncope_circumstances:
        adjusted_risk *= 1.5
        risk_factors.append("Exertional syncope: significant cardiac risk")

    if "syncope_during_exercise" in syncope_circumstances:
        adjusted_risk *= 2.0
        risk_factors.append("Syncope during exercise: highest cardiac risk")

    if "supine_syncope" in syncope_circumstances:
        adjusted_risk *= 1.8
        risk_factors.append("Syncope while supine: concerning for arrhythmia")

    if "chest_pain_with_syncope" in syncope_circumstances:
        adjusted_risk *= 1.6
        risk_factors.append("Chest pain with syncope: possible cardiac etiology")

    if "palpitations_with_syncope" in syncope_circumstances:
        adjusted_risk *= 1.4
        risk_factors.append("Palpitations preceding syncope: arrhythmia concern")

    if "prior_mi" in cardiac_history:
        adjusted_risk *= 1.5
        risk_factors.append("Prior MI: structural heart disease risk")

    if "heart_failure" in cardiac_history:
        adjusted_risk *= 1.8
        risk_factors.append("Heart failure: increased arrhythmia and hemodynamic risk")

    if "ventricular_tachycardia" in cardiac_history:
        adjusted_risk *= 2.5
        risk_factors.append("History of VT: high recurrence risk")

    if "family_history_scd" in cardiac_history:
        adjusted_risk *= 1.4
        risk_factors.append("Family history of sudden cardiac death")

    if adjusted_risk >= 8.0:
        risk_category = "HIGH"
        disposition = "Admit for cardiac monitoring and urgent workup"
    elif adjusted_risk >= 5.0:
        risk_category = "MODERATE"
        disposition = "Observation unit with telemetry. Cardiology consultation."
    elif adjusted_risk >= 3.0:
        risk_category = "LOW-MODERATE"
        disposition = "ED observation. Consider outpatient cardiology follow-up."
    else:
        risk_category = "LOW"
        disposition = "Discharge with outpatient follow-up"

    return {
        "syncope_risk_score": syncope_risk_score,
        "ccs_class": ccs_class,
        "ccs_modifier": ccs_modifier,
        "adjusted_risk_score": round(adjusted_risk, 2),
        "risk_category": risk_category,
        "disposition": disposition,
        "risk_factors": risk_factors,
        "ccs_description": ccs_info["description"],
    }


class CCSPrescreeningAgent:
    """Sub-agent for CCS pre-screening score."""

    def __init__(self):
        self.agent_name = "CCSPrescreeningAgent"

    def evaluate(self, syncope_risk_score: float, ccs_class: str,
                 syncope_circumstances: Optional[List[str]] = None,
                 cardiac_history: Optional[List[str]] = None) -> Dict[str, Any]:
        """Evaluate CCS pre-screening."""
        result = calculate_ccs_syncope_score(syncope_risk_score, ccs_class,
                                              syncope_circumstances, cardiac_history)
        alerts = []

        if result["risk_category"] == "HIGH":
            alerts.append({
                "type": "HIGH_SYNCOPE_RISK", "severity": "CRITICAL",
                "message": f"High-risk syncope (score: {result['adjusted_risk_score']:.2f}). "
                           f"CCS: {ccs_class}.",
                "recommendation": result["disposition"]
            })

        if "syncope_during_exercise" in (syncope_circumstances or []):
            alerts.append({
                "type": "EXERCISE_SYNCOPE", "severity": "CRITICAL",
                "message": "Syncope during exercise: mandatory cardiac evaluation.",
                "recommendation": "Admit. Echocardiogram, stress test, and Holter monitoring."
            })

        return {"ccs_result": result, "alerts": alerts}
