(() => {
  "use strict";

  const colors = {
    grid: "#293a48",
    axis: "#425463",
    label: "#a1b4c3",
    text: "#eef4f7",
    panel: "#18232d",
  };
  const font = "system-ui, sans-serif";
  const pointFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });
  const timeSteps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120, 180,
    300, 600, 900, 1200, 1800, 3600, 7200, 14400, 21600, 43200, 86400];

  function timeText(seconds, fractional = false) {
    const tenths = Math.max(0, Math.round(seconds * 10));
    const whole = fractional ? Math.floor(tenths / 10) : Math.round(seconds);
    const minutes = Math.floor(whole / 60);
    const clock = `${minutes}:${String(whole % 60).padStart(2, "0")}`;
    return fractional ? `${clock}.${tenths % 10}` : clock;
  }

  function lowerBound(points, time, afterExact = false) {
    let left = 0;
    let right = points.length;
    while (left < right) {
      const middle = (left + right) >>> 1;
      if (points[middle][0] < time || (afterExact && points[middle][0] === time)) {
        left = middle + 1;
      } else {
        right = middle;
      }
    }
    return left;
  }

  function gapThreshold(points) {
    const intervals = [];
    for (let index = 1; index < points.length; index += 1) {
      const interval = points[index][0] - points[index - 1][0];
      if (interval > 0) intervals.push(interval);
    }
    intervals.sort((left, right) => left - right);
    const center = (intervals.length - 1) / 2;
    const median = (intervals[Math.floor(center)] + intervals[Math.ceil(center)]) / 2;
    return Number.isFinite(median) ? Math.max(10, median * 5) : 10;
  }

  function gapBefore(entry, index) {
    const elapsed = entry.sampleTimes;
    const interval = elapsed
      ? elapsed[index] - elapsed[index - 1]
      : entry.points[index][0] - entry.points[index - 1][0];
    return entry.segmentBreaks?.has(index) || interval > entry.gap;
  }

  function numericStep(span, target) {
    const roughStep = span / target;
    const base = 10 ** Math.floor(Math.log10(roughStep));
    return [1, 2, 2.5, 5, 10].find((multiple) => multiple * base >= roughStep) * base;
  }

  function yAxis(series, target) {
    let minimum = Infinity;
    let maximum = -Infinity;
    for (const { points, start, end } of series) {
      for (let index = start; index < end; index += 1) {
        const [, value, lower = value, upper = value] = points[index];
        minimum = Math.min(minimum, lower);
        maximum = Math.max(maximum, upper);
      }
    }
    const hasSamples = Number.isFinite(minimum);
    if (!hasSamples) return { minimum: 0, maximum: 1, step: 0.25, hasSamples };
    const span = maximum - minimum;
    const padding = span === 0 ? Math.max(Math.abs(minimum) * 0.04, 0.1) : span * 0.04;
    const step = numericStep(span + padding * 2, target);
    const floor = Math.floor((minimum - padding) / step) * step;
    return {
      minimum: minimum >= 0 ? Math.max(0, floor) : floor,
      maximum: Math.ceil((maximum + padding) / step) * step,
      step,
      hasSamples,
    };
  }

  function strokeStyle(context, entry, width) {
    context.strokeStyle = entry.color;
    context.lineWidth = width;
    context.setLineDash(entry.dashed ? [5, 3] : []);
  }

  function formatNumber(value, step) {
    const exponent = Math.floor(Math.log10(step));
    const isHalfStep = Math.abs(step / 10 ** exponent - 2.5) < 1e-9;
    const decimals = Math.min(8, Math.max(0, -exponent + Number(isHalfStep)));
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: decimals })
      .format(Math.abs(value) < step * 0.001 ? 0 : value);
  }

  function pointText(point, unit, formatValue) {
    const value = formatValue(point[1]);
    const measurement = unit ? `${value} ${unit}` : value;
    return point[4] ? `${measurement} · n=${point[4]}` : measurement;
  }

  function truncate(context, text, width) {
    if (context.measureText(text).width <= width) return text;
    let shortened = text;
    while (shortened && context.measureText(`${shortened}…`).width > width) {
      shortened = shortened.slice(0, -1);
    }
    return `${shortened}…`;
  }

  class CardaQChart {
    constructor(canvas, { interactive = false } = {}) {
      this.canvas = canvas;
      this.context = canvas.getContext("2d");
      this.background = document.createElement("canvas");
      this.interactive = interactive;
      this.cursor = null;
      this.frame = null;
      if (interactive) this.bindCursor();
      if (typeof ResizeObserver === "function") {
        this.observer = new ResizeObserver(() => this.drawBackground());
        this.observer.observe(canvas);
      } else {
        window.addEventListener("resize", () => this.drawBackground());
      }
    }

    render({ series, unit = "", style, formatValue = pointFormatter.format, range, xAxis, overlayUnit }) {
      const [start, end] = range;
      this.range = [start, end > start ? end : start + 1];
      this.unit = unit;
      this.overlayUnit = overlayUnit;
      this.style = style;
      this.formatValue = formatValue;
      this.xAxis = xAxis;
      this.series = series.map((entry, index) => {
        const { points } = entry;
        return {
          ...entry,
          unit: entry.unit ?? unit,
          formatValue: entry.formatValue ?? formatValue,
          style: entry.style ?? style,
          dashed: entry.dashed ?? index % 2 === 1,
          start: lowerBound(points, this.range[0]),
          end: lowerBound(points, this.range[1], true),
          gap: this.xAxis?.bucketWidth ?? gapThreshold(entry.sourcePoints ?? points),
          markOffset: style === "binned" ? (index - (series.length - 1) / 2) * 5 : 0,
        };
      });
      this.cursor = null;
      if (this.interactive) {
        this.canvas.setAttribute("aria-valuemin", this.range[0]);
        this.canvas.setAttribute("aria-valuemax", this.range[1]);
        this.updateAccessibleCursor();
      }
      this.drawBackground();
    }

    bindCursor() {
      this.canvas.tabIndex = 0;
      this.canvas.setAttribute("role", "slider");
      if (!this.canvas.hasAttribute("aria-label") && !this.canvas.hasAttribute("aria-labelledby")) {
        this.canvas.setAttribute("aria-label", "Chart time cursor");
      }
      this.canvas.style.touchAction = "pan-y";
      const move = (event) => {
        if (!this.plot || (event.pointerType === "touch" && event.type === "pointermove" && !event.buttons)) {
          return;
        }
        const bounds = this.canvas.getBoundingClientRect();
        const x = (event.clientX - bounds.left) * this.width / bounds.width;
        const y = (event.clientY - bounds.top) * this.height / bounds.height;
        const { left, right, top, bottom } = this.plot;
        this.cursor = x >= left && x <= right && y >= top && y <= bottom
          ? this.snapCursor(this.range[0] + (x - left) / (right - left) * (this.range[1] - this.range[0]))
          : null;
        this.queuePaint();
      };
      this.canvas.addEventListener("pointermove", move);
      this.canvas.addEventListener("pointerdown", move);
      this.canvas.addEventListener("pointerleave", (event) => {
        if (event.pointerType !== "touch") this.clearCursor();
      });
      this.canvas.addEventListener("pointercancel", () => this.clearCursor());
      this.canvas.addEventListener("blur", () => this.clearCursor());
      this.canvas.addEventListener("keydown", (event) => this.handleCursorKey(event));
    }

    handleCursorKey(event) {
      if (!this.range) return;
      const [start, end] = this.range;
      const bucket = this.xAxis?.bucketWidth;
      const step = bucket
        ? bucket * (event.shiftKey ? 3 : 1)
        : (end - start) * (event.shiftKey ? 0.05 : 0.01);
      const cursor = this.cursor ?? (bucket ? start - step : start);
      switch (event.key) {
        case "ArrowLeft":
        case "ArrowDown": this.cursor = Math.max(start, cursor - step); break;
        case "ArrowRight":
        case "ArrowUp": this.cursor = Math.min(end, cursor + step); break;
        case "Home": this.cursor = start; break;
        case "End": this.cursor = end; break;
        case "Escape": this.cursor = null; break;
        default: return;
      }
      if (this.cursor !== null) this.cursor = this.snapCursor(this.cursor);
      event.preventDefault();
      this.queuePaint();
    }

    snapCursor(position) {
      const width = this.xAxis?.bucketWidth;
      if (!width) return position;
      const [start, end] = this.range;
      const center = start + (Math.floor((position - start) / width) + 0.5) * width;
      return Math.max(start + width / 2, Math.min(end - width / 2, center));
    }

    cursorText(value) {
      return this.xAxis ? this.xAxis.formatCursor(value) : timeText(value, true);
    }

    clearCursor() {
      if (this.cursor === null) return;
      this.cursor = null;
      this.queuePaint();
    }

    queuePaint() {
      if (this.frame !== null) return;
      this.frame = requestAnimationFrame(() => {
        this.frame = null;
        this.paint();
      });
    }

    cursorSamples() {
      if (this.cursor === null) return [];
      return this.series.map((entry) => {
        const { points, start, end, gap } = entry;
        const next = lowerBound(points, this.cursor);
        const left = next - 1;
        const nextDistance = next >= start && next < end ? points[next][0] - this.cursor : Infinity;
        const leftDistance = left >= start && left < end ? this.cursor - points[left][0] : Infinity;
        const sample = Math.min(nextDistance, leftDistance) <= (this.xAxis?.cursorTolerance ?? gap / 2)
          ? points[leftDistance <= nextDistance ? left : next]
          : null;
        return { ...entry, sample };
      });
    }

    updateAccessibleCursor(samples = []) {
      this.canvas.setAttribute("aria-valuenow", this.cursor ?? this.range[0]);
      if (this.cursor === null) {
        this.canvas.setAttribute("aria-valuetext", "Use the arrow keys to inspect readings");
        return;
      }
      const description = samples.map(({ label, sample, unit, formatValue }) => sample
        ? `${label}, ${pointText(sample, unit, formatValue)} at ${this.cursorText(sample[0])}`
        : `${label}, no nearby sample`);
      this.canvas.setAttribute("aria-valuetext", [this.cursorText(this.cursor), ...description].join(". "));
    }

    drawBackground() {
      if (!this.series) return;
      const { clientWidth: width, clientHeight: height } = this.canvas;
      if (width < 100 || height < 85) return;
      this.width = width;
      this.height = height;
      const ratio = Math.min(window.devicePixelRatio || 1, 3);
      this.canvas.width = this.background.width = Math.round(width * ratio);
      this.canvas.height = this.background.height = Math.round(height * ratio);
      const context = this.background.getContext("2d");
      context.setTransform(this.background.width / width, 0, 0, this.background.height / height, 0, 0);
      context.font = `12px ${font}`;
      const top = 23;
      const bottom = height - (this.interactive ? 45 : 26);
      function scale(entries) {
        const axis = yAxis(entries, Math.max(2, Math.floor((height - 63) / 42)));
        const ticks = [];
        for (let i = 0; i <= Math.round((axis.maximum - axis.minimum) / axis.step); i++) {
          const value = axis.minimum + i * axis.step;
          ticks.push([value, formatNumber(value, axis.step)]);
        }
        const margin = Math.max(32, ...ticks.map(([, label]) => Math.ceil(context.measureText(label).width) + 11));
        const y = value => bottom - (value - axis.minimum) / (axis.maximum - axis.minimum) * (bottom - top);
        return { ticks, margin, y, hasSamples: axis.hasSamples };
      }
      const separate = this.overlayUnit !== undefined && this.overlayUnit !== this.unit;
      const primary = scale(separate ? this.series.filter(entry => !entry.overlay) : this.series);
      const secondary = separate ? scale(this.series.filter(entry => entry.overlay)) : primary;
      const left = primary.margin;
      const right = width - (this.overlayUnit !== undefined ? secondary.margin : 13);
      const [start, end] = this.range;
      const x = (time) => left + (time - start) / (end - start) * (right - left);
      this.plot = { left, right, top, bottom, x, y: primary.y, overlayY: secondary.y };

      if (primary.hasSamples || secondary.hasSamples) {
        this.drawAxes(context, primary.hasSamples ? primary.ticks : []);
        if (this.overlayUnit !== undefined) {
          context.textAlign = "left";
          if (secondary.hasSamples) {
            for (const [value, label] of secondary.ticks) context.fillText(label, right + 6, secondary.y(value));
          }
          context.textAlign = "right";
          context.fillText(this.overlayUnit, right, 9);
        }
        context.save();
        context.beginPath();
        context.rect(left, top, right - left, bottom - top);
        context.clip();
        for (const entry of this.series) this.drawSeries(context, entry);
        context.restore();
      } else {
        context.font = `14px ${font}`;
        context.fillStyle = colors.label;
        context.textAlign = "center";
        context.textBaseline = "middle";
        let emptyMessage = "No samples in this time range";
        if (this.style === "binned") emptyMessage = "No speed bands with enough samples";
        else if (this.xAxis) emptyMessage = "No samples with observed distance";
        context.fillText(emptyMessage, width / 2, height / 2);
      }
      this.paint();
    }

    drawAxes(context, yTicks) {
      const { left, right, top, bottom, x, y } = this.plot;
      const [start, end] = this.range;
      const target = Math.max(2, Math.floor((right - left) / (this.interactive ? 95 : 65)));
      const step = this.xAxis
        ? Math.max(this.xAxis.bucketWidth ?? 0, numericStep(end - start, target))
        : timeSteps.find((interval) => interval >= (end - start) / target)
          ?? numericStep(end - start, target);
      context.lineWidth = 1;
      context.textBaseline = "middle";
      context.fillStyle = colors.label;
      context.textAlign = "right";
      context.strokeStyle = colors.grid;
      context.beginPath();
      for (const [value, label] of yTicks) {
        const row = y(value);
        context.moveTo(left, row);
        context.lineTo(right, row);
        context.fillText(label, left - 8, row);
      }
      const firstTick = Math.ceil(start / step);
      const lastTick = Math.floor(end / step + 1e-9);
      for (let index = firstTick; index <= lastTick; index += 1) {
        const tick = index * step;
        const column = x(tick);
        const label = this.xAxis ? formatNumber(tick, step) : timeText(tick, step < 1);
        const halfWidth = context.measureText(label).width / 2;
        const labelX = Math.min(right - halfWidth, Math.max(left, column));
        context.moveTo(column, top);
        context.lineTo(column, bottom);
        context.textAlign = "center";
        context.fillText(label, labelX, bottom + 14);
      }
      context.stroke();

      context.strokeStyle = colors.axis;
      context.beginPath();
      context.moveTo(left, top);
      context.lineTo(left, bottom);
      context.lineTo(right, bottom);
      context.stroke();
      context.textAlign = "left";
      context.fillText(this.unit, left, 9);
      if (this.interactive) {
        context.textAlign = "center";
        context.fillText(this.xAxis?.label ?? "Elapsed time in min:sec", (left + right) / 2, this.height - 8);
      }
    }

    drawSeries(context, entry) {
      if (this.style === "binned") {
        this.drawBins(context, entry);
        return;
      }
      const { points, start, end } = entry;
      if (start === end) return;
      const { x } = this.plot;
      const y = entry.overlay ? this.plot.overlayY : this.plot.y;
      const first = start > 0 && start < points.length && !gapBefore(entry, start)
        ? start - 1 : start;
      const stop = end > 0 && end < points.length && !gapBefore(entry, end)
        ? end + 1 : end;
      const isolated = [];
      let previousValue;
      let segmentLength = 0;
      context.beginPath();
      strokeStyle(context, entry, this.interactive ? 2 : 1.6);
      context.lineJoin = "round";
      context.lineCap = "round";
      for (let index = first; index < stop; index += 1) {
        const [time, value] = points[index];
        if (index === first || gapBefore(entry, index)) {
          if (segmentLength === 1) isolated.push(index - 1);
          context.moveTo(x(time), y(value));
          segmentLength = 1;
        } else {
          if (entry.style === "step" && previousValue !== value) context.lineTo(x(time), y(previousValue));
          context.lineTo(x(time), y(value));
          segmentLength += 1;
        }
        previousValue = value;
      }
      context.stroke();
      if (segmentLength === 1) isolated.push(stop - 1);
      context.fillStyle = entry.color;
      for (const index of isolated) {
        const [time, value] = points[index];
        context.beginPath();
        context.arc(x(time), y(value), 2, 0, 2 * Math.PI);
        context.fill();
      }
    }

    drawBins(context, entry) {
      const { x, y } = this.plot;
      const { points, start, end, markOffset, color, dashed } = entry;
      context.fillStyle = context.strokeStyle = color;
      context.lineWidth = 1.5;
      for (let index = start; index < end; index += 1) {
        const [center, median, lower, upper] = points[index];
        const column = x(center) + markOffset;
        const top = y(upper);
        const bottom = y(lower);
        context.globalAlpha = 0.56;
        context.beginPath();
        context.moveTo(column - 3, top);
        context.lineTo(column + 3, top);
        context.moveTo(column, top);
        context.lineTo(column, bottom);
        context.moveTo(column - 3, bottom);
        context.lineTo(column + 3, bottom);
        context.stroke();
        context.globalAlpha = 1;
        context.beginPath();
        if (dashed) context.rect(column - 3, y(median) - 3, 6, 6);
        else context.arc(column, y(median), 3.5, 0, 2 * Math.PI);
        context.fill();
      }
    }

    paint() {
      if (!this.plot) return;
      const context = this.context;
      const { width, height } = this.canvas;
      context.setTransform(1, 0, 0, 1, 0, 0);
      context.clearRect(0, 0, width, height);
      context.drawImage(this.background, 0, 0);
      if (!this.interactive) return;
      const samples = this.cursorSamples();
      this.updateAccessibleCursor(samples);
      if (this.cursor === null) return;
      context.setTransform(width / this.width, 0, 0, height / this.height, 0, 0);
      this.drawCursor(context, samples);
    }

    drawCursor(context, samples) {
      const { left, right, top, bottom, x, y } = this.plot;
      const column = x(this.cursor);
      context.lineWidth = 1;
      context.strokeStyle = colors.label;
      context.setLineDash([3, 4]);
      context.beginPath();
      context.moveTo(column, top);
      context.lineTo(column, bottom);
      context.stroke();
      context.setLineDash([]);
      for (const { color, markOffset, sample, overlay } of samples) {
        if (!sample) continue;
        context.beginPath();
        context.arc(x(sample[0]) + markOffset, (overlay ? this.plot.overlayY : y)(sample[1]), 4, 0, 2 * Math.PI);
        context.fillStyle = color;
        context.fill();
        context.strokeStyle = colors.panel;
        context.lineWidth = 1.5;
        context.stroke();
      }

      const width = Math.min(278, this.width - 20);
      const height = 30 + samples.length * 25;
      const preferredLeft = column + width + 13 <= right ? column + 13 : column - width - 13;
      const boxLeft = Math.max(left > 45 ? left - 22 : 8, Math.min(this.width - width - 8, preferredLeft));
      const boxTop = top + 9;
      context.fillStyle = colors.panel;
      context.strokeStyle = colors.axis;
      context.lineWidth = 1;
      context.beginPath();
      if (typeof context.roundRect === "function") {
        context.roundRect(boxLeft, boxTop, width, height, 8);
      } else {
        context.rect(boxLeft, boxTop, width, height);
      }
      context.fill();
      context.stroke();
      context.textBaseline = "middle";
      context.font = `600 13px ${font}`;
      context.textAlign = "left";
      context.fillStyle = colors.text;
      const heading = this.xAxis ? this.cursorText(this.cursor) : `${this.cursorText(this.cursor)} elapsed`;
      context.fillText(heading, boxLeft + 12, boxTop + 16);

      samples.forEach((entry, index) => {
        const row = boxTop + 38 + index * 25;
        strokeStyle(context, entry, 2);
        context.beginPath();
        context.moveTo(boxLeft + 12, row);
        context.lineTo(boxLeft + 26, row);
        context.stroke();
        context.setLineDash([]);
        const value = entry.sample ? pointText(entry.sample, entry.unit, entry.formatValue) : "No nearby sample";
        context.font = `600 12px ${font}`;
        context.fillStyle = entry.sample ? colors.text : colors.label;
        context.textAlign = "right";
        context.fillText(value, boxLeft + width - 12, row);
        const labelWidth = width - 52 - context.measureText(value).width;
        context.font = `12px ${font}`;
        context.fillStyle = colors.label;
        context.textAlign = "left";
        context.fillText(truncate(context, entry.label, labelWidth), boxLeft + 34, row);
      });
    }
  }

  window.CardaQChart = CardaQChart;
})();
