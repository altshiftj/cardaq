(() => {
  "use strict";

  const colors = ["#63e6be", "#ffad84", "#a7baff", "#f2d475"];
  const observers = new WeakMap();

  function html(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function svg(tag, attributes, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function clock(seconds, precise = false) {
    const millis = Math.round(seconds * 1000);
    const minutes = Math.floor(millis / 60000);
    const wholeSeconds = String(Math.floor(millis / 1000) % 60).padStart(2, "0");
    const fraction = precise ? String(millis % 1000).padStart(3, "0").replace(/0+$/, "") : "";
    return `${minutes}:${wholeSeconds}${fraction ? "." + fraction : ""}`;
  }

  function figure(frame, guide) {
    const title = frame.parentElement.querySelector("summary").textContent;
    const note = html("p", guide, "chart-instructions");
    const plot = svg("svg", {width: "100%", "aria-label": title});
    frame.replaceChildren(note, plot);
    return {frame, plot};
  }

  function label(plot, x, y, text, attributes = {}) {
    plot.append(svg("text", {x, y, fill: "var(--muted)", "font-size": 12, ...attributes}, text));
  }

  function timeStep(end, width) {
    const target = end / Math.max(2, Math.floor(width / 82));
    const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
    return steps.find(step => step >= target) || Math.ceil(target / 3600) * 3600;
  }

  function axes(plot, width, height, end) {
    plot.replaceChildren();
    plot.setAttribute("height", height);
    plot.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const left = width < 480 ? 60 : 84;
    const right = width - 20;
    const bottom = height - 42;
    const x = seconds => left + (right - left) * seconds / end;
    const step = timeStep(end, right - left);
    for (let seconds = 0; seconds <= end; seconds += step) {
      const at = x(seconds);
      plot.append(svg("line", {x1: at, x2: at, y1: 10, y2: bottom, stroke: "var(--line)"}));
      label(plot, at, bottom + 16, clock(seconds), {"text-anchor": "middle"});
    }
    label(plot, (left + right) / 2, height - 6, "Elapsed time (min:sec)", {"text-anchor": "middle"});
    return {x, left, right};
  }

  function eventText(cylinder, poll) {
    const before = poll.count - poll.delta;
    return `Cylinder ${cylinder} · ${clock(poll.previousSeconds, true)} to ${clock(poll.seconds, true)} elapsed · counter ${before} → ${poll.count} (+${poll.delta})`;
  }

  function drawEvents(plot, width, end, channels, readout) {
    const {x, left, right} = axes(plot, width, 204, end);
    for (const [index, {cylinder, polls}] of channels.entries()) {
      const y = 24 + index * 40;
      const color = colors[index];
      label(plot, left - 9, y + 4, `Cyl ${cylinder}`, {fill: color, "text-anchor": "end"});
      plot.append(svg("line", {x1: left, x2: right, y1: y, y2: y, stroke: "var(--line)"}));
      if (!polls.length) {
        label(plot, left + 6, y - 6, "No readings");
        continue;
      }
      const ticks = polls.map(poll => `M ${x(poll.seconds)} ${y - 3} v 6`).join(" ");
      plot.append(svg("path", {d: ticks, stroke: "var(--muted)", opacity: 0.7}));
      for (const poll of polls.filter(reading => reading.delta > 0)) {
        const start = x(poll.previousSeconds);
        const stop = x(poll.seconds);
        const description = eventText(cylinder, poll);
        const mark = svg("g", {
          class: "misfire-marker", tabindex: 0, role: "button", "aria-label": description
        });
        mark.append(svg("title", {}, description));
        mark.append(svg("path", {
          d: `M ${start} ${y - 5} v 10 M ${start} ${y} H ${stop}`,
          fill: "none", stroke: color, "stroke-width": 2
        }));
        mark.append(svg("circle", {cx: stop, cy: y, r: 10, fill: "transparent"}));
        mark.append(svg("circle", {cx: stop, cy: y, r: 5, fill: color}));
        if (poll.delta > 1) {
          label(mark, stop, y - 9, `+${poll.delta}`, {fill: color, "text-anchor": "middle"});
        }
        const show = () => { readout.textContent = description; };
        mark.addEventListener("focus", show);
        mark.addEventListener("pointerenter", show);
        mark.addEventListener("click", show);
        mark.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            show();
          }
        });
        plot.append(mark);
      }
    }
  }

  function drawTotals(plot, width, end, channels) {
    const {x, left, right} = axes(plot, width, 304, end);
    const maximum = Math.max(1, ...channels.map(({polls}) => polls.at(-1)?.cumulative || 0));
    for (const [index, {cylinder, polls}] of channels.entries()) {
      const floor = 57 + index * 65;
      const color = colors[index];
      const y = total => floor - total / maximum * 38;
      label(plot, 8, y(maximum) + 22, `Cyl ${cylinder}`, {fill: color});
      for (const count of [maximum, 0]) {
        label(plot, left - 6, y(count) + 3, count, {"text-anchor": "end", "font-size": 10});
        plot.append(svg("line", {x1: left, x2: right, y1: y(count), y2: y(count), stroke: "var(--line)"}));
      }
      if (!polls.length) {
        label(plot, left + 6, floor - 13, "No readings");
        continue;
      }
      const first = polls[0];
      const last = polls.at(-1);
      const steps = [`M ${x(first.seconds)} ${floor}`];
      for (const poll of polls) {
        if (poll.delta > 0) steps.push(`H ${x(poll.seconds)} V ${y(poll.cumulative)}`);
      }
      steps.push(`H ${x(last.seconds)}`);
      plot.append(svg("path", {d: steps.join(" "), stroke: color, "stroke-width": 2.5, fill: "none"}));
      plot.append(svg("circle", {cx: x(last.seconds), cy: y(last.cumulative), r: 3.5, fill: color}));
      const anchorRight = x(last.seconds) > right - 44;
      label(plot, x(last.seconds) + (anchorRight ? -6 : 6), y(last.cumulative) - 5,
        String(last.cumulative), {fill: color, "text-anchor": anchorRight ? "end" : "start"});
    }
  }

  function eventLog(events) {
    const wrap = html("div", undefined, "notebook-table-wrap");
    wrap.tabIndex = 0;
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", "Detection intervals");
    const table = html("table", undefined, "notebook-table");
    const header = table.createTHead().insertRow();
    for (const name of ["Cylinder", "Previous reading", "Increase seen", "Counter", "Added"]) {
      const cell = html("th", name);
      cell.scope = "col";
      header.append(cell);
    }
    const body = table.createTBody();
    for (const {cylinder, poll} of events) {
      const row = body.insertRow();
      for (const value of [cylinder, clock(poll.previousSeconds, true), clock(poll.seconds, true),
        `${poll.count - poll.delta} → ${poll.count}`, `+${poll.delta}`]) {
        row.insertCell().textContent = value;
      }
    }
    wrap.append(table);
    return wrap;
  }

  function counterNotes(channels) {
    const notes = [];
    for (const {cylinder, polls} of channels) {
      const first = polls[0];
      if (first?.count > 0) {
        notes.push(`Cylinder ${cylinder} already read ${first.count} at its first check (${clock(first.seconds, true)}). That sets its starting point.`);
      }
      for (const poll of polls) {
        if (poll.delta < 0) {
          notes.push(`Cylinder ${cylinder} fell from ${poll.count - poll.delta} to ${poll.count} at ${clock(poll.seconds, true)}. The observed total carried forward.`);
        }
      }
    }
    return notes.join(" ");
  }

  window.renderMisfirePlots = function renderMisfirePlots(drive, container) {
    observers.get(container)?.disconnect();
    observers.delete(container);
    const channels = drive?.misfires || [];
    const haveReadings = channels.some(({polls}) => polls.length);
    for (const panel of container.querySelectorAll(".misfire-plot")) panel.hidden = !haveReadings;
    container.querySelector("#misfire-empty").hidden = !drive || haveReadings;
    if (!haveReadings) return;

    const events = channels.flatMap(({cylinder, polls}) =>
      polls.filter(poll => poll.delta > 0).map(poll => ({cylinder, poll}))
    ).sort((a, b) => a.poll.seconds - b.poll.seconds || a.cylinder - b.cylinder);
    const eventsChart = figure(container.querySelector("#misfire-events-chart"),
      "Each short gray tick is a counter reading. A colored dot marks the first reading that showed an increase. The bar to its left reaches back to the previous reading. The computer could have counted the misfire anywhere in that interval. A dot labeled +2 means two new counts appeared between those checks.");
    eventsChart.plot.setAttribute("role", "group");
    const comparable = channels.some(({polls}) => polls.length > 1);
    let message = "Each cylinder has at most one reading. A second reading is needed to detect a rise.";
    if (comparable) message = "No increases appeared between the available readings.";
    if (events.length) message = "Hover, tap or focus a dot for both reading times and the change in count.";
    const readout = html("p", message, "chart-instructions");
    readout.setAttribute("aria-live", "polite");
    eventsChart.frame.append(readout);
    const log = container.querySelector("#misfire-log");
    log.hidden = !events.length;
    log.querySelector("summary").textContent = `Detection intervals (${events.length})`;
    log.querySelector("div").replaceChildren(...(events.length ? [eventLog(events)] : []));

    const totalsChart = figure(container.querySelector("#misfire-totals-chart"),
      "Each cylinder starts at zero at its first reading. Its line steps up by the size of each observed increase and ends at its last reading. If the computer’s counter drops, the running total keeps the increases already seen. A flat line means no additional increase was observed. A rise and reset between readings can go unseen.");
    totalsChart.plot.setAttribute("role", "img");
    totalsChart.plot.setAttribute("aria-label", "Cumulative observed misfires. " + channels.map(({cylinder, polls}) =>
      `Cylinder ${cylinder}, ${polls.length ? polls.at(-1).cumulative : "no readings"}`
    ).join(". "));
    const notes = counterNotes(channels);
    if (notes) totalsChart.frame.append(html("p", notes, "chart-instructions"));

    const end = Math.max(1, drive.span || 0, ...channels.map(({polls}) => polls.at(-1)?.seconds || 0));
    let previousWidth = 0;
    function draw() {
      const width = Math.max(160, Math.round(container.getBoundingClientRect().width));
      if (width === previousWidth) return;
      previousWidth = width;
      drawEvents(eventsChart.plot, width, end, channels, readout);
      drawTotals(totalsChart.plot, width, end, channels);
    }
    draw();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(draw);
      observer.observe(container);
      observers.set(container, observer);
    }
  };
})();
