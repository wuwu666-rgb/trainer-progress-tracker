// After sign-in, take the client back to a pending offline workout so the
// recording page can upload it with the current session's CSRF token.
(() => {
  if (document.querySelector("#workout-editor")) return;
  const script = document.currentScript;
  // With defer, currentScript identifies the script currently executing.
  const userId = script?.dataset.userId;
  if (!userId) return;
  const prefix = "onetrainer-draft-";
  let keys;
  try { keys = Object.keys(localStorage); } catch { return; }
  for (const key of keys) {
    if (!key.startsWith(prefix)) continue;
    let draft;
    try { draft = JSON.parse(localStorage.getItem(key)); } catch { continue; }
    // Older drafts with no owner remain available by manually reopening the
    // workout; do not automatically send one from an unknown account.
    if (!draft?.pending || String(draft.ownerId) !== userId) continue;
    const workoutId = key.slice(prefix.length);
    if (!/^[1-9]\d*$/.test(workoutId)) continue;
    const attemptKey = "onetrainer-resume-attempt-" + workoutId;
    const attempt = `${draft.savedAt}:${userId}`;
    try {
      if (sessionStorage.getItem(attemptKey) === attempt) continue;
      sessionStorage.setItem(attemptKey, attempt);
    } catch { /* Still try once if session storage is unavailable. */ }
    window.location.assign(`/workouts/${workoutId}/record`);
    return;
  }
})();
