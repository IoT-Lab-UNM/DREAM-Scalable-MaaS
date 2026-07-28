
const siteContainers = {
  NMSU: document.getElementById("nmsuDevices"),
  NMT: document.getElementById("nmtDevices"),
  NTU: document.getElementById("ntuDevices"),
};

async function loadSites() {
  const res = await fetch("/api/sites");
  const data = await res.json();

  Object.entries(data.sites).forEach(([site, details]) => {
    siteContainers[site].innerHTML = "";
    details.devices.forEach((d) => {
      const div = document.createElement("div");
      div.className = "device";
      div.id = d.id;
      div.innerHTML = `<b>${d.id}</b><br>type:${d.type.replace("_", " ")}<br>h:${d.health} q:${d.queue} rtt:${details.rtt_ms}ms`;
      siteContainers[site].appendChild(div);
    });
  });
}

function formPayload() {
  return {
    client_location: document.getElementById("client_location").value,
    routing_mode: document.getElementById("routing_mode").value,
    preferred_site: document.getElementById("preferred_site").value,
    device_type: document.getElementById("device_type").value,
    sla_tier: document.getElementById("sla_tier").value,
    material: "PLA",
    deadline_minutes: 120
  };
}

function highlight(order) {
  document.querySelectorAll(".site, .device").forEach(x => x.classList.remove("selected"));
  const site = order.selected.site;
  const deviceId = order.selected.id;
  const siteBox = document.querySelector(`.site[data-site="${site}"]`);
  const deviceBox = document.getElementById(deviceId);
  if (siteBox) siteBox.classList.add("selected");
  if (deviceBox) deviceBox.classList.add("selected");

  document.getElementById("selectedDevice").textContent = deviceId;
  document.getElementById("selectedSite").textContent = site;
  document.getElementById("score").textContent = order.selected.score;
  document.getElementById("health").textContent = order.selected.health;
  document.getElementById("queue").textContent = order.selected.queue;
  document.getElementById("rtt").textContent = `${order.selected.rtt_ms} ms`;

  document.getElementById("inspector").textContent = JSON.stringify({
    order_id: order.order_id,
    state: order.state,
    selected: order.selected,
    selection_logic: order.selection_logic
  }, null, 2);
}

async function loadOrders() {
  const res = await fetch("/api/orders");
  const data = await res.json();
  document.getElementById("orders").textContent = JSON.stringify(data.orders.slice(-5), null, 2);
}

document.getElementById("submit").addEventListener("click", async () => {
  const res = await fetch("/api/orders", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(formPayload())
  });

  const order = await res.json();
  if (!res.ok) {
    alert(order.error || "Failed to submit order");
    return;
  }

  highlight(order);
  await loadOrders();
});

loadSites();
loadOrders();
setInterval(loadOrders, 5000);
