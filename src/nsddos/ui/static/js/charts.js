(function () {
  const palette = {
    green: "#7cff6b",
    cyan: "#61f2ff",
    amber: "#ffcb68",
    red: "#ff6f78",
    muted: "#7cb9c4",
    ink: "#07131c",
  };

  function pickColors(count) {
    const base = [palette.cyan, palette.green, palette.amber, palette.red, "#98abff", "#b68fff"];
    return Array.from({ length: count }, (_value, index) => base[index % base.length]);
  }

  function clear(canvas, context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = palette.ink;
    context.fillRect(0, 0, canvas.width, canvas.height);
  }

  function resize(canvas) {
    const width = canvas.clientWidth || 640;
    const height = canvas.clientHeight || 320;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function drawAxes(context, width, height) {
    context.strokeStyle = "rgba(97, 242, 255, 0.16)";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(48, 18);
    context.lineTo(48, height - 34);
    context.lineTo(width - 16, height - 34);
    context.stroke();
  }

  function drawLine(canvas, context, chart) {
    const points = chart.points || [];
    const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
    const width = canvas.width;
    const height = canvas.height;
    const innerWidth = width - 72;
    const innerHeight = height - 74;
    const step = points.length > 1 ? innerWidth / Math.max(points.length - 1, 1) : innerWidth / 2;
    drawAxes(context, width, height);
    context.strokeStyle = palette.cyan;
    context.lineWidth = 2.5;
    context.beginPath();
    points.forEach((point, index) => {
      const x = 48 + index * step;
      const y = height - 34 - ((Number(point.value) || 0) / max) * innerHeight;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.stroke();
    points.forEach((point, index) => {
      const x = 48 + index * step;
      const y = height - 34 - ((Number(point.value) || 0) / max) * innerHeight;
      context.fillStyle = palette.green;
      context.beginPath();
      context.arc(x, y, 4, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = palette.muted;
      context.font = "11px 'JetBrains Mono'";
      context.fillText(String(point.label).slice(0, 10), Math.max(16, x - 14), height - 12);
    });
  }

  function drawBars(canvas, context, chart) {
    const points = chart.points || [];
    const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
    const width = canvas.width;
    const height = canvas.height;
    const innerHeight = height - 78;
    const barWidth = Math.max(24, (width - 72) / Math.max(points.length, 1) - 12);
    drawAxes(context, width, height);
    pickColors(points.length).forEach((color, index) => {
      const point = points[index];
      const value = Number(point.value) || 0;
      const barHeight = (value / max) * innerHeight;
      const x = 56 + index * (barWidth + 12);
      const y = height - 34 - barHeight;
      context.fillStyle = color;
      context.fillRect(x, y, barWidth, Math.max(barHeight, 1));
      context.fillStyle = palette.muted;
      context.font = "11px 'JetBrains Mono'";
      context.fillText(String(point.label).slice(0, 10), x, height - 12);
    });
  }

  function drawChart(canvas, chart) {
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    resize(canvas);
    clear(canvas, context);
    if ((chart.chart_type || "").toLowerCase() === "line") {
      drawLine(canvas, context, chart);
      return;
    }
    drawBars(canvas, context, chart);
  }

  function renderCharts(page) {
    const charts = [];
    if (page.traffic_chart) charts.push(page.traffic_chart);
    if (page.attack_chart) charts.push(page.attack_chart);
    (page.charts || []).forEach((chart) => charts.push(chart));
    charts.forEach((chart) => {
      const canvas = document.getElementById(`chart-${chart.chart_id}`);
      if (canvas) {
        drawChart(canvas, chart);
      }
    });
  }

  window.nsddosCharts = { renderCharts };
})();
