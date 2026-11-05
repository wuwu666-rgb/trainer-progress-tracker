const exerciseType = document.querySelector("#exercise-type");

exerciseType.addEventListener("change", () => {
  for (const fields of document.querySelectorAll("[data-exercise-fields]")) {
    const active = fields.dataset.exerciseFields === exerciseType.value;
    fields.hidden = !active;
    fields.disabled = !active;
  }
});
