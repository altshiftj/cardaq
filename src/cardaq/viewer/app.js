(() => {
  "use strict";

  const colors = ["#63e6be", "#ffad84", "#a7baff", "#f2d475", "#f4a9df", "#8fd9ee"];
  const favorites = [
    { id: "ecm_vehicle_speed_kph", title: "Vehicle speed", summary: "Peak" },
    { id: "ecm_engine_speed_rpm", title: "Engine speed", summary: "Peak" },
    { id: "ecm_coolant_sensor_1_c", title: "Coolant sensor 1", summary: "First reading" },
    { id: "derived_pulley_ratio", title: "Pulley ratio estimate", summary: "Range" },
  ];
  const metricGroups = ["Derived", "Shifter verification", "Recorded signals"];
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
  const byId = (id) => document.getElementById(id);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function swatch(color) {
    const marker = element("span", "drive-swatch");
    marker.style.color = color;
    marker.setAttribute("aria-hidden", "true");
    return marker;
  }

  function display(value, unit, formatValue = number.format) {
    if (value === undefined) return "—";
    const text = formatValue(value);
    return unit ? `${text} ${unit}` : text;
  }

  function displayRange(summary, unit, formatValue) {
    const maximum = display(summary.max, unit, formatValue);
    if (summary.min === summary.max) return maximum;
    return `${formatValue(summary.min)}–${maximum}`;
  }

  function metricPresentation(metric) {
    const unit = metric.unit === "ratio" ? "" : metric.unit;
    const formatter = Number.isInteger(metric.precision)
      ? new Intl.NumberFormat(undefined, { maximumFractionDigits: metric.precision })
      : number;
    const formatValue = metric.format === "hex"
      ? (value) => `0x${value.toString(16).toUpperCase().padStart(2, "0")} (${formatter.format(value)})`
      : formatter.format;
    return { ...metric, unit, formatValue };
  }

  function chartLabel(label, unit) {
    return `${label} over elapsed time${unit ? `, in ${unit}` : ""}`;
  }

  function duration(seconds) {
    const rounded = Math.round(seconds);
    return `${Math.floor(rounded / 60)}m ${String(rounded % 60).padStart(2, "0")}s`;
  }

  function summarize(points, end = Infinity) {
    let min = Infinity;
    let max = -Infinity;
    let count = 0;
    for (const [time, value] of points) {
      if (time > end) break;
      min = Math.min(min, value);
      max = Math.max(max, value);
      count += 1;
    }
    return count ? { min, max, count } : null;
  }

  function driveCard(drive) {
    const card = element("article", "drive-card");
    const name = element("h3", "drive-name");
    name.append(swatch(drive.color), element("span", "", drive.name));
    card.append(name);
    if (drive.started) card.append(element("p", "drive-meta", drive.started));

    const stats = element("dl", "drive-stats");
    const values = [
      ["Data span", duration(drive.span)],
      ["Peak speed", display(summarize(drive.series.ecm_vehicle_speed_kph ?? [])?.max, "km/h")],
      ["Peak RPM", display(summarize(drive.series.ecm_engine_speed_rpm ?? [])?.max, "rpm")],
    ];
    for (const [label, value] of values) {
      const stat = element("div", "drive-stat");
      stat.append(element("dt", "", label), element("dd", "", value));
      stats.append(stat);
    }
    card.append(stats);
    return card;
  }

  function lineSeries(drives, id) {
    return drives.map((drive) => ({
      label: drive.name,
      color: drive.color,
      points: drive.series[id] ?? [],
    }));
  }

  function seriesEnd(series) {
    return Math.max(1, ...series.map(({ points }) => points.at(-1)?.[0] ?? 0));
  }

  function metricStat(series, { unit, formatValue }, end) {
    const stat = element("div", "metric-stat");
    const name = element("span", "metric-stat-name");
    name.append(swatch(series.color), element("span", "", series.label));
    const summary = summarize(series.points, end);
    let values = "No samples in this window";
    if (summary) {
      const range = displayRange(summary, unit, formatValue);
      values = `${range} · ${number.format(summary.count)} ${summary.count === 1 ? "sample" : "samples"}`;
    }
    stat.append(name, element("span", "metric-stat-values", values));
    return stat;
  }

  function quickStat(points, statistic, { unit, formatValue }) {
    if (statistic === "First reading") return display(points[0]?.[1], unit, formatValue);
    const summary = summarize(points);
    if (!summary) return "—";
    return statistic === "Range"
      ? displayRange(summary, unit, formatValue)
      : display(summary.max, unit, formatValue);
  }

  function addMetricOptions(select, metrics, metricOrder) {
    const groups = new Map(metricGroups.map((label) => {
      const group = document.createElement("optgroup");
      group.label = label;
      return [label, group];
    }));
    for (const id of metricOrder) {
      const { label, unit, group } = metrics[id];
      const option = new Option(unit ? `${label} (${unit})` : label, id);
      (groups.get(group) ?? groups.get("Recorded signals")).append(option);
    }
    select.append(...Array.from(groups.values()).filter((group) => group.childElementCount));
    const defaultMetric = favorites[0].id;
    select.value = metrics[defaultMetric] ? defaultMetric : metricOrder[0];
  }

  function init() {
    const { drives, metrics: definitions } = JSON.parse(byId("capture-data").textContent);
    const metrics = Object.fromEntries(Object.entries(definitions).map(([id, metric]) => [
      id, metricPresentation(metric),
    ]));
    drives.forEach((drive, index) => { drive.color = colors[index % colors.length]; });
    byId("drive-list").replaceChildren(...drives.map(driveCard));

    const metric = byId("metric");
    const timeWindow = byId("window");
    const mainCanvas = byId("main-chart");
    const chart = new window.CardaQChart(mainCanvas, { interactive: true });
    const quickMetrics = favorites.filter(({ id }) => metrics[id]);
    const metricOrder = [...new Set([...quickMetrics.map(({ id }) => id), ...Object.keys(metrics)])];
    addMetricOptions(metric, metrics, metricOrder);

    function render() {
      const selectedMetric = metrics[metric.value];
      const { label, description, unit, style, formatValue } = selectedMetric;
      const series = lineSeries(drives, metric.value);
      const fullEnd = seriesEnd(series);
      const end = timeWindow.value === "full" ? fullEnd : Math.min(fullEnd, Number(timeWindow.value));
      byId("metric-title").textContent = label;
      byId("metric-description").textContent = description;
      mainCanvas.setAttribute("aria-label", chartLabel(label, unit));
      chart.render({ series, unit, style, formatValue, range: [0, end] });
      byId("metric-stats").replaceChildren(...series.map((line) => metricStat(line, selectedMetric, end)));
    }

    metric.addEventListener("change", render);
    timeWindow.addEventListener("change", render);

    const quickLooks = byId("quick-looks");
    quickLooks.closest("section").hidden = quickMetrics.length === 0;
    quickLooks.classList.toggle("quick-looks-four", quickMetrics.length === 4);
    for (const { id, title, summary } of quickMetrics) {
      const quickMetric = metrics[id];
      const { unit, style, formatValue } = quickMetric;
      const series = lineSeries(drives, id);
      const fragment = byId("quick-card-template").content.cloneNode(true);
      const button = fragment.querySelector("button");
      const canvas = fragment.querySelector("canvas");
      button.textContent = title;
      button.setAttribute("aria-label", `Open ${title.toLowerCase()} in the signal explorer`);
      button.addEventListener("click", () => {
        metric.value = id;
        timeWindow.value = "full";
        render();
        metric.focus();
      });
      canvas.setAttribute("aria-label", chartLabel(title, unit));
      const labels = series.map(({ label, points }) => `${label} ${quickStat(points, summary, quickMetric)}`);
      fragment.querySelector(".quick-summary").textContent = `${summary} · ${labels.join(" / ")}`;
      quickLooks.append(fragment);
      new window.CardaQChart(canvas).render({ series, unit, style, formatValue, range: [0, seriesEnd(series)] });
    }
    render();
  }

  try {
    init();
  } catch (error) {
    const status = byId("viewer-error");
    status.textContent = "The recordings could not be displayed. Regenerate the page with cardaq view.";
    status.hidden = false;
    console.error(error);
  }
})();
