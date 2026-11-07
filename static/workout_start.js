const planOptions = document.querySelector("[data-available-plans]");
const planPicker = document.querySelector("#workout-plan");
const startButton = planOptions.querySelector("button");
const statusMessage = planOptions.querySelector("[data-plan-status]");
let refreshing = false;

function updateStartButton() {
  const selected = planPicker.selectedOptions[0];
  startButton.textContent = selected?.hasAttribute("data-in-progress")
    ? "Continue workout"
    : "Record this workout";
  startButton.disabled = !planPicker.value;
}

async function refreshPlans() {
  if (!planOptions.open || document.hidden || refreshing) return;
  refreshing = true;
  try {
    const response = await fetch(planOptions.dataset.availablePlans, { redirect: "error" });
    if (!response.ok) throw new Error("Plan list unavailable");
    const { plans } = await response.json();
    const selectedPlan = planPicker.value;
    planPicker.replaceChildren(new Option(plans.length ? "Choose a plan" : "No plans available", ""));
    for (const plan of plans) {
      const option = new Option(plan.in_progress ? plan.name + " (draft)" : plan.name, plan.id);
      option.toggleAttribute("data-in-progress", plan.in_progress);
      planPicker.add(option);
    }
    if (plans.some((plan) => plan.id === selectedPlan)) planPicker.value = selectedPlan;
    updateStartButton();
    statusMessage.hidden = true;
  } catch {
    statusMessage.textContent = "Could not refresh plans. Close and reopen this section to try again.";
    statusMessage.hidden = false;
  } finally {
    refreshing = false;
  }
}

planOptions.addEventListener("toggle", refreshPlans);
planPicker.addEventListener("change", updateStartButton);
document.addEventListener("visibilitychange", refreshPlans);
window.addEventListener("pageshow", refreshPlans);
updateStartButton();
