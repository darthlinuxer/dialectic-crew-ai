# Visão Geral - Product Backlog Priorizado

## O que é o Product Backlog?

O Product Backlog é uma **lista ordenada** de tudo que pode ser necessário no produto. É a única fonte de requisitos para qualquer mudança a ser feita no produto. É dinâmico e evolui constantemente.

## Responsabilidade

- **Product Owner**: Responsável pelo backlog
  - Conteúdo
  - Priorização
  - Clareza dos itens
  - Acessibilidade para todos

## Características do Backlog

### 1. Ordenado (Priorizado)
- **Um único ordenamento**: Não existem prioridades iguais
- **Topo do backlog**: Itens mais importantes e refinados
- **Fundo do backlog**: Itens menos detalhados e menor prioridade
- **Priorização contínua**: Revisada regularmente

### 2. Emergente
- **Evolui**: Muda conforme aprendizado
- **Nunca completo**: Sempre pode ter novos itens
- **Refinamento contínuo**: Itens são detalhados ao longo do tempo
- **Adaptável**: Responde a mudanças de mercado e feedback

### 3. Estimado
- **Story points**: Tamanho relativo de cada item
- **Ordem de magnitude**: Estimativas iniciais podem ser grosseiras
- **Refinamento**: Itens próximos ao topo têm estimativas mais precisas

## Estrutura do Backlog

### Hierarquia Típica

```
Product Backlog
├── Iniciativa 1
│   ├── Épico 1.1
│   │   ├── Story A (Prioridade 1)
│   │   ├── Story B (Prioridade 2)
│   │   └── Story C (Prioridade 3)
│   └── Épico 1.2
│       └── ...
├── Iniciativa 2
│   └── ...
└── Stories independentes
```

### Tipos de Itens

1. **Iniciativas**: Grandes objetivos estratégicos
2. **Épicos**: Funcionalidades grandes
3. **User Stories**: Incrementos entregáveis
4. **Bugs**: Defeitos a corrigir
5. **Tech Debt**: Melhorias técnicas
6. **Spikes**: Investigações e POCs

## Priorização do Backlog

### Fatores de Priorização

1. **Valor de Negócio**
   - ROI esperado
   - Satisfação do cliente
   - Vantagem competitiva
   - Alinhamento estratégico

2. **Risco**
   - Incerteza técnica
   - Dependências externas
   - Aprender cedo vs tarde

3. **Dependências**
   - O que bloqueia outros itens?
   - Pré-requisitos técnicos
   - Sequência lógica

4. **Custo de Adiamento (Cost of Delay)**
   - Quanto custa NÃO fazer agora?
   - Oportunidades perdidas
   - Penalidades contratuais

### Técnicas de Priorização

#### 1. MoSCoW
- **Must have**: Essencial, sem isso o produto falha
- **Should have**: Importante mas não crítico
- **Could have**: Desejável se houver tempo
- **Won't have** (this time): Fora de escopo nesta release

#### 2. Value vs Effort Matrix

```
High Value
     ↑
     |  Quick Wins  |  Major Projects
     |  (Priorize!)  |  (Planejar bem)
     |______________|_________________
     |              |
     |  Fill-Ins    |  Thankless Tasks
     |  (Se sobrar)  |  (Evitar/Questionar)
     └──────────────────────────> High Effort
```

#### 3. WSJF (Weighted Shortest Job First)

```
WSJF = Cost of Delay / Job Duration

Cost of Delay = Business Value + Time Criticality + Risk Reduction

Priorize itens com maior WSJF
```

#### 4. Kano Model

- **Must-be**: Features básicas esperadas
- **Performance**: Mais é melhor (ex: velocidade)
- **Attractive**: "Wow factors" que encantam
- **Indifferent**: Não importam para o usuário
- **Reverse**: Usuário prefere sem elas

## Refinamento do Backlog

### O que é Refinamento?

Processo contínuo de:
- Adicionar detalhes a itens
- Estimar ou re-estimar
- Quebrar itens grandes
- Ordenar/reordenar itens
- Remover itens obsoletos

### Quando Refinar?

- **Sessões dedicadas**: Backlog refinement meetings (até 10% do tempo do time)
- **Contínuo**: Product Owner e time refinam conforme necessário
- **Antes do Sprint Planning**: Top do backlog deve estar "Ready"

### Definition of Ready (DoR)

Item está pronto para Sprint Planning quando tem:

- [ ] **User story clara**: Como/Quero/Para que
- [ ] **Critérios de aceitação**: BDD (Given-When-Then)
- [ ] **Estimativa**: Story points definidos
- [ ] **Tamanho adequado**: Cabe em 1 sprint
- [ ] **Sem dependências bloqueantes**: Ou resolvidas
- [ ] **Entendimento compartilhado**: Time sabe o que fazer

## Gerenciando o Backlog

### Tamanho do Backlog

**Ideal**: 2-3 sprints de trabalho detalhado no topo

- **Muito grande**: Difícil de gerenciar, muitos itens obsoletos
- **Muito pequeno**: Time pode ficar sem trabalho

### Grooming Regular

**Recomendação**: Revisar backlog completo a cada 2-4 semanas

- **Remover**: Itens não mais relevantes
- **Atualizar**: Mudanças de prioridade
- **Quebrar**: Épicos em stories
- **Adicionar**: Novos itens identificados

### Comunicação

**Backlog é público e acessível**:
- Stakeholders podem ver prioridades
- Time entende direção do produto
- Transparência sobre próximos passos

## Backlog vs Roadmap

### Diferenças

| Aspecto | Backlog | Roadmap |
|---------|---------|---------|
| **Nível** | Tático | Estratégico |
| **Horizonte** | 2-6 meses | 6-24 meses |
| **Detalhe** | Alto (stories) | Baixo (temas/épicos) |
| **Mudança** | Frequente | Menos frequente |
| **Audiência** | Time Scrum | Stakeholders/Executivos |

### Relacionamento

```
Roadmap (Visão estratégica)
    ↓
Product Backlog (Execução tática)
    ↓
Sprint Backlog (Trabalho imediato)
```

## Métricas do Backlog

### Health Metrics

1. **Backlog Growth Rate**: Novos itens vs completados
2. **Age of Items**: Quanto tempo itens ficam no backlog?
3. **Throughput**: Quantos itens completados por sprint?
4. **Refinement Ratio**: % de itens com DoR

### Red Flags 🚩

- Backlog cresce mais rápido que throughput
- Muitos itens > 6 meses sem progresso
- Stories não refinadas no topo
- Falta de clareza de prioridade

## Ferramentas

### Populares
- **Jira**: Backlog view com drag-and-drop
- **Azure DevOps**: Backlog hierarchy
- **Trello**: Kanban-style backlog
- **Linear**: Modern backlog management
- **Monday.com**: Visual backlog boards

### Features Importantes
- Priorização por drag-and-drop
- Filtering e grouping
- Estimativas e story points
- Links entre itens (dependencies)
- Sprint planning integration

## Boas Práticas

### ✅ Faça
- Mantenha backlog priorizado sempre
- Refine continuamente
- Remova itens obsoletos regularmente
- Quebre épicos em stories
- Envolva stakeholders na priorização
- Use critérios objetivos de priorização
- Mantenha topo do backlog com DoR

### ❌ Evite
- Backlog como "wishlist" infinita
- Itens sem critérios de aceitação
- Priorização por pessoa que grita mais alto
- Deixar itens envelhecerem sem revisão
- Backlog como repositório de "talvez algum dia"
- Falta de transparência nas prioridades

## Anti-Patterns

### 1. "Junkyard Backlog"
**Problema**: Backlog vira depósito de todas ideias
**Solução**: Regularmente remova itens > 6 meses sem progresso

### 2. "Frozen Backlog"
**Problema**: Prioridades nunca mudam
**Solução**: Re-priorize baseado em feedback e aprendizado

### 3. "Details Everywhere"
**Problema**: Todos itens super detalhados
**Solução**: Detalhe apenas topo do backlog (princípio Just-in-Time)

### 4. "Wishful Thinking"
**Problema**: Ignorar capacidade real do time
**Solução**: Base roadmap em velocity histórica

## Referências

- **Scrum Guide** (scrum.org): Definição oficial de Product Backlog
- **Roman Pichler**: Product Backlog management
- **Mike Cohn**: User Story prioritization
- **Jeff Patton**: Story Mapping para organizar backlog
- **Henrik Kniberg**: Visualizing backlogs
