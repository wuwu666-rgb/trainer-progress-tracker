const exerciseList = document.querySelector("#exercise-list");
const exerciseFields = document.querySelector("#exercise-fields");
let showingInvalidExercise = false;

function updateExerciseButtons() {
  const buttons = exerciseList.querySelectorAll("[data-remove-exercise]");
  for (const button of buttons) {
    button.hidden = buttons.length === 1;
  }
  for (const card of exerciseList.children) {
    const up = card.querySelector('[data-move-exercise="up"]');
    const down = card.querySelector('[data-move-exercise="down"]');
    if (up && down) {
      up.disabled = !card.previousElementSibling;
      down.disabled = !card.nextElementSibling;
    }
  }
}

document.querySelector("#add-exercise").addEventListener("click", () => {
  exerciseList.append(exerciseFields.content.cloneNode(true));
  updateExerciseButtons();
  const card = exerciseList.lastElementChild;
  if (card.matches("details")) card.open = true;
  card.querySelector("input").focus();
});

exerciseList.addEventListener("invalid", (event) => {
  const card = event.target.closest("[data-plan-exercise]");
  if (card && !showingInvalidExercise) {
    card.open = true;
    showingInvalidExercise = true;
    window.setTimeout(() => { showingInvalidExercise = false; }, 0);
  }
  const weightDetails = event.target.closest(".target-weight");
  if (weightDetails) weightDetails.open = true;
}, true);

exerciseList.addEventListener("input", (event) => {
  const card = event.target.closest("[data-plan-exercise]");
  if (!card) return;
  const exercise = card.querySelector('[name="exercise"]').value.trim();
  const sets = card.querySelector('[name="target_sets"]').value;
  const reps = card.querySelector('[name="target_reps"]').value;
  card.querySelector("[data-plan-exercise-name]").textContent = exercise || "New exercise";
  card.querySelector("[data-plan-exercise-targets]").textContent =
    sets && reps ? `${sets} sets × ${reps} reps` : "";
});

exerciseList.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  const card = button.closest("#exercise-list > *");
  if (button.matches("[data-remove-exercise]") && exerciseList.children.length > 1) {
    card.remove();
  } else if (button.dataset.moveExercise === "up" && card.previousElementSibling) {
    card.previousElementSibling.before(card);
  } else if (button.dataset.moveExercise === "down" && card.nextElementSibling) {
    card.nextElementSibling.after(card);
  }
  updateExerciseButtons();
  if (button.dataset.moveExercise) {
    (button.disabled ? card.querySelector("input") : button).focus();
  }
});

updateExerciseButtons();
