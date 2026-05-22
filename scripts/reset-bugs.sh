#!/bin/bash
# 테스트 후 원복: Generator가 수정한 버그 코드를 원래 상태로 되돌림
# 사용법: ./scripts/reset-bugs.sh

set -e

echo "🔄 버그 코드 원복 중..."

# data-worker config.py
cat > services/data-worker/app/config.py << 'EOF'
"""data-worker configuration."""

# BUG: 타임아웃 1초 → 느린 쿼리 항상 실패
DB_TIMEOUT = 1

# BUG: 재시도 0회 → 일시적 에러에도 즉시 실패
MAX_RETRIES = 0

# BUG: 배치 크기 10000 → 메모리 과다 사용으로 OOM 유발
BATCH_SIZE = 10000

# 정상 설정값들
WORKER_CONCURRENCY = 4
LOG_LEVEL = "INFO"
EOF

# bff-service config.js
cat > services/bff-service/src/config.js << 'EOF'
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
EOF

# api-gateway config.go
cat > services/api-gateway/config.go << 'EOF'
package main

import "time"

// BUG: 프록시 타임아웃 1초 → 대부분의 upstream 응답 timeout
var ProxyTimeout = 1 * time.Second

// BUG: 유휴 연결 1개 → 동시 요청 시 매번 새 연결 생성
var MaxIdleConns = 1

// BUG: 헤더 읽기 100ms → 느린 네트워크 클라이언트 차단
var ReadHeaderTimeout = 100 * time.Millisecond
EOF

# core-business application.yaml
cat > services/core-business/src/main/resources/application.yaml << 'EOF'
server:
  port: 8081
  connection-timeout: 1000

spring:
  datasource:
    url: jdbc:h2:mem:coredb
    driver-class-name: org.h2.Driver
    hikari:
      maximum-pool-size: 1
      connection-timeout: 500
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: false

management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: always
EOF

echo "✅ 버그 코드 원복 완료"
echo ""
echo "다음 단계:"
echo "  git add -A && git commit -m 'reset: 버그 코드 원복 (재테스트용)' && git push"
