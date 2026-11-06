const unit = document.querySelector("#result-unit");
const result = document.querySelector("#record-result");
const resultLabel = document.querySelector("#record-result-label");
const details = document.querySelector(".record-extra");
const date = document.querySelector("#record-date");
const dateSummary = document.querySelector("#record-date-summary");
const weight = document.querySelector("#record-weight");
const distance = document.querySelector("#record-distance");

unit.addEventListener("change", () => {
  const timed = unit.value === "minutes";
  resultLabel.textContent = timed ? "Duration" : "Reps";
  result.min = timed ? "0" : "1";
  result.step = timed ? "any" : "1";
  result.inputMode = timed ? "decimal" : "numeric";
  weight.closest("label").hidden = weight.disabled = timed;
  distance.closest("label").hidden = distance.disabled = !timed;
});

date.addEventListener("input", () => {
  dateSummary.textContent = date.value === date.max ? "Today" : date.value || "Choose a date";
});

details.addEventListener("invalid", () => {
  details.open = true;
}, true);
