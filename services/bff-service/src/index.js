const express = require("express");
const { UPSTREAM_TIMEOUT, DATA_WORKER_PORT } = require("./config");

const app = express();
const PORT = process.env.PORT || 3000;

// BUG: DATA_WORKER_PORT=9999 → 연결 실패 (정상: 8000)
const DATA_WORKER_URL = process.env.DATA_WORKER_URL || `http://data-worker:${DATA_WORKER_PORT}`;
const CORE_BUSINESS_URL = process.env.CORE_BUSINESS_URL || "http://core-business:8081";

app.use(express.json());

app.get("/healthz", (req, res) => {
  res.json({ status: "ok", service: "bff-service" });
});

// 핵심 API: gateway → bff → data-worker + core-business (멀티 트랜잭션)
app.get("/aggregate", async (req, res) => {
  const controller = new AbortController();
  // BUG: UPSTREAM_TIMEOUT=500ms → 대부분 timeout
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT);

  try {
    const [dataRes, itemsRes] = await Promise.all([
      fetch(`${DATA_WORKER_URL}/process`, {
        method: "POST",
        signal: controller.signal,
      }),
      fetch(`${CORE_BUSINESS_URL}/items`, {
        signal: controller.signal,
      }),
    ]);

    clearTimeout(timeout);

    const data = await dataRes.json();
    const items = await itemsRes.json();

    res.json({
      status: "ok",
      data_worker: data,
      core_business: { items },
      aggregated_at: new Date().toISOString(),
    });
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === "AbortError") {
      res.status(504).json({
        error: "upstream_timeout",
        message: `Upstream 응답 시간 초과 (${UPSTREAM_TIMEOUT}ms)`,
        config: { UPSTREAM_TIMEOUT, DATA_WORKER_PORT, DATA_WORKER_URL },
      });
    } else {
      res.status(502).json({
        error: "upstream_error",
        message: err.message,
        target: DATA_WORKER_URL,
      });
    }
  }
});

// 서비스 상태 조회
app.get("/status", async (req, res) => {
  const services = [
    { name: "data-worker", url: `${DATA_WORKER_URL}/healthz` },
    { name: "core-business", url: `${CORE_BUSINESS_URL}/actuator/health` },
  ];

  const results = await Promise.all(
    services.map(async (svc) => {
      try {
        const r = await fetch(svc.url);
        return { name: svc.name, status: r.ok ? "up" : "down", code: r.status };
      } catch (e) {
        return { name: svc.name, status: "down", error: e.message };
      }
    })
  );

  res.json({ services: results });
});

app.listen(PORT, () => {
  console.log(`bff-service listening on :${PORT}`);
});
