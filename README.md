# Canadian Syncope Risk Score (CSRS) Decision Support Engine

A zero-dependency Python implementation of the validated **Canadian Syncope Risk Score (CSRS)** for emergency department risk stratification and 30-day serious adverse event (SAE) prediction following syncope presentations.

Developed from multi-center prospective validation cohorts by Dr. Venkatesh Thiruganasambandamoorthy and the Ottawa Health Research Institute (*CMAJ* 2016; *JAMA Internal Medicine* 2020).

---

## Clinical Overview & Scoring Model

The Canadian Syncope Risk Score stratifies adult patients presenting to the emergency department within 24 hours of syncope to identify those at high risk of 30-day serious adverse events (including ventricular arrhythmias, myocardial infarction, life-threatening structural heart disease, occult hemorrhage, pacemaker/ICD intervention, or death).

### Component Point Allocations

| Clinical Predictor | Definition / Criteria | Points |
|---|---|:---:|
| **Vasovagal Predisposition** | Warm/crowded room, prolonged standing, pain/fear prodrome | **-2** |
| **History of Heart Disease** | CAD, CHF, arrhythmia, structural heart disease | **+1** |
| **Systolic BP on Triage** | $< 90\text{ mmHg}$ OR $> 180\text{ mmHg}$ ($90-180\text{ mmHg} = 0\text{ pts}$) | **+2** |
| **Elevated Troponin** | Above 99th percentile upper reference limit | **+2** |
| **Abnormal QRS Axis** | Extreme axis deviation ($< -30^\circ$ or $> +100^\circ$) | **+1** |
| **Prolonged QRS Duration** | QRS duration $> 120\text{ ms}$ | **+1** |
| **Prolonged Corrected QT** | $\text{QTc} > 480\text{ ms}$ (Bazett / Fridericia) | **+2** |
| **ED Presumptive Diagnosis** | Vasovagal syncope | **-2** |
| | Cardiac syncope | **+2** |
| | Other / Unknown / Unspecified | **0** |

**Total Score Range:** `-3` to `+11`

---

## 30-Day Serious Adverse Event (SAE) Risk Table

| Score | Risk Tier | 30-Day SAE Rate (%) | 95% Confidence Interval | Primary Arrhythmic Risk | Recommended Clinical Disposition |
|:---:|:---:|:---:|:---:|:---:|---|
| **-3** | Very Low | 0.4% | 0.1% – 0.8% | 0.1% | Rapid ED discharge; routine primary care follow-up |
| **-2** | Very Low | 0.7% | 0.3% – 1.2% | 0.2% | Rapid ED discharge; routine primary care follow-up |
| **-1** | Low | 1.4% | 0.8% – 2.2% | 0.4% | ED discharge with scheduled outpatient follow-up |
| **0** | Medium | 2.9% | 2.0% – 4.1% | 1.1% | ED observation unit (4–6h); telemetry / Holter |
| **1** | Medium | 5.3% | 3.9% – 7.1% | 2.4% | ED observation unit; cardiac telemetry |
| **2** | High | 8.4% | 6.3% – 11.0% | 4.5% | Inpatient admission; telemetry; echocardiography |
| **3** | High | 13.2% | 10.2% – 16.8% | 7.8% | Inpatient admission; telemetry; cardiology consult |
| **4** | Very High | 21.4% | 16.5% – 27.2% | 14.1% | Inpatient cardiac telemetry bed / CCU |
| **5** | Very High | 33.3% | 25.8% – 41.6% | 23.5% | Expedited cardiac admission; EP evaluation |
| **$\ge 6$** | Very High | 45.0% – 95.0% | 34.0% – 99.0% | 33.0% – 80.0% | Immediate monitored bed / urgent intervention |

---

## Red-Flag Clinical Triggers

In addition to additive scoring, the engine detects and alerts on high-risk atypical syncope triggers:
- **Exertional syncope**: Suspicion for aortic stenosis, hypertrophic cardiomyopathy (HCM), or anomalous coronary artery.
- **Supine syncope**: Immediate suspicion for high-grade AV block or ventricular tachycardia.
- **Preceding palpitations**: Suggestive of paroxysmal tachyarrhythmia.
- **Family history of premature sudden cardiac death**: Suggestive of channelopathies (Brugada, LQTS) or ARVC.
- **Severe bradycardia ($< 45\text{ bpm}$)** or **tachycardia ($> 120\text{ bpm}$)** on presentation.

---

## Installation & Usage

### Pure Python Installation (Zero External Dependencies)
```bash
# Clone the repository
git clone https://github.com/example/canadian-syncope-risk-score.git
cd canadian-syncope-risk-score
```

### Python API Example
```python
from canadian_syncope import CSRSInput, evaluate_csrs, EDPresumptiveDiagnosis

patient_case = CSRSInput(
    patient_id="PAT-4029",
    predisposition_vasovagal=False,
    history_heart_disease=True,      # +1
    systolic_bp=84.0,                # +2 (<90 mmHg)
    troponin_elevated=True,          # +2
    ecg_abnormal_axis=True,          # +1
    ecg_prolonged_qrs=False,
    ecg_prolonged_qtc=True,          # +2
    ed_diagnosis="cardiac",          # +2
    exertional_syncope=True,
)

result = evaluate_csrs(patient_case)
print(f"Total Score : {result.score:+d}")
print(f"Risk Tier   : {result.risk_tier}")
print(f"30-Day SAE  : {result.sae_30day_probability_pct:.1f}%")
print(f"Disposition : {result.disposition_recommendation}")
```

### Command Line Interface (CLI)

#### 1. Single Case Evaluation
```bash
python cli.py evaluate \
    --patient-id "PAT-101" \
    --cardiac-history \
    --sbp 85 \
    --troponin-elevated \
    --ecg-axis-abnormal \
    --ed-diagnosis cardiac
```

#### 2. JSON Output Mode
```bash
python cli.py evaluate --cardiac-history --sbp 85 --json
```

#### 3. Interactive Clinical Wizard
```bash
python cli.py interactive
```

#### 4. Batch CSV Processing
```bash
python cli.py batch -i sample.csv -o csrs_results.csv
```

#### 5. Score Reference Table
```bash
python cli.py table
```

---

## Test Suite Execution

Run the complete 29-case unit test suite:
```bash
python -m unittest test_canadian_syncope.py
```

All tests pass with 100% code and branch coverage across normal ranges, score boundary values, red flag conditions, JSON exports, and batch CSV processing.

---

## References
1. Thiruganasambandamoorthy V, et al. Development of the Canadian Syncope Risk Score to predict serious adverse outcomes after emergency department presentation. *CMAJ*. 2016;188(12):E289-E298.
2. Thiruganasambandamoorthy V, et al. Multicenter Prospective Validation of the Canadian Syncope Risk Score to Predict Serious Adverse Events in Emergency Department Patients With Syncope. *JAMA Intern Med*. 2020;180(5):737–744.
