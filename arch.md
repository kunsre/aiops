🤖 자율형 SRE 멀티 에이전트 시스템 (AIOps) 상세 구축 계획 및 워크플로우 명세서
본 문서는 단일 LLM의 한계를 극복하고, 고도화된 폴리글랏(Polyglot) MSA 환경에서 시스템 장애 자가 복구(Self-Healing) 및 자율적 기능 배포를 수행하기 위한 멀티 에이전트(Multi-Agent) 시스템의 아키텍처, 시나리오, 상태 전이 및 도구 매니페스트를 다룹니다.

1. 시스템 아키텍처 및 에이전트 토폴로지 (Topology)
본 아키텍처는 에이전트 간의 단순한 선형적 호출을 넘어, 복잡한 피드백 루프와 순환 참조(Cyclic Loop)를 안정적으로 제어하기 위해 LangGraph 기반의 유향 유사이클 그래프(Directed Cyclic Graph) 구조로 설계됩니다. 각 에이전트는 독립된 컨텍스트와 전용 도구(Tools) 체인을 가지며, 공유 상태(Shared State) 객체를 통해 데이터를 주고받습니다.

Plaintext
       ┌─────────────────── Alertmanager / Human Input ───────────────────┐
       │                                                                  │
       ▼                                                                  ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│   Monitor    │ ──────────> │  Generator   │ <────────── │   Planner    │
│  (SRE Agent) │             │ (Dev Agent)  │             │  (PM Agent)  │
└──────────────┘             └──────────────┘             └──────────────┘
       ▲                            │
       │                            ▼
       │                     ┌──────────────┐
       └──────────────────── │  Evaluator   │
        (If Retest Passes)   │  (QA Agent)  │
                             └──────────────┘
                                    │
                                    ▼ (If Test Fails - Loop Back)
1.1. 에이전트 페르소나 및 핵심 책무 (Roles & Responsibilities)
Monitor (SRE 관제 에이전트)

책무: 클러스터 내부의 아웃풋 알람 감지, VictoriaMetrics API를 통한 PromQL/LogQL 교차 검증, 장애 원인(인프라 vs 앱 버그) 분류 및 Jandi 메신저 등 외부 채널로 1차 리포팅.

Planner (기획/아키텍트 에이전트)

책무: 신규 기능 추가 또는 아키텍처 변경 요구사항 수렴, 4개 마이크로서비스 간의 의존성 및 영향도 분석, 구현 스펙 및 인수 테스트 조건(Acceptance Criteria) 정의.

Generator (개발 및 프로비저닝 에이전트)

책무: Monitor의 원인 분석 기반 핫픽스(Hotfix) 코드 작성, Planner의 스펙 기준 신규 기능 구현, K8s 매니페스트 수정, GitHub PR(Pull Request) 자동 발행.

Evaluator (검증 및 릴리스 에이전트)

책무: 샌드박스 환경에 테스트 워크로드 트리거, 성공 시 GitOps 배포 승인, 실패 시 원인 로그와 함께 Generator로 롤백 요청(피드백 루프 생성).

2. 멀티 에이전트 공유 상태 (Shared State) 스키마
LangGraph 채널을 통해 모든 에이전트가 공유하고 업데이트하는 상태 객체의 구조입니다.

JSON
{
  "pipeline_id": "uuid",
  "trigger_source": "ALERTMANAGER | PLANNER_REQUEST",
  "target_services": ["api-gateway", "data-worker", "core-business", "bff-service"],
  "status": "INIT | ANALYZING | IMPLEMENTING | TESTING | RETRYING | COMPLETED",
  "rca_report": {
    "root_cause_service": "string",
    "failure_mode": "string",
    "evidence_logs": ["string"]
  },
  "proposed_changes": [
    {
      "repository": "string",
      "pull_request_url": "string",
      "diff": "string"
    }
  ],
  "evaluation_results": {
    "is_passed": boolean,
    "error_logs": ["string"]
  },
  "retry_count": "integer (최대 3회 제한)"
}
3. 세부 실행 시나리오 및 데이터 플로우 (Detailed Scenarios)
시나리오 A: 자가 복구 루프 (OOM 크래시 발생 및 자동 스케일 업)
대상 서비스: data-worker (Python FastAPI)

발생 원인: 데이터 파이프라인 연산 중 메모리 누수로 인한 K8s OOMKilled 발생.

감지 (Monitor): Alertmanager 알람 수신 후 query_promql로 메모리 지표 확인. rca_report에 '메모리 제한 부족' 기록 후 Generator 호출.

구현 (Generator): K8s 배포 설정 파일(deployments/data-worker.yaml)의 resources.limits.memory 값을 2Gi에서 4Gi로 상향하는 PR 발행.

검증 (Evaluator): 격리된 네임스페이스에 수정된 매니페스트를 임시 배포. 부하 테스트 통과 시 PR 머지 및 운영 배포 승인. Monitor가 최종 지표 안정화 확인.

시나리오 B: 자율 개발 루프 (Planner 주도 신규 캐싱 도입)
대상 서비스: api-gateway (Go)

목표: Gateway 단에 Redis 캐시 레이어를 도입.

기획 (Planner): "Redis 헬스체크 실패 시 DB로 폴백되어야 함", "토큰 TTL은 3600초" 등의 인수 조건을 명세화.

구현 (Generator): Go 소스 코드에 Redis 연동 로직 추가 및 인프라 매니페스트(Helm values) 수정 후 PR 오픈.

검증 (Evaluator): 샌드박스에서 Redis 컨테이너와 함께 띄워 테스트. 만약 연결 권한 에러(FAIL)가 나면 실패 로그를 담아 상태를 RETRYING으로 변경하고 Generator로 돌려보냄(Feedback Loop). 재수정된 코드가 통과(PASS)하면 최종 배포.

4. 에이전트별 세부 도구(Tools) 명세
에이전트들이 Function Calling으로 사용할 실제 파이썬/Go 기반 커스텀 함수들입니다.

4.1. Monitor 에이전트
query_promql(query, time_range): VictoriaMetrics에 쿼리하여 리소스 지표 반환.

query_logql(namespace, app, filter): VictoriaLogs에서 특정 에러 스트림 로그 반환.

4.2. Generator 에이전트
get_git_repository(repo_url, branch): 작업 디렉토리로 소스 클론.

patch_codebase(file_path, target, replacement): 파일의 특정 라인 패치.

create_pull_request(repo, title, body): GitHub/GitLab API를 통한 PR 생성.

4.3. Evaluator 에이전트
trigger_test_pipeline(pr_number): 샌드박스 클러스터 환경에 임시 배포 구동.

run_load_test(target_url, rps): 엔드포인트에 가상 트래픽 부하 인가.

approve_and_sync_gitops(pr_number): 테스트 합격 후 PR 머지 및 ArgoCD Sync 트리거.

5. 단계별 마일스톤
Phase 1: 실험실 환경 구축 (MVP 타겟 앱)

Go, Python, Java, Node.js 기반 4개 데모 마이크로서비스 프로젝트 생성 및 의도적 장애 코드 내장.

로컬 K8s 환경에 Vector + VictoriaMetrics 구성.

Phase 2: 단일 에이전트 런타임 통합

API 래퍼 라이브러리 및 커스텀 Tool 펑션 구현. 개별 에이전트 프롬프트 튜닝 및 Function Calling 테스트.

Phase 3: LangGraph 멀티 에이전트 완성

상태 객체 기반 에이전트 노드 결합 및 순환 참조(롤백) 로직 안정화. 무인 자가 복구 루프 최종 테스트.
