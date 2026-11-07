const editor = document.querySelector("#workout-editor");
const exercises = document.querySelector("#workout-exercises");
const exerciseTemplate = document.querySelector("#workout-new-exercise");
const setTemplate = document.querySelector("#workout-new-set");
const discard = document.querySelector("#workout-discard");
let nextExercise = 1;
let dirty = false;
let showingInvalid = false;

function makeFields(template, key) {
  const fields = template.content.firstElementChild.cloneNode(true);
  fields.querySelectorAll("[name]").forEach((field) => {
    field.name = field.name.replace("__KEY__", key);
    if (field.name === "exercise_key") field.value = key;
  });
  return fields;
}

function updateExercises() {
  exercises.querySelectorAll("[data-workout-exercise]").forEach((exercise, index) => {
    const name = exercise.querySelector("[data-exercise-name]");
    if (name) {
      exercise.querySelector("[data-exercise-title]").textContent = name.value.trim() || `Exercise ${index + 1}`;
    }
  });
}

function updateSets(exercise) {
  const unit = exercise.querySelector("[data-set-unit]");
  if (unit) unit.dataset.lastUnit = unit.value;
  const timed = unit?.value === "minutes";
  exercise.querySelectorAll("[data-workout-set]").forEach((set, index) => {
    const number = index + 1;
    const result = set.querySelector("[data-set-result]");
    set.querySelector("[data-set-number]").textContent = `Set ${number}`;
    set.querySelector("[data-remove-set]").setAttribute("aria-label", `Remove set ${number}`);
    set.querySelector("[data-result-label]").textContent = timed ? "Minutes" : "Reps";
    set.querySelector("[data-weight-field]").hidden = timed;
    set.querySelector("[data-set-weight]").readOnly = timed;
    result.min = timed ? "0" : "1";
    result.step = timed ? "any" : "1";
    result.inputMode = timed ? "decimal" : "numeric";
  });
  updateSetProgress(exercise);
}

function updateSetProgress(exercise) {
  const results = exercise.querySelectorAll("[data-set-result]");
  const count = Array.from(results).filter((result) => result.validity.valid && result.valueAsNumber > 0).length;
  const progress = exercise.querySelector("[data-set-progress]");
  progress.hidden = count === 0;
  progress.textContent = `${count} ${count === 1 ? "set" : "sets"} entered`;
}

function addExercise() {
  let key;
  do {
    key = `new-${nextExercise++}`;
  } while (exercises.querySelector(`[data-workout-exercise="${key}"]`));
  const exercise = makeFields(exerciseTemplate, key);
  exercise.dataset.workoutExercise = key;
  exercises.append(exercise);
  exercise.open = true;
  updateSets(exercise);
  updateExercises();
  exercise.querySelector("[data-exercise-name]").focus();
}

editor.addEventListener("click", (event) => {
  const button = event.target.closest("button[type=button]");
  if (!button) return;
  dirty = true;
  if (button.id === "workout-add-exercise") {
    addExercise();
    return;
  }

  const exercise = button.closest("[data-workout-exercise]");
  if (button.hasAttribute("data-add-set")) {
    const set = makeFields(setTemplate, exercise.dataset.workoutExercise);
    exercise.querySelector("[data-workout-sets]").append(set);
    updateSets(exercise);
    set.querySelector("[data-set-result]").focus();
  } else if (button.hasAttribute("data-remove-set")) {
    button.closest("[data-workout-set]").remove();
    updateSets(exercise);
    exercise.querySelector("[data-add-set]").focus();
  } else if (button.hasAttribute("data-remove-exercise")) {
    exercise.remove();
    updateExercises();
    document.querySelector("#workout-add-exercise").focus();
  }
});

editor.addEventListener("input", (event) => {
  dirty = true;
  if (event.target.matches("[data-exercise-name]")) updateExercises();
  if (event.target.matches("[data-set-result]")) {
    updateSetProgress(event.target.closest("[data-workout-exercise]"));
  }
});
editor.addEventListener("change", (event) => {
  if (!event.target.matches("[data-set-unit]")) return;
  const unit = event.target;
  const exercise = unit.closest("[data-workout-exercise]");
  const fields = Array.from(exercise.querySelectorAll("[data-set-result], [data-set-weight]"));
  if (fields.some((field) => field.value) && !window.confirm("Changing the unit clears the sets for this exercise. Continue?")) {
    unit.value = unit.dataset.lastUnit;
    return;
  }
  fields.forEach((field) => {
    field.value = "";
  });
  updateSets(exercise);
});
editor.addEventListener("invalid", (event) => {
  if (showingInvalid) return;
  showingInvalid = true;
  const details = event.target.closest("details");
  if (details) details.open = true;
  window.setTimeout(() => { showingInvalid = false; }, 0);
}, true);
editor.addEventListener("submit", () => {
  dirty = false;
});
discard.addEventListener("submit", (event) => {
  if (window.confirm("Discard this draft and its saved sets?")) {
    dirty = false;
  } else {
    event.preventDefault();
  }
});
window.addEventListener("beforeunload", (event) => {
  if (!dirty) return;
  event.preventDefault();
  event.returnValue = true;
});
window.addEventListener("pageshow", (event) => {
  if (event.persisted && !dirty) window.location.reload();
});

exercises.querySelectorAll("[data-workout-exercise]").forEach(updateSets);
document.querySelector("[data-workout-error]")?.focus();
