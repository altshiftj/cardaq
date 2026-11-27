(() => {
  "use strict";

  const colors = ["#63e6be", "#ffad84", "#a7baff", "#f2d475", "#f4a9df", "#8fd9ee"];
  const favorites = [
    { id: "ecm_vehicle_speed_kph", title: "Vehicle speed", summary: "Peak" },
    { id: "ecm_engine_speed_rpm", title: "Engine speed", summary: "Peak" },
    { id: "ecm_coolant_sensor_1_c", title: "Coolant sensor 1", summary: "First reading" },
    { id: "derived_pulley_ratio", title: "Pulley ratio estimate", summary: "Range" },
    { id: "derived_crank_torque_nm", title: "ECU-estimated crank torque", summary: "Range" },
    { id: "derived_crank_power_hp", title: "ECU-estimated crank horsepower", summary: "Range" },
  ];
  const metricGroups = ["Derived", "Shifter verification", "Recorded signals", "Capture quality"];
  const operatingMetrics = [
    ["derived_pulley_ratio", "Pulley ratio estimate", "Think of pedaling a bike beside someone riding at the same speed. The higher dot is like having to pedal more times for each turn of the wheel. Here we estimate that from two spinning parts inside the transmission."],
    ["ecm_engine_speed_rpm", "Engine speed", "Pick a speed you held on both trips. The higher dot means the engine was usually spinning faster on that drive, even though the car was traveling at about the same speed."],
    ["ecm_engine_fuel_rate_g_s", "Engine fuel rate", "A higher dot means the engine was using gas faster at that road speed. That can happen going uphill even if the speedometer barely moves."],
    ["derived_crank_torque_nm", "ECU-estimated crank torque", "At this road speed, a higher dot means the ECU estimates more turning effort at the crankshaft."],
    ["derived_crank_power_kw", "ECU-estimated crank power", "At this road speed, compare the estimated mechanical output in kW. Grade and acceleration can change the power demand."],
    ["derived_crank_power_hp", "ECU-estimated crank horsepower", "Compare estimated crankshaft output in mechanical horsepower across the same road-speed bands."],
    ["derived_air_mass_per_cylinder_mg", "Air mass per intake event", "Each time a cylinder fills, it takes in a gulp of air. At the same road speed, the higher dot means the average gulp contained more air on that drive."],
  ];
  const distanceId = "derived_distance_km";
  const metricInputs = {
    derived_crank_torque_nm: ["ecm_indicated_torque_pct", "ecm_friction_torque_pct", "ecm_reference_torque_nm"],
    derived_crank_power_kw: ["derived_crank_torque_nm", "ecm_engine_speed_rpm"],
    derived_crank_power_hp: ["derived_crank_power_kw"],
    derived_pulley_ratio: ["candidate_drive_pulley_rpm", "candidate_driven_pulley_rpm"],
    derived_torque_converter_slip_rpm: ["honda_engine_speed_rpm", "candidate_torque_converter_turbine_rpm"],
    derived_drive_minus_turbine_rpm: ["candidate_drive_pulley_rpm", "candidate_torque_converter_turbine_rpm"],
    derived_longitudinal_acceleration_m_s2: ["ecm_vehicle_speed_kph"],
    derived_cvt_minus_coolant_c: ["candidate_cvt_fluid_temperature_c", "ecm_coolant_sensor_1_c"],
    derived_converter_slip_pct: ["derived_torque_converter_slip_rpm", "honda_engine_speed_rpm"],
    derived_ratio_change_pct_s: ["derived_pulley_ratio"],
    derived_output_speed_change_pct_s: ["candidate_driven_pulley_rpm"],
    derived_manifold_vacuum_kpa: ["ecm_barometric_pressure_kpa", "ecm_manifold_pressure_kpa"],
    derived_coolant_sensor_difference_c: ["ecm_coolant_sensor_1_c", "ecm_coolant_sensor_2_c"],
    derived_engine_coolant_warming_rate: ["ecm_coolant_sensor_1_c"],
    derived_cvt_fluid_warming_rate: ["candidate_cvt_fluid_temperature_c"],
    derived_catalyst_warming_rate: ["ecm_catalyst_temperature_c"],
    derived_distance_km: ["ecm_vehicle_speed_kph"],
    derived_engine_revolutions: ["ecm_engine_speed_rpm"],
    derived_fuel_used_g: ["ecm_engine_fuel_rate_g_s"],
    derived_rolling_fuel_g_km: ["derived_fuel_used_g", "derived_distance_km"],
    derived_rolling_revolutions_per_km: ["derived_engine_revolutions", "derived_distance_km"],
    derived_rolling_fuel_per_1000_rev: ["derived_fuel_used_g", "derived_engine_revolutions"],
    derived_engine_on_stopped_s: ["ecm_vehicle_speed_kph", "ecm_engine_speed_rpm"],
    derived_engine_on_stopped_fuel_g: ["ecm_engine_fuel_rate_g_s", "derived_engine_on_stopped_s"],
    derived_positive_speed_energy_j_kg: ["ecm_vehicle_speed_kph"],
    derived_air_mass_per_cylinder_mg: ["ecm_mass_airflow_g_s", "ecm_engine_speed_rpm"],
    derived_fuel_cut_candidate: ["ecm_engine_fuel_rate_g_s", "ecm_accelerator_pedal_pct", "ecm_vehicle_speed_kph", "ecm_engine_speed_rpm"],
  };
  const distanceSampleGap = 1.5;
  const speedBand = 10;
  const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
  const tripNumber = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
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

  function chartLabel(label, unit, axis = "elapsed time") {
    return `${label} over ${axis}${unit ? `, in ${unit}` : ""}`;
  }

  function duration(seconds) {
    const rounded = Math.round(seconds);
    return `${Math.floor(rounded / 60)}m ${String(rounded % 60).padStart(2, "0")}s`;
  }

  function summarize(points, end = Infinity, start = 0) {
    let min = Infinity;
    let max = -Infinity;
    let count = 0;
    for (const [time, value] of points) {
      if (time > end) break;
      if (time < start) continue;
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
    if (drive.vehicle) {
      const code = drive.vehicle.vin_sha256?.slice(0, 12);
      card.append(element("p", "drive-meta", [drive.vehicle.label, code].filter(Boolean).join(" · ")));
    }

    const stats = element("dl", "drive-stats");
    const values = [
      ["Data span", duration(drive.span)],
      ["Peak speed", display(summarize(drive.series.ecm_vehicle_speed_kph ?? [])?.max, "km/h")],
      ["Peak RPM", display(summarize(drive.series.ecm_engine_speed_rpm ?? [])?.max, "rpm")],
    ];
    const { distanceKm, engineRevolutions, fuelGrams, engineOnStoppedSeconds } = drive.summary ?? {};
    if (Number.isFinite(distanceKm)) values.push(["Distance", `${tripNumber.format(distanceKm)} km`]);
    if (Number.isFinite(engineRevolutions)) {
      values.push(["Engine revs", `${number.format(Math.round(engineRevolutions))} rev`]);
    }
    if (Number.isFinite(fuelGrams)) values.push(["Fuel used", `${tripNumber.format(fuelGrams / 1000)} kg`]);
    if (Number.isFinite(engineOnStoppedSeconds)) {
      values.push(["Stopped, engine on", duration(engineOnStoppedSeconds)]);
    }
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
      dashed: drive.dashed,
      points: drive.series[id] ?? [],
    }));
  }

  function distanceSeries(drives, id, end) {
    return drives.map(({ name, color, dashed, series }) => {
      const sourcePoints = series[id] ?? [];
      const distance = series[distanceId] ?? [];
      const points = [];
      const sampleTimes = [];
      const segmentBreaks = new Set();
      let index = 0;
      let segment = 0;
      let previousSegment = 0;
      for (const [time, value] of sourcePoints) {
        if (time > end) break;
        while (distance[index]?.[0] < time) {
          const next = distance[index + 1];
          if (next && next[0] - distance[index][0] > distanceSampleGap) segment += 1;
          index += 1;
        }
        const after = distance[index];
        if (!after) break;
        let position = after[1];
        if (time !== after[0]) {
          const before = distance[index - 1];
          if (!before || after[0] - before[0] > distanceSampleGap) continue;
          const fraction = (time - before[0]) / (after[0] - before[0]);
          position = before[1] + fraction * (after[1] - before[1]);
        }
        if (points.length && segment !== previousSegment) segmentBreaks.add(points.length);
        previousSegment = segment;
        points.push([position, value]);
        sampleTimes.push(time);
      }
      return { label: name, color, dashed, points, sourcePoints, sampleTimes, segmentBreaks };
    });
  }

  function seriesEnd(series) {
    return Math.max(1, ...series.map(({ points }) => points.at(-1)?.[0] ?? 0));
  }

  function windowReading(points, [start, end], metric) {
    const values = [];
    for (const [position, value] of points) {
      if (position > end) break;
      if (position >= start) values.push(value);
    }
    if (!values.length) return "No samples in this window";
    const samples = `${number.format(values.length)} ${values.length === 1 ? "sample" : "samples"}`;
    const show = (value) => display(value, metric.unit, metric.formatValue);
    if (metric.format === "hex") {
      const counts = new Map();
      for (const code of values) counts.set(code, (counts.get(code) ?? 0) + 1);
      const ranked = [...counts].sort(([a, n], [b, m]) => m - n || a - b);
      const common = ranked.slice(0, 3).map(([code, n]) => `${metric.formatValue(code)} × ${number.format(n)}`);
      const more = ranked.length > 3 ? ` · +${ranked.length - 3} other codes` : "";
      return `${samples} · ${common.join(", ")}${more}`;
    }
    if (metric.summary === "flag") {
      const flagged = values.filter((value) => value === 1).length;
      return `${number.format(flagged)} of ${samples} flagged`;
    }
    const first = values[0];
    const last = values.at(-1);
    if (values.length === 1) return `${show(first)} · ${samples}`;
    if (metric.summary === "change") {
      return `First ${show(first)} → last ${show(last)} · net change ${show(last - first)} · ${samples}`;
    }
    values.sort((a, b) => a - b);
    const min = values[0];
    const max = values.at(-1);
    if (min === max) return `${show(min)} in all ${samples}`;
    const reading = metric.unit === "°C" && metric.group === "Recorded signals"
      ? `First ${show(first)} → last ${show(last)}`
      : `Sample median ${show(quantile(values, 0.5))}`;
    return `${reading} · range ${displayRange({ min, max }, metric.unit, metric.formatValue)} · ${samples}`;
  }

  function metricStat(series, metric, range) {
    const stat = element("div", "metric-stat");
    const name = element("span", "metric-stat-name");
    name.append(swatch(series.color), element("span", "", series.label));
    stat.append(name, element("span", "metric-stat-values", windowReading(series.points, range, metric)));
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

  function enableMetricSearch(select) {
    const input = byId(`${select.id}-search`);
    const list = byId(`${select.id}-options`);
    const menu = list.parentElement;
    const empty = menu.querySelector('[role="status"]');
    const rows = [];
    for (const child of select.children) {
      const grouped = child instanceof HTMLOptGroupElement;
      const group = grouped ? element("div") : list;
      if (grouped) {
        group.setAttribute("role", "group");
        group.setAttribute("aria-label", child.label);
        const heading = element("div", "signal-group-name", child.label);
        heading.setAttribute("aria-hidden", "true");
        group.append(heading);
        list.append(group);
      }
      for (const option of grouped ? child.children : [child]) {
        const row = element("div", "", option.label);
        row.id = `${list.id}-${option.index}`;
        row.dataset.value = option.value;
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", "false");
        group.append(row);
        rows.push({ option, row, text: option.label.toLowerCase() });
      }
    }

    let matches = [];
    let active;
    function highlight(row) {
      active?.setAttribute("aria-selected", "false");
      active = row;
      if (row) {
        row.setAttribute("aria-selected", "true");
        input.setAttribute("aria-activedescendant", row.id);
        if (row.offsetTop < menu.scrollTop) menu.scrollTop = row.offsetTop;
        else if (row.offsetTop + row.offsetHeight > menu.scrollTop + menu.clientHeight) {
          menu.scrollTop = row.offsetTop + row.offsetHeight - menu.clientHeight;
        }
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function filter() {
      const query = input.value.trim().toLowerCase();
      matches = [];
      for (const { option, row, text } of rows) {
        row.hidden = option.disabled || !text.includes(query);
        if (!row.hidden) matches.push(row);
      }
      for (const group of list.querySelectorAll('[role="group"]')) {
        group.hidden = !group.querySelector('[role="option"]:not([hidden])');
      }
      empty.hidden = matches.length > 0;
      menu.hidden = false;
      input.setAttribute("aria-expanded", "true");
      menu.scrollTop = 0;
      const current = !query && matches.find(row => row.dataset.value === select.value);
      highlight(current || matches[0]);
    }

    function open() {
      input.value = "";
      filter();
    }
    function close() {
      menu.hidden = true;
      highlight(null);
      input.setAttribute("aria-expanded", "false");
      input.value = select.selectedOptions[0]?.label ?? "";
    }
    function choose(row) {
      select.value = row.dataset.value;
      close();
      input.select();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    input.addEventListener("focus", () => input.select());
    input.addEventListener("click", () => { if (menu.hidden) open(); });
    input.addEventListener("input", filter);
    input.addEventListener("blur", close);
    input.addEventListener("keydown", event => {
      if (event.isComposing) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (menu.hidden) open();
        else {
          const index = matches.indexOf(active) + (event.key === "ArrowDown" ? 1 : -1);
          highlight(matches[Math.max(0, Math.min(index, matches.length - 1))]);
        }
      } else if (!menu.hidden && event.key === "Enter" && active) {
        event.preventDefault();
        choose(active);
      } else if (!menu.hidden && event.key === "Escape") {
        event.preventDefault();
        close();
        input.select();
      }
    });
    menu.addEventListener("mousedown", event => event.preventDefault());
    list.addEventListener("click", event => {
      const row = event.target.closest('[role="option"]');
      if (row) choose(row);
    });
    return close;
  }

  function nearestValue(points, time, maxAge) {
    let low = 0;
    let high = points.length;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (points[middle][0] < time) low = middle + 1;
      else high = middle;
    }
    const before = points[low - 1];
    const after = points[low];
    const earlierAge = before ? time - before[0] : Infinity;
    const laterAge = after ? after[0] - time : Infinity;
    if (Math.min(earlierAge, laterAge) > maxAge) return undefined;
    return (earlierAge <= laterAge ? before : after)[1];
  }

  function quantile(sorted, fraction) {
    const position = (sorted.length - 1) * fraction;
    const low = Math.floor(position);
    return sorted[low] + (sorted[Math.ceil(position)] - sorted[low]) * (position - low);
  }

  function operatingBins(drive, metric, loadBand) {
    const {
      ecm_vehicle_speed_kph: speed = [],
      honda_vehicle_speed_kph: hondaSpeed = [],
      ecm_calculated_load_pct: load = [],
    } = drive.series;
    const bands = new Map();
    for (const [time, value] of drive.series[metric] ?? []) {
      const roadSpeed = (metric === "derived_pulley_ratio" ? nearestValue(hondaSpeed, time, 0) : undefined)
        ?? nearestValue(speed, time, 0.75);
      if (!(roadSpeed > 0)) continue;
      if (loadBand !== "all") {
        const loadValue = nearestValue(load, time, 1.6);
        if (loadValue === undefined) continue;
        const band = loadValue < 35 ? "low" : loadValue < 65 ? "medium" : "high";
        if (loadBand !== band) continue;
      }
      const center = (Math.floor(roadSpeed / speedBand) + 0.5) * speedBand;
      if (!bands.has(center)) bands.set(center, []);
      bands.get(center).push(value);
    }
    const points = [];
    for (const [center, observations] of bands) {
      if (observations.length < 3) continue;
      observations.sort((a, b) => a - b);
      points.push([center, quantile(observations, 0.5), quantile(observations, 0.25),
        quantile(observations, 0.75), observations.length]);
    }
    return { label: drive.name, color: drive.color, dashed: drive.dashed, points: points.sort((a, b) => a[0] - b[0]) };
  }

  function speedBandText(center) {
    const half = speedBand / 2;
    return `${center - half}–<${center + half} km/h`;
  }

  function renderOperatingValues(series, metric) {
    const table = byId("operating-values");
    const columns = series.map(({ points }) => new Map(points.map((point) => [point[0], point])));
    const centers = [...new Set(columns.flatMap((column) => [...column.keys()]))].sort((a, b) => a - b);
    const heading = element("thead");
    const headRow = element("tr");
    for (const name of ["Speed band", ...series.map(({ label }) => label)]) {
      const cell = element("th", "", name);
      cell.scope = "col";
      headRow.append(cell);
    }
    heading.append(headRow);

    const body = element("tbody");
    for (const center of centers) {
      const row = element("tr");
      const label = element("th", "", speedBandText(center));
      label.scope = "row";
      row.append(label);
      for (const column of columns) {
        const cell = element("td");
        const point = column.get(center);
        if (point) {
          const [, median, lower, upper, count] = point;
          cell.append(
            element("span", "", display(median, metric.unit, metric.formatValue)),
            element("small", "", `IQR ${metric.formatValue(lower)}–${metric.formatValue(upper)} · n=${count}`),
          );
        } else {
          cell.textContent = "—";
        }
        row.append(cell);
      }
      body.append(row);
    }
    table.replaceChildren(heading, body);
    table.closest("details").hidden = !centers.length;
  }

  function initOperatingMap(getDrives, metrics) {
    const map = byId("operating-map");
    const usableMetrics = operatingMetrics.filter(([id]) => metrics[id]);
    if (!usableMetrics.length) return;

    const metricSelect = byId("operating-metric");
    const loadSelect = byId("operating-load");
    for (const [id, label] of usableMetrics) {
      const { unit } = metrics[id];
      metricSelect.append(new Option(unit ? `${label} (${unit})` : label, id));
    }
    byId("operating-load-control").hidden = !metrics.ecm_calculated_load_pct;
    const canvas = byId("operating-chart");
    const chart = new window.CardaQChart(canvas, { interactive: true });
    const xAxis = { bucketWidth: speedBand, formatCursor: speedBandText, label: "Road speed (km/h)" };

    function render() {
      const drives = getDrives();
      map.hidden = !drives.some(({ series }) =>
        series.ecm_vehicle_speed_kph?.length || series.honda_vehicle_speed_kph?.length);
      if (map.hidden) return;
      const maxSpeed = drives.reduce((maximum, { series }) => Math.max(
        maximum,
        summarize(series.ecm_vehicle_speed_kph ?? [])?.max ?? 0,
        summarize(series.honda_vehicle_speed_kph ?? [])?.max ?? 0,
      ), 0);
      const range = [0, (Math.floor(maxSpeed / speedBand) + 1) * speedBand];
      const id = metricSelect.value;
      const metric = metrics[id];
      const series = drives.map((drive) => operatingBins(drive, id, loadSelect.value));
      byId("operating-interpretation").textContent = usableMetrics[metricSelect.selectedIndex][2];
      canvas.setAttribute("aria-label", `${metric.label} by road speed`);
      chart.render({ series, unit: metric.unit, style: "binned", formatValue: metric.formatValue, range, xAxis });
      const stats = byId("operating-stats");
      stats.replaceChildren(...series.map(({ label, color, points }) => {
        const stat = element("div", "metric-stat");
        const name = element("span", "metric-stat-name");
        name.append(swatch(color), element("span", "", label));
        const count = points.reduce((sum, point) => sum + point[4], 0);
        const summary = points.length
          ? `${number.format(count)} plotted samples · ${points.length} speed bands`
          : "No speed bands with enough samples";
        stat.append(name, element("span", "metric-stat-values", summary));
        return stat;
      }));
      renderOperatingValues(series, metric);
    }

    metricSelect.addEventListener("change", render);
    loadSelect.addEventListener("change", render);
    return render;
  }

  function notebookHeader(label, drives) {
    const head = element("thead");
    const row = element("tr");
    const first = element("th", "", label);
    first.scope = "col";
    row.append(first);
    for (const drive of drives) {
      const heading = element("th");
      heading.scope = "col";
      const name = element("span", "notebook-drive-label");
      name.append(swatch(drive.color), element("span", "", drive.name));
      heading.append(name);
      row.append(heading);
    }
    head.append(row);
    return head;
  }

  function warmupTable(drives) {
    const targets = new Map();
    const signalOrder = new Map();
    const columns = drives.map(({ thermal = [] }) => {
      const values = new Map();
      for (const milestone of thermal ?? []) {
        const { label, target, seconds } = milestone;
        if (!label || !Number.isFinite(target) || !Number.isFinite(seconds) || seconds < 0) continue;
        if (!signalOrder.has(label)) signalOrder.set(label, signalOrder.size);
        const key = JSON.stringify([label, target]);
        targets.set(key, { label, target });
        values.set(key, milestone);
      }
      return values;
    });
    byId("thermal-panel").hidden = !targets.size;
    if (!targets.size) return false;
    const ordered = [...targets].sort(([, first], [, second]) =>
      signalOrder.get(first.label) - signalOrder.get(second.label) || first.target - second.target,
    );
    const rows = element("tbody");
    for (const [key, { label, target }] of ordered) {
      const row = element("tr");
      const title = element("th");
      title.scope = "row";
      title.append(element("span", "", label), element("small", "", `${number.format(target)} °C`));
      row.append(title);
      for (const column of columns) {
        const point = column.get(key);
        const cell = element("td");
        if (point) {
          cell.append(element("span", "", point.alreadyWarm ? "At start" : duration(point.seconds)));
          if (Number.isFinite(point.distanceKm)) {
            cell.append(element("small", "", `${tripNumber.format(point.distanceKm / 1.609344)} mi`));
          }
        } else {
          cell.textContent = "—";
          cell.setAttribute("aria-label", "No milestone recorded");
        }
        row.append(cell);
      }
      rows.append(row);
    }
    byId("thermal-values").replaceChildren(notebookHeader("Threshold", drives), rows);
    return true;
  }

  function dwellTable(drives) {
    const bands = new Set();
    let maximum = 0;
    const columns = drives.map(({ dwell = [] }) => {
      const values = new Map();
      for (const { label, seconds } of dwell ?? []) {
        if (!label || !Number.isFinite(seconds) || seconds < 0) continue;
        bands.add(label);
        values.set(label, seconds);
        maximum = Math.max(maximum, seconds);
      }
      return values;
    });
    byId("dwell-panel").hidden = !bands.size;
    if (!bands.size) return false;
    const rows = element("tbody");
    for (const label of bands) {
      const row = element("tr");
      const title = element("th", "", label);
      title.scope = "row";
      row.append(title);
      for (const [index, column] of columns.entries()) {
        const seconds = column.get(label);
        const cell = element("td", "dwell-cell", seconds === undefined ? "—" : duration(seconds));
        if (seconds !== undefined) {
          const track = element("span", "dwell-track");
          track.setAttribute("aria-hidden", "true");
          const bar = element("span", "dwell-bar");
          bar.style.backgroundColor = drives[index].color;
          bar.style.width = `${maximum ? seconds / maximum * 100 : 0}%`;
          track.append(bar);
          cell.append(track);
        }
        row.append(cell);
      }
      rows.append(row);
    }
    const table = byId("dwell-values");
    table.style.setProperty("--dwell-drives", drives.length);
    table.replaceChildren(notebookHeader("Speed band", drives), rows);
    return true;
  }

  function eventTime(event) {
    const start = duration(event.start);
    const end = duration(event.end);
    return start === end ? start : `${start}–${end}`;
  }

  function renderTripEvents(drives, openEvent) {
    const recordings = drives.map((drive) => ({
      drive,
      events: (drive.events ?? []).filter(({ start, end, kind, label }) =>
        Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end >= start && kind && label,
      ).sort((a, b) => a.start - b.start),
    })).filter(({ events }) => events.length);
    byId("event-panel").hidden = !recordings.length;
    if (!recordings.length) return false;
    const driveSelect = byId("event-drive");
    const kindSelect = byId("event-kind");
    const eventList = byId("trip-events");
    const previousDrive = driveSelect.value;
    driveSelect.replaceChildren(...recordings.map(({ drive }) => new Option(drive.name, drive.id)));
    if (recordings.some(({ drive }) => drive.id === previousDrive)) driveSelect.value = previousDrive;
    const current = () => recordings[driveSelect.selectedIndex];
    byId("event-drive-control").hidden = recordings.length === 1;

    function renderEvents() {
      const { drive, events } = current();
      const buttons = [];
      for (const event of events) {
        if (kindSelect.value && event.kind !== kindSelect.value) continue;
        const item = element("li");
        const button = element("button", "trip-event");
        button.type = "button";
        const when = element("span", "trip-event-time", eventTime(event));
        const detail = element("span", "trip-event-detail");
        detail.append(element("span", "trip-event-name", event.label));
        if (event.description) detail.append(element("span", "trip-event-description", event.description));
        button.append(when, detail);
        button.addEventListener("click", () => openEvent(event, drive));
        item.append(button);
        buttons.push(item);
      }
      eventList.replaceChildren(...buttons);
      eventList.scrollTop = 0;
      byId("events-empty").hidden = buttons.length > 0;
    }

    function renderFilter() {
      const { events } = current();
      const kinds = new Map(events.map(({ kind, label }) => [kind, label]));
      const previous = kindSelect.value;
      kindSelect.replaceChildren(new Option("All events", ""));
      for (const [kind, label] of kinds) kindSelect.add(new Option(label, kind));
      if (kinds.has(previous)) kindSelect.value = previous;
      byId("event-kind-control").hidden = kinds.size < 2;
      renderEvents();
    }
    driveSelect.onchange = renderFilter;
    kindSelect.onchange = renderEvents;
    renderFilter();
    return true;
  }

  function eventRange(event, endOfSeries) {
    const context = Math.min(30, Math.max(10, (event.end - event.start) * 0.18));
    return [Math.max(0, event.start - context), Math.min(endOfSeries, event.end + context)];
  }

  function initSectionNav() {
    const nav = byId("section-nav");
    const header = nav.closest("header");
    const entries = Array.from(nav.querySelectorAll("a"), link => ({
      link, section: byId(link.hash.slice(1)),
    }));
    let visible = [];
    let queued = false;

    function highlight() {
      queued = false;
      const inset = header.offsetHeight + 20;
      let current = visible[0];
      for (const entry of visible) {
        if (entry.section.getBoundingClientRect().top > inset) break;
        current = entry;
      }
      if (window.scrollY > 0 && window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) {
        current = visible.at(-1);
      }
      for (const entry of entries) {
        if (entry === current) entry.link.setAttribute("aria-current", "location");
        else entry.link.removeAttribute("aria-current");
      }
    }

    window.addEventListener("scroll", () => {
      if (!queued) {
        queued = true;
        requestAnimationFrame(highlight);
      }
    }, { passive: true });
    function sizeHeader() {
      document.documentElement.style.setProperty("--masthead-height", `${header.offsetHeight}px`);
      highlight();
    }
    if (typeof ResizeObserver === "function") new ResizeObserver(sizeHeader).observe(header);
    else window.addEventListener("resize", sizeHeader);

    return () => {
      visible = entries.filter(({ section }) => !section.hidden);
      for (const { link, section } of entries) link.hidden = section.hidden;
      nav.hidden = !visible.length;
      sizeHeader();
    };
  }

  function init() {
    const { drives: recordings, metrics: definitions, comparisonNotes = {}, live } = JSON.parse(byId("capture-data").textContent);
    const saved = live && history.state?.library?.folder === live.folder ? history.state.library : {};
    let remember = () => ({});
    if (live) {
      const status = byId("library-status");
      const messages = [`Watching ${live.folder} for CSV changes.`];
      if (!recordings.length) messages.push("Waiting for a readable CarDAQ recording.");
      if (live.skipped.length) messages.push(`Unreadable recordings: ${live.skipped.join(", ")}.`);
      status.hidden = false;
      status.textContent = messages.join(" ");
      async function checkFolder() {
        try {
          const reply = await fetch("/revision", {cache: "no-store"});
          if (!reply.ok) throw new Error("Folder unavailable");
          if (await reply.text() !== live.revision) {
            history.replaceState({library: {folder: live.folder, ...remember()}}, "");
            location.reload();
            return;
          }
          status.textContent = messages.join(" ");
        } catch {
          status.textContent = "Folder viewer disconnected. Retrying in five seconds.";
        }
        setTimeout(checkFolder, 5000);
      }
      setTimeout(checkFolder, 5000);
      if (!recordings.length) {
        document.querySelector(".workspace").hidden = true;
        return;
      }
    }
    const metrics = Object.fromEntries(Object.entries(definitions).map(([id, metric]) => [
      id, metricPresentation(metric),
    ]));
    const filter = byId("drive-filter");
    const driveOptions = byId("drive-options");
    const toggles = recordings.map((drive, index) => {
      drive.id = String(index);
      drive.color = colors[index % colors.length];
      drive.dashed = index % 2 === 1;
      const label = element("label", "recording-choice");
      label.style.setProperty("--drive-color", drive.color);
      label.style.setProperty("--trace-style", drive.dashed ? "dashed" : "solid");
      const checkbox = element("input");
      checkbox.type = "checkbox";
      checkbox.checked = !saved.unchecked?.includes(drive.name);
      const name = element("span", "recording-name", drive.name);
      name.id = `recording-name-${index}`;
      checkbox.setAttribute("aria-labelledby", name.id);
      const distance = drive.summary?.distanceKm;
      const facts = [duration(drive.span)];
      if (Number.isFinite(distance)) facts.push(`${tripNumber.format(distance)} km`);
      const text = element("span", "recording-copy");
      text.append(name, element("span", "recording-facts", facts.join(" · ")));
      label.append(checkbox, text);
      driveOptions.append(label);
      return checkbox;
    });
    byId("recordings").hidden = false;
    for (const [id, open] of [["collapse-all", false], ["expand-all", true]]) {
      byId(id).addEventListener("click", () => {
        for (const panel of document.querySelectorAll(".workspace details")) panel.open = open;
      });
    }
    byId("fold-actions").hidden = false;
    function revealTarget(hash) {
      const target = byId(hash.slice(1));
      if (target === byId("top")) byId("recording-panel").open = true;
      for (let panel = target?.closest("details"); panel; panel = panel.parentElement.closest("details")) {
        panel.open = true;
      }
    }
    document.addEventListener("click", event => {
      const link = event.target.closest("a[href^='#']");
      if (link) revealTarget(link.hash);
    });
    window.addEventListener("hashchange", () => revealTarget(location.hash));
    let drives = recordings;

    const metric = byId("metric");
    const overlay = byId("overlay");
    const timeWindow = byId("window");
    const axis = byId("axis");
    const mainCanvas = byId("main-chart");
    const chart = new window.CardaQChart(mainCanvas, { interactive: true });
    const quickMetrics = favorites.filter(({ id }) => metrics[id]);
    const metricOrder = [...new Set([...quickMetrics.map(({ id }) => id), ...Object.keys(metrics)])];
    const scope = [`${recordings.length} recording${recordings.length === 1 ? "" : "s"}`];
    if (metricOrder.length) scope.push(`${metricOrder.length} signal${metricOrder.length === 1 ? "" : "s"}`);
    byId("report-scope").textContent = scope.join("  /  ");
    addMetricOptions(metric, metrics, metricOrder);
    addMetricOptions(overlay, metrics, metricOrder);
    overlay.value = metrics[saved.overlay] ? saved.overlay : "";
    if (metrics[saved.metric]) metric.value = saved.metric;
    const syncMetricSearch = enableMetricSearch(metric);
    const syncOverlaySearch = enableMetricSearch(overlay);
    if (saved.axis) axis.value = saved.axis;
    if (saved.window && saved.window !== "event") timeWindow.value = saved.window;
    let selection;
    remember = () => ({
      unchecked: recordings.filter((_, index) => !toggles[index].checked).map(drive => drive.name),
      metric: metric.value, overlay: overlay.value, axis: axis.value, window: timeWindow.value,
      panels: Array.from(document.querySelectorAll(".workspace details[id]"), panel => [panel.id, panel.open]),
      event: selection && {name: selection.drive.name, start: selection.event.start, kind: selection.event.kind},
    });

    function render() {
      const selectedMetric = metrics[metric.value];
      const { label, description, unit, style, formatValue } = selectedMetric;
      for (const option of overlay.options) option.disabled = option.value === metric.value;
      if (overlay.value === metric.value) overlay.value = "";
      syncMetricSearch();
      syncOverlaySearch();
      const second = metrics[overlay.value];
      let series = lineSeries(drives, metric.value);
      let extra = second ? lineSeries(drives, overlay.value) : [];
      const fullEnd = seriesEnd([...series, ...extra]);
      const activeEvent = timeWindow.value === "event" ? selection : undefined;
      const end = activeEvent || timeWindow.value === "full"
        ? fullEnd : Math.min(fullEnd, Number(timeWindow.value));
      let range = activeEvent
        ? eventRange(activeEvent.event, Math.max(end, activeEvent.drive.span, activeEvent.event.end))
        : [0, end];
      let xAxis;
      if (axis.value === "distance") {
        series = distanceSeries(drives, metric.value, end);
        if (second) extra = distanceSeries(drives, overlay.value, end);
        const distanceEnd = Math.max(
          0.001,
          ...drives.map(({ series }) => summarize(series[distanceId] ?? [], end)?.max ?? 0),
          ...series.map(({ points }) => points.at(-1)?.[0] ?? 0),
        );
        range = [0, distanceEnd];
        xAxis = {
          label: "Observed distance (km)",
          cursorTolerance: 0.15,
          formatCursor: (value) => `${tripNumber.format(value)} km`,
        };
      }
      byId("metric-title").textContent = label;
      byId("metric-description").textContent = selectedMetric.request
        ? `${description} (OBD ${selectedMetric.request})` : description;
      byId("metric-interpretation").textContent = selectedMetric.interpretation;
      byId("lesson-source-label").textContent = selectedMetric.group === "Derived"
        ? "How the math works" : "What the car measures";
      for (const field of ["plain", "source", "reading", "caution"]) {
        byId(`lesson-${field}`).textContent = selectedMetric.lesson[field];
      }
      const companions = (metricInputs[metric.value] ?? []).filter((id) => metrics[id]);
      const links = byId("lesson-related");
      links.hidden = companions.length === 0;
      links.replaceChildren();
      if (companions.length) {
        links.append(element("span", "", "Compare with"));
        for (const id of companions) {
          const button = element("button", "notebook-button", metrics[id].label);
          button.type = "button";
          button.addEventListener("click", () => {
            metric.value = id;
            render();
            byId("metric-search").focus();
          });
          links.append(button);
        }
      }
      const note = timeWindow.value === "full" && drives.length === recordings.length
        ? comparisonNotes[metric.value] : "";
      byId("comparison-note").hidden = !note;
      byId("comparison-note-text").textContent = note || "";
      const chartAxis = xAxis ? "observed distance" : "elapsed time";
      mainCanvas.setAttribute("aria-label", chartLabel(label, unit, chartAxis));
      const context = byId("event-context");
      context.hidden = !activeEvent;
      if (activeEvent) {
        const { drive, event } = activeEvent;
        byId("event-context-text").textContent = `${drive.name} · ${event.label} · ${eventTime(event)}`;
      }
      const chartGuide = "lesson-plain chart-instructions";
      mainCanvas.setAttribute("aria-describedby", activeEvent ? `event-context-text ${chartGuide}` : chartGuide);
      byId("chart-instructions").textContent = xAxis
        ? "Read left to right by distance traveled. Each color follows one drive. Switch to elapsed time to see stops and gaps. Hover, tap, or use the arrow keys for a reading."
        : "Read left to right as the drive goes on. Each color follows one drive. A gap means we missed readings. Hover, tap, or use the arrow keys for a reading.";
      if (second) {
        for (const line of series) {
          line.dashed = false;
          line.label = `${label} · ${line.label}`;
        }
        for (const line of extra) {
          Object.assign(line, { overlay: true, dashed: true, style: second.style || "line",
            unit: second.unit, formatValue: second.formatValue, label: `${second.label} · ${line.label}` });
        }
        const key = `Solid, left: ${label}. Dashed, right: ${second.label}. Each color follows one drive.`;
        byId("chart-instructions").textContent = key + " Hover, tap, or use the arrow keys for both readings.";
        mainCanvas.setAttribute("aria-label", key);
      }
      chart.render({ series: [...series, ...extra], unit, style, formatValue, range, xAxis, overlayUnit: second?.unit });
      byId("metric-stats").replaceChildren(...series.map(line => metricStat(line, selectedMetric, range)),
        ...extra.map(line => metricStat(line, second, range)));
    }

    metric.addEventListener("change", render);
    overlay.addEventListener("change", render);
    timeWindow.addEventListener("change", () => {
      if (timeWindow.value === "event") axis.value = "time";
      render();
    });
    axis.addEventListener("change", () => {
      if (axis.value === "distance" && timeWindow.value === "event") timeWindow.value = "full";
      render();
    });
    byId("event-reset").addEventListener("click", () => {
      timeWindow.value = "full";
      render();
      timeWindow.focus();
    });

    function openEvent(event, drive) {
      if (!selection) timeWindow.add(new Option("Selected event", "event"));
      selection = { event, drive };
      axis.value = "time";
      timeWindow.value = "event";
      const [start, end] = eventRange(event, Math.max(drive.span, event.end));
      const preferred = event.kind === "engine-start" || event.kind === "engine-restart"
        ? "ecm_engine_speed_rpm" : favorites[0].id;
      if (metric.value === favorites[0].id || !summarize(drive.series[metric.value] ?? [], end, start)) {
        const match = [preferred, ...metricOrder].find((id) =>
          metrics[id] && summarize(drive.series[id] ?? [], end, start),
        );
        if (match) metric.value = match;
      }
      byId("signal-explorer").open = true;
      render();
      byId("signal-explorer").scrollIntoView({ block: "start" });
      mainCanvas.focus({ preventScroll: true });
    }

    const quickLooks = byId("quick-looks");
    const updateQuickLooks = quickMetrics.map(({ id, title, summary }) => {
      const quickMetric = metrics[id];
      const { unit, style, formatValue } = quickMetric;
      const fragment = byId("quick-card-template").content.cloneNode(true);
      const button = fragment.querySelector("button");
      const canvas = fragment.querySelector("canvas");
      fragment.querySelector("h3").textContent = title;
      const arrow = element("span", "quick-arrow", "→");
      arrow.setAttribute("aria-hidden", "true");
      button.append(arrow);
      button.setAttribute("aria-label", `Open ${title.toLowerCase()} in the signal explorer`);
      button.addEventListener("click", () => {
        byId("signal-explorer").open = true;
        metric.value = id;
        timeWindow.value = "full";
        render();
        byId("signal-explorer").scrollIntoView({ block: "start" });
        byId("metric-search").focus({ preventScroll: true });
      });
      canvas.setAttribute("aria-label", chartLabel(title, unit));
      const table = fragment.querySelector(".quick-summary");
      table.setAttribute("aria-label", `${title} by drive`);
      table.querySelector(".quick-statistic").textContent = summary;
      const readings = table.tBodies[0];
      quickLooks.append(fragment);
      const quickChart = new window.CardaQChart(canvas);
      return () => {
        const series = lineSeries(drives, id);
        readings.replaceChildren(...series.map(({ label, color, points }) => {
          const row = element("tr");
          const heading = element("th");
          heading.scope = "row";
          const name = element("span", "quick-drive-name");
          name.append(swatch(color), element("span", "", label));
          heading.append(name);
          row.append(heading, element("td", "", quickStat(points, summary, quickMetric)));
          return row;
        }));
        quickChart.render({ series, unit, style, formatValue, range: [0, seriesEnd(series)] });
      };
    });
    const updateOperatingMap = initOperatingMap(() => drives, metrics);
    const updateNav = initSectionNav();
    const misfireDrive = byId("misfire-drive");
    const misfirePlots = byId("misfire-plots");
    function drawMisfires() {
      window.renderMisfirePlots(drives[misfireDrive.selectedIndex], misfirePlots);
    }
    misfireDrive.addEventListener("change", drawMisfires);

    function updateSelection() {
      drives = recordings.filter((_, index) => toggles[index].checked);
      if (selection && !drives.includes(selection.drive)) {
        if (timeWindow.value === "event") timeWindow.value = "full";
        timeWindow.querySelector('option[value="event"]').remove();
        selection = undefined;
      }
      const canPlotDistance = drives.some(({ series }) => (series[distanceId]?.at(-1)?.[1] ?? 0) > 0);
      byId("axis-control").hidden = !canPlotDistance;
      byId("timeline-controls").classList.toggle("has-distance-axis", canPlotDistance);
      if (drives.length && !canPlotDistance) axis.value = "time";
      byId("drive-list").replaceChildren(...drives.map(driveCard));
      byId("drive-count").textContent = `${drives.length} of ${recordings.length}`;
      byId("recording-details").hidden = !drives.length;
      byId("empty-selection").hidden = drives.length > 0;
      byId("signal-explorer").hidden = !drives.length || !metricOrder.length;
      const previousDrive = misfireDrive.value;
      misfireDrive.replaceChildren(...drives.map((drive) => new Option(drive.name, drive.id)));
      if (drives.some((drive) => drive.id === previousDrive)) misfireDrive.value = previousDrive;
      byId("misfire-history").hidden = !drives.length;
      drawMisfires();
      byId("quick-section").hidden = !drives.length || !quickMetrics.length;
      const haveEvents = renderTripEvents(drives, openEvent);
      const haveThermal = warmupTable(drives);
      const haveDwell = dwellTable(drives);
      byId("trip-notebook").hidden = !(haveEvents || haveThermal || haveDwell);
      if (drives.length && metricOrder.length) render();
      for (const update of updateQuickLooks) update();
      updateOperatingMap?.();
      updateNav();
    }
    filter.addEventListener("change", updateSelection);
    byId("restore-recordings").addEventListener("click", () => {
      for (const checkbox of toggles) checkbox.checked = true;
      updateSelection();
      toggles[0].focus();
    });
    if (saved.window === "event" && saved.event) {
      const drive = recordings.find(item => item.name === saved.event.name);
      const event = drive?.events.find(item => item.kind === saved.event.kind && item.start === saved.event.start);
      if (event) {
        selection = {drive, event};
        timeWindow.add(new Option("Selected event", "event"));
        timeWindow.value = "event";
      }
    }
    updateSelection();
    for (const [id, open] of saved.panels ?? []) {
      const panel = byId(id);
      if (panel instanceof HTMLDetailsElement) panel.open = open;
    }
    revealTarget(location.hash);
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
