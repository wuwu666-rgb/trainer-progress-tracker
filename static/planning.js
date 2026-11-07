const exerciseList = document.querySelector("#exercise-list");
const exerciseFields = document.querySelector("#exercise-fields");

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
  exerciseList.lastElementChild.querySelector("input").focus();
});

exerciseList.addEventListener("invalid", (event) => {
  const weightDetails = event.target.closest(".target-weight");
  if (weightDetails) weightDetails.open = true;
}, true);

exerciseList.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  const card = button.closest("fieldset");
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
