(function () {
  function safeJson(id) {
    const node = document.getElementById(id);
    if (!node) return null;
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
    if (!root || !page.status_bar) return;
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

  function renderMetrics(page) {
    const root = document.querySelector(".metric-grid");
    if (!root || !(page.stats || []).length) return;
    root.innerHTML = (page.stats || []).map((card) => `
      <article class="metric-card ${text(card.tone)}">
        <div class="metric-label">${text(card.label)}</div>
        <div class="metric-value">${text(card.value)}</div>
        <div class="metric-detail">${text(card.detail)}</div>
      </article>
    `).join("");
  }

  function renderStatuses(page) {
    const root = document.querySelector(".status-tile-grid");
    if (!root || !(page.statuses || []).length) return;
    root.innerHTML = (page.statuses || []).map((tile) => `
      <article class="status-tile ${text(tile.state)}">
        <div class="status-tile-label">${text(tile.label)}</div>
        <div class="status-tile-value">${text(tile.value)}</div>
        <div class="status-tile-detail">${text(tile.detail)}</div>
      </article>
    `).join("");
  }

  function renderFeed(page) {
    const panel = document.getElementById("feedPanel");
    if (!panel || !page.feed) return;
    panel.innerHTML = `
      <div class="panel-header">
        <div>
          <div class="panel-kicker">EVENT STREAM</div>
          <div class="panel-title">${text(page.feed.title)}</div>
        </div>
      </div>
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
    if (!panel || !(page.services || []).length) return;
    panel.innerHTML = `
      <div class="panel-header">
        <div>
          <div class="panel-kicker">SERVICE MATRIX</div>
          <div class="panel-title">Container Runtime Health</div>
        </div>
      </div>
      <table class="terminal-table">
        <thead>
          <tr><th>SERVICE</th><th>STATE</th><th>DETAIL</th></tr>
        </thead>
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

  function renderTables(page) {
    const panels = document.querySelectorAll(".data-panel");
    if (!panels.length || !(page.tables || []).length) return;
    panels.forEach((panel, index) => {
      const table = page.tables[index];
      if (!table) return;
      panel.innerHTML = `
        <div class="panel-header">
          <div>
            <div class="panel-kicker">DATA PANEL</div>
            <div class="panel-title">${text(table.title)}</div>
          </div>
        </div>
        ${table.rows && table.rows.length ? `
          <table class="terminal-table">
            <thead>
              <tr>${(table.columns || []).map((column) => `<th>${text(column.label)}</th>`).join("")}</tr>
            </thead>
            <tbody>
              ${(table.rows || []).map((row) => `
                <tr class="${text(row.state)}">
                  ${(row.values || []).map((value) => `<td>${text(value)}</td>`).join("")}
                </tr>
              `).join("")}
            </tbody>
          </table>
        ` : `<div class="empty-state">${text(table.empty_message)}</div>`}
      `;
    });
  }

  function patchMeta(page) {
    const updatedAt = document.getElementById("updatedAt");
    if (updatedAt) {
      updatedAt.textContent = text(page.updated_at || "LIVE");
    }
  }

  async function runAction(action) {
    const response = await fetch(`/ui/api/lab/actions/${action}`, { method: "POST" });
    if (!response.ok) return;
    const payload = await response.json();
    const feed = document.getElementById("feedPanel");
    if (feed && payload.detail) {
      const stamp = new Date().toISOString().slice(11, 19);
      const eventFeed = feed.querySelector(".event-feed");
      if (eventFeed) {
        eventFeed.insertAdjacentHTML("afterbegin", `
          <div class="feed-row warn">
            <span class="feed-time">[${stamp}]</span>
            <span class="feed-level">ACTION</span>
            <span class="feed-source">OPS</span>
            <span class="feed-message">${text(payload.detail)}</span>
          </div>
        `);
      }
    }
  }

  function bindActions() {
    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.getAttribute("data-action");
        if (action) {
          runAction(action);
        }
      });
    });
  }

  function applyPage(page) {
    renderStatusBar(page);
    renderMetrics(page);
    renderStatuses(page);
    renderFeed(page);
    renderServices(page);
    renderTables(page);
    patchMeta(page);
    if (window.nsddosCharts) {
      window.nsddosCharts.renderCharts(page);
    }
    if (window.nsddosTopology) {
      window.nsddosTopology.renderTopology(page.topology || null);
    }
  }

  function connectWebSocket() {
    if (document.body.dataset.pageName === "lab-console") return;
    const wsPath = document.body.dataset.wsPath;
    if (!wsPath) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}${wsPath}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      applyPage(payload.page || {});
    };
    socket.onclose = () => {
      const badge = document.getElementById("liveStateBadge");
      if (badge) badge.textContent = "stale";
      window.setTimeout(connectWebSocket, 1500);
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.pageName === "lab-console") return;
    const snapshot = safeJson("pageSnapshot");
    if (snapshot) {
      applyPage(snapshot);
    }
    bindActions();
    connectWebSocket();
  });
})();
