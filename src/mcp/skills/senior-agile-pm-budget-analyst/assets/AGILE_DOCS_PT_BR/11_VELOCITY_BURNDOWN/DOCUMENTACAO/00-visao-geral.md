# Visão Geral - Velocity & Burndown Charts

## O que é Velocity?

**Velocity** é a quantidade de trabalho (story points) que um Scrum Team consegue completar em um sprint. É uma métrica de **capacidade real** do time, baseada em histórico.

### Características
- **Medida em story points** (não horas)
- **Específica do time** (não compare times diferentes)
- **Estabiliza ao longo do tempo** (após 3-5 sprints)
- **Usada para previsão** de entregas futuras

## Calculando Velocity

### Fórmula Simples
```
Velocity do Sprint = Story Points Completados no Sprint
```

### Velocity Média
```
Velocity Média = Soma(Story Points dos últimos N sprints) / N

Exemplo (últimos 3 sprints):
Sprint 1: 18 pontos
Sprint 2: 21 pontos
Sprint 3: 19 pontos
Velocity Média: (18+21+19)/3 = 19.3 pontos/sprint
```

### O que Conta?

✅ **Conta**: Stories 100% Done (Definition of Done satisfeita)
❌ **Não conta**:
- Stories parcialmente completas
- Stories iniciadas mas não finalizadas
- Trabalho não planejado (bugs urgentes)
- Spikes/investigações (geralmente)

## Fatores que Afetam Velocity

### Aumentam Velocity
- ✅ Time ganha experiência
- ✅ Processos melhoram
- ✅ Tech debt reduzida
- ✅ Ferramentas/automação
- ✅ Menos interrupções

### Diminuem Velocity
- ❌ Novos membros (ramp-up)
- ❌ Turnover de equipe
- ❌ Tech debt acumulada
- ❌ Dependências externas
- ❌ Mudanças frequentes de prioridade

### Normal/Esperado
- 📊 Férias e feriados
- 📊 Treinamentos
- 📊 Suporte/hotfixes
- 📊 Complexidade das stories

## Usando Velocity para Previsão

### Previsão de Conclusão

```
Sprints Restantes = Story Points Restantes / Velocity Média

Exemplo:
- Backlog restante: 76 pontos
- Velocity média: 19 pontos/sprint
- Previsão: 76/19 = 4 sprints (8 semanas)
```

### Range de Previsão

Use **best case, typical, worst case**:

```
Best: Backlog / Velocity Máxima Histórica
Typical: Backlog / Velocity Média
Worst: Backlog / Velocity Mínima Histórica

Exemplo:
- 76 pontos restantes
- Velocities: 17 (min), 19 (avg), 21 (max)

Best: 76/21 = 3.6 sprints
Typical: 76/19 = 4.0 sprints
Worst: 76/17 = 4.5 sprints

Comunicar: "Entre 3.5 e 4.5 sprints" (7-9 semanas)
```

## O que é Burndown Chart?

**Burndown Chart** mostra o **trabalho restante** ao longo do tempo. Usado para monitorar progresso e prever se o sprint goal será atingido.

### Eixos
- **Eixo X**: Tempo (dias do sprint ou sprints do release)
- **Eixo Y**: Trabalho restante (story points ou tasks)

### Linhas
- **Linha Ideal**: Progresso perfeito linear
- **Linha Real**: Progresso atual do time
- **Projeção**: Onde chegaremos se continuar neste ritmo

## Tipos de Burndown

### 1. Sprint Burndown (Diário)

Mostra progresso **dentro de um sprint**.

```
Story Points
    ↑
 30 |●
 25 | ●╲
 20 |  ●─╲
 15 |   ●──╲
 10 |    ●───╲  ← Ideal
  5 |     ●─────●╲
  0 └──────────────────> Dias
     D1 D2 D3 D4 D5 D6 D7 D8 D9 D10
```

**Atualização**: Diária (durante daily standup)

### 2. Release Burndown (Por Sprint)

Mostra progresso **ao longo de múltiplos sprints** até uma release.

```
Story Points
    ↑
200 |●
150 | ●
100 |  ●
 50 |   ●
  0 └─────────> Sprints
     S1 S2 S3 S4 S5 S6
```

**Atualização**: Ao final de cada sprint

## Burnup Chart (Alternativa)

**Burnup** mostra **trabalho completado** (aumentando) vs **total de trabalho** (scope line).

### Vantagens sobre Burndown
- ✅ Visualiza mudanças de scope
- ✅ Mostra progresso positivo (subindo)
- ✅ Mais fácil ver velocity

```
Story Points
    ↑
150 |         ────────── Total Scope
    |       ╱
100 |     ╱
    |   ╱
 50 | ╱  ← Work Completed
    |●
  0 └─────────> Sprints
     S1 S2 S3 S4 S5 S6
```

## Interpretando os Charts

### Padrões Comuns

#### 1. On Track ✅
```
Real acompanha Ideal de perto
→ Tudo OK, sprint/release no caminho certo
```

#### 2. Ahead of Schedule 🚀
```
Real abaixo da linha Ideal (termina antes)
→ Stories mais simples que esperado
→ Ou velocity subestimada
```

#### 3. Behind Schedule ⚠️
```
Real acima da linha Ideal
→ Stories mais complexas
→ Blockers/impedimentos
→ Underestimation
```

#### 4. Flat Line (Nenhum Progresso) 🚨
```
Linha Real horizontal
→ Impedimento crítico
→ Requer ação imediata
```

#### 5. Scope Change
```
Total scope sobe ou desce
→ Mudanças no backlog
→ Visível em Burnup, não em Burndown
```

## Métricas Derivadas

### 1. Completion Rate
```
Completion Rate = Story Points Completados / Story Points Comprometidos

Exemplo: 18/21 = 85.7%
```

### 2. Forecast Date
```
Dias restantes = Story Points Restantes / (Velocity / Dias no Sprint)

Exemplo:
- 10 pontos restantes
- Velocity média: 20 pontos/sprint
- Sprint de 10 dias
- Previsão: 10 / (20/10) = 5 dias
```

### 3. Days Ahead/Behind
```
Diferença entre projeção e linha ideal
```

## Boas Práticas

### ✅ Faça
- Atualize diariamente (sprint burndown)
- Use para discussão, não punição
- Foque em tendências, não pontos isolados
- Discuta desvios no daily standup
- Ajuste previsões baseado em realidade
- Mantenha visível para o time

### ❌ Evite
- Manipular números para "parecer bem"
- Comparar velocity entre times
- Usar como métrica de performance individual
- Burndown como ferramenta de microgestão
- Ignorar feedback que charts dão
- Esconder maus resultados

## Ferramentas

### Nativas de Agile Tools
- **Jira**: Sprint burndown/burnup automáticos
- **Azure DevOps**: Velocity e burndown charts
- **Trello**: Power-Ups para burndown
- **Linear**: Built-in velocity tracking

### Planilhas
- Excel/Google Sheets com fórmulas
- Templates pré-feitos

### Custom Dashboards
- Tableau/Power BI conectado a Jira API
- Grafana com Prometheus
- Python scripts para automação

## Antipadrões

### 1. "Gaming" Velocity
- Inflar estimativas para parecer mais produtivo
- Contar work in progress como done
- **Solução**: Foco em value entregue, não números

### 2. Comparações Entre Times
- "Time A tem velocity 30, Time B só 20"
- **Problema**: Story points são relativos ao time
- **Solução**: Cada time tem sua baseline

### 3. Velocity como Performance Metric
- Pressionar time para "aumentar velocity"
- **Problema**: Cria incentivos errados
- **Solução**: Velocity é ferramenta de planejamento, não avaliação

### 4. Ignorar Contexto
- "Velocity caiu, time está pior!"
- **Problema**: Ignora férias, tech debt, novos membros
- **Solução**: Analise fatores contextuais

## Comunicando para Stakeholders

### Para Executivos
- **Foco**: Previsão de conclusão
- **Formato**: "Entregaremos entre 7-9 semanas"
- **Visual**: Burnup com scope line

### Para Product Owner
- **Foco**: Capacidade de planejamento
- **Formato**: "Podemos comprometer ~19 pontos/sprint"
- **Visual**: Velocity trend

### Para Time
- **Foco**: Progresso diário
- **Formato**: "Estamos 2 pontos atrás, precisa de ajuda?"
- **Visual**: Sprint burndown atualizado

## Referências

- **Scrum Guide**: Não menciona velocity explicitamente (é emergent)
- **Mike Cohn**: "Agile Estimating and Planning" - Velocity chapter
- **Henrik Kniberg**: "Scrum and XP from the Trenches"
- **Atlassian**: Velocity reports documentation
