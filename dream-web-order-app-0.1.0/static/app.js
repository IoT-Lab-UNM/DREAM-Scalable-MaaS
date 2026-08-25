const $ = (id) => document.getElementById(id);
let activeJobId = null;
let pollTimer = null;
let pendingAction = null;

function value(v, fallback = "—") {
  return (v === null || v === undefined || v === "") ? fallback : String(v);
}

function setBadge(el, online, eligible) {
  el.className = "badge";
  if (online && eligible) {
    el.classList.add("good");
    el.textContent = "READY";
  } else if (online) {
    el.classList.add("warn");
    el.textContent = "ONLINE / NOT ELIGIBLE";
  } else {
    el.classList.add("bad");
    el.textContent = "OFFLINE";
  }
}

function addActivity(text, kind = "info") {
  const box = $("activity");
  const empty = box.querySelector(".activity-empty");
  if (empty) empty.remove();
  const row = document.createElement("div");
  row.className = `activity-row ${kind}`;
  const now = new Date().toLocaleTimeString();
  row.innerHTML = `<span>${now}</span><b>${text}</b>`;
  box.prepend(row);
  while (box.children.length > 8) box.removeChild(box.lastChild);
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  let body;
  try { body = await res.json(); }
  catch { body = {error: `HTTP ${res.status}`}; }
  if (!res.ok) {
    const err = new Error(body.error || body.detail || `HTTP ${res.status}`);
    err.body = body;
    err.status = res.status;
    throw err;
  }
  return body;
}

async function loadHealth() {
  try {
    const data = await fetchJSON("/api/health");
    $("backendState").textContent = data.status === "ok" ? "HEALTHY" : "DEGRADED";
  } catch (err) {
    $("backendState").textContent = "UNREACHABLE";
  }
}

async function loadDevices() {
  try {
    const data = await fetchJSON("/api/devices");
    const printer = data.devices["ender3-printer-01"] || {};
    const robot = data.devices["freenove-arm-01"] || {};

    const pt = printer.twins || {};
    const rt = robot.twins || {};

    $("printerState").textContent = value(pt.printerState || printer.state).toUpperCase();
    $("printerEligible").textContent = printer.eligible === true ? "ELIGIBLE" : "NOT ELIGIBLE";
    $("printerTwinState").textContent = value(pt.printerState);
    $("printerProgress").textContent = pt.progress !== undefined ? `${pt.progress}%` : "—";
    $("printerActiveJob").textContent = value(pt.activeJob);
    $("printerFault").textContent = value(pt.fault);
    setBadge($("printerBadge"), printer.state === "online", printer.eligible === true);

    $("robotState").textContent = value(rt.operatingState || robot.state).toUpperCase();
    $("robotEligible").textContent = robot.eligible === true ? "ELIGIBLE" : "NOT ELIGIBLE";
    $("robotTwinState").textContent = value(rt.operatingState);
    $("robotCurrentTask").textContent = value(rt.currentTask);
    $("robotFault").textContent = value(rt.fault);
    setBadge($("robotBadge"), robot.state === "online", robot.eligible === true);
  } catch (err) {
    addActivity(`Device refresh failed: ${err.message}`, "bad");
  }
}

function renderJob(job) {
  if (!job) return;
  $("jobId").textContent = value(job.id || activeJobId);
  $("jobState").textContent = value(job.state);
  $("policyDecision").textContent = value(job.policy_decision);
  $("slaDecision").textContent = value(job.sla_decision);
  $("inspector").textContent = JSON.stringify({
    id: job.id,
    device_id: job.device_id,
    action: job.action,
    state: job.state,
    policy_decision: job.policy_decision,
    sla_decision: job.sla_decision,
    last_error: job.last_error,
    completed_at: job.completed_at
  }, null, 2);
}

async function pollJob() {
  if (!activeJobId) return;
  try {
    const job = await fetchJSON(`/api/jobs/${activeJobId}`);
    renderJob(job);
    await loadDevices();
    if (["COMPLETED", "FAILED", "REJECTED", "CANCELLED"].includes(job.state)) {
      clearInterval(pollTimer);
      pollTimer = null;
      addActivity(`Job ${job.state}: ${job.action}`, job.state === "COMPLETED" ? "good" : "bad");
    }
  } catch (err) {
    addActivity(`Job poll failed: ${err.message}`, "bad");
  }
}

async function executeAction(actionKey, button) {
  button.disabled = true;
  $("lastAction").textContent = actionKey.replaceAll("_", " ").toUpperCase();
  addActivity(`Submitting ${actionKey}…`);

  try {
    const result = await fetchJSON(`/api/actions/${actionKey}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: "{}"
    });
    activeJobId = result.job_id;
    const dispatched = result.dispatch || result.created || {};
    renderJob(dispatched);
    $("inspector").textContent = JSON.stringify(result, null, 2);
    addActivity(`Dispatched ${result.label}`, "good");

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(pollJob, 2000);
    await pollJob();
  } catch (err) {
    const detail = err.body || {error: err.message};
    $("inspector").textContent = JSON.stringify(detail, null, 2);
    addActivity(`Action failed: ${err.message}`, "bad");
  } finally {
    button.disabled = false;
  }
}

function askConfirmation(actionKey, button) {
  const physical = button.classList.contains("danger-aware");
  if (!physical) {
    executeAction(actionKey, button);
    return;
  }

  pendingAction = {actionKey, button};
  const label = button.textContent.trim();
  $("confirmText").textContent = `${label} will command physical hardware. Confirm the device workspace is clear and safe.`;
  $("confirmModal").classList.remove("hidden");
}

function closeConfirm() {
  $("confirmModal").classList.add("hidden");
  pendingAction = null;
}

document.querySelectorAll("button[data-action]").forEach((button) => {
  button.addEventListener("click", () => askConfirmation(button.dataset.action, button));
});

$("confirmCancel").addEventListener("click", closeConfirm);
$("confirmProceed").addEventListener("click", async () => {
  if (!pendingAction) return closeConfirm();
  const {actionKey, button} = pendingAction;
  closeConfirm();
  await executeAction(actionKey, button);
});

$("refreshDevices").addEventListener("click", async () => {
  await Promise.all([loadHealth(), loadDevices()]);
  addActivity("Device state refreshed", "good");
});

loadHealth();
loadDevices();
setInterval(loadDevices, 10000);
setInterval(loadHealth, 30000);
