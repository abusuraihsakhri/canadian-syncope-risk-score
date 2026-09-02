# Canadian Syncope Risk Score

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

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

CCS Pre-Screening Score for Canadian Syncope Risk Score.
Refines syncope risk stratification using Canadian Cardiovascular Society classification
and clinical presentation features.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`RiskTier`** — dedicated module for risk tier evaluation and state verification.
- **`EDPresumptiveDiagnosis`** — dedicated module for e d presumptive diagnosis evaluation and state verification.
- **`CSRSInput`**: Clinical presentation features for Canadian Syncope Risk Score evaluation.
- **`CSRSResult`**: Output dossier for Canadian Syncope Risk Score calculation.
- **`CCSPrescreeningAgent`**: Sub-agent for CCS pre-screening score.
- **`CSRSPresentation`** — dedicated module for c s r s presentation evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  score = 0
  lookup_score = int(_clamp(score, -3, 11))
  elif score == -1:
  calc_res = calculate_metrics(**r)
  """Calculate CCS pre-screening score for syncope."""
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --- <value> --patient-id <value> --vasovagal-predisposition <value> --cardiac-history <value>
```

### Parameter Reference
- `---`: Specifies input measurement or parameter value.
- `--patient-id`: Specifies input measurement or parameter value.
- `--vasovagal-predisposition`: Specifies input measurement or parameter value.
- `--cardiac-history`: Specifies input measurement or parameter value.
- `--sbp`: Specifies input measurement or parameter value.
- `--troponin-elevated`: Specifies input measurement or parameter value.
- `--ecg-axis-abnormal`: Specifies input measurement or parameter value.
- `--ecg-qrs-prolonged`: Specifies input measurement or parameter value.
- `--ecg-qtc-prolonged`: Specifies input measurement or parameter value.
- `--ed-diagnosis`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `patient_id` | Parameter / observation metric | Required |
| `predisposition_vasovagal` | Parameter / observation metric | Required |
| `history_heart_disease` | Parameter / observation metric | Required |
| `systolic_bp` | Parameter / observation metric | Required |
| `troponin_elevated` | Parameter / observation metric | Required |
| `ecg_abnormal_axis` | Parameter / observation metric | Required |
| `ecg_prolonged_qrs` | Parameter / observation metric | Required |
| `ecg_prolonged_qtc` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t canadian-syncope-risk-score .
docker run -p 8000:8000 canadian-syncope-risk-score
```
