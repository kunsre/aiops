# AIOps - 자율형 SRE 멀티 에이전트 자가복구 시스템

LangGraph 기반 멀티 에이전트가 MSA 환경의 장애를 자동으로 감지 → 분석 → 수정 → 검증하는 시스템.

## 아키텍처

```
사용자 요청 → api-gateway (Go) → bff-service (Node.js) → data-worker (Python)
                                                       → core-business (Java)

장애 발생 시:
┌─────────────────────────────────────────────────────────────────────────┐
│  VictoriaMetrics + vmalert → Alertmanager → Agent Webhook               │
│                                                                         │
│  🔍 Monitor: PromQL/LogQL로 RCA 분석 (한국어)                           │
│       ↓                                                                 │
│  🔧 Generator: 버그 코드 패치 + GitHub PR 생성 (한국어 RCA 포함)        │
│       ↓                                                                 │
│  🧪 Evaluator: 코드 리뷰 (PASS/FAIL)                                   │
│       ↓                                                                 │
│  👀 잔디 알림: "리뷰 승인 대기" + PR 링크                               │
│       ↓                                                                 │
│  🧑‍💻 운영자: PR 리뷰 → Merge → ArgoCD 자동 배포                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## 기술 스택

| 구성 요소 | 기술 |
|----------|------|
| 에이전트 프레임워크 | LangGraph (Python) |
| LLM | AWS Bedrock (Claude Haiku/Sonnet) |
| 모니터링 | VictoriaMetrics + VictoriaLogs + vmalert |
| 알림 | Alertmanager → Jandi Webhook |
| GitOps | ArgoCD |
| 인프라 | Kubernetes (Kind 로컬 / EKS 프로덕션) |
| IaC | Terraform |

## 데모 서비스 (폴리글랏 MSA)

| 서비스 | 언어 | 역할 |
|--------|------|------|
| api-gateway | Go | 단일 진입점, bff로 프록시 |
| bff-service | Node.js | 어그리게이터 (data-worker + core-business 병렬 호출) |
| data-worker | Python FastAPI | 데이터 처리 + DB 쿼리 |
| core-business | Java Spring Boot | CRUD + H2 DB |

## 브랜치 전략 (Bug Branch Architecture)

```
main            = 정상 상태 (모든 설정값 healthy)
bug/db-timeout  = data-worker DB_TIMEOUT=1, MAX_RETRIES=0
bug/batch-oom   = data-worker BATCH_SIZE=10000
bug/wrong-port  = bff-service DATA_WORKER_PORT=9999
bug/upstream-timeout = bff-service UPSTREAM_TIMEOUT=500
bug/proxy-timeout    = api-gateway ProxyTimeout=1s
bug/pool-exhaustion  = core-business max-pool-size=1
```

bug 브랜치는 영구 보존되며 에이전트에 의해 수정되지 않습니다.

## 자가복구 시나리오

| 시나리오 | Bug Branch | 장애 현상 | 에이전트 패치 |
|---------|-----------|----------|-------------|
| DB Timeout | `bug/db-timeout` | 504 (쿼리 2.5초, timeout 1초) | DB_TIMEOUT = 1 → 30 |
| Batch OOM | `bug/batch-oom` | OOMKilled (배치 10000개) | BATCH_SIZE = 10000 → 100 |
| Wrong Port | `bug/wrong-port` | 502 (포트 9999 연결 실패) | DATA_WORKER_PORT = 9999 → 8000 |
| Upstream Timeout | `bug/upstream-timeout` | 504 (timeout 500ms) | UPSTREAM_TIMEOUT = 500 → 10000 |
| Proxy Timeout | `bug/proxy-timeout` | 502 (gateway timeout 1초) | ProxyTimeout = 1s → 30s |
| Pool Exhaustion | `bug/pool-exhaustion` | 500 (pool 1개 고갈) | max-pool-size = 1 → 10 |

## 데모 사이클

```
1. 대시보드에서 시나리오 선택 → "장애 주입" 클릭
   └─ ArgoCD targetRevision을 bug/* 브랜치로 전환
   └─ ArgoCD auto-sync → 버그 코드 배포

2. "트래픽 발생" 클릭 → MSA 체인 호출 → 에러 발생
   └─ VictoriaMetrics 메트릭 쌓임 → vmalert rule 발화

3. Alertmanager → 에이전트 webhook 자동 트리거
   └─ Monitor: RCA 분석 (한국어)
   └─ Generator: bug branch 기반 fix PR 생성
   └─ Evaluator: 코드 리뷰

4. 잔디 알림: "리뷰 승인 대기" + PR 링크

5. 운영자: GitHub PR 리뷰 → Merge
   └─ ArgoCD가 main 감지 → 정상 코드 배포 → 복구 완료

6. 다시 테스트? → 1번부터 반복 (bug branch는 영구 보존)
   또는 "정상 복구" 버튼으로 즉시 main 복원
```

## 빠른 시작

### 사전 요구사항
- Docker
- Kind (`brew install kind`)
- kubectl
- Helm

### 1. 클러스터 생성 + 배포

```bash
# Kind 클러스터 생성
kind create cluster --name aiops

# 네임스페이스
kubectl --context kind-aiops create namespace aiops
kubectl --context kind-aiops create namespace monitoring

# 서비스 이미지 빌드 + Kind 로드
docker build -t data-worker:latest services/data-worker/
docker build -t api-gateway:latest services/api-gateway/
docker build -t bff-service:latest services/bff-service/
docker build -t core-business:latest services/core-business/
docker build -t aiops-agent:latest agents/
docker build -t fault-dashboard:latest services/fault-dashboard/
kind load docker-image data-worker:latest api-gateway:latest bff-service:latest core-business:latest aiops-agent:latest fault-dashboard:latest --name aiops

# K8s 배포
kubectl --context kind-aiops apply -f services/data-worker/k8s/
kubectl --context kind-aiops apply -f services/api-gateway/k8s/
kubectl --context kind-aiops apply -f services/bff-service/k8s/
kubectl --context kind-aiops apply -f services/core-business/k8s/
kubectl --context kind-aiops apply -f agents/k8s/
kubectl --context kind-aiops apply -f services/fault-dashboard/k8s/
```

### 2. 모니터링 스택 설치

```bash
helm repo add vm https://victoriametrics.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm install victoriametrics vm/victoria-metrics-single -n monitoring
helm install kube-state-metrics prometheus-community/kube-state-metrics -n monitoring
helm install alertmanager prometheus-community/alertmanager -n monitoring
helm install vmalert vm/victoria-metrics-alert -n monitoring
```

### 3. ArgoCD 설치

```bash
kubectl --context kind-aiops create namespace argocd
kubectl --context kind-aiops apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl --context kind-aiops apply -f gitops/appproject.yaml
kubectl --context kind-aiops apply -f gitops/applications/
```

### 4. 대시보드 접속

```bash
kubectl --context kind-aiops port-forward -n aiops svc/fault-dashboard 8080:8080
# http://localhost:8080
```

### 5. 시크릿 설정

```bash
kubectl --context kind-aiops create secret generic aiops-secrets -n aiops \
  --from-literal=AWS_BEARER_TOKEN_BEDROCK="your-token" \
  --from-literal=GITHUB_TOKEN="ghp_your-token"
```

## Timeout Budgeting (프로덕션 권장 설계)

```
Client Request (30s)
  └─► api-gateway ProxyTimeout: 10s
        └─► bff-service UPSTREAM_TIMEOUT: 5s
              ├─► data-worker DB_TIMEOUT: 3s
              └─► core-business HikariCP connection-timeout: 2.5s
```

현재 데모에서는 의도적으로 비정상 값을 설정하여 장애를 유발합니다.
에이전트가 이 버그들을 감지하고 정상값으로 패치하는 것이 자가복구 시나리오입니다.

## 가드레일 (Safety)

- **토큰 예산**: 파이프라인당 LLM 호출 최대 30회 → 초과 시 강제 종료
- **쿨다운**: 같은 서비스 5분 내 중복 트리거 차단
- **Max Memory Limit**: 4Gi 초과 제안 시 에스컬레이션
- **PR 자동 Close**: Evaluator 실패 시 PR 닫힘 → "수동 확인 필요" 알림
- **Human-in-the-loop**: 에이전트는 PR만 생성, 머지는 운영자가 직접

## 테스트 후 원복

Bug branch 아키텍처이므로 원복 스크립트가 필요 없습니다:
- 대시보드 "정상 복구" 버튼 → 모든 앱 main으로 복원
- bug branch는 영구 보존 → 다음 데모 시 재사용

## 프로젝트 구조

```
aiops/
├── agents/              # LangGraph 멀티 에이전트 (Python)
│   ├── src/aiops_agents/
│   │   ├── graph.py     # StateGraph 정의
│   │   ├── state.py     # Pydantic 공유 상태
│   │   ├── config.py    # Bedrock LLM 설정
│   │   ├── llm.py       # ChatBedrockAnthropic 래퍼
│   │   ├── guardrails.py # 안전장치
│   │   ├── runner.py    # 시각화 파이프라인 실행기
│   │   ├── nodes/       # Monitor, Generator, Evaluator, Planner
│   │   ├── tools/       # PromQL, LogQL, GitHub, Source Code
│   │   ├── prompts/     # 에이전트별 시스템 프롬프트
│   │   └── webhooks/    # Alertmanager + Jandi 연동
│   ├── k8s/             # 에이전트 K8s 배포
│   ├── Dockerfile
│   └── tests/
├── services/            # 4개 데모 마이크로서비스
│   ├── api-gateway/     # Go
│   ├── bff-service/     # Node.js
│   ├── data-worker/     # Python FastAPI
│   ├── core-business/   # Java Spring Boot
│   └── fault-dashboard/ # 장애 주입 대시보드 (nginx)
├── infra/               # Terraform (EKS/VPC/ECR/IAM)
├── monitoring/          # Alert rules, Vector config
├── gitops/              # ArgoCD Applications
├── scripts/             # 유틸리티 스크립트
└── arch.md              # 원본 아키텍처 명세
```
