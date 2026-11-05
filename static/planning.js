const exerciseList = document.querySelector("#exercise-list");
const exerciseFields = document.querySelector("#exercise-fields");

function updateRemoveButtons() {
  const buttons = exerciseList.querySelectorAll("[data-remove-exercise]");
  for (const button of buttons) {
    button.hidden = buttons.length === 1;
  }
}

document.querySelector("#add-exercise").addEventListener("click", () => {
  exerciseList.append(exerciseFields.content.cloneNode(true));
  updateRemoveButtons();
  exerciseList.lastElementChild.querySelector("input").focus();
});

exerciseList.addEventListener("click", (event) => {
  if (event.target.matches("[data-remove-exercise]") && exerciseList.children.length > 1) {
    event.target.closest("fieldset").remove();
    updateRemoveButtons();
  }
});

updateRemoveButtons();
