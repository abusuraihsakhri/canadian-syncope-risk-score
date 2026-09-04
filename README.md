# Canadian Syncope Risk Score (CSRS)

> **Domain:** Emergency Cardiology & Clinical Decision Support  
> **Reference:** Thiruganasambandamoorthy et al., *CMAJ* 2016; 188(12):E289-E298.  
> **Validation:** Thiruganasambandamoorthy et al., *JAMA Intern Med* 2020; 180(5):737-744.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-58%20Passed-brightgreen.svg)

---

## 📖 Overview

The **Canadian Syncope Risk Score (CSRS)** is a validated clinical decision instrument developed to stratify adult emergency department (ED) syncope patients for their risk of **30-day serious adverse events (SAE)** following index evaluation.

Syncope accounts for 1%–2% of all ED visits. While the majority of presentations represent benign vasovagal episodes, a critical subset harbours occult cardiac or life-threatening systemic etiologies. The CSRS integrates clinical history, triage vitals, initial investigations (cardiac troponin, 12-lead ECG markers), and emergency physician presumptive diagnoses to guide safe discharge versus observation and expedited inpatient admission.

---

## 🎯 30-Day Serious Adverse Outcomes Evaluated

The primary clinical endpoint is 30-day serious adverse cardiovascular or non-cardiovascular outcomes:

1. **Ventricular Arrhythmias:** Ventricular fibrillation (VF), sustained or symptomatic ventricular tachycardia (VT).
2. **Myocardial Infarction (MI):** Acute coronary syndrome with biomarker necrosis or ischemic ECG evolution.
3. **Structural Heart Disease Complications:** Severe aortic stenosis, acute heart failure, hypertrophic obstructive cardiomyopathy decompensation.
4. **Aortic Dissection:** Thoracic or abdominal aortic dissection presenting with syncopal collapse.
5. **Subarachnoid Hemorrhage (SAH):** Intracranial hemorrhage presenting with loss of consciousness.
6. **Internal Bleeding:** Massive gastrointestinal, retroperitoneal, or intra-abdominal hemorrhage.
7. **Pacemaker / ICD Placement:** Unscheduled bradyarrhythmia pacing (high-grade AV block, sick sinus syndrome) or secondary prevention ICD implantation within 30 days.

---

## 🧮 CSRS Scoring Formulation

The composite score spans **-3 to +11** based on 9 clinical and investigative parameters assessed in the ED:

### 1. Clinical Factors
| Parameter | Definition / Criteria | Score Points |
|:----------|:----------------------|:------------:|
| **Predisposition to Vasovagal Symptoms** | Warm crowded place, prolonged standing, fear, emotion, or severe pain triggers | **-1** (or -2 in expanded rule) |
| **History of Heart Disease** | CAD, prior MI, heart failure, valvular heart disease, or past ventricular arrhythmia | **+1** |
| **Systolic BP on Triage** | Severe hypotension (<90 mmHg) OR severe hypertension (>180 mmHg) | **+2** |

### 2. Investigations
| Parameter | Definition / Criteria | Score Points |
|:----------|:----------------------|:------------:|
| **Elevated Troponin** | Serum cardiac troponin > 99th percentile upper reference limit (URL) | **+2** |
| **Abnormal QRS Axis** | Frontal plane QRS axis < -30° (left-axis deviation) or > +100° (right-axis deviation) | **+1** |
| **QRS Duration Prolongation** | QRS duration > 102 ms (or bundle-branch block / conduction delay > 120 ms) | **+1** |
| **Corrected QT Prolongation** | Corrected QT interval (QTc) > 480 ms (Bazett formula) | **+2** |

### 3. Emergency Department Presumptive Diagnosis
| Parameter | Clinical Impression at ED Completion | Score Points |
|:----------|:-------------------------------------|:------------:|
| **Vasovagal Syncope** | High clinical suspicion for pure neurocardiogenic / reflex etiology | **-2** |
| **Cardiac Syncope** | High clinical suspicion for primary arrhythmic or structural cardiac etiology | **+2** |
| **Other / Unknown** | Orthostatic, situational, medication-induced, or cryptogenic presentation | **0** |

---

## 📊 Risk Tiers & 30-Day SAE Probability Calibration

Empirical risk distributions derived from Canadian multi-center derivation and validation cohorts:

| Risk Category | CSRS Score Range | 30-Day SAE Risk (%) | 95% Confidence Interval | Arrhythmic Risk (%) | Disposition Recommendation |
|:-------------:|:----------------:|:-------------------:|:-----------------------:|:-------------------:|:---------------------------|
| **Very Low** | **-3 to -2** | **~0.4% – 0.7%** | 0.1% – 1.2% | 0.1% – 0.2% | Safe for immediate ED discharge; routine primary care follow-up |
| **Low** | **-1** | **~1.4%** | 0.8% – 2.2% | 0.4% | Low risk; safe for discharge after ED observation period |
| **Medium** | **0 to 1** | **~2.9% – 5.3%** | 2.0% – 7.1% | 1.1% – 2.4% | Intermediate risk; 4–6 hr ED observation, telemetry monitoring |
| **High** | **2 to 3** | **~8.4% – 13.2%** | 6.3% – 16.8% | 4.5% – 7.8% | High risk; hospital admission recommended, urgent cardiology consult |
| **Very High** | **4 to 11** | **~21.4% – 95.0%** | 16.5% – 99.0% | 14.1% – 80.0% | Critical risk; inpatient telemetry / CCU admission, urgent echo & EP |

---

## 💻 CLI Quickstart & Usage

### 1. Batch CSV Processing
Process an entire cohort of ED presentations from a CSV file:

```bash
python cli.py batch -i sample.csv -o csrs_results.csv
```

### 2. Single Presentation Evaluation
Evaluate an individual clinical case using command-line arguments:

```bash
# High-risk patient with cardiac history, hypotension, and elevated troponin
python cli.py evaluate \
  --patient-id PAT-042 \
  --cardiac-history \
  --sbp 84.0 \
  --troponin-elevated \
  --ecg-qtc-prolonged \
  --ed-diagnosis cardiac
```

JSON output mode:
```bash
python cli.py evaluate --cardiac-history --sbp 88.0 --troponin-elevated --json
```

### 3. Display Calibrated Score Reference Table
```bash
python cli.py table
```

### 4. Interactive Clinical Wizard
```bash
python cli.py interactive
```

---

## 🐍 Python API Quickstart

```python
from canadian_syncope import CSRSInput, evaluate_csrs, calculate_metrics

# 1. Structured Dataclass Interface
patient = CSRSInput(
    patient_id="ED-2026-881",
    predisposition_vasovagal=False,
    history_heart_disease=True,
    systolic_bp=86.0,
    troponin_elevated=True,
    ecg_abnormal_axis=True,
    ecg_prolonged_qrs=False,
    ecg_prolonged_qtc=True,
    ed_diagnosis="cardiac",
)

result = evaluate_csrs(patient)

print(f"Patient ID: {result.patient_id}")
print(f"Score: {result.score:+d}")
print(f"Risk Tier: {result.risk_tier}")
print(f"30-day SAE Probability: {result.sae_30day_probability_pct:.1f}%")
print(f"Arrhythmic Risk: {result.arrhythmic_risk_probability_pct:.1f}%")
print(f"Disposition: {result.disposition_recommendation}")

# 2. Dictionary / Kwargs Pipeline Interface
metrics = calculate_metrics(
    patient_id="ED-2026-882",
    predisposition_vasovagal=True,
    history_heart_disease=False,
    systolic_bp=118.0,
    troponin_elevated=False,
    ed_diagnosis="vasovagal",
)
print(f"Score: {metrics['score']}, Tier: {metrics['risk_tier']}")
```

---

## 🧪 Testing & Verification

Run the test suite using `pytest`:

```bash
python -m pytest -p no:zarr -v
```

Perform a smoke test on batch processing:
```bash
python cli.py batch -i sample.csv -o out_smoke.csv
```

---

## 📄 License

This software is released under the [MIT License](LICENSE).
