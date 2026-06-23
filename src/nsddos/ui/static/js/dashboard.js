(function () {
  function safeJson(id) {
    const node = document.getElementById(id);
    if (!node) {
      return null;
    }
    try {
      return JSON.parse(node.textContent);
    } catch (_error) {
      return null;
    }
  }

  function text(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function renderStatusBar(page) {
    const root = document.getElementById("statusBar");
    if (!root || !page.status_bar) {
      return;
    }
    root.innerHTML = (page.status_bar.fields || []).map((field) => `
      <div class="status-field ${text(field.state)}">
        <span class="status-label">${text(field.label)}</span>
        <span class="status-value">${text(field.value)}</span>
      </div>
    `).join("");
    const badge = document.getElementById("liveStateBadge");
    if (badge) {
      badge.textContent = text(page.status_bar.live_state || "live");
    }
  }

  function renderFeed(page) {
    const panel = document.getElementById("feedPanel");
    if (!panel || !page.feed) {
      return;
    }
    panel.innerHTML = `
      <div class="panel-title">${text(page.feed.title)}</div>
      <div class="event-feed">
        ${(page.feed.entries || []).map((entry) => `
          <div class="feed-row ${text(entry.level).toLowerCase()}">
            <span class="feed-time">[${text(entry.timestamp)}]</span>
            <span class="feed-level">${text(entry.level)}</span>
            <span class="feed-source">${text(entry.source)}</span>
            <span class="feed-message">${text(entry.message)}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function renderServices(page) {
    const panel = document.getElementById("servicesPanel");
    if (!panel || !(page.services || []).length) {
      return;
    }
    panel.innerHTML = `
      <div class="panel-title">SERVICE STATUS</div>
      <table class="terminal-table">
        <tbody>
          ${(page.services || []).map((service) => `
            <tr class="${text(service.status).toLowerCase()}">
              <td>${text(service.name)}</td>
              <td>${text(service.status)}</td>
              <td>${text(service.detail)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  function renderTopology(page) {
    const svg = document.querySelector("[data-topology='true']");
    if (!svg || !page.topology) {
      return;
    }
    (page.topology.nodes || []).forEach((node) => {
      const element = svg.querySelector(`[data-node-id="${node.node_id}"]`);
      if (!element) {
        return;
      }
      element.setAttribute("class", `topology-node ${text(node.state).toLowerCase()}`);
    });
    (page.topology.edges || []).forEach((edge) => {
      const element = svg.querySelector(`[data-edge-id="${edge.edge_id}"]`);
      if (!element) {
        return;
      }
      element.setAttribute("class", `topology-edge ${text(edge.state).toLowerCase()}${edge.pulse ? " pulse" : ""}`);
    });
  }

  function patchMeta(page) {
    const updatedAt = document.getElementById("updatedAt");
    if (updatedAt) {
      updatedAt.textContent = text(page.updated_at);
    }
  }

  function connectWebSocket() {
    if (document.body.dataset.pageName === "lab-console") {
      return;
    }
    const wsPath = document.body.dataset.wsPath;
    if (!wsPath) {
      return;
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}${wsPath}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      const page = payload.page || {};
      renderStatusBar(page);
      renderFeed(page);
      renderServices(page);
      renderTopology(page);
      patchMeta(page);
      if (window.nsddosCharts) {
        window.nsddosCharts.renderCharts(page);
      }
    };
    socket.onclose = () => {
      const badge = document.getElementById("liveStateBadge");
      if (badge) {
        badge.textContent = "stale";
      }
      window.setTimeout(connectWebSocket, 1500);
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const snapshot = safeJson("pageSnapshot");
    if (snapshot) {
      renderStatusBar(snapshot);
      renderFeed(snapshot);
      renderServices(snapshot);
      renderTopology(snapshot);
      if (window.nsddosCharts) {
        window.nsddosCharts.renderCharts(snapshot);
      }
    }
    connectWebSocket();
  });
})();
