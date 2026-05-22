"""Visual pipeline runner with Rich terminal output."""

import os
import time
from uuid import uuid4

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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


def run_pipeline(alert_content: str, target_services: list[str]):
    """Run the full self-healing pipeline with visual output."""
    _header()

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

    # === MONITOR ===
    console.print("[yellow]  ⏳ Monitor analyzing...[/yellow]")
    start = time.time()
    monitor_result = monitor_node(state)
    elapsed = time.time() - start

    rca = monitor_result["rca_report"]
    monitor_lines = [
        f"[bold]Root Cause:[/bold] {rca.root_cause_service}",
        f"[bold]Failure Mode:[/bold] {rca.failure_mode}",
        f"[bold]Recommended:[/bold] {rca.recommended_action}",
        f"[dim]({elapsed:.1f}s elapsed)[/dim]",
    ]

    # Extract tool calls from messages
    for msg in monitor_result.get("messages", []):
        if msg.get("role") == "monitor":
            content = msg["content"]
            if isinstance(content, str) and len(content) > 200:
                monitor_lines.append("")
                monitor_lines.append("[dim]── Analysis Excerpt ──[/dim]")
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
    console.print("[cyan]  ⏳ Generator implementing fix...[/cyan]")
    start = time.time()
    gen_result = generator_node(state2)
    elapsed = time.time() - start

    gen_lines = [f"[dim]({elapsed:.1f}s elapsed)[/dim]"]
    for change in gen_result.get("proposed_changes", []):
        gen_lines.append(f"[bold]File:[/bold] {change.file_path}")
        gen_lines.append(f"[bold]Diff:[/bold] {change.diff}")
        if change.pull_request_url:
            gen_lines.append(f"[bold green]PR:[/bold green] [link={change.pull_request_url}]{change.pull_request_url}[/link]")

    if not gen_result.get("proposed_changes"):
        for msg in gen_result.get("messages", []):
            if msg.get("role") == "generator":
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                gen_lines.append(f"[dim]{content[:300]}...[/dim]")

    _step_panel("🔧", "GENERATOR (Dev Agent)", "cyan", gen_lines)

    for change in gen_result.get("proposed_changes", []):
        if change.pull_request_url:
            send_jandi_generator(
                service=target_services[0],
                pr_url=change.pull_request_url,
                diff_summary=change.diff[:200],
            )

    _arrow()

    # === EVALUATOR ===
    state3 = state2.model_copy(update=gen_result)
    console.print("[green]  ⏳ Evaluator validating...[/green]")
    start = time.time()
    eval_result = evaluator_node(state3)
    elapsed = time.time() - start

    eval_results = eval_result.get("evaluation_results")
    passed = eval_results.is_passed if eval_results else False

    eval_lines = [f"[dim]({elapsed:.1f}s elapsed)[/dim]"]
    if passed:
        eval_lines.append("[bold green]✅ PASSED[/bold green]")
    else:
        eval_lines.append("[bold red]❌ FAILED[/bold red]")
        if eval_results:
            if eval_results.failed_resource:
                eval_lines.append(f"[bold]Resource:[/bold] {eval_results.failed_resource}")
            if eval_results.failure_phase:
                eval_lines.append(f"[bold]Phase:[/bold] {eval_results.failure_phase}")
            if eval_results.error_logs:
                eval_lines.append("")
                eval_lines.append("[dim]── Error Logs ──[/dim]")
                eval_lines.append(f"[dim]{eval_results.error_logs[0][:300]}...[/dim]")

    eval_color = "green" if passed else "red"
    _step_panel("🧪", "EVALUATOR (QA Agent)", eval_color, eval_lines)

    eval_detail = eval_results.error_logs[0][:200] if eval_results and eval_results.error_logs else "OK"
    send_jandi_evaluator(service=target_services[0], passed=passed, detail=eval_detail)

    # === REVIEW REQUEST (Human-in-the-loop) ===
    if passed and gen_result.get("proposed_changes"):
        pr_url = gen_result["proposed_changes"][-1].pull_request_url or "N/A"
        rca_summary = f"{rca.root_cause_service}: {rca.failure_mode}"
        fix_summary = gen_result["proposed_changes"][-1].diff[:200]
        evaluator_verdict = eval_detail

        send_jandi_review_request(
            service=target_services[0],
            pr_url=pr_url,
            rca_summary=rca_summary,
            fix_summary=fix_summary,
            evaluator_verdict="검증 통과 - 머지 승인 대기",
        )

    # === RESULT ===
    console.print()
    final_status = eval_result.get("status", PipelineStatus.FAILED)
    send_jandi_pipeline_complete(service=target_services[0], status=final_status.value)

    if final_status == PipelineStatus.COMPLETED:
        pr_link = ""
        if gen_result.get("proposed_changes"):
            pr_link = f"\n[dim]PR: {gen_result['proposed_changes'][-1].pull_request_url}[/dim]"
        console.print(Panel.fit(
            "[bold green]✅ VALIDATION PASSED[/bold green]\n"
            f"[green]운영자 리뷰 승인 대기 중: {', '.join(target_services)}[/green]"
            f"{pr_link}",
            border_style="green",
        ))
    elif final_status == PipelineStatus.RETRYING:
        console.print(Panel.fit(
            f"[bold yellow]🔄 RETRYING ({eval_result.get('retry_count', 0)}/3)[/bold yellow]\n"
            "[yellow]Evaluator requested Generator to fix issues[/yellow]",
            border_style="yellow",
        ))
    else:
        console.print(Panel.fit(
            "[bold red]💀 PIPELINE FAILED[/bold red]",
            border_style="red",
        ))

    return eval_result


if __name__ == "__main__":
    run_pipeline(
        alert_content="[ContainerOOMKilled] data-worker pod was OOMKilled. Container memory limit 256Mi exceeded. Pod restarted 3 times in last 5 minutes.",
        target_services=["data-worker"],
    )
