export const COMPONENTS = Object.freeze({
  predisposition_vasovagal: -1,
  history_heart_disease: 1,
  abnormal_systolic_bp: 2,
  troponin_elevated: 2,
  ecg_abnormal_axis: 1,
  ecg_prolonged_qrs: 1,
  ecg_prolonged_qtc: 2,
  ed_dx_vasovagal: -2,
  ed_dx_cardiac: 2,
});

export const RISK_CATEGORIES = Object.freeze([
  Object.freeze({ min: -3, max: -2, tier: "Very Low", rate: 0.2 }),
  Object.freeze({ min: -1, max: 0, tier: "Low", rate: 0.7 }),
  Object.freeze({ min: 1, max: 3, tier: "Medium", rate: 8.0 }),
  Object.freeze({ min: 4, max: 5, tier: "High", rate: 19.2 }),
  Object.freeze({ min: 6, max: 11, tier: "Very High", rate: 51.3 }),
]);

export function riskCategory(score) {
  const category = RISK_CATEGORIES.find(({ min, max }) => score >= min && score <= max);
  if (!category) throw new RangeError(`CSRS score ${score} is outside the validated range -3 to 11.`);
  return category;
}

export function calculateCsrs(input) {
  const sbp = Number(input.systolicBp);
  if (!Number.isFinite(sbp) || sbp <= 0) {
    throw new TypeError("Systolic BP must be a finite positive number.");
  }

  const components = [];
  const add = (key, label) => components.push({ key, label, points: COMPONENTS[key] });

  if (input.predispositionVasovagal) add("predisposition_vasovagal", "Predisposition to vasovagal symptoms");
  if (input.historyHeartDisease) add("history_heart_disease", "History of heart disease");
  if (sbp < 90 || sbp > 180) add("abnormal_systolic_bp", "Any ED systolic BP <90 or >180 mm Hg");
  if (input.troponinElevated) add("troponin_elevated", "Troponin above 99th percentile");
  if (input.ecgAbnormalAxis) add("ecg_abnormal_axis", "Abnormal QRS axis");
  if (input.ecgProlongedQrs) add("ecg_prolonged_qrs", "QRS duration >130 ms");
  if (input.ecgProlongedQtc) add("ecg_prolonged_qtc", "QTc >480 ms");
  if (input.edDiagnosis === "vasovagal") add("ed_dx_vasovagal", "ED diagnosis: vasovagal syncope");
  else if (input.edDiagnosis === "cardiac") add("ed_dx_cardiac", "ED diagnosis: cardiac syncope");
  else if (!new Set(["other", "unknown"]).has(input.edDiagnosis)) {
    throw new TypeError("Unsupported ED diagnosis.");
  }

  const score = components.reduce((sum, component) => sum + component.points, 0);
  const category = riskCategory(score);
  return Object.freeze({ score, components, ...category });
}

export function managementContext(tier) {
  if (tier === "Very Low" || tier === "Low") {
    return "In the 2020 validation report, very-low- and low-risk patients could generally be discharged after ED evaluation when no serious cause was identified. Apply clinical judgment and local protocols.";
  }
  if (tier === "Medium") {
    return "The 2020 validation report describes shared decision-making regarding disposition for medium-risk patients. Apply clinical judgment and local protocols.";
  }
  return "The 2020 validation report describes a short course of hospitalization as a reasonable option for higher-risk patients. Apply clinical judgment and local protocols.";
}
