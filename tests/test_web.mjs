import assert from "node:assert/strict";
import { calculateCsrs, riskCategory } from "../csrs.mjs";

const base = {
  predispositionVasovagal: false,
  historyHeartDisease: false,
  systolicBp: 120,
  troponinElevated: false,
  ecgAbnormalAxis: false,
  ecgProlongedQrs: false,
  ecgProlongedQtc: false,
  edDiagnosis: "unknown",
};

assert.equal(calculateCsrs(base).score, 0);
assert.equal(calculateCsrs({ ...base, predispositionVasovagal: true }).score, -1);
assert.equal(calculateCsrs({ ...base, systolicBp: 89 }).score, 2);
assert.equal(calculateCsrs({ ...base, systolicBp: 181 }).score, 2);
assert.equal(calculateCsrs({ ...base, ecgProlongedQrs: true }).score, 1);
assert.deepEqual(riskCategory(-2), { min: -3, max: -2, tier: "Very Low", rate: 0.2 });
assert.deepEqual(riskCategory(0), { min: -1, max: 0, tier: "Low", rate: 0.7 });
assert.deepEqual(riskCategory(3), { min: 1, max: 3, tier: "Medium", rate: 8.0 });
assert.deepEqual(riskCategory(5), { min: 4, max: 5, tier: "High", rate: 19.2 });
assert.deepEqual(riskCategory(11), { min: 6, max: 11, tier: "Very High", rate: 51.3 });
assert.throws(() => calculateCsrs({ ...base, systolicBp: 0 }), /finite positive/);
console.log("Web calculator tests passed.");
