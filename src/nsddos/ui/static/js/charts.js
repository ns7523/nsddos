(function () {
  const NS = "http://www.w3.org/2000/svg";

  function svgNode(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function renderLine(svg, chart) {
    const width = 620;
    const height = 220;
    const left = 42;
    const top = 16;
    const innerWidth = width - left - 16;
    const innerHeight = height - top - 28;
    const max = Math.max(...chart.points.map((point) => Number(point.value) || 0), 1);

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.appendChild(svgNode("line", { x1: left, y1: top + innerHeight, x2: width - 10, y2: top + innerHeight, class: "chart-axis" }));
    svg.appendChild(svgNode("line", { x1: left, y1: top, x2: left, y2: top + innerHeight, class: "chart-axis" }));

    const points = chart.points.map((point, index) => {
      const x = left + (chart.points.length === 1 ? innerWidth / 2 : (innerWidth / Math.max(chart.points.length - 1, 1)) * index);
      const y = top + innerHeight - ((Number(point.value) || 0) / max) * (innerHeight - 12);
      return { x, y, label: point.label, value: point.value };
    });

    svg.appendChild(svgNode("polyline", {
      points: points.map((point) => `${point.x},${point.y}`).join(" "),
      class: "chart-line",
    }));

    points.forEach((point) => {
      svg.appendChild(svgNode("circle", { cx: point.x, cy: point.y, r: 3, class: "chart-dot" }));
      const label = svgNode("text", { x: point.x, y: height - 6, "text-anchor": "middle", class: "chart-label" });
      label.textContent = point.label;
      svg.appendChild(label);
    });

    const value = svgNode("text", { x: left, y: 12, class: "chart-value" });
    value.textContent = `${Math.round(max)} ${chart.unit}`;
    svg.appendChild(value);
  }

  function renderBar(svg, chart) {
    const width = 620;
    const height = 220;
    const left = 24;
    const top = 16;
    const bottom = 40;
    const innerHeight = height - top - bottom;
    const max = Math.max(...chart.points.map((point) => Number(point.value) || 0), 1);
    const barWidth = Math.max((width - left * 2) / Math.max(chart.points.length, 1) - 18, 22);

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.appendChild(svgNode("line", { x1: left, y1: top + innerHeight, x2: width - left, y2: top + innerHeight, class: "chart-axis" }));

    chart.points.forEach((point, index) => {
      const value = Number(point.value) || 0;
      const x = left + index * (barWidth + 18);
      const barHeight = (value / max) * (innerHeight - 12);
      const y = top + innerHeight - barHeight;
      svg.appendChild(svgNode("rect", { x, y, width: barWidth, height: Math.max(barHeight, 1), class: "chart-bar" }));

      const label = svgNode("text", { x: x + barWidth / 2, y: height - 18, "text-anchor": "middle", class: "chart-label" });
      label.textContent = point.label;
      svg.appendChild(label);

      const amount = svgNode("text", { x: x + barWidth / 2, y: y - 6, "text-anchor": "middle", class: "chart-value" });
      amount.textContent = String(Math.round(value * 100) / 100);
      svg.appendChild(amount);
    });
  }

  function renderChart(svg, chart) {
    clear(svg);
    const frame = svgNode("g", { class: "chart-frame" });
    svg.appendChild(frame);
    if ((chart.chart_type || "").toLowerCase() === "line") {
      renderLine(svg, chart);
      return;
    }
    renderBar(svg, chart);
  }

  function renderCharts(page) {
    const charts = [];
    if (page.traffic_chart) {
      charts.push(page.traffic_chart);
    }
    if (page.attack_chart) {
      charts.push(page.attack_chart);
    }
    (page.charts || []).forEach((chart) => charts.push(chart));
    charts.forEach((chart) => {
      const svg = document.getElementById(`chart-${chart.chart_id}`);
      if (!svg) {
        return;
      }
      renderChart(svg, chart);
    });
  }

  window.nsddosCharts = { renderCharts };
})();
