# Visão Geral - Análise de Caminho Crítico (CPM)

## O que é Critical Path Method (CPM)?

CPM é uma técnica de análise de rede de projeto que identifica a **sequência mais longa de atividades dependentes**, determinando a duração mínima do projeto. Desenvolvido em 1950s por DuPont e Remington Rand.

## Conceitos Fundamentais

### 1. Network Diagram
Representação visual de todas as tasks e suas dependências.

```
[Task A] → [Task B] → [Task D]
     ↓
  [Task C] ──────────→ [Task E]
```

### 2. Caminho (Path)
Sequência de tasks conectadas do início ao fim do projeto.

### 3. Caminho Crítico
O **caminho mais longo** em duração. Tasks neste caminho:
- Têm **slack zero** (folga zero)
- Qualquer atraso impacta o projeto inteiro
- Requerem gerenciamento rigoroso

### 4. Slack/Float
Tempo que uma task pode atrasar sem impactar o projeto.

```
Slack = Latest Start - Earliest Start
ou
Slack = Latest Finish - Earliest Finish
```

## Cálculos do CPM

### Forward Pass (Cálculo ES e EF)

**Earliest Start (ES)**: Momento mais cedo que task pode começar
**Earliest Finish (EF)**: ES + Duration

```
Regra: ES da task = MAX(EF de todos predecessores)
```

**Exemplo**:
```
Task A: Duration=3, ES=0, EF=3
Task B: Duration=2, Predecessor=A, ES=3, EF=5
Task C: Duration=4, Predecessor=A, ES=3, EF=7
Task D: Duration=1, Predecessors=B,C, ES=7, EF=8
```

### Backward Pass (Cálculo LS e LF)

**Latest Finish (LF)**: Momento mais tarde que task pode terminar sem atrasar projeto
**Latest Start (LS)**: LF - Duration

```
Regra: LF da task = MIN(LS de todos successors)
```

**Para última task**: LF = EF (fim do projeto)

### Calculando Slack

```
Slack = LS - ES = LF - EF

Se Slack = 0 → Task está no Caminho Crítico
Se Slack > 0 → Task tem folga
```

## Identificando o Caminho Crítico

### Algoritmo

1. **Forward Pass**: Calcular ES e EF de todas tasks
2. **Determinar duração do projeto**: EF da última task
3. **Backward Pass**: Calcular LS e LF de todas tasks
4. **Calcular Slack**: Para cada task
5. **Caminho Crítico**: Todas tasks com Slack = 0

### Exemplo Completo

| Task | Duration | Predecessor | ES | EF | LS | LF | Slack | Crítico? |
|------|----------|-------------|----|----|----|----|-------|----------|
| A | 3 | - | 0 | 3 | 0 | 3 | 0 | ✅ Sim |
| B | 2 | A | 3 | 5 | 5 | 7 | 2 | ❌ Não |
| C | 4 | A | 3 | 7 | 3 | 7 | 0 | ✅ Sim |
| D | 1 | B,C | 7 | 8 | 7 | 8 | 0 | ✅ Sim |

**Caminho Crítico**: A → C → D (Duração: 8 dias)
**Path alternativo**: A → B → D (Duração: 6 dias, slack de 2 dias)

## Por que CPM é Importante?

### Benefícios

1. **Prazo do Projeto**: Duração mínima realista
2. **Priorização**: Saber onde focar recursos
3. **Risk Management**: Tasks críticas = maior risco
4. **Otimização**: Onde comprimir cronograma
5. **Comunicação**: Visual para stakeholders

### Decisões Baseadas em CPM

- **Allocar recursos**: Priories tasks críticas
- **Fast-tracking**: Paralelizar tasks críticas (se possível)
- **Crashing**: Adicionar recursos para acelerar path crítico
- **Monitoramento**: Acompanhar tasks críticas de perto

## CPM em Projetos Agile

### Desafios
- Agile valoriza adaptação vs plano fixo
- Sprints adicionam complexidade
- Escopo pode mudar

### Aplicações Agile-Friendly

1. **Nível de Épico**: CPM para épicos, não stories
2. **Rolling Wave**: Recalcular CPM a cada sprint
3. **Dependências**: Identificar épicos bloqueadores
4. **Release Planning**: CPM para planejar releases

### Exemplo Agile

```
Sprint 1-2: Épico A (Login/Auth) ───────> [Crítico]
Sprint 3-4: Épico B (Dashboard) ─────────> [Crítico]
Sprint 3-5: Épico C (Reports) ──────> [2 sprints slack]
Sprint 5-6: Épico D (Integration) ────────> [Crítico]
```

**Caminho Crítico**: A → B → D (6 sprints)
**Épico C**: Pode atrasar 2 sprints sem impacto

## Otimizando o Caminho Crítico

### 1. Fast-Tracking (Paralelização)

**Conceito**: Fazer tasks em paralelo que normalmente seriam sequenciais

**Exemplo**:
```
Antes: [Design] → [Development] (8 semanas)
Depois: [Design] ↔ [Development] (5 semanas)
       (começar dev antes de finalizar design)
```

**Riscos**: Retrabalho se design mudar

### 2. Crashing (Adicionar Recursos)

**Conceito**: Adicionar pessoas/recursos para acelerar tasks críticas

**Fórmula**:
```
Cost Slope = (Crash Cost - Normal Cost) / (Normal Duration - Crash Duration)
```

**Escolha**: Task com menor cost slope no path crítico

**Lei de Brooks**: "Adding people to a late project makes it later" - cuidado com onboarding overhead!

### 3. Re-sequencing

Mudar ordem de tasks ou dependências para encurtar path crítico.

### 4. Eliminar Desperdício

- Remove tasks desnecessárias
- Simplifica processos
- Automatiza onde possível

## Bottlenecks e Riscos

### Identificando Bottlenecks

**Bottleneck** = Task no caminho crítico com:
- Recursos escassos
- Alta complexidade
- Muitas dependências

**Indicadores**:
- Multiple paths convergem nesta task
- Recurso único/especializado
- Alta incerteza técnica

### Análise de Riscos

**Priorize riscos em tasks críticas**:

| Risk Level | Criteria |
|-----------|----------|
| 🔴 **Critical** | No caminho crítico + alta incerteza |
| 🟠 **High** | No caminho crítico + média incerteza |
| 🟡 **Medium** | Não crítico + alta incerteza |
| 🟢 **Low** | Não crítico + baixa incerteza |

## Monitoramento Contínuo

### KPIs do Caminho Crítico

1. **Critical Path Duration**: Sempre mudando?
2. **Number of Critical Tasks**: Aumentando?
3. **Slack Consumption Rate**: Folga sendo consumida rapidamente?
4. **Critical Task Completion %**: No prazo?

### Sinais de Alerta 🚨

- Task crítica atrasou
- Slack de tasks não-críticas consumido (aproximando de crítico)
- Novo caminho crítico emergiu
- Duração do projeto aumentou

## Ferramentas

### Software Especializado
- **Microsoft Project**: CPM clássico
- **Primavera P6**: Enterprise project management
- **FastTrack Schedule**: Foco em CPM

### Python/Scripts
```python
import networkx as nx

# Criar grafo de dependências
G = nx.DiGraph()
G.add_edge('A', 'B', weight=3)
G.add_edge('A', 'C', weight=5)

# Calcular caminho crítico
critical_path = nx.dag_longest_path(G, weight='weight')
```

### Agile Tools
- Jira: Dependency tracking
- Azure DevOps: Delivery Plans
- LucidChart/Miro: Network diagrams

## Limitações do CPM

### Problemas

1. **Determinístico**: Assume durações exatas (na prática, há incerteza)
2. **Estático**: Não captura mudanças frequentes de Agile
3. **Complexidade**: Difícil manter com muitas tasks
4. **Recursos ignorados**: CPM clássico não considera resource constraints

### Alternativas/Complementos

- **PERT**: Usa distribuições probabilísticas de duração
- **Monte Carlo**: Simulação de múltiplos cenários
- **Chain Critical**: Considera recursos limitados
- **Kanban**: Para fluxo contínuo sem dependencies complexas

## Boas Práticas

### ✅ Faça
- Recalcule CPM regularmente (cada sprint em Agile)
- Foque gerenciamento em tasks críticas
- Documente premissas de duração
- Use para comunicação com stakeholders
- Identifique e mitigue riscos em path crítico
- Considere múltiplos cenários (otimista/pessimista)

### ❌ Evite
- Tratar CPM como plano imutável
- Ignorar incertezas nas estimativas
- Negligenciar tasks não-críticas
- CPM muito detalhado (micro-tasks)
- Esquecer de atualizar após mudanças
- Assumir recursos ilimitados

## Referências

- **PMI PMBOK**: Critical Path Method
- **Goldratt**: "Critical Chain" (theory of constraints)
- **Kelley & Walker**: Original CPM paper (1959)
- **PERT vs CPM**: Understanding differences
