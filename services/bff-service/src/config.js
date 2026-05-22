/**
 * bff-service configuration
 *
 * BUG SCENARIOS (Generator가 패치할 대상):
 * - UPSTREAM_TIMEOUT: 500ms로 설정되어 대부분 타임아웃 (정상: 10000ms)
 * - DATA_WORKER_URL: 잘못된 포트 9999 → 연결 실패 (정상: 8000)
 * - MAX_CONCURRENT_REQUESTS: 1로 설정 → 동시 요청 불가 (정상: 50)
 */

// BUG: 타임아웃 500ms → 대부분의 upstream 응답이 timeout
const UPSTREAM_TIMEOUT = 500;

// BUG: 잘못된 포트 번호 → data-worker 연결 실패
const DATA_WORKER_PORT = 9999;

// BUG: 동시 요청 1개 → 두 번째 요청부터 대기/실패
const MAX_CONCURRENT_REQUESTS = 1;

// 정상 설정값들
const RETRY_COUNT = 2;
const LOG_LEVEL = "info";

module.exports = {
  UPSTREAM_TIMEOUT,
  DATA_WORKER_PORT,
  MAX_CONCURRENT_REQUESTS,
  RETRY_COUNT,
  LOG_LEVEL,
};
