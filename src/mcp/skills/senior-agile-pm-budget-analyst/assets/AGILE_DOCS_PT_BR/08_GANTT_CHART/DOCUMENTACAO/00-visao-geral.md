# Visão Geral - Gráfico de Gantt

## O que é um Gráfico de Gantt?

O Gráfico de Gantt é uma ferramenta de visualização de cronograma que mostra tarefas ao longo do tempo, suas durações, dependências e marcos importantes. Criado por Henry Gantt em 1910, é amplamente usado em gerenciamento de projetos.

## Componentes do Gantt

### 1. Eixo Horizontal (Tempo)
- Dias, semanas, meses
- Períodos de sprint (em Agile)
- Data início e fim do projeto

### 2. Eixo Vertical (Tasks)
- User Stories / Tasks / Épicos
- Organizados hierarquicamente
- Agrupados por iniciativa ou sprint

### 3. Barras
- **Comprimento**: Duração da task
- **Posição**: Quando começa e termina
- **Cor**: Status, prioridade, ou responsável
- **Progresso**: % completado (barra preenchida)

### 4. Dependências
- **Setas**: Conectam tasks dependentes
- **Tipos**: Finish-to-Start, Start-to-Start, etc.

### 5. Milestones
- **Diamante/Triângulo**: Eventos importantes
- **Zero duração**: Pontos no tempo
- **Exemplos**: Release, demo, aprovação

## Gantt em Projetos Agile/Scrum

### Desafios
- Agile valoriza adaptação vs planejamento fixo
- Sprints mudam baseado em aprendizado
- Escopo pode variar

### Adaptações Agile-Friendly

1. **Gantt de Alto Nível**
   - Mostrar épicos/iniciativas, não stories
   - Períodos em sprints, não dias exatos
   - Atualizar após cada sprint

2. **Rolling Wave Planning**
   - Detalhar apenas próximos 2-3 sprints
   - Restante em nível de épico
   - Refinar conforme se aproxima

3. **Flexibility Built-in**
   - Buffer entre épicos
   - Múltiplos cenários (otimista/realista/pessimista)
   - Marcar itens como "tentativo"

## Tipos de Dependências

### 1. Finish-to-Start (FS) - Mais Comum
```
Task A ────────>
               Task B ────────>
```
Task B só pode começar após Task A terminar.

### 2. Start-to-Start (SS)
```
Task A ────────────>
  Task B ──────────>
```
Task B pode começar quando Task A começar.

### 3. Finish-to-Finish (FF)
```
Task A ────────────>
      Task B ──────>
```
Task B deve terminar quando Task A terminar.

### 4. Start-to-Finish (SF) - Raro
```
Task A ────>
  Task B ───────────>
```
Task B só pode terminar quando Task A começar.

## Criando um Gantt Agile

### Passo 1: Listar Tasks/Stories
- Iniciativas e épicos do projeto
- User stories principais
- Milestones (releases, demos)

### Passo 2: Estimar Duração
```
Duração (sprints) = Story Points / Velocity

Exemplo:
- Épico: 34 story points
- Velocity: 17 pontos/sprint
- Duração: 34/17 = 2 sprints
```

### Passo 3: Identificar Dependências
- Técnicas: Infraestrutura antes de features
- De negócio: Login antes de checkout
- De conhecimento: Spike antes de implementação

### Passo 4: Sequenciar Tasks
- Critical Path first (tarefas que não têm slack)
- Dependências must be satisfied
- Paralelizar quando possível

### Passo 5: Adicionar Milestones
- Sprint Reviews/Demos
- Releases para produção
- Checkpoints de stakeholder
- Go/No-Go decisions

### Passo 6: Buffer e Contingência
- 10-20% buffer entre épicos maiores
- Risk buffer para itens de alta incerteza
- Sprint de "catch-up" se necessário

## Caminho Crítico no Gantt

### O que é?

O **Caminho Crítico** é a sequência mais longa de tarefas dependentes que determina a duração mínima do projeto.

Tasks no caminho crítico têm **slack zero** - qualquer atraso impacta o projeto todo.

### Visualizando no Gantt

- Cor diferente (geralmente vermelho)
- Barras mais grossas
- Ícone especial

### Implicações

- **Foco**: Gerenciar tasks críticas de perto
- **Recursos**: Priorizar recursos para path crítico
- **Riscos**: Mitigação prioritária
- **Fast-tracking**: Paralelizar tasks críticas se possível

## Gantt vs Burndown

| Aspecto | Gantt | Burndown |
|---------|-------|----------|
| **Foco** | Cronograma e dependências | Progresso e velocity |
| **Eixo X** | Tempo (datas) | Tempo (sprints/dias) |
| **Eixo Y** | Tasks/Stories | Story points restantes |
| **Uso** | Planejamento e coordenação | Monitoramento diário |
| **Stakeholders** | Executivos, PM | Scrum Team |
| **Frequência** | Atualização semanal/sprint | Atualização diária |

**Conclusão**: Use ambos! Gantt para visão estratégica, Burndown para tático.

## Ferramentas

### Especializadas em Gantt
- **Microsoft Project**: Clássico para Gantt
- **Smartsheet**: Gantt colaborativo online
- **TeamGantt**: Simples e visual
- **GanttProject**: Open source

### Agile Tools com Gantt
- **Jira**: Timeline view (Gantt-style)
- **Azure DevOps**: Delivery Plans
- **Monday.com**: Gantt views
- **Asana**: Timeline feature

### Scripts Python
```python
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

# Criar Gantt programaticamente para automação
```

## Boas Práticas

### ✅ Faça
- Mantenha simples em Agile (alto nível)
- Atualize após cada sprint
- Marque caminho crítico claramente
- Use cores para status/prioridade
- Inclua buffer para incertezas
- Documente dependências

### ❌ Evite
- Gantt detalhado demais (micro-tasks)
- Tratar como plano fixo imutável
- Esquecer de atualizar regularmente
- Ignorar feedback e adaptar
- Gantt como ferramenta de microgestão
- Dependências artificiais

## Gantt para Stakeholders

### Comunicação Executiva

**O que mostrar**:
- Épicos e iniciativas (não stories individuais)
- Releases e milestones principais
- Caminho crítico
- Riscos maiores

**Como apresentar**:
- Visual limpo sem muito detalhe
- Cores para status (on track / at risk / delayed)
- Notas sobre mudanças desde última versão
- Próximos milestones em destaque

### Exemplo de Slide

```
Q1 2026                Q2 2026                Q3 2026
|__________________|__________________|__________________|
  [Épico A]────────────>
                    [Épico B]──────>
                              [Épico C]────────>
     △ Release 1.0        △ Release 2.0    △ Release 3.0
```

## Limitações do Gantt

### Problemas Comuns

1. **Falsa Precisão**: Parece mais certo do que é
2. **Rigidez**: Difícil mostrar adaptações Agile
3. **Complexidade**: Pode ficar overwhelming
4. **Manutenção**: Trabalho para manter atualizado
5. **Foco errado**: Tasks vs valor entregue

### Quando NÃO usar Gantt

- Projetos muito incertos/exploratórios
- Times muito pequenos (< 5 pessoas)
- Sprints isolados sem dependências
- Quando burndown/kanban são suficientes

## Alternativas e Complementos

### 1. Kanban Board
- Visualiza fluxo de trabalho
- Foco em WIP limits
- Melhor para trabalho contínuo

### 2. Burndown/Burnup Charts
- Acompanha velocity
- Mostra progresso diário
- Previsão de conclusão

### 3. Roadmap Visual
- Tema-based planning
- Now/Next/Later
- Menos compromisso com datas

### 4. Dependency Matrix
- Tabela de dependências
- Mais simples que Gantt
- Boa para discussão de riscos

## Referências

- **PMI (Project Management Institute)**: Schedule Management
- **Microsoft Project**: Gantt best practices
- **Scaled Agile (SAFe)**: PI Planning with Gantt
- **Atlassian**: Timeline planning in Jira
