const express = require("express");

const app = express();
const PORT = process.env.PORT || 3000;

const DATA_WORKER_URL =
  process.env.DATA_WORKER_URL || "http://data-worker:8000";
const CORE_BUSINESS_URL =
  process.env.CORE_BUSINESS_URL || "http://core-business:8081";

app.get("/healthz", (req, res) => {
  res.json({ status: "ok", service: "bff-service" });
});

app.get("/api/aggregate", async (req, res) => {
  try {
    const [dataRes, itemsRes] = await Promise.all([
      fetch(`${DATA_WORKER_URL}/healthz`),
      fetch(`${CORE_BUSINESS_URL}/items`),
    ]);

    const data = await dataRes.json();
    const items = await itemsRes.json();

    res.json({
      data_worker_status: data,
      items: items,
      aggregated_at: new Date().toISOString(),
    });
  } catch (err) {
    res.status(502).json({ error: "upstream_error", message: err.message });
  }
});

app.get("/api/status", async (req, res) => {
  const services = [
    { name: "data-worker", url: `${DATA_WORKER_URL}/healthz` },
    { name: "core-business", url: `${CORE_BUSINESS_URL}/actuator/health` },
  ];

  const results = await Promise.all(
    services.map(async (svc) => {
      try {
        const r = await fetch(svc.url);
        return { name: svc.name, status: r.ok ? "up" : "down" };
      } catch {
        return { name: svc.name, status: "down" };
      }
    })
  );

  res.json({ services: results });
});

app.listen(PORT, () => {
  console.log(`bff-service listening on :${PORT}`);
});
