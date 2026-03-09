"""
Fluxo dialético para planejamento da execução de uma user story.
Produz UserStoryExecutionPlan (tese → antítese → síntese → validação).

Usa features nativas do CrewAI:
- output_pydantic: structured output do Validador (elimina parsing manual de JSON)
- Task guardrails: validação automática da estrutura do plano
- akickoff() + asyncio.wait_for(): timeout nativo
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai import Task, Crew

from dialectic.agents import visionario, critico_socratico, sintetizador, validador_macro
from dialectic.export import execution_plan_to_markdown
from dialectic.prd_flow import OUTPUT_DIR
from schemas import PRDSchema, UserStoryExecutionPlan

CREW_KICKOFF_TIMEOUT = int(os.getenv("CREW_KICKOFF_TIMEOUT", "300"))


# ---------------------------------------------------------------------------
# Guardrail: validates plan structure from output_pydantic
# ---------------------------------------------------------------------------

def _plan_guardrail(result) -> tuple[bool, Any]:
    """Ensures validation task returns a valid UserStoryExecutionPlan."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, UserStoryExecutionPlan):
        if pydantic_obj.tasks and len(pydantic_obj.tasks) >= 1:
            return (True, result)
        return (False, "Plan must include at least one implementation task (tasks list is empty)")
    return (
        False,
        "Output must be a valid UserStoryExecutionPlan JSON with fields: "
        "user_story_id, user_story_title, approach_summary, tasks, quality_score, "
        "consensus_reached, final_validation_notes. Return ONLY the JSON.",
    )


# ---------------------------------------------------------------------------
# Async crew execution with timeout
# ---------------------------------------------------------------------------

def _run_crew_with_timeout(crew: Crew, timeout: int):
    async def _run():
        return await asyncio.wait_for(crew.akickoff(), timeout=timeout)
    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_latest_prd() -> Path:
    jsons = list(Path(OUTPUT_DIR).glob("PRD_*.json"))
    if not jsons:
        raise FileNotFoundError(f"Nenhum PRD em {OUTPUT_DIR}/")
    return max(jsons, key=lambda p: p.stat().st_mtime)


def _load_prd(path: str) -> tuple[PRDSchema, dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    prd = PRDSchema.model_validate(data)
    return prd, data


def _normalize_us_ref(s: str) -> str:
    s = s.strip().upper()
    if s.isdigit():
        return s
    if s.startswith("US") and len(s) > 2 and s[2:].isdigit():
        return "US" + str(int(s[2:]))
    return s


def _get_user_story(prd: PRDSchema, ref: str | None):
    if ref is None:
        return prd.user_stories[0]
    ref_norm = _normalize_us_ref(ref)
    for us in prd.user_stories:
        if ref_norm == _normalize_us_ref(us.id):
            return us
    try:
        idx = int(ref)
        return prd.user_stories[idx]
    except (ValueError, IndexError):
        raise ValueError(f"User story não encontrada: {ref}. Disponíveis: {[u.id for u in prd.user_stories]}")


# ---------------------------------------------------------------------------
# Main planning function
# ---------------------------------------------------------------------------

def run_user_story_planning(
    prd_path: str | None,
    user_story_ref: str | None,
    vision_content: str,
) -> dict:
    """
    Executa ciclo dialético para gerar plano de implementação de uma user story.

    Uses native CrewAI features:
    - output_pydantic for structured plan output
    - Task guardrails for output validation
    - akickoff() + asyncio.wait_for() for timeout
    """
    if prd_path is None:
        prd_path = str(_find_latest_prd())
    prd, _ = _load_prd(prd_path)
    us = _get_user_story(prd, user_story_ref)

    us_context = f"""
User Story: {us.id} — {us.title}
Descrição: {us.description}
Critérios de aceite: {chr(10).join('- ' + ac for ac in us.acceptance_criteria)}
Esforço: {us.effort}
Dependências: {', '.join(us.dependencies) or 'Nenhuma'}
"""
    feature_context = f"Feature (PRD): {prd.feature_name}. Objetivo: {prd.objective}"

    task_tese = Task(
        description=f"""
VISÃO MACRO (VISION.md):
{vision_content}

CONTEXTO DA FEATURE:
{feature_context}

USER STORY A IMPLEMENTAR:
{us_context}

Gere a TESE: um plano de implementação inicial para esta user story.
Inclua:
1. Abordagem técnica resumida (approach_summary)
2. Lista de tasks de implementação (id, title, description, order, dependencies)
3. Riscos que você já considera
4. Notas técnicas relevantes

Seja concreto e alinhado com a visão macro. Não invente módulos fora do escopo do PRD.
""",
        expected_output="Plano de implementação estruturado (abordagem + tasks + riscos + notas)",
        agent=visionario,
    )

    task_antitese = Task(
        description=f"""
VISÃO MACRO:
{vision_content}

A proposta de implementação (tese) para a user story foi:
[output do Visionário]

Aplique o método socrático. Liste TODAS:
1. Falhas e pontos fracos do plano
2. Contradições com VISION.md ou com o PRD da feature
3. Riscos de dívida técnica ou overscope
4. Tasks faltando ou mal ordenadas
5. Critérios de aceite não cobertos pelo plano

Seja implacável. Cada crítica deve ser específica e acionável.
""",
        expected_output="Crítica detalhada do plano de implementação",
        agent=critico_socratico,
        context=[task_tese],
    )

    task_sintese = Task(
        description=f"""
VISÃO MACRO:
{vision_content}

USER STORY: {us.id} — {us.title}

Você recebeu:
- A tese: plano de implementação do Visionário
- A antítese: críticas do Crítico Socrático

Produza a SÍNTESE: plano de implementação refinado que:
1. Preserva o que havia de bom na tese
2. Incorpora TODAS as críticas da antítese
3. Lista tasks claras (id, title, description, order, dependencies)
4. Inclui approach_summary, risks_mitigated, tech_notes
5. Está alinhado com VISION.md e com o PRD

Formato que o Validador espera: abordagem resumida, lista de tasks numeradas, riscos mitigados, notas técnicas.
""",
        expected_output="Plano de implementação refinado (abordagem + tasks + riscos mitigados + notas)",
        agent=sintetizador,
        context=[task_tese, task_antitese],
    )

    task_validacao = Task(
        description=f"""
Com base na SÍNTESE do plano de implementação para a user story {us.id} — {us.title},
produza o documento final.

Preencha:
- user_story_id: "{us.id}"
- user_story_title: "{us.title}"
- approach_summary: resumo da abordagem (da síntese)
- tasks: lista de ImplementationTask (id, title, description, order, dependencies)
- risks_mitigated: lista de riscos que foram mitigados
- tech_notes: notas técnicas
- quality_score: float 0-10 (uma casa decimal). Aprove se >= 9.0
- consensus_reached: true se o plano está pronto para execução
- final_validation_notes: explicação breve
""",
        expected_output="UserStoryExecutionPlan válido com quality_score e consensus_reached",
        agent=validador_macro,
        output_pydantic=UserStoryExecutionPlan,
        guardrail=_plan_guardrail,
        guardrail_max_retries=2,
        context=[task_tese, task_antitese, task_sintese],
    )

    crew = Crew(
        agents=[visionario, critico_socratico, sintetizador, validador_macro],
        tasks=[task_tese, task_antitese, task_sintese, task_validacao],
        process="sequential",
        verbose=True,
    )

    print(f"\n{'='*60}")
    print(f"Planejamento dialético — {us.id} {us.title}")
    print(f"{'='*60}\n")

    result = _run_crew_with_timeout(crew, CREW_KICKOFF_TIMEOUT)

    # Extract plan via output_pydantic (native CrewAI structured output)
    plan_valid: UserStoryExecutionPlan | None = None
    pydantic_result = getattr(result, "pydantic", None)
    if isinstance(pydantic_result, UserStoryExecutionPlan):
        plan_valid = pydantic_result
    else:
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_pydantic = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_pydantic, UserStoryExecutionPlan):
                plan_valid = last_pydantic

    # Fallback: if output_pydantic failed, try parsing raw text
    if plan_valid is None:
        raw_text = getattr(result, "raw", None) or str(result)
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_raw = getattr(tasks_out[-1], "raw", None)
            if last_raw and isinstance(last_raw, str) and last_raw.strip():
                raw_text = last_raw
        try:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
            json_str = match.group(1).strip() if match else raw_text
            plan_dict = json.loads(json_str)
            plan_dict.setdefault("user_story_id", us.id)
            plan_dict.setdefault("user_story_title", us.title)
            plan_valid = UserStoryExecutionPlan.model_validate(plan_dict)
        except Exception:
            from schemas import ImplementationTask
            plan_valid = UserStoryExecutionPlan(
                user_story_id=us.id,
                user_story_title=us.title,
                approach_summary="Falha ao extrair plano estruturado do output.",
                tasks=[ImplementationTask(id="T-001", title="Placeholder", description="N/A", order=1)],
                quality_score=0.0,
                consensus_reached=False,
                final_validation_notes="output_pydantic e parsing manual falharam",
            )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = f"{OUTPUT_DIR}/exec_{us.id}_{timestamp}"
    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump(plan_valid.model_dump(), f, indent=2, ensure_ascii=False)
    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(execution_plan_to_markdown(plan_valid))
    print(f"\nPlano salvo: {base}.json e {base}.md")
    return {
        "plan": plan_valid.model_dump(),
        "quality_score": plan_valid.quality_score,
        "plan_path_json": f"{base}.json",
        "plan_path_md": f"{base}.md",
    }
