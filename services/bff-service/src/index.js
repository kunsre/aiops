const express = require("express");

const app = express();
const PORT = process.env.PORT || 3000;

const DATA_WORKER_URL =
  process.env.DATA_WORKER_URL || "http://data-worker:8000";
const CORE_BUSINESS_URL =
  process.env.CORE_BUSINESS_URL || "http://core-business:8081";

// === Fault state ===
let errorMode = false;
let latencyMs = 0;
let wrongUrl = false; // simulate misconfigured upstream URL

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

  const dataUrl = wrongUrl ? "http://wrong-host:9999" : DATA_WORKER_URL;

  try {
    const [dataRes, itemsRes] = await Promise.all([
      fetch(`${dataUrl}/healthz`),
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

app.post("/fault/wrong-upstream", (req, res) => {
  wrongUrl = true;
  res.json({ status: "wrong_url_enabled", message: "Upstream URL set to wrong-host:9999" });
});

app.post("/fault/wrong-upstream/disable", (req, res) => {
  wrongUrl = false;
  res.json({ status: "wrong_url_disabled" });
});

app.post("/fault/crash", (req, res) => {
  res.json({ status: "crashing" });
  setTimeout(() => process.exit(1), 100);
});

app.post("/fault/unhandled", (req, res) => {
  // Simulate unhandled exception → crash
  throw new Error("Unhandled exception: Cannot read property 'id' of undefined");
});

// Global error handler middleware (must be last)
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({ 
    error: "internal_server_error", 
    message: err.message 
  });
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Don't exit the process, just log it
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // Don't exit the process for demo purposes, but log it
  // In production, you might want to gracefully shutdown
});

app.listen(PORT, () => {
  console.log(`bff-service listening on :${PORT}`);
});
