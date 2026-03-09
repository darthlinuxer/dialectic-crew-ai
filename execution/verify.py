"""
Task verification and status tracking for execution plans.

Provides:
- show_status(): display task completion table
- mark_task(): manually set task status
- verify_task(): use LLM agent to verify acceptance criteria
- update_task_status(): programmatic status update with persistence
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from schemas import UserStoryExecutionPlan, PRDSchema, ImplementationTask

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR


# ---------------------------------------------------------------------------
# Plan I/O
# ---------------------------------------------------------------------------

def _find_latest_plan() -> Path:
    base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Diretório {PRD_OUTPUT_DIR} não encontrado.")
    jsons = list(base.glob("exec_*.json"))
    if not jsons:
        raise FileNotFoundError(f"Nenhum plano em {PRD_OUTPUT_DIR}/ (esperado exec_*.json)")
    return max(jsons, key=lambda p: p.stat().st_mtime)


def load_plan(plan_path: str | None) -> tuple[UserStoryExecutionPlan, str]:
    """Load plan from file. Returns (plan, resolved_path)."""
    if plan_path is None or plan_path == "--latest":
        path = str(_find_latest_plan())
    else:
        path = plan_path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Plano não encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UserStoryExecutionPlan.model_validate(data), path


def save_plan(plan: UserStoryExecutionPlan, path: str) -> None:
    """Persist plan back to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)


def _find_task(plan: UserStoryExecutionPlan, task_id: str) -> ImplementationTask:
    norm = task_id.strip().upper()
    for t in plan.tasks:
        if t.id.upper() == norm:
            return t
    available = [t.id for t in plan.tasks]
    raise ValueError(f"Task '{task_id}' não encontrada. Disponíveis: {available}")


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

_STATUS_ICONS = {
    "pending": "[ ]",
    "in_progress": "[~]",
    "completed": "[x]",
    "failed": "[!]",
}


def show_status(plan_path: str | None = None) -> dict:
    """Display task status table. Returns summary dict."""
    plan, resolved = load_plan(plan_path)

    print(f"\n{'='*65}")
    print(f"  {plan.user_story_id} — {plan.user_story_title}")
    print(f"  Score: {plan.quality_score}/10.0  |  Plano: {resolved}")
    print(f"{'='*65}")

    counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
    for t in sorted(plan.tasks, key=lambda x: (x.order, x.id)):
        icon = _STATUS_ICONS.get(t.status, "[ ]")
        deps = f"  (deps: {', '.join(t.dependencies)})" if t.dependencies else ""
        notes = f"  -- {t.verification_notes}" if t.verification_notes else ""
        completed = f"  ({t.completed_at})" if t.completed_at else ""
        print(f"  {icon} {t.id} — {t.title}{deps}{completed}{notes}")
        counts[t.status] = counts.get(t.status, 0) + 1

    total = len(plan.tasks)
    done = counts["completed"]
    print(f"\n  Progresso: {done}/{total} concluídas", end="")
    if counts["failed"]:
        print(f", {counts['failed']} falharam", end="")
    if counts["in_progress"]:
        print(f", {counts['in_progress']} em andamento", end="")
    print(f"\n{'='*65}\n")

    return {
        "plan_path": resolved,
        "total": total,
        **counts,
    }


# ---------------------------------------------------------------------------
# Mark task
# ---------------------------------------------------------------------------

def mark_task(
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    plan_path: str | None = None,
    notes: str = "",
) -> dict:
    """Manually set task status and persist."""
    plan, resolved = load_plan(plan_path)
    task = _find_task(plan, task_id)

    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    elif status == "pending":
        task.completed_at = None

    save_plan(plan, resolved)
    icon = _STATUS_ICONS.get(status, "[ ]")
    print(f"  {icon} {task.id} — {task.title} -> {status}")
    if notes:
        print(f"      Notas: {notes}")
    return {"task_id": task.id, "status": status, "plan_path": resolved}


# ---------------------------------------------------------------------------
# Update task status (programmatic, used by dialectic_execution)
# ---------------------------------------------------------------------------

def update_task_status(
    plan_path: str,
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    notes: str = "",
) -> None:
    """Update task status in-place and save. Used by execution engine."""
    plan, resolved = load_plan(plan_path)
    task = _find_task(plan, task_id)
    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    save_plan(plan, resolved)


# ---------------------------------------------------------------------------
# Verify task with LLM (acceptance criteria check)
# ---------------------------------------------------------------------------

def _load_prd_for_plan(plan: UserStoryExecutionPlan, prd_path: str | None) -> PRDSchema | None:
    """Try to load the PRD that contains the user story for this plan."""
    if prd_path:
        with open(prd_path, "r", encoding="utf-8") as f:
            return PRDSchema.model_validate(json.load(f))
    base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        return None
    jsons = list(base.glob("PRD_*.json"))
    if not jsons:
        return None
    latest = max(jsons, key=lambda p: p.stat().st_mtime)
    with open(latest, "r", encoding="utf-8") as f:
        return PRDSchema.model_validate(json.load(f))


def verify_task(
    task_id: str,
    plan_path: str | None = None,
    prd_path: str | None = None,
) -> dict:
    """
    Verify task completion using an LLM agent that checks:
    1. Task description fulfillment (files exist, code correct)
    2. Acceptance criteria from PRD (if available)

    Updates plan status based on verification result.
    """
    plan, resolved = load_plan(plan_path)
    task = _find_task(plan, task_id)

    prd = _load_prd_for_plan(plan, prd_path)
    acceptance_criteria: list[str] = []
    if prd:
        us_id_norm = plan.user_story_id.strip().upper().replace("-", "").replace("_", "")
        for us in prd.user_stories:
            id_norm = us.id.strip().upper().replace("-", "").replace("_", "")
            if id_norm == us_id_norm:
                acceptance_criteria = us.acceptance_criteria
                break

    ac_text = ""
    if acceptance_criteria:
        ac_text = "\n\nACCEPTANCE CRITERIA da User Story (verifique se esta task contribui para atendê-los):\n"
        ac_text += "\n".join(f"- {ac}" for ac in acceptance_criteria)

    from crewai import Task, Crew
    from dialectic.agents import validador_macro
    from schemas import ValidationOutput

    verify_task_desc = Task(
        description=f"""
Verifique se a task abaixo foi implementada corretamente no codebase.

TASK: {task.id} — {task.title}
DESCRIÇÃO: {task.description}

Use as ferramentas de leitura de arquivo para verificar se:
1. Os arquivos/artefatos descritos na task existem
2. O conteúdo está correto e alinhado com a descrição
3. Não há erros óbvios
{ac_text}

Responda com quality_score (0-10), consensus_reached (true se task está completa), e final_validation_notes explicando o que foi verificado.
""",
        expected_output="ValidationOutput com quality_score, consensus_reached, final_validation_notes",
        agent=validador_macro,
        output_pydantic=ValidationOutput,
    )

    from dialectic.tools import file_read_tool
    validador_macro_with_tools = validador_macro.model_copy()
    validador_macro_with_tools.tools = [file_read_tool]

    crew = Crew(
        agents=[validador_macro_with_tools],
        tasks=[verify_task_desc],
        verbose=True,
    )

    print(f"\n  Verificando {task.id} — {task.title}...")
    result = crew.kickoff()

    validation: ValidationOutput | None = None
    pydantic_result = getattr(result, "pydantic", None)
    if isinstance(pydantic_result, ValidationOutput):
        validation = pydantic_result
    else:
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_p = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_p, ValidationOutput):
                validation = last_p

    if validation is None:
        raw = getattr(result, "raw", str(result))
        print(f"  Falha ao obter resultado estruturado. Raw: {raw[:500]}")
        return {"task_id": task.id, "verified": False, "notes": "Falha na verificação"}

    verified = validation.consensus_reached and validation.quality_score >= 7.0
    new_status: Literal["completed", "failed"] = "completed" if verified else "failed"

    task.status = new_status
    task.verification_notes = validation.final_validation_notes
    if verified:
        task.completed_at = datetime.now().isoformat(timespec="seconds")

    save_plan(plan, resolved)

    icon = _STATUS_ICONS.get(new_status, "[ ]")
    print(f"\n  {icon} {task.id} — score: {validation.quality_score}/10")
    print(f"      Status: {new_status}")
    print(f"      Notas: {validation.final_validation_notes[:300]}")

    return {
        "task_id": task.id,
        "verified": verified,
        "score": validation.quality_score,
        "status": new_status,
        "notes": validation.final_validation_notes,
        "plan_path": resolved,
    }
