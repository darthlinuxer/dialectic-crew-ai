"""
Execução do plano aprovado: consome UserStoryExecutionPlan e gera artefatos (spec/esboço).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Union

from schemas import UserStoryExecutionPlan

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR

EXEC_OUTPUT_DIR = "exec_output"


def _find_latest_plan() -> Path:
    """Encontra o plano de execução mais recente em prd_output/ (exec_*.json)."""
    base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Diretório {PRD_OUTPUT_DIR} não encontrado.")
    jsons = list(base.glob("exec_*.json"))
    if not jsons:
        raise FileNotFoundError(f"Nenhum plano de execução em {PRD_OUTPUT_DIR}/ (esperado exec_*.json)")
    return max(jsons, key=lambda p: p.stat().st_mtime)


def _load_plan(plan_path: str) -> UserStoryExecutionPlan:
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UserStoryExecutionPlan.model_validate(data)


def _artifact_markdown(plan: UserStoryExecutionPlan) -> str:
    """Gera Markdown com spec/esboço de implementação por task (para execução manual ou futura geração de código)."""
    lines = [
        f"# Spec de implementação — {plan.user_story_id} {plan.user_story_title}",
        "",
        f"*Gerado em {datetime.now().isoformat(timespec='seconds')}*",
        "",
        "---",
        "",
        "## Abordagem",
        "",
        plan.approach_summary,
        "",
        "---",
        "",
        "## Tasks (ordem de execução)",
        "",
    ]
    for t in sorted(plan.tasks, key=lambda x: (x.order, x.id)):
        deps = f" *Dependências: {', '.join(t.dependencies)}*" if t.dependencies else ""
        lines.extend([
            f"### {t.id} — {t.title}",
            "",
            t.description,
            deps,
            "",
        ])
    if plan.risks_mitigated:
        lines.extend(["---", "", "## Riscos mitigados", ""])
        for r in plan.risks_mitigated:
            lines.append(f"- {r}")
        lines.append("")
    if plan.tech_notes:
        lines.extend(["---", "", "## Notas técnicas", "", plan.tech_notes, ""])
    return "\n".join(lines).strip() + "\n"


def run_execution(
    plan_path: str | None = None,
    plan: Union[UserStoryExecutionPlan, dict] | None = None,
    output_dir: str | None = None,
) -> dict:
    """
    Consome um UserStoryExecutionPlan e gera artefato de execução (spec em Markdown).
    Args:
        plan_path: Caminho para arquivo JSON do plano (exec_*.json). Ignorado se plan for passado.
        plan: Plano já carregado (dict ou UserStoryExecutionPlan). Opcional.
        output_dir: Diretório de saída (default: exec_output).
    Returns:
        dict com output_path (arquivo .md gerado), plan_id, success.
    """
    out_dir = output_dir or EXEC_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)

    if plan is not None:
        if isinstance(plan, dict):
            plan_obj = UserStoryExecutionPlan.model_validate(plan)
        else:
            plan_obj = plan
        plan_id = plan_obj.user_story_id
    else:
        path = plan_path
        if path is None or path == "--latest":
            path = str(_find_latest_plan())
        if not os.path.exists(path):
            raise FileNotFoundError(f"Plano não encontrado: {path}")
        plan_obj = _load_plan(path)
        plan_id = plan_obj.user_story_id

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_id = plan_id.replace(" ", "_")
    filename = f"spec_{safe_id}_{timestamp}.md"
    output_path = os.path.join(out_dir, filename)

    content = _artifact_markdown(plan_obj)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "output_path": output_path,
        "plan_id": plan_id,
        "plan_title": plan_obj.user_story_title,
    }
