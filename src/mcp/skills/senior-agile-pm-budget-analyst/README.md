# Senior Agile PM & Budget Analyst Skill

## Visão Geral

Esta skill foi desenvolvida para auxiliar gerentes de projeto seniores especializados em **metodologia Agile/Scrum** com foco em **análise de orçamento**. A skill permite criar, atualizar e revisar artefatos Agile/Scrum seguindo as melhores práticas, incluindo:

- **Iniciativas** estratégicas do projeto
- **Épicos** (conjuntos de user stories relacionadas)
- **User Stories (cards)** com formato BDD (Given-When-Then)
- **Estimativas** usando Poker Planning (escala Fibonacci)
- **Orçamento detalhado** baseado em story points e custos de recursos
- **Gráficos de Gantt** com dependências e milestones
- **Análise de Caminho Crítico** (Critical Path Method)

## Características Principais

### 1. Metodologia Scrum Completa
- **3 Cs**: Card, Conversation, Confirmation
- **Formato de User Story**: "Como [usuário], eu quero [funcionalidade] para que [benefício]"
- **BDD (Behavior-Driven Development)**: Critérios de aceitação no formato Given-When-Then
- **Definition of Done**: Checklists específicas para cada story

### 2. Poker Planning Configurável
- Relação pontos-sprint configurável (padrão: 5 pontos = 2 semanas)
- Escala Fibonacci (1, 2, 3, 5, 8, 13, 21...)
- Quebra automática de stories > threshold
- Rastreabilidade de estimativas

### 3. Análise de Orçamento Detalhada
- Cálculo baseado em story points e composição da equipe
- Taxas horárias/diárias por função
- Overhead (15-30% típico)
- Custos fixos (licenças, infraestrutura)
- Contingência (10-20% típico)
- Rastreabilidade completa: projeto → iniciativas → épicos → user stories

### 4. Planejamento e Cronograma
- Gráficos de Gantt com dependências
- Análise de Caminho Crítico (CPM)
- Identificação de bottlenecks
- Suporte a scripts Python para visualizações

## Estrutura de Arquivos

```
senior-agile-pm-budget-analyst/
├── SKILL.md                    # Metadata e overview da skill
├── PROMPT.md                   # Prompt otimizado carregado na invocação
├── README.md                   # Este arquivo
├── reference/                  # Arquivos de referência
│   ├── artifact-index.md       # Mapeamento de artefatos
│   ├── workflows.md            # Workflows (analyze, create, update, review)
│   └── quality-checks.md       # Padrões de qualidade e checklists
└── assets/
    └── AGILE_DOCS_PT_BR/       # Artefatos em Português (PT-BR)
        ├── 01_INICIATIVAS/          # ✅ Completo (template + inputs)
        ├── 02_EPICOS/               # ✅ Completo (template + inputs)
        ├── 03_USER_STORIES/         # ✅ Completo (template + inputs + docs)
        ├── 04_POKER_PLANNING/       # ✅ Completo (template + inputs)
        ├── 05_BACKLOG_PRIORIZADO/   # ✅ Completo (template + inputs)
        ├── 06_SPRINT_PLANNING/      # ✅ Completo (template + inputs)
        ├── 07_ORCAMENTO_PROJETO/    # ✅ Completo (template + inputs + docs)
        ├── 08_GANTT_CHART/          # ✅ Completo (template + inputs)
        ├── 09_CAMINHO_CRITICO/      # ✅ Completo (template + inputs)
        ├── 10_ANALISE_PROJETO/      # ✅ Completo (template + inputs)
        ├── 11_VELOCITY_BURNDOWN/    # ✅ Completo (template + inputs)
        └── 12_RETROSPECTIVA/        # ✅ Completo (template + inputs)
```

## Como Usar

### Invocar a Skill

No Claude Code, use:
```
/senior-agile-pm-budget-analyst
```

Ou mencione explicitamente quando solicitar:
- Análise de projeto usando Agile/Scrum
- Criação de user stories com BDD
- Estimativas com poker planning
- Cálculo de orçamento baseado em story points
- Geração de Gantt ou análise de caminho crítico

### Comandos Disponíveis

1. **analyze**: Analisa projeto completo e cria breakdown (iniciativas → épicos → user stories)
2. **create**: Cria um novo artefato usando template
3. **update**: Atualiza artefato existente
4. **review**: Revisa artefato contra padrões Scrum/BDD

### Exemplo de Uso

```
Analise este projeto de e-commerce e crie:
- Iniciativas estratégicas
- Épicos por iniciativa
- User stories detalhadas com BDD
- Estimativas usando poker planning (5 pontos = 2 semanas)
- Orçamento completo (equipe: 3 devs, 1 QA, 1 designer)
- Gráfico de Gantt
- Análise de caminho crítico
```

## Configuração Inicial

Ao usar a skill, você será questionado sobre:

1. **Poker Planning**:
   - Relação pontos-sprint (ex: 5 pontos = 2 semanas)
   - Threshold para breakdown (ex: stories > 5 pontos)

2. **Equipe e Custos** (para orçamento):
   - Composição da equipe (funções e quantidades)
   - Taxas horárias/diárias por função
   - Percentual de overhead (padrão: 20%)
   - Percentual de contingência (padrão: 15%)

3. **Projeto**:
   - Nome e objetivos
   - Duração esperada
   - Restrições e premissas

## Artefatos Disponíveis

### ✅ Todos os 12 Artefatos Completos!

1. ✅ **Iniciativas** (01_INICIATIVAS) - Template + Inputs
2. ✅ **Épicos** (02_EPICOS) - Template + Inputs
3. ✅ **User Stories** (03_USER_STORIES) - Template + Inputs + Documentação completa
4. ✅ **Poker Planning** (04_POKER_PLANNING) - Template + Inputs
5. ✅ **Backlog Priorizado** (05_BACKLOG_PRIORIZADO) - Template + Inputs
6. ✅ **Sprint Planning** (06_SPRINT_PLANNING) - Template + Inputs
7. ✅ **Orçamento do Projeto** (07_ORCAMENTO_PROJETO) - Template + Inputs + Documentação completa
8. ✅ **Gantt Chart** (08_GANTT_CHART) - Template + Inputs
9. ✅ **Caminho Crítico** (09_CAMINHO_CRITICO) - Template + Inputs (CPM)
10. ✅ **Análise Completa** (10_ANALISE_PROJETO) - Template + Inputs
11. ✅ **Velocity & Burndown** (11_VELOCITY_BURNDOWN) - Template + Inputs
12. ✅ **Retrospectiva** (12_RETROSPECTIVA) - Template + Inputs

## Metodologia BDD (Given-When-Then)

Todos os critérios de aceitação seguem o formato:

```
**Critério: [Título]**
- **Given** (Dado): [Contexto inicial ou pré-condição]
- **When** (Quando): [Ação ou evento que ocorre]
- **Then** (Então):
  - [Resultado esperado 1]
  - [Resultado esperado 2]
  - [Resultado esperado 3]
```

Este formato garante:
- ✅ Clareza e entendimento compartilhado
- ✅ Testabilidade objetiva
- ✅ Facilita automação de testes (Cucumber, JBehave)
- ✅ Validação pelo Product Owner

## Scripts Python

Quando necessário, a skill pode gerar scripts Python para:
- Visualização de Gráficos de Gantt (matplotlib)
- Cálculo de Caminho Crítico (networkx)
- Análise de dados (pandas)
- Dashboards de orçamento e velocity

## Quality Checks

Todos os artefatos passam por verificações de qualidade:

✅ User stories no formato "Como/Quero/Para que"
✅ Critérios BDD com Given-When-Then
✅ Story points usando Fibonacci
✅ Stories > threshold quebradas
✅ Definition of Done específica
✅ Rastreabilidade completa
✅ Cálculos de orçamento validados
✅ Dependencies mapeadas

## Status da Implementação

🎉 **100% Completa!** Todos os 12 artefatos Agile/Scrum foram implementados com templates e inputs.

- 12/12 TEMPLATE.md criados ✅
- 12/12 INPUTS.md criados ✅
- Documentação detalhada para artefatos principais ✅
- Artifact index completo ✅
- Workflows documentados ✅
- Quality checks definidos ✅

## Referências

- **Scrum Guide**: scrum.org
- **User Stories Applied**: Mike Cohn
- **Agile Estimating and Planning**: Mike Cohn
- **BDD Best Practices**: cucumber.io
- **Critical Path Method**: Project Management Institute (PMI)

## Suporte

Para dúvidas ou melhorias, consulte:
- [SKILL.md](SKILL.md) - Overview completo
- [PROMPT.md](PROMPT.md) - Prompt detalhado
- [reference/workflows.md](reference/workflows.md) - Workflows detalhados
- [reference/quality-checks.md](reference/quality-checks.md) - Padrões de qualidade

---

**Criado em**: 2026-02-05
**Versão**: 1.0
**Baseado em**: senior-pmbok-pm skill structure
