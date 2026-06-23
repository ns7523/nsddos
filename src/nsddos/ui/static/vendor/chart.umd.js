(function () {
  function palette(index) {
    const colors = ["#55e6ff", "#a9ff68", "#ff667d", "#ffb84d", "#89a8ff", "#c184ff"];
    return colors[index % colors.length];
  }

  function clear(canvas, context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#091121";
    context.fillRect(0, 0, canvas.width, canvas.height);
  }

  function drawBar(canvas, context, labels, values) {
    const width = canvas.width;
    const height = canvas.height;
    const maxValue = Math.max(...values, 1);
    const barWidth = Math.max(20, (width - 48) / Math.max(values.length, 1) - 10);
    values.forEach((value, index) => {
      const x = 24 + index * (barWidth + 10);
      const barHeight = ((height - 60) * value) / maxValue;
      const y = height - 30 - barHeight;
      context.fillStyle = palette(index);
      context.fillRect(x, y, barWidth, barHeight);
      context.fillStyle = "#d7e5ff";
      context.font = "11px sans-serif";
      context.fillText(labels[index].slice(0, 10), x, height - 12);
    });
  }

  function drawLine(canvas, context, labels, values) {
    const width = canvas.width;
    const height = canvas.height;
    const maxValue = Math.max(...values, 1);
    const step = values.length > 1 ? (width - 48) / (values.length - 1) : width / 2;
    context.strokeStyle = "#55e6ff";
    context.lineWidth = 3;
    context.beginPath();
    values.forEach((value, index) => {
      const x = 24 + index * step;
      const y = height - 30 - ((height - 60) * value) / maxValue;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
      context.fillStyle = "#d7e5ff";
      context.font = "11px sans-serif";
      context.fillText(labels[index].slice(0, 10), x - 12, height - 12);
    });
    context.stroke();
  }

  function drawDoughnut(canvas, context, labels, values) {
    const total = values.reduce((sum, value) => sum + value, 0) || 1;
    let angle = -Math.PI / 2;
    values.forEach((value, index) => {
      const slice = (value / total) * Math.PI * 2;
      context.beginPath();
      context.moveTo(canvas.width / 2, canvas.height / 2);
      context.fillStyle = palette(index);
      context.arc(canvas.width / 2, canvas.height / 2, 70, angle, angle + slice);
      context.closePath();
      context.fill();
      angle += slice;
      context.fillStyle = "#d7e5ff";
      context.font = "11px sans-serif";
      context.fillText(labels[index].slice(0, 12), 16, 20 + index * 14);
    });
    context.globalCompositeOperation = "destination-out";
    context.beginPath();
    context.arc(canvas.width / 2, canvas.height / 2, 36, 0, Math.PI * 2);
    context.fill();
    context.globalCompositeOperation = "source-over";
  }

  class LightweightChart {
    constructor(canvas, config) {
      this.canvas = canvas;
      this.context = canvas.getContext("2d");
      this.type = config.type;
      this.data = config.data;
      this.update();
    }

    update() {
      const rect = this.canvas.getBoundingClientRect();
      this.canvas.width = Math.max(320, Math.floor(rect.width || 320));
      this.canvas.height = 220;
      clear(this.canvas, this.context);
      const labels = this.data.labels || [];
      const values = this.data.datasets[0]?.data || [];
      if (this.type === "doughnut") {
        drawDoughnut(this.canvas, this.context, labels, values);
        return;
      }
      if (this.type === "line") {
        drawLine(this.canvas, this.context, labels, values);
        return;
      }
      drawBar(this.canvas, this.context, labels, values);
    }

    destroy() {
      clear(this.canvas, this.context);
    }
  }

  window.Chart = LightweightChart;
})();
