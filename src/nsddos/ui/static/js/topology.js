(function () {
  let graph = null;

  function stateColor(state) {
    const normalized = String(state || "").toLowerCase();
    if (normalized === "online") return "#7cff6b";
    if (normalized === "degraded") return "#ffcb68";
    if (normalized === "offline") return "#ff6f78";
    return "#61f2ff";
  }

  function toElements(topology) {
    const nodes = (topology.nodes || []).map((node) => ({
      data: {
        id: node.node_id,
        label: node.label,
        state: node.state,
      },
      position: { x: node.x, y: node.y },
    }));
    const edges = (topology.edges || []).map((edge) => ({
      data: {
        id: edge.edge_id,
        source: edge.source,
        target: edge.target,
        state: edge.state,
        pulse: Boolean(edge.pulse),
      },
    }));
    return [...nodes, ...edges];
  }

  function style(topology) {
    void topology;
    return [
      {
        selector: "node",
        style: {
          "background-color": (element) => stateColor(element.data("state")),
          "border-color": "#61f2ff",
          "border-width": 1.5,
          "label": "data(label)",
          "font-family": "JetBrains Mono",
          "font-size": 12,
          "text-valign": "bottom",
          "text-margin-y": 10,
          "color": "#d8fbff",
          "shape": "round-rectangle",
          "width": 48,
          "height": 48,
        },
      },
      {
        selector: "edge",
        style: {
          "line-color": (element) => stateColor(element.data("state")),
          "target-arrow-color": (element) => stateColor(element.data("state")),
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "width": 2,
          "line-style": (element) => (element.data("pulse") ? "solid" : "dashed"),
        },
      },
    ];
  }

  function safeJson(text) {
    try {
      return JSON.parse(text);
    } catch (_error) {
      return null;
    }
  }

  function renderTopology(topology) {
    const root = document.getElementById("topologyCanvas");
    if (!root || !window.cytoscape || !topology) {
      return;
    }
    if (!graph) {
      graph = window.cytoscape({
        container: root,
        elements: toElements(topology),
        style: style(topology),
        layout: { name: "preset" },
        userZoomingEnabled: false,
        userPanningEnabled: true,
      });
      return;
    }
    graph.elements().remove();
    graph.add(toElements(topology));
    graph.style(style(topology));
    graph.layout({ name: "preset" }).run();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("topologyCanvas");
    if (!root) {
      return;
    }
    renderTopology(safeJson(root.dataset.topologyPayload || ""));
  });

  window.nsddosTopology = { renderTopology };
})();
