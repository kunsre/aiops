"""Visual pipeline runner with Rich terminal output."""

import time
from uuid import uuid4

import httpx
from rich.console import Console
from rich.panel import Panel

from aiops_agents.config import GITHUB_REPO, GITHUB_TOKEN
from aiops_agents.guardrails import (
    LLMCallCounter,
    TokenBudgetExceeded,
    RETRY_DELAY_SECONDS,
)
from aiops_agents.state import AgentState, PipelineStatus, TriggerSource
from aiops_agents.nodes.monitor import monitor_node
from aiops_agents.nodes.generator import generator_node
from aiops_agents.nodes.evaluator import evaluator_node
from aiops_agents.webhooks.jandi import (
    send_jandi_evaluator,
    send_jandi_generator,
    send_jandi_monitor,
    send_jandi_pipeline_complete,
    send_jandi_review_request,
)

console = Console()


def _header():
    console.print()
    console.print(Panel.fit(
        "[bold white]AIOps Self-Healing Pipeline[/bold white]\n"
        "[dim]LangGraph Multi-Agent System[/dim]",
        border_style="blue",
    ))
    console.print()


def _step_panel(icon: str, title: str, color: str, lines: list[str]):
    content = "\n".join(lines)
    console.print(Panel(
        content,
        title=f"{icon} {title}",
        border_style=color,
        padding=(0, 1),
    ))


def _arrow():
    console.print("         [dim]│[/dim]")
    console.print("         [dim]▼[/dim]")


def _close_pr(pr_url: str):
    """실패 시 열려있는 PR을 close."""
    if not pr_url or "github.com" not in pr_url:
        return
    # Extract PR number from URL
    try:
        pr_number = pr_url.rstrip("/").split("/")[-1]
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        httpx.patch(
            f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}",
            headers=headers,
            json={"state": "closed"},
            timeout=10.0,
        )
    except Exception:
        pass


def run_pipeline(alert_content: str, target_services: list[str]):
    """Run the full self-healing pipeline with visual output."""
    _header()
    call_counter = LLMCallCounter()

    state = AgentState(
        pipeline_id=uuid4(),
        trigger_source=TriggerSource.ALERTMANAGER,
        target_services=target_services,
        messages=[{"role": "alert", "content": alert_content}],
    )

    # === TRIGGER ===
    _step_panel("🚨", "ALERT RECEIVED", "red", [
        f"[red bold]Services:[/red bold] {', '.join(target_services)}",
        f"[red]{alert_content}[/red]",
    ])
    _arrow()

    pr_url = None

    try:
        # === MONITOR ===
        console.print("[yellow]  ⏳ Monitor 분석 중...[/yellow]")
        start = time.time()
        call_counter.increment()
        monitor_result = monitor_node(state)
        elapsed = time.time() - start

        rca = monitor_result["rca_report"]
        monitor_lines = [
            f"[bold]원인 서비스:[/bold] {rca.root_cause_service}",
            f"[bold]장애 유형:[/bold] {rca.failure_mode}",
            f"[bold]권고 조치:[/bold] {rca.recommended_action}",
            f"[dim]({elapsed:.1f}s 소요)[/dim]",
        ]

        for msg in monitor_result.get("messages", []):
            if msg.get("role") == "monitor":
                content = msg["content"]
                if isinstance(content, str) and len(content) > 200:
                    monitor_lines.append("")
                    monitor_lines.append("[dim]── 분석 요약 ──[/dim]")
                    monitor_lines.append(f"[dim]{content[:300]}...[/dim]")

        _step_panel("🔍", "MONITOR (SRE Agent)", "yellow", monitor_lines)

        send_jandi_monitor(
            service=rca.root_cause_service,
            failure_mode=rca.failure_mode,
            action=rca.recommended_action or "N/A",
        )
        _arrow()

        # === GENERATOR ===
        state2 = state.model_copy(update=monitor_result)
        console.print("[cyan]  ⏳ Generator 수정 중...[/cyan]")
        start = time.time()
        call_counter.increment()
        gen_result = generator_node(state2)
        elapsed = time.time() - start

        gen_lines = [f"[dim]({elapsed:.1f}s 소요)[/dim]"]
        for change in gen_result.get("proposed_changes", []):
            gen_lines.append(f"[bold]파일:[/bold] {change.file_path}")
            gen_lines.append(f"[bold]변경:[/bold] {change.diff}")
            if change.pull_request_url:
                pr_url = change.pull_request_url
                gen_lines.append(f"[bold green]PR:[/bold green] {pr_url}")

        if not gen_result.get("proposed_changes"):
            for msg in gen_result.get("messages", []):
                if msg.get("role") == "generator":
                    content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                    gen_lines.append(f"[dim]{content[:300]}...[/dim]")

        _step_panel("🔧", "GENERATOR (Dev Agent)", "cyan", gen_lines)

        if pr_url:
            send_jandi_generator(
                service=target_services[0],
                pr_url=pr_url,
                diff_summary=gen_result["proposed_changes"][-1].diff[:200] if gen_result.get("proposed_changes") else "",
            )
        _arrow()

        # === EVALUATOR ===
        state3 = state2.model_copy(update=gen_result)
        console.print("[green]  ⏳ Evaluator 코드 리뷰 중...[/green]")
        start = time.time()
        call_counter.increment()
        eval_result = evaluator_node(state3)
        elapsed = time.time() - start

        eval_results = eval_result.get("evaluation_results")
        passed = eval_results.is_passed if eval_results else False

        eval_lines = [f"[dim]({elapsed:.1f}s 소요)[/dim]"]
        if passed:
            eval_lines.append("[bold green]✅ 검증 통과[/bold green]")
        else:
            eval_lines.append("[bold red]❌ 검증 실패[/bold red]")
            if eval_results and eval_results.error_logs:
                eval_lines.append(f"[dim]{eval_results.error_logs[0][:300]}...[/dim]")

        eval_color = "green" if passed else "red"
        _step_panel("🧪", "EVALUATOR (QA Agent)", eval_color, eval_lines)

        eval_detail = eval_results.error_logs[0][:200] if eval_results and eval_results.error_logs else "검증 통과"
        send_jandi_evaluator(service=target_services[0], passed=passed, detail=eval_detail)

        # === RESULT ===
        console.print()
        final_status = eval_result.get("status", PipelineStatus.FAILED)

        if final_status == PipelineStatus.COMPLETED and pr_url:
            # 성공: 리뷰 요청
            rca_summary = f"{rca.root_cause_service}: {rca.failure_mode}"
            send_jandi_review_request(
                service=target_services[0],
                pr_url=pr_url,
                rca_summary=rca_summary,
                fix_summary=gen_result["proposed_changes"][-1].diff[:200] if gen_result.get("proposed_changes") else "",
                evaluator_verdict="코드 리뷰 통과 - 운영자 머지 승인 대기",
            )
            send_jandi_pipeline_complete(service=target_services[0], status=final_status.value)
            console.print(Panel.fit(
                "[bold green]✅ 검증 완료 - 운영자 리뷰 대기[/bold green]\n"
                f"[green]PR: {pr_url}[/green]",
                border_style="green",
            ))

        elif final_status == PipelineStatus.RETRYING:
            # 실패: PR close + 종료 (retry 안 함 - 토큰 절약)
            if pr_url:
                _close_pr(pr_url)
            send_jandi_pipeline_complete(service=target_services[0], status="FAILED")
            console.print(Panel.fit(
                "[bold red]❌ 자가복구 실패 - PR 닫힘[/bold red]\n"
                "[red]코드 리뷰 미통과. 운영자 수동 확인 필요.[/red]",
                border_style="red",
            ))

        else:
            if pr_url:
                _close_pr(pr_url)
            send_jandi_pipeline_complete(service=target_services[0], status="FAILED")
            console.print(Panel.fit(
                "[bold red]💀 파이프라인 실패[/bold red]",
                border_style="red",
            ))

    except TokenBudgetExceeded as e:
        # 토큰 초과: 강제 종료 + PR close
        console.print(Panel.fit(
            f"[bold red]🚫 토큰 예산 초과 - 강제 종료[/bold red]\n"
            f"[red]{e}[/red]",
            border_style="red",
        ))
        if pr_url:
            _close_pr(pr_url)
        send_jandi_pipeline_complete(service=target_services[0], status="TOKEN_EXCEEDED")

    except Exception as e:
        # 예상치 못한 에러
        console.print(Panel.fit(
            f"[bold red]💀 예상치 못한 에러[/bold red]\n"
            f"[red]{type(e).__name__}: {e}[/red]",
            border_style="red",
        ))
        if pr_url:
            _close_pr(pr_url)
        send_jandi_pipeline_complete(service=target_services[0], status="ERROR")

    finally:
        console.print(f"\n[dim]파이프라인 종료. LLM 호출: {call_counter.count}회[/dim]\n")

    return eval_result if 'eval_result' in locals() else None


if __name__ == "__main__":
    run_pipeline(
        alert_content="[ContainerOOMKilled] data-worker pod was OOMKilled. Container memory limit 256Mi exceeded.",
        target_services=["data-worker"],
    )
