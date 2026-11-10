// Offline recording for the workout page: keeps entries in this browser,
// restores them after a reload or lost connection, and syncs on reconnect.
// Loaded before workout.js so restored fields exist when the guide starts.
(() => {
  const editor = document.querySelector("#workout-editor");
  if (!editor || !editor.dataset.syncUrl) return;

  const status = document.querySelector("#workout-sync-status");
  const exercises = document.querySelector("#workout-exercises");
  const setTemplate = document.querySelector("#workout-new-set");
  const exerciseTemplate = document.querySelector("#workout-new-exercise");
  const pageRevision = Number(editor.dataset.revision);
  const PREFIX = "onetrainer-draft-";
  const KEY = PREFIX + editor.dataset.workoutId;
  const MAX_AGE = 14 * 24 * 60 * 60 * 1000;
  let touched = false;
  let syncing = false;
  let allowLeave = false;
  let locked = false; // true while the user decides what to do with an older draft
  let timer;

  // Browser storage can be blocked or full; recording must still work without it.
  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY));
    } catch {
      return null;
    }
  }

  function store(draft) {
    try {
      localStorage.setItem(KEY, JSON.stringify(draft));
      return true;
    } catch {
      return false;
    }
  }

  function clear() {
    try {
      localStorage.removeItem(KEY);
    } catch {}
  }

  function purgeOldDrafts() {
    try {
      for (const key of Object.keys(localStorage)) {
        if (!key.startsWith(PREFIX)) continue;
        const draft = JSON.parse(localStorage.getItem(key));
        if (!draft || Date.now() - draft.savedAt > MAX_AGE) localStorage.removeItem(key);
      }
    } catch {}
  }

  function setStatus(message, actions = []) {
    status.replaceChildren();
    if (!message) {
      status.hidden = true;
      return;
    }
    status.append(message);
    for (const [label, handler] of actions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "workspace-secondary";
      button.textContent = label;
      button.addEventListener("click", handler);
      status.append(" ", button);
    }
    status.hidden = false;
  }

  function showIdle() {
    const pending = load()?.pending;
    if (pending) {
      setStatus(pending === "complete"
        ? "Workout finished on this device. It will be saved when you are back online."
        : "Draft saved on this device. It will sync when you are back online.");
    } else if (!navigator.onLine) {
      setStatus("You are offline. Your entries are saved on this device and will sync when you reconnect.");
    } else {
      setStatus("");
    }
  }

  function collect() {
    return Array.from(new FormData(editor)).filter(
      ([name, value]) => typeof value === "string" && name !== "csrf_token" && name !== "revision",
    );
  }

  function saveDraft(pending) {
    if (locked) return;
    const existing = load();
    store({
      baseRevision: existing?.baseRevision ?? pageRevision,
      savedAt: Date.now(),
      entries: collect(),
      pending: pending === undefined ? existing?.pending ?? null : pending,
    });
  }

  function schedule() {
    touched = true;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => saveDraft(), 300);
  }

  function flush() {
    if (!touched) return;
    window.clearTimeout(timer);
    saveDraft();
  }

  function fillKey(node, key) {
    node.querySelectorAll("[name]").forEach((field) => {
      field.name = field.name.replace("__KEY__", key);
      if (field.name === "exercise_key") field.value = key;
    });
    return node;
  }

  function restore(entries) {
    const values = new Map();
    for (const [name, value] of entries) {
      if (!values.has(name)) values.set(name, []);
      values.get(name).push(value);
    }
    const keys = values.get("exercise_key") || [];
    exercises.querySelectorAll("[data-workout-exercise]").forEach((exercise) => {
      if (!keys.includes(exercise.dataset.workoutExercise) && exercise.querySelector("[data-remove-exercise]")) {
        exercise.remove();
      }
    });
    for (const key of keys) {
      let exercise = exercises.querySelector(`[data-workout-exercise="${key}"]`);
      if (!exercise && exerciseTemplate && /^new-\d+$/.test(key)) {
        exercise = fillKey(exerciseTemplate.content.firstElementChild.cloneNode(true), key);
        exercise.dataset.workoutExercise = key;
        exercises.append(exercise);
      }
      if (!exercise) continue;
      const name = exercise.querySelector("[data-exercise-name]");
      if (name && values.has(`name_${key}`)) name.value = values.get(`name_${key}`)[0];
      const unit = exercise.querySelector("[data-set-unit]");
      if (unit && values.has(`unit_${key}`)) unit.value = values.get(`unit_${key}`)[0];

      const container = exercise.querySelector("[data-workout-sets]");
      const results = values.get(`result_${key}`) || [];
      const weights = values.get(`weight_${key}`) || [];
      const rows = Array.from(container.querySelectorAll("[data-workout-set]"));
      while (rows.length > results.length) rows.pop().remove();
      while (rows.length < results.length) {
        const row = fillKey(setTemplate.content.firstElementChild.cloneNode(true), key);
        container.append(row);
        rows.push(row);
      }
      rows.forEach((row, index) => {
        row.querySelector("[data-set-result]").value = results[index] ?? "";
        row.querySelector("[data-set-weight]").value = weights[index] ?? "";
      });
    }
    const date = editor.querySelector('[name="workout_date"]');
    if (date && values.has("workout_date")) date.value = values.get("workout_date")[0];
    touched = true;
  }

  function leave(url) {
    allowLeave = true;
    window.location.assign(url);
  }

  async function sync() {
    const draft = load();
    if (!draft?.pending || syncing || !navigator.onLine) return;
    syncing = true;
    setStatus("Syncing your offline entries…");
    const body = new URLSearchParams(draft.entries);
    body.set("revision", String(draft.baseRevision));
    body.set("action", draft.pending);
    try {
      const response = await fetch(editor.dataset.syncUrl, {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: { "X-CSRF-Token": editor.dataset.csrf, Accept: "application/json" },
      });
      if (response.redirected || !(response.headers.get("content-type") || "").includes("application/json")) {
        setStatus("Sign in again to sync. Your entries are kept on this device.", [
          ["Sign in", () => leave("/login")],
        ]);
        return;
      }
      const result = await response.json();
      if (response.ok && result.state === "ok") {
        clear();
        if (result.complete) {
          leave(result.url);
        } else {
          const next = new URL(window.location.href);
          next.searchParams.set("saved", "1");
          leave(next);
        }
        return;
      }
      // Keep the local copy; stop retrying until the user decides.
      store({ ...draft, pending: null });
      if (result.state === "completed") {
        setStatus(result.error, [["View workout", () => leave(result.url)]]);
      } else if (result.state === "conflict") {
        setStatus(result.error, [["Reload to review", () => leave(window.location.href)]]);
      } else {
        setStatus(result.error || "Your entries could not be saved. Check them and try again.");
      }
    } catch {
      setStatus("Still offline. Your entries are saved on this device and will sync when you reconnect.");
    } finally {
      syncing = false;
    }
  }

  function startup() {
    purgeOldDrafts();
    let draft = load();
    if (draft && !draft.pending && new URLSearchParams(window.location.search).get("saved") === "1") {
      clear();
      draft = null;
    }
    if (!draft) {
      showIdle();
      return;
    }
    if (draft.baseRevision === pageRevision) {
      restore(draft.entries);
      if (draft.pending) sync();
      else setStatus("Restored the unsaved entries from this device.");
      if (!draft.pending && navigator.onLine === false) showIdle();
      return;
    }
    locked = true;
    setStatus(
      "This workout changed since you recorded entries on this device. Use your entries or discard them?",
      [
        ["Use my entries", () => {
          locked = false;
          restore(draft.entries);
          store({ ...draft, baseRevision: pageRevision, pending: null, savedAt: Date.now() });
          setStatus("Your entries are back in the form. Review them, then save.");
        }],
        ["Discard them", () => {
          locked = false;
          clear();
          showIdle();
        }],
      ],
    );
  }

  editor.addEventListener("input", schedule);
  editor.addEventListener("change", schedule);
  editor.addEventListener("click", (event) => {
    if (event.target.closest("button[type=button]")) window.setTimeout(schedule, 0);
  });
  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
  window.addEventListener("beforeunload", (event) => {
    // Runs before workout.js's own prompt: a finished sync should not ask to stay.
    if (allowLeave) event.stopImmediatePropagation();
  });
  window.addEventListener("online", () => {
    if (load()?.pending) sync();
    else showIdle();
  });
  window.addEventListener("offline", showIdle);

  // Bubbling to document means workout.js's own submit handlers already ran,
  // including the "Finish this workout?" confirmation that may cancel the submit.
  document.addEventListener("submit", (event) => {
    if (event.defaultPrevented) return;
    if (event.target.id === "workout-discard") {
      if (navigator.onLine) {
        clear();
      } else {
        event.preventDefault();
        window.alert("Reconnect to discard this draft.");
      }
      return;
    }
    if (event.target !== editor || navigator.onLine) return;
    const action = event.submitter?.value;
    if (action !== "save" && action !== "complete") return;
    event.preventDefault();
    window.clearTimeout(timer);
    touched = true;
    saveDraft(action);
    showIdle();
  });

  startup();
})();
