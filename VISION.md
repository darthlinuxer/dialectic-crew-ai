# VISION.md — Visão Macro do Sistema

## Sobre o Projeto

**Dialectic Crew AI** é o próprio produto: uma aplicação que usa **método dialético** (tese → antítese → síntese → validação) para gerar PRDs (Product Requirement Documents) de alta qualidade. O sistema se auto-orienta por esta visão para evitar drift e para evoluir em direção à sua vocação.

**Intenção:** Ser a melhor ferramenta de método dialético capaz de gerar PRDs em **Markdown** e **JSON**, com qualidade validada (score ≥ 9.0) e alinhamento explícito a uma visão macro (VISION.md).

**Vocação:**  
- **Núcleo:** Gerar PRDs estruturados (objetivo, macro_impact, user_stories, anti_drift_questions) em **dois formatos** — `.md` (legível, versionável, colaborativo) e `.json` (máquina, integrações, APIs).  
- **Método:** Garantir que toda proposta passe por contradição (antítese) e síntese antes da aprovação, reduzindo viés e overscope.  
- **Evolução:** Expandir o mesmo método dialético para outros artefatos e fases do ciclo de vida (ver “Possibilidades de Uso” abaixo).

---

## Objetivos de Negócio

1. **PRDs em Markdown e JSON** — Todo PRD aprovado deve ser persistido em `prd_output/` tanto como `.md` (documento narrativo, pronto para humanos) quanto como `.json` (schema validado, pronto para ferramentas).
2. **Qualidade por dialética** — Manter o loop Tese → Antítese → Síntese → Validação com retry até score ≥ 9.0 e zero contradições com VISION.md.
3. **Anti-drift** — Todos os agentes leem VISION.md; perguntas anti-drift e validação garantem alinhamento contínuo com a visão macro.
4. **Auto-aprimoramento** — O projeto usa esta VISION para se guiar; mudanças de comportamento ou escopo devem ser coerentes com este documento.

---

## Escopo do Sistema

### Módulos / Componentes Principais

| Componente      | Descrição |
|-----------------|-----------|
| **dialectic**   | Núcleo dialético: agentes (Visionário, Crítico Socrático, Sintetizador, Validador), tools, estado, DialecticFlow (PRD com retry), export (PRD e plano em Markdown). |
| **planning**    | Planejamento da execução: por user story, produz UserStoryExecutionPlan (tese → antítese → síntese → validação). |
| **execution**   | Execução do plano aprovado: consome UserStoryExecutionPlan e gera artefatos (spec/esboço em Markdown; extensível para código ou integrações). |
| **schemas**     | Fonte de verdade para PRD e planos: PRDSchema, UserStory, MacroImpact, AntiDriftQuestion; UserStoryExecutionPlan, ImplementationTask. |
| **main / CLI**  | Comandos: `prd "feature"` (PRD com dialética), `plan [prd] [US]` (plano por user story), `execute [plano]` (artefato de execução). |

### Integrações (atuais / desejadas)

- **Entrada:** Argumentos de CLI, conteúdo de VISION.md, variáveis de ambiente (API keys).
- **Saída:** Arquivos em `prd_output/` (PRD e planos em **JSON + Markdown**); artefatos de execução em `exec_output/`.
- **LLM:** Suporte a múltiplos provedores (OpenAI, Anthropic, Groq, MiniMax, etc.) configurável em `dialectic/agents.py`.

---

## Stack Tecnológico

- **Runtime:** Python 3.10–3.13
- **Framework de agentes:** CrewAI (Flow API, Crew, Tasks, Agents)
- **Validação:** Pydantic (PRDSchema, UserStory, etc.)
- **Config:** pyproject.toml, uv (recomendado), .env para API keys

---

## Requisitos Não-Funcionais

- **Reprodutibilidade:** Lock de dependências (uv.lock) e schema estável para PRD.
- **Clareza:** PRD em Markdown para leitura humana; JSON para pipelines e automação.
- **Qualidade:** Nenhum PRD aprovado com score &lt; 9.0 sem que o fluxo tenha tentado retry até o limite configurado.
- **Manutenibilidade:** Código legível, responsabilidades bem separadas (flow, agents, schemas).

---

## Princípios de Design

1. **Dialética como núcleo** — Tese, antítese e síntese não são opcionais; o Validador é o gate único para aprovação.
2. **VISION.md como âncora** — Toda proposta é confrontada com a visão macro; anti-drift é obrigatório.
3. **Dual output (MD + JSON)** — Atender tanto leitores humanos quanto ferramentas e integrações.
4. **Extensível** — Arquitetura deve permitir novos fluxos (ex.: dialética para execução de user stories) sem quebrar o núcleo.

---

## Possibilidades de Uso (Roadmap Conceitual)

### Já no escopo

- Gerar PRD a partir de uma feature request, com output em **JSON** e **Markdown** em `prd_output/`.
- **Planejar** a execução de user stories no formato definido em `schemas.py`: cada user story segue o modelo **UserStory** (id, title, description, acceptance_criteria, effort, dependencies). O planejamento produz **UserStoryExecutionPlan** (user_story_id, approach_summary, tasks como **ImplementationTask** — id, title, description, order, dependencies —, risks_mitigated, tech_notes, quality_score, consensus_reached).
- **Executar** o plano aprovado: o módulo de execução consome o UserStoryExecutionPlan e gera artefatos (spec em Markdown com tasks ordenadas e critérios de aceite; extensível para esboços de código, specs ou integração com issues).

### Em evolução

- **Ciclo dialético por user story (planning)** — Já implementado: tese (plano inicial) → antítese (críticas) → síntese (plano refinado) → validação (UserStoryExecutionPlan aprovado). Formato alinhado a `schemas.py`.
- **Execução avançada** — A partir do plano aprovado: geração de esboços de código, integração opcional com GitHub Issues/Jira, ou atualização de backlog (mantendo o método dialético como gate).

- **Outras possibilidades**
  - Gerar ADRs (Architecture Decision Records) via mesmo fluxo dialético.
  - Refinar backlog (priorização e slicing) com tese/antítese/síntese.
  - Revisar PRDs existentes (re-tese, re-antítese, re-síntese a partir de um PRD antigo ou de feedback).

---

## Roadmap Sugerido

### Fase 1 (atual)

- [x] Fluxo dialético com 4 agentes e retry até 9.0
- [x] Output PRD em JSON e Markdown em `prd_output/`
- [x] Módulos **dialectic**, **planning**, **execution** e CLI (`prd` | `plan` | `execute`)

### Fase 2

- [ ] Opção de escolher apenas MD, apenas JSON ou ambos
- [ ] Templates de Markdown configuráveis para o PRD
- [ ] Documentação de “como estender” para novos formatos (ex.: YAML)

### Fase 3 (planejamento e execução de user stories)

- [x] **Planejamento** no formato UserStoryExecutionPlan: para cada user story, ciclo dialético (tese → antítese → síntese → validação) produz plano com tasks (ImplementationTask) e score; persistência em `prd_output/exec_*.json` e `.md`.
- [x] **Execução** a partir do plano: geração de artefato (spec em Markdown) em `exec_output/`; ponto de entrada para futura geração de código ou integração com ferramentas.
- [ ] Integração opcional com GitHub Issues, Jira, etc. para criar tasks a partir do plano aprovado
- [ ] Opção de gerar esboços de código por task (mantendo o método dialético como gate)

---

*Este documento deve ser lido por TODOS os agentes antes de propor qualquer solução. Ele define a vocação do produto e o rumo da evolução.*
