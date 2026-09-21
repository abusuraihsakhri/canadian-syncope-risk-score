# Canadian Syncope Risk Score

### [Open the Live Application →](https://abusuraihsakhri.github.io/canadian-syncope-risk-score/)

A dependency-free implementation of the **Canadian Syncope Risk Score (CSRS)** for research, education, and reproducible score calculation. The repository provides a browser calculator, Python API, CLI, CSV batch processing, and automated tests.

## What it calculates

The implementation follows the published nine-component CSRS:

| Component | Points |
| --- | ---: |
| Predisposition to vasovagal symptoms | -1 |
| History of heart disease | +1 |
| Any ED systolic BP reading <90 or >180 mm Hg | +2 |
| Troponin above the local 99th percentile | +2 |
| QRS axis <−30° or >100° | +1 |
| QRS duration >130 ms | +1 |
| QTc >480 ms | +2 |
| ED diagnosis of vasovagal syncope | -2 |
| ED diagnosis of cardiac syncope | +2 |

Validated risk categories are **Very Low (-3 to -2)**, **Low (-1 to 0)**, **Medium (1 to 3)**, **High (4 to 5)**, and **Very High (6 to 11)**. The browser and Python outputs show the observed 30-day serious-outcome rate for the corresponding category in the 2020 prospective multicenter validation cohort. This is a category-level cohort rate, not an individualized probability.

## Browser calculator

The static interface runs entirely in the browser. It includes light and dark themes, responsive layout, keyboard-accessible controls, explicit validation, and no analytics or data submission. Enter the score components and select **Analyze**.

No patient data are sent to a server by the application. Theme preference is the only value stored locally in the browser.

## Python and CLI

Requires Python 3.10 or later and has no runtime dependencies.

~~~bash
python cli.py evaluate --vasovagal-predisposition --sbp 120 --json
python cli.py batch -i sample.csv -o results.csv
python cli.py table
~~~

Python API:

~~~python
from canadian_syncope import CSRSInput, evaluate_csrs

result = evaluate_csrs(CSRSInput(
    predisposition_vasovagal=True,
    history_heart_disease=False,
    systolic_bp=120,
    troponin_elevated=False,
    ecg_abnormal_axis=False,
    ecg_prolonged_qrs=False,
    ecg_prolonged_qtc=False,
    ed_diagnosis="vasovagal",
))

print(result.score, result.risk_tier)
~~~

## Testing

~~~bash
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/test_web.mjs
~~~

GitHub Actions runs syntax checks, Python tests across supported versions, CLI smoke tests, browser-calculator tests, and static security checks.

## Clinical scope and evidence

The CSRS was developed for patients presenting to an emergency department with syncope and validated for 30-day serious outcomes after the index ED evaluation. It should not be used as a substitute for diagnosis, clinical judgment, local protocols, or assessment of a serious cause already identified during the ED visit.

Primary references:

- Thiruganasambandamoorthy V, et al. *Development of the Canadian Syncope Risk Score to predict serious adverse events after emergency department assessment of syncope.* CMAJ. 2016;188(12):E289-E298. doi:10.1503/cmaj.151469.
- Thiruganasambandamoorthy V, et al. *Multicenter Emergency Department Validation of the Canadian Syncope Risk Score.* JAMA Intern Med. 2020;180(5):737-744. doi:10.1001/jamainternmed.2020.0288.

## Privacy

The browser calculator is static. It does not transmit entered values, use analytics, or contact an application backend. Only the selected color theme is stored in local browser storage.

## Technology and browser support

The web interface uses semantic HTML, CSS, and modern JavaScript modules without third-party packages. Current versions of Chrome, Edge, Firefox, and Safari are supported. The Python implementation uses only the standard library.

Python-in-the-browser runtimes such as Pyodide are intentionally not used: the calculation is simple enough to reproduce directly in a small tested JavaScript module, avoiding a large WebAssembly runtime and network dependency.

## License

MIT. See [LICENSE](LICENSE).
