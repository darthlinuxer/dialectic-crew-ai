"""
Ponto de entrada principal do Dialectic Crew AI.

Comandos:
  python main.py prd "sua feature request"   — gera PRD com dialética
  python main.py plan [prd.json] [US-001]   — planeja execução de uma user story
  python main.py execute [plan.json|--latest] — gera artefato de execução do plano
  python main.py "sua feature request"       — compatível: equivale a prd
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Imports após dotenv
from dialectic import DialecticFlow, run_dialectic_flow
from dialectic.state import DialecticState
from dialectic.prd_flow import OUTPUT_DIR
from planning.flow import run_user_story_planning
from execution.runner import run_execution
from execution.dialectic_execution import run_dialectic_execution
from execution.verify import show_status, mark_task, verify_task


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     DIALECTIC CREW AI - PRD & Planning v1.1                   ║
║                                                              ║
║     Dialética: Tese → Antítese → Síntese → Validação         ║
║     Comandos: prd | plan | execute | status | verify | help   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Uso:
  python main.py <comando> [argumentos...]
  dialectic-crew <comando> [argumentos...]

Comandos:

  prd "sua feature request"
      Gera um PRD (Product Requirement Document) usando o método dialético
      (tese → antítese → síntese → validação). Requer VISION.md no diretório atual.
      Salva em prd_output/ (JSON + Markdown).
      Ex.: python main.py prd "Login com 2FA"

  plan [prd.json] [US-001|índice]
      Planeja a execução de uma user story com dialética. Gera um plano
      (UserStoryExecutionPlan) com tasks e score. Por padrão usa o último
      PRD em prd_output/ e a primeira user story.
      Salva em prd_output/ (exec_<US>_<timestamp>.json e .md).
      Ex.: python main.py plan
           python main.py plan prd_output/PRD_20260308_1640.json US1

  execute [plan.json|--latest] [--spec-only]
      Executa o plano com CrewAI e dialética por task. Cada task passa por
      Tese → Antítese → Síntese → Validação; retry até score >= 9.0.
      Use --spec-only para apenas gerar spec em Markdown (comportamento legado).
      Por padrão usa o plano mais recente em prd_output/ (exec_*.json).
      Salva em exec_output/<run_id>/ (report.json, outputs).
      Ex.: python main.py execute
           python main.py execute prd_output/exec_US1_20260308_1200.json
           python main.py execute --spec-only

  status [plan.json|--latest]
      Mostra o status de todas as tasks do plano (pending, in_progress,
      completed, failed). Por padrão usa o plano mais recente.
      Ex.: python main.py status
           python main.py status prd_output/exec_US1_20260308_1750.json

  mark <task_id> <status> [plan.json]
      Marca manualmente o status de uma task.
      Status válidos: pending, in_progress, completed, failed
      Ex.: python main.py mark T0 completed
           python main.py mark T3 failed prd_output/exec_US1_20260308_1750.json

  verify <task_id> [plan.json] [--prd prd.json]
      Verifica se uma task foi implementada corretamente usando um agente LLM.
      O agente lê os arquivos do projeto e valida contra a descrição da task
      e os acceptance criteria da user story (se --prd fornecido).
      Atualiza automaticamente o status da task no plano.
      Ex.: python main.py verify T0
           python main.py verify T2 --prd prd_output/PRD_20260308_1640.json

  help, -h, --help
      Mostra esta mensagem.

Compatibilidade:
  python main.py "sua feature"
      Equivale a: python main.py prd "sua feature"

Requisitos:
  - VISION.md no diretório atual (para prd e plan)
  - API key no .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, MINIMAX_API_KEY ou GROQ_API_KEY)
"""


def _check_api_key():
    has = bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("MINIMAX_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )
    if not has:
        print("⚠️  Configure sua API key primeiro!")
        print("   Copie .env.example para .env e adicione a key\n")
    return has


def _read_vision():
    if not os.path.exists("VISION.md"):
        print("⚠️  VISION.md não encontrado!")
        sys.exit(1)
    with open("VISION.md", "r", encoding="utf-8") as f:
        return f.read()


def cmd_prd(feature_request: str):
    """Gera PRD a partir da feature com dialética."""
    vision = _read_vision()
    flow = DialecticFlow()
    flow.state.feature_objective = feature_request
    flow.state.vision_content = vision
    flow.kickoff()
    state = flow.state
    print("\n" + "=" * 60)
    print("🎉 PROCESSO DIALÉTICO CONCLUÍDO!")
    print("=" * 60)
    print(f"📈 Quality Score: {state.quality_score}/10.0")
    print(f"🔄 Total rodadas: {state.retry_count + 1}")
    print(f"✅ Consensus: {state.consensus_reached}")
    print("=" * 60)


def cmd_plan(prd_path: str | None, us_ref: str | None):
    """Planeja execução de uma user story (dialética)."""
    vision = _read_vision()
    if prd_path and not os.path.exists(prd_path):
        print(f"⚠️ PRD não encontrado: {prd_path}")
        sys.exit(1)
    result = run_user_story_planning(prd_path, us_ref, vision)
    print(f"📈 Score: {result['quality_score']}/10.0")


def cmd_execute(plan_path: str | None, spec_only: bool = False):
    """Executa o plano (real ou spec-only)."""
    try:
        if spec_only:
            result = run_execution(plan_path=plan_path or "--latest")
            print(f"\n✅ Spec gerado: {result['output_path']}")
            print(f"   Plano: {result['plan_id']} — {result['plan_title']}")
        else:
            vision = _read_vision()
            result = run_dialectic_execution(
                plan_path=plan_path or "--latest",
                vision_content=vision,
            )
            status = "todas as tasks concluídas" if result["overall_success"] else "algumas tasks falharam"
            print(f"\n✅ Execução concluída: {result['output_path']}")
            print(f"   Plano: {result['plan_id']} — {result['plan_title']}")
            print(f"   Status: {status}")
            print(f"   Relatório: {result['report_path']}")
    except FileNotFoundError as e:
        print(f"⚠️ {e}")
        sys.exit(1)


def cmd_status(plan_path: str | None):
    """Mostra status das tasks do plano."""
    try:
        show_status(plan_path)
    except FileNotFoundError as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_mark(task_id: str, status: str, plan_path: str | None):
    """Marca status de uma task manualmente."""
    valid = ("pending", "in_progress", "completed", "failed")
    if status not in valid:
        print(f"  Status inválido: '{status}'. Use: {', '.join(valid)}")
        sys.exit(1)
    try:
        mark_task(task_id, status, plan_path)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_verify(task_id: str, plan_path: str | None, prd_path: str | None):
    """Verifica task com agente LLM."""
    try:
        result = verify_task(task_id, plan_path, prd_path)
        if result["verified"]:
            print(f"\n  Task {task_id} verificada com sucesso!")
        else:
            print(f"\n  Task {task_id} NÃO passou na verificação.")
    except (FileNotFoundError, ValueError) as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_help():
    """Mostra ajuda dos comandos CLI."""
    print(HELP_TEXT.strip())


def main():
    args = sys.argv[1:]
    if not args:
        print(BANNER)
        print("Uso: python main.py <comando> [argumentos...]")
        print("      python main.py help   para ver todos os comandos.\n")
        sys.exit(1)

    sub = args[0].lower()
    if sub in ("help", "-h", "--help"):
        print(BANNER)
        cmd_help()
        sys.exit(0)

    print(BANNER)
    _check_api_key()

    if sub == "prd":
        if len(args) < 2:
            print("📝 Informe a feature: python main.py prd 'sua feature aqui'")
            sys.exit(1)
        cmd_prd(" ".join(args[1:]))
        return
    if sub == "plan":
        prd_path = args[1] if len(args) > 1 else None
        us_ref = args[2] if len(args) > 2 else None
        cmd_plan(prd_path, us_ref)
        return
    if sub == "execute":
        remaining = [a for a in args[1:] if not a.startswith("-")]
        spec_only = "--spec-only" in args
        plan_path = remaining[0] if remaining else "--latest"
        cmd_execute(plan_path, spec_only=spec_only)
        return
    if sub == "status":
        plan_path = args[1] if len(args) > 1 else None
        cmd_status(plan_path)
        return
    if sub == "mark":
        if len(args) < 3:
            print("Uso: python main.py mark <task_id> <status> [plan.json]")
            print("  Status válidos: pending, in_progress, completed, failed")
            sys.exit(1)
        task_id = args[1]
        status = args[2]
        plan_path = args[3] if len(args) > 3 else None
        cmd_mark(task_id, status, plan_path)
        return
    if sub == "verify":
        if len(args) < 2:
            print("Uso: python main.py verify <task_id> [plan.json] [--prd prd.json]")
            sys.exit(1)
        task_id = args[1]
        remaining = [a for a in args[2:] if not a.startswith("-")]
        plan_path = remaining[0] if remaining else None
        prd_path = None
        if "--prd" in args:
            prd_idx = args.index("--prd")
            if prd_idx + 1 < len(args):
                prd_path = args[prd_idx + 1]
        cmd_verify(task_id, plan_path, prd_path)
        return

    # Compatibilidade: um único argumento sem subcomando = prd
    if len(args) == 1 and not args[0].startswith("-"):
        cmd_prd(args[0])
        return

    print("Comando desconhecido. Use: prd | plan | execute | help")
    sys.exit(1)


if __name__ == "__main__":
    main()
