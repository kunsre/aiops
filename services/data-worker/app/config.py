"""data-worker configuration.

BUG SCENARIOS (Generator가 패치할 대상):
- DB_TIMEOUT: 1초로 설정되어 대부분의 쿼리가 타임아웃 (정상: 30초)
- MAX_RETRIES: 0으로 설정되어 재시도 없음 (정상: 3회)
- BATCH_SIZE: 10000으로 설정되어 메모리 과다 사용 (정상: 100)
"""

# BUG: 타임아웃 1초 → 느린 쿼리 항상 실패
DB_TIMEOUT = 1

# BUG: 재시도 0회 → 일시적 에러에도 즉시 실패
MAX_RETRIES = 0

# BUG: 배치 크기 10000 → 메모리 과다 사용으로 OOM 유발
BATCH_SIZE = 10000

# 정상 설정값들
WORKER_CONCURRENCY = 4
LOG_LEVEL = "INFO"
