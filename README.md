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

| 서비스 | 언어 | 역할 | 의도적 버그 |
|--------|------|------|------------|
| api-gateway | Go | 단일 진입점, bff로 프록시 | `ProxyTimeout = 1s` (정상: 30s) |
| bff-service | Node.js | 어그리게이터 (data-worker + core-business 호출) | `UPSTREAM_TIMEOUT = 500ms`, `DATA_WORKER_PORT = 9999` |
| data-worker | Python FastAPI | 데이터 처리 | `DB_TIMEOUT = 1s`, `BATCH_SIZE = 10000` |
| core-business | Java Spring Boot | CRUD + DB | `HikariCP max-pool-size = 1` |

## 자가복구 시나리오

| 시나리오 | 장애 현상 | 에이전트 수정 |
|---------|----------|-------------|
| DB Timeout | data-worker 504 (쿼리 2.5초, timeout 1초) | `config.py` DB_TIMEOUT = 1 → 30 |
| Batch OOM | data-worker OOMKilled (배치 10000개) | `config.py` BATCH_SIZE = 10000 → 100 |
| Wrong Port | bff → data-worker 연결 실패 502 | `config.js` DATA_WORKER_PORT = 9999 → 8000 |
| Upstream Timeout | bff 504 (timeout 500ms) | `config.js` UPSTREAM_TIMEOUT = 500 → 10000 |
| Proxy Timeout | gateway 502 (timeout 1초) | `config.go` ProxyTimeout = 1s → 30s |
| Pool Exhaustion | core-business 500 (pool 1개) | `application.yaml` max-pool-size = 1 → 10 |

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

```bash
# Generator가 버그를 수정한 후, 데모를 다시 실행하려면:
./scripts/reset-bugs.sh
git add -A && git commit -m "reset: 버그 코드 원복" && git push
```

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
