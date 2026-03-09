"""
Testes de validação do fluxo (sem chamadas LLM).
Valida: carregar PRD, export MD, plano de execução, get user story.
"""

import json
import sys
from pathlib import Path

# raiz do projeto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas import PRDSchema, UserStoryExecutionPlan, ImplementationTask
from dialectic.export import prd_to_markdown, execution_plan_to_markdown


def test_load_prd_and_export_md():
    """Carrega PRD fixture e gera Markdown."""
    path = Path(__file__).parent.parent / "prd_output" / "PRD_test_fixture.json"
    if not path.exists():
        print("⚠️ Fixture não encontrado:", path)
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    prd = PRDSchema.model_validate(data)
    md = prd_to_markdown(prd)
    assert "PRD — Login com 2FA" in md
    assert "US-001" in md and "US-002" in md
    assert "Configurar 2FA" in md
    print("✅ PRD load + prd_to_markdown OK")
    return True


def test_execution_plan_export_md():
    """Gera Markdown a partir de UserStoryExecutionPlan."""
    plan = UserStoryExecutionPlan(
        user_story_id="US-001",
        user_story_title="Configurar 2FA",
        approach_summary="Implementar fluxo de configuração com TOTP e QR code.",
        tasks=[
            ImplementationTask(id="T-001", title="Backend: endpoint 2FA", description="Criar API para ativar 2FA", order=1, dependencies=[]),
            ImplementationTask(id="T-002", title="Frontend: tela configuração", description="Tela com QR e backup", order=2, dependencies=["T-001"]),
        ],
        risks_mitigated=["Armazenamento seguro do secret"],
        tech_notes="Usar pyotp no backend.",
        quality_score=9.0,
        consensus_reached=True,
        final_validation_notes="Plano aprovado.",
    )
    md = execution_plan_to_markdown(plan)
    assert "US-001" in md and "Configurar 2FA" in md
    assert "T-001" in md and "T-002" in md
    assert "approach_summary" not in md  # é "Abordagem" em PT
    print("✅ execution_plan_to_markdown OK")
    return True


def test_get_user_story():
    """Resolve user story por id e por índice (lógica espelhada de run_user_story_dialectic)."""
    path = Path(__file__).parent.parent / "prd_output" / "PRD_test_fixture.json"
    if not path.exists():
        print("⚠️ Fixture não encontrado")
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    prd = PRDSchema.model_validate(data)

    def get_us(prd: PRDSchema, ref: str | None):
        if ref is None:
            return prd.user_stories[0]
        for us in prd.user_stories:
            if us.id.upper() == ref.upper():
                return us
        idx = int(ref)
        return prd.user_stories[idx]

    us1 = get_us(prd, None)
    assert us1.id == "US-001"
    us2 = get_us(prd, "US-002")
    assert us2.id == "US-002"
    us0 = get_us(prd, "0")
    assert us0.id == "US-001"
    print("✅ _get_user_story (None, US-002, 0) OK")
    return True


if __name__ == "__main__":
    ok = True
    ok &= test_load_prd_and_export_md()
    ok &= test_execution_plan_export_md()
    ok &= test_get_user_story()
    sys.exit(0 if ok else 1)
