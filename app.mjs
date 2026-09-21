import { calculateCsrs, managementContext } from "./csrs.mjs";

const $ = (id) => document.getElementById(id);
const form = $("csrsForm");
const sbp = $("sbp");
const sbpError = $("sbpError");
const resultHeading = $("resultHeading");
const scoreValue = $("scoreValue");
const rateValue = $("rateValue");
const riskBadge = $("riskBadge");
const interpretation = $("interpretation");
const componentList = $("componentList");
const componentCount = $("componentCount");

function selectedDiagnosis() {
  return form.elements.diagnosis.value;
}

function readInput() {
  return {
    predispositionVasovagal: $("predisposition").checked,
    historyHeartDisease: $("heartDisease").checked,
    systolicBp: sbp.value,
    troponinElevated: $("troponin").checked,
    ecgAbnormalAxis: $("axis").checked,
    ecgProlongedQrs: $("qrs").checked,
    ecgProlongedQtc: $("qtc").checked,
    edDiagnosis: selectedDiagnosis(),
  };
}

function setBadge(tier) {
  riskBadge.className = "risk-badge";
  if (tier === "Very Low" || tier === "Low") riskBadge.classList.add("low");
  else if (tier === "Medium") riskBadge.classList.add("medium");
  else riskBadge.classList.add("high");
  riskBadge.textContent = tier;
}

function render(result) {
  sbpError.hidden = true;
  sbp.removeAttribute("aria-invalid");
  resultHeading.textContent = `${result.tier} risk category`;
  scoreValue.textContent = result.score > 0 ? `+${result.score}` : String(result.score);
  rateValue.textContent = `${result.rate.toFixed(1)}%`;
  setBadge(result.tier);
  interpretation.textContent = managementContext(result.tier);
  componentList.replaceChildren();
  componentCount.textContent = String(result.components.length);

  if (result.components.length === 0) {
    const item = document.createElement("li");
    item.className = "muted";
    item.textContent = "No point-scoring components selected.";
    componentList.append(item);
    return;
  }

  for (const component of result.components) {
    const item = document.createElement("li");
    const sign = component.points > 0 ? "+" : "";
    item.textContent = `${component.label} (${sign}${component.points})`;
    componentList.append(item);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    render(calculateCsrs(readInput()));
  } catch (error) {
    sbpError.textContent = error instanceof Error ? error.message : "Invalid input.";
    sbpError.hidden = false;
    sbp.setAttribute("aria-invalid", "true");
    sbp.focus();
  }
});

$("resetButton").addEventListener("click", () => {
  form.reset();
  sbp.value = "120";
  sbpError.hidden = true;
  sbp.removeAttribute("aria-invalid");
  resultHeading.textContent = "Ready to calculate";
  scoreValue.textContent = "0";
  rateValue.textContent = "—";
  riskBadge.className = "risk-badge neutral";
  riskBadge.textContent = "—";
  interpretation.textContent = "Enter the published score components and select Analyze.";
  componentCount.textContent = "0";
  const item = document.createElement("li");
  item.className = "muted";
  item.textContent = "No calculation yet.";
  componentList.replaceChildren(item);
});

const themeToggle = $("themeToggle");
const root = document.documentElement;
const preferredTheme = localStorage.getItem("csrs-theme");
if (preferredTheme === "dark" || preferredTheme === "light") root.dataset.theme = preferredTheme;

themeToggle.addEventListener("click", () => {
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("csrs-theme", next);
});
