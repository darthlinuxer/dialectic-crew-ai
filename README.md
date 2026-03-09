# Dialectic Crew AI

> Sistema de geração automática de PRD usando dialética socrática/hegeliana com CrewAI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.10+-purple.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## O que é?

O **Dialectic Crew AI** gera PRDs (Product Requirement Documents) de alta qualidade usando um processo dialético:

```
TESE → ANTÍTESE → SÍNTESE → VALIDAÇÃO → (RETRY ATÉ 9.0)
```

- **Tese (Visionário)**: Propõe solução inicial
- **Antítese (Crítico)**: Destrói a proposta com críticas
- **Síntese (Sintetizador)**: Funde as ideias na melhor versão
- **Validação (Gate)**: Aprova se score >= 9.0

## Features

- 4 agentes IA trabalhando em harmonia (modelos OpenAI por tier)
- Retry automático até atingir nota 9.0
- Validação Pydantic com `output_pydantic` nativo do CrewAI
- Task Guardrails para validação automática de output
- Timeout nativo com `akickoff()` + `asyncio.wait_for()`
- Anti-drift: todos os agentes leem VISION.md
- Task tracking: status, verificação com LLM, acceptance criteria
- Dual export: JSON + Markdown com YAML frontmatter

## Instalação

```bash
# Clone e instale
git clone <repo-url>
cd dialectic-crew-ai
uv sync

# Configure API key
cp .env.example .env
# Edite .env e adicione OPENAI_API_KEY=sk-...
```

## Uso (CLI)

### Gerar PRD

```bash
python main.py prd "Login com 2FA"
```

### Planejar execução de user story

```bash
# Último PRD, primeira user story
python main.py plan

# PRD e user story específicos
python main.py plan prd_output/PRD_20260308_1640.json US1
```

### Executar plano com dialética

```bash
# Usa o plano mais recente
python main.py execute

# Plano específico
python main.py execute prd_output/exec_US1_20260308_1750.json

# Apenas gerar spec Markdown (sem LLM)
python main.py execute --spec-only
```

### Verificar status das tasks

```bash
# Status de todas as tasks do plano mais recente
python main.py status

# Plano específico
python main.py status prd_output/exec_US1_20260308_1750.json
```

### Marcar task manualmente

```bash
# Marcar como concluída
python main.py mark T0 completed

# Marcar como falhada (com plano específico)
python main.py mark T3 failed prd_output/exec_US1_20260308_1750.json
```

### Verificar task com agente LLM

```bash
# Verifica se a task foi implementada corretamente
python main.py verify T0

# Com PRD para verificar acceptance criteria
python main.py verify T2 --prd prd_output/PRD_20260308_1640.json
```

### CLI alternativa (override de output format)

```bash
python -m main.cli "Login com 2FA" --output-format both
```

## Configuração (.env)

| Variável | Descrição | Default |
|----------|-----------|---------|
| `OPENAI_API_KEY` | API key da OpenAI | (obrigatório) |
| `LLM_MODEL_SIMPLE` | Modelo para tasks leves (validação) | `gpt-4o-mini` |
| `LLM_MODEL_COMPLEX` | Modelo para tasks complexas (implementação, crítica) | `gpt-4o` |
| `LLM_MODEL_REASONING` | Modelo para arquitetura e decisões macro | `o3-mini` |
| `LLM_REQUEST_TIMEOUT` | Timeout por request LLM (segundos) | `900` |
| `PRD_OUTPUT_FORMAT` | Formato de export do PRD: `json`, `md`, `both` | `json` |
| `PRD_OUTPUT_DIR` | Diretório de saída do PRD | `prd_output` |
| `MAX_RETRIES_PER_TASK` | Retries por task no ciclo dialético | `3` |
| `MIN_QUALITY_SCORE` | Score mínimo para aprovar task (0-10) | `7.5` |
| `CREW_KICKOFF_TIMEOUT` | Timeout total para crew.akickoff() (segundos) | `300` |

## Formato do Markdown exportado

O Markdown gerado inclui YAML frontmatter com metadados de auditoria:

```yaml
---
quality_score: 9.2
validation_status: approved
generated_at: 2026-03-08T20:00:00Z
vision_hash: a1b2c3d4...  # SHA-256 de VISION.md
---
```

Seções do corpo:
- `# Objetivo`
- `## Macro Impact`
- `## User Stories` (com acceptance criteria e effort)
- `## Anti-Drift Questions`

## Estrutura do projeto

```
dialectic-crew-ai/
├── main.py                  # CLI principal (prd, plan, execute, status, mark, verify)
├── schemas.py               # Modelos Pydantic (PRD, tasks, execução)
├── VISION.md                # Visão macro do sistema
├── dialectic/               # Core dialético
│   ├── agents.py            # Agentes CrewAI (tiers de modelo)
│   ├── prd_flow.py          # Flow principal (tese→antítese→síntese→validação)
│   ├── state.py             # Estado do flow
│   ├── export.py            # Exportador dual (JSON+MD) com atomicidade
│   ├── config.py            # Configuração de exportação
│   └── tools.py             # Ferramentas CrewAI (FileRead, FileWrite)
├── planning/                # Planejamento de user stories
│   └── flow.py              # Ciclo dialético para planos de execução
├── execution/               # Execução de planos
│   ├── dialectic_execution.py  # Execução com ciclo dialético por task
│   ├── runner.py            # Geração de spec Markdown
│   └── verify.py            # Task tracking e verificação
├── tests/                   # Testes unitários
└── prd_output/              # PRDs e planos gerados
```

## Testes

```bash
# Rodar todos os testes unitários
uv run python -m pytest tests/ -v --ignore=tests/test_llm_tooling.py

# Rodar teste de tool calling (requer API key)
uv run python tests/test_llm_tooling.py
```
