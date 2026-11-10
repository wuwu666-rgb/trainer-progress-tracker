// Progress charts: dependency-free SVG line charts drawn from the JSON in #chart-data.
(() => {
  const dataNode = document.querySelector("#chart-data");
  if (!dataNode) return;
  let data;
  try {
    data = JSON.parse(dataNode.textContent);
  } catch {
    return;
  }

  const SVG = "http://www.w3.org/2000/svg";
  const W = 600;
  const H = 260;
  const M = { top: 16, right: 20, bottom: 34, left: 52 };

  function el(name, attrs = {}, text) {
    const node = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const day = (iso) => Date.parse(`${iso}T00:00:00Z`);
  const shortDate = (iso) => new Date(day(iso)).toLocaleDateString(undefined, {
    month: "short", day: "numeric", timeZone: "UTC",
  });
  const longDate = (iso) => new Date(day(iso)).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
  });
  const trim = (number) => String(Math.round(number * 100) / 100);

  // Round axis bounds and ticks (1, 2, 2.5, 5 x 10^n) so labels read cleanly.
  function niceScale(values) {
    let low = Math.min(...values);
    let high = Math.max(...values);
    if (low === high) {
      low -= 1;
      high += 1;
    }
    const rough = (high - low) / 3;
    const magnitude = 10 ** Math.floor(Math.log10(rough));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((candidate) => candidate >= rough);
    const start = Math.max(0, Math.floor(low / step) * step);
    const end = Math.ceil(high / step) * step;
    const ticks = [];
    for (let value = start; value <= end + step / 2; value += step) ticks.push(value);
    return { min: start, max: end, ticks };
  }

  function message(container, text) {
    container.replaceChildren();
    const note = document.createElement("p");
    note.className = "chart-empty";
    note.textContent = text;
    container.append(note);
  }

  function lineChart(container, points, { label, unit }) {
    if (points.length < 2) {
      message(container, "Record at least two measurements to see a chart.");
      return;
    }
    const first = points[0];
    const last = points[points.length - 1];
    const change = last.value - first.value;
    const summary = `${label}: ${trim(first.value)} ${unit} on ${longDate(first.date)} to ` +
      `${trim(last.value)} ${unit} on ${longDate(last.date)}, ` +
      `${change === 0 ? "no change" : `${change > 0 ? "up" : "down"} ${trim(Math.abs(change))} ${unit}`}.`;

    const times = points.map((point) => day(point.date));
    const [t0, t1] = [times[0], times[times.length - 1]];
    const scale = niceScale(points.map((point) => point.value));
    const [v0, v1] = [scale.min, scale.max];
    const x = (time) => M.left + ((time - t0) / (t1 - t0 || 1)) * (W - M.left - M.right);
    const y = (value) => H - M.bottom - ((value - v0) / (v1 - v0)) * (H - M.top - M.bottom);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": summary, class: "chart-svg" });
    svg.append(el("title", {}, summary));

    for (const value of scale.ticks) {
      svg.append(
        el("line", { x1: M.left, x2: W - M.right, y1: y(value), y2: y(value), class: "chart-grid" }),
        el("text", { x: M.left - 8, y: y(value) + 4, "text-anchor": "end", class: "chart-tick" }, trim(value)),
      );
    }
    const tickIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
    for (const index of tickIndexes) {
      const anchor = index === 0 ? "start" : index === points.length - 1 ? "end" : "middle";
      svg.append(el("text", {
        x: x(times[index]), y: H - 10, "text-anchor": anchor, class: "chart-tick",
      }, shortDate(points[index].date)));
    }
    svg.append(el("polyline", {
      points: points.map((point, i) => `${x(times[i]).toFixed(1)},${y(point.value).toFixed(1)}`).join(" "),
      class: "chart-line",
    }));
    points.forEach((point, i) => {
      const dot = el("circle", { cx: x(times[i]).toFixed(1), cy: y(point.value).toFixed(1), r: 4, class: "chart-dot" });
      dot.append(el("title", {}, `${longDate(point.date)}: ${trim(point.value)} ${unit}`));
      svg.append(dot);
    });

    container.replaceChildren(svg);
    const caption = document.createElement("p");
    caption.className = "chart-caption";
    caption.textContent = summary;
    container.append(caption);
  }

  lineChart(document.querySelector("#chart-body-weight"), data.bodyWeight || [], {
    label: "Body weight", unit: "lb",
  });

  const exercises = data.exercises || [];
  const exerciseChart = document.querySelector("#chart-exercise");
  const picker = document.querySelector("#chart-exercise-picker");
  const select = document.querySelector("#chart-exercise-select");
  if (!exercises.length) {
    message(exerciseChart, "Record an exercise on at least two different days to see its progress.");
    return;
  }
  exercises.forEach((exercise, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = exercise.label;
    select.append(option);
  });
  picker.hidden = exercises.length < 2;

  function drawExercise() {
    const exercise = exercises[Number(select.value)];
    lineChart(exerciseChart, exercise.points, {
      label: `${exercise.name} ${exercise.unit === "minutes" ? "total time" : "top weight"}`,
      unit: exercise.unit === "minutes" ? "min" : "lb",
    });
  }
  select.addEventListener("change", drawExercise);
  drawExercise();
})();
