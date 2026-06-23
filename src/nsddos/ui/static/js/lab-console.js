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

  function setActionStatus(status) {
    const root = document.getElementById("labActionStatus");
    if (!root || !status) return;
    root.innerHTML = `
      <span class="lab-status-label">STATUS</span>
      <span class="lab-status-value">${text(status.state)}</span>
      <span class="lab-status-detail">${text(status.detail)}</span>
    `;
  }

  function renderTelemetry(lab) {
    const root = document.getElementById("labTelemetryGrid");
    if (!root || !lab) return;
    root.innerHTML = (lab.telemetry || []).map((item) => `
      <article class="lab-telemetry-card ${text(item.state)}">
        <div class="lab-telemetry-label">${text(item.label)}</div>
        <div class="lab-telemetry-value">${text(item.value)}</div>
        <div class="lab-telemetry-detail">${text(item.detail)}</div>
      </article>
    `).join("");
  }

  function bindDrawer(lab, activateHost) {
    const drawer = document.getElementById("labDrawer");
    const title = document.getElementById("labDrawerTitle");
    const state = document.getElementById("labDrawerState");
    const detail = document.getElementById("labDrawerDetail");
    const meta = document.getElementById("labDrawerMeta");
    const close = document.getElementById("labDrawerClose");
    if (!drawer || !title || !state || !detail || !meta) return;
    const nodes = Object.fromEntries((lab.nodes || []).map((node) => [node.node_id, node]));
    document.querySelectorAll(".lab-node").forEach((button) => {
      button.onclick = () => {
        const node = nodes[button.getAttribute("data-node-id") || ""];
        if (!node) return;
        title.textContent = text(node.label);
        state.textContent = text(node.state);
        detail.textContent = text(node.detail);
        meta.innerHTML = Object.entries(node.metadata || {}).map(([key, value]) => `
          <div class="lab-meta-row"><span>${text(key)}</span><span>${text(value)}</span></div>
        `).join("");
        if (node.kind === "host") {
          meta.innerHTML += `<button type="button" class="lab-inline-action" data-open-host="${text(node.node_id)}">Open shell</button>`;
          const action = meta.querySelector("[data-open-host]");
          if (action) action.onclick = () => activateHost(node.node_id);
        }
        drawer.hidden = false;
      };
    });
    if (close) {
      close.onclick = () => {
        drawer.hidden = true;
      };
    }
  }

  function bindTerminals(lab) {
    const output = document.getElementById("labTerminalOutput");
    const input = document.getElementById("labTerminalInput");
    const prompt = document.getElementById("labTerminalPrompt");
    const tabs = document.querySelectorAll(".lab-terminal-tab");
    if (!output || !input || !prompt) return function () {};

    const state = {
      activeHost: (lab.terminal_tabs || [])[0]?.host || "h1",
      prompts: Object.fromEntries((lab.terminal_tabs || []).map((tab) => [tab.host, tab.prompt])),
      buffers: Object.fromEntries((lab.terminal_tabs || []).map((tab) => [tab.host, ""])),
      sockets: {},
    };

    function activateHost(host) {
      state.activeHost = host;
      tabs.forEach((tab) => tab.classList.toggle("active", tab.getAttribute("data-host") === host));
      prompt.textContent = text(state.prompts[host] || `${host}#`);
      output.textContent = text(state.buffers[host] || "");
      output.scrollTop = output.scrollHeight;
      input.focus();
    }

    tabs.forEach((tab) => {
      const host = tab.getAttribute("data-host") || "";
      tab.onclick = () => activateHost(host);
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${window.location.host}/ui/ws/lab-terminal/${host}`);
      state.sockets[host] = socket;
      socket.onmessage = (event) => {
        state.buffers[host] = `${state.buffers[host] || ""}${event.data}`.slice(-30000);
        if (host === state.activeHost) {
          output.textContent = state.buffers[host];
          output.scrollTop = output.scrollHeight;
        }
      };
    });

    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const value = input.value;
      const socket = state.sockets[state.activeHost];
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(`${value}\n`);
      }
      input.value = "";
    });

    activateHost(state.activeHost);
    return activateHost;
  }

  function bindActions(setStatus, activateHost) {
    document.querySelectorAll(".lab-action-button").forEach((button) => {
      button.onclick = async () => {
        const action = button.getAttribute("data-action") || "";
        if (action.startsWith("open-") && action.endsWith("-shell")) {
          activateHost(action.replace("open-", "").replace("-shell", ""));
          return;
        }
        const response = await fetch(`/ui/api/lab/actions/${action}`, { method: "POST" });
        const payload = await response.json();
        setStatus(payload);
      };
    });
  }

  function connectSnapshot(setStatus) {
    const badge = document.getElementById("liveStateBadge");
    const updatedAt = document.getElementById("updatedAt");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ui/ws/lab-console`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      const page = payload.page || {};
      const lab = page.lab_console || {};
      renderTelemetry(lab);
      setActionStatus(lab.action_status || {});
      if (updatedAt) updatedAt.textContent = text(page.updated_at || "LIVE");
    };
    socket.onopen = () => {
      if (badge) badge.textContent = "connected";
    };
    socket.onclose = () => {
      if (badge) badge.textContent = "stale";
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.pageName !== "lab-console") return;
    const snapshot = safeJson("pageSnapshot");
    const lab = snapshot?.lab_console || {};
    const activateHost = bindTerminals(lab);
    bindDrawer(lab, activateHost);
    bindActions(setActionStatus, activateHost);
    setActionStatus(lab.action_status || {});
    connectSnapshot(setActionStatus);
  });
})();
