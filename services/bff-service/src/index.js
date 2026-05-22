const express = require("express");
const { UPSTREAM_TIMEOUT, DATA_WORKER_PORT, MAX_CONCURRENT_REQUESTS } = require("./config");

const app = express();
const PORT = process.env.PORT || 3000;

// BUG: DATA_WORKER_PORT=9999 (wrong port) → connection refused
const DATA_WORKER_URL =
  process.env.DATA_WORKER_URL || `http://data-worker:${DATA_WORKER_PORT}`;
const CORE_BUSINESS_URL =
  process.env.CORE_BUSINESS_URL || "http://core-business:8081";

// === Fault state ===
let errorMode = false;
let latencyMs = 0;

app.use(express.json());

app.get("/healthz", (req, res) => {
  if (errorMode) {
    return res.status(503).json({ status: "error", message: "Service degraded" });
  }
  res.json({ status: "ok", service: "bff-service" });
});

app.get("/api/aggregate", async (req, res) => {
  if (latencyMs > 0) {
    await new Promise((r) => setTimeout(r, latencyMs));
  }

  try {
    // BUG: UPSTREAM_TIMEOUT=500ms → most requests timeout
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT);

    const [dataRes, itemsRes] = await Promise.all([
      fetch(`${DATA_WORKER_URL}/healthz`, { signal: controller.signal }),
      fetch(`${CORE_BUSINESS_URL}/items`, { signal: controller.signal }),
    ]);

    clearTimeout(timeout);

    const data = await dataRes.json();
    const items = await itemsRes.json();

    res.json({
      data_worker_status: data,
      items: items,
      aggregated_at: new Date().toISOString(),
    });
  } catch (err) {
    if (err.name === "AbortError") {
      res.status(504).json({
        error: "upstream_timeout",
        message: `Upstream did not respond within ${UPSTREAM_TIMEOUT}ms`,
        config: { UPSTREAM_TIMEOUT, DATA_WORKER_PORT },
      });
    } else {
      res.status(502).json({ error: "upstream_error", message: err.message });
    }
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

// === Fault Injection ===

app.post("/fault/error503", (req, res) => {
  errorMode = true;
  res.json({ status: "error_mode_enabled", message: "healthz will return 503" });
});

app.post("/fault/error503/disable", (req, res) => {
  errorMode = false;
  res.json({ status: "error_mode_disabled" });
});

app.post("/fault/latency/:ms", (req, res) => {
  latencyMs = parseInt(req.params.ms);
  res.json({ status: "latency_injected", latency_ms: latencyMs });
});

app.post("/fault/latency/disable", (req, res) => {
  latencyMs = 0;
  res.json({ status: "latency_removed" });
});

app.post("/fault/crash", (req, res) => {
  res.json({ status: "crashing" });
  setTimeout(() => process.exit(1), 100);
});

app.post("/fault/unhandled", (req, res) => {
  throw new Error("Unhandled exception: Cannot read property 'id' of undefined");
});

app.listen(PORT, () => {
  console.log(`bff-service listening on :${PORT}`);
});
