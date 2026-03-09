# Visão Geral - Análise Completa do Projeto

## O que é Análise Completa de Projeto?

É uma avaliação abrangente que combina todos os artefatos Agile/Scrum para fornecer uma visão holística do projeto: estrutura (iniciativas/épicos/stories), estimativas (poker planning), orçamento, cronograma (Gantt), riscos (caminho crítico) e métricas (velocity).

## Objetivos da Análise

### Para Executivos
- **Viabilidade**: Projeto é factível?
- **ROI**: Vale o investimento?
- **Timeline**: Quando estará pronto?
- **Riscos**: Quais os maiores riscos?

### Para Product Owner
- **Priorização**: O que fazer primeiro?
- **Scope**: O que está incluído/excluído?
- **Trade-offs**: Onde podemos negociar?

### Para Scrum Team
- **Entendimento**: Qual o big picture?
- **Planejamento**: Como estruturar sprints?
- **Dependências**: O que bloqueia o quê?

## Estrutura da Análise

### 1. Visão Geral do Projeto
- **Objetivo**: Por que este projeto existe?
- **Stakeholders**: Quem está envolvido?
- **Success Criteria**: Como medir sucesso?
- **Timeline**: Início e fim esperados

### 2. Breakdown Estrutural

```
Projeto
├── Iniciativa 1 (Estratégica)
│   ├── Épico 1.1 (Grande funcionalidade)
│   │   ├── Story A (Implementável)
│   │   ├── Story B
│   │   └── Story C
│   └── Épico 1.2
│       └── ...
└── Iniciativa 2
    └── ...
```

**Métricas de Breakdown**:
- Total de Iniciativas: X
- Total de Épicos: Y
- Total de User Stories: Z
- Complexidade média por nível

### 3. Estimativas e Esforço

**Poker Planning Results**:
- Total Story Points: XXX pontos
- Distribuição por iniciativa
- Distribuição por épico
- Stories > threshold que precisam breakdown

**Velocity e Duração**:
```
Duração = Total Story Points / Velocity

Exemplo:
- 89 pontos total
- Velocity: 17 pontos/sprint
- Duração: 89/17 ≈ 5-6 sprints (10-12 semanas)
```

### 4. Análise de Orçamento

**Composição de Custos**:
```
Custo Total = Base + Overhead + Fixos + Contingência

Exemplo:
- Base (recursos): R$ 200.000
- Overhead (20%): R$ 40.000
- Fixos (infra): R$ 25.000
- Contingência (15%): R$ 39.750
- TOTAL: R$ 304.750
```

**Rastreabilidade**:
- Custo por iniciativa
- Custo por épico
- Custo por sprint
- ROI esperado vs investimento

### 5. Cronograma e Dependências

**Gantt de Alto Nível**:
- Épicos distribuídos no tempo
- Milestones (releases, demos)
- Dependências críticas visualizadas

**Caminho Crítico**:
- Tasks/épicos no critical path
- Duração mínima do projeto
- Bottlenecks identificados
- Estratégias de otimização

### 6. Análise de Riscos

**Matriz de Riscos**:

| Risco | Probabilidade | Impacto | Criticidade | Mitigação |
|-------|--------------|---------|-------------|-----------|
| Integração API falhar | Médio | Alto | 🔴 Critical | POC antecipada + Plan B |
| Membro chave sair | Baixo | Alto | 🟠 High | Knowledge sharing |

**Categorias**:
- Riscos técnicos
- Riscos de recursos
- Riscos de negócio
- Riscos externos

### 7. Métricas de Sucesso

**Leading Indicators** (durante):
- Velocity trend
- Burn rate vs budget
- Sprint goal achievement rate
- Team satisfaction

**Lagging Indicators** (após):
- ROI realizado
- Time-to-market
- Customer satisfaction (NPS)
- Qualidade (bugs, retrabalho)

## Processo de Análise

### Fase 1: Coleta de Dados (1-2 dias)

1. **Workshops com stakeholders**: Objetivos, requisitos, restrições
2. **Análise de documentos existentes**: Business case, estratégia
3. **Technical discovery**: Arquitetura, integrações, tech stack
4. **Competitive analysis**: Benchmarks, mercado

### Fase 2: Breakdown e Estimativa (2-3 dias)

1. **Identificar iniciativas** estratégicas
2. **Quebrar em épicos**
3. **Detalhar user stories** para épicos prioritários
4. **Poker planning** para estimar stories
5. **Validar estimativas** com technical leads

### Fase 3: Planejamento Financeiro (1 dia)

1. **Definir composição da equipe**
2. **Calcular taxas e custos**
3. **Projetar orçamento**
4. **Análise de sensibilidade** (otimista/realista/pessimista)

### Fase 4: Cronograma e Dependências (1 dia)

1. **Mapear dependências** entre épicos
2. **Criar Gantt** de alto nível
3. **Calcular caminho crítico**
4. **Identificar bottlenecks**

### Fase 5: Análise de Riscos e Recomendações (1 dia)

1. **Identificar riscos** principais
2. **Priorizar** por impacto × probabilidade
3. **Definir mitigações**
4. **Formular recomendações**

### Fase 6: Documentação e Apresentação (1 dia)

1. **Compilar análise** completa
2. **Criar apresentação executiva**
3. **Preparar materiais** de apoio
4. **Apresentar** para stakeholders

**Total**: 6-8 dias de trabalho concentrado

## Outputs da Análise

### Documentos Principais

1. **Executive Summary** (2-3 páginas)
   - Objetivo e escopo
   - Timeline e orçamento
   - Principais riscos
   - Recomendação: Go/No-Go

2. **Breakdown Detalhado**
   - Hierarquia completa
   - Story points por nível
   - Priorização

3. **Plano Financeiro**
   - Orçamento detalhado
   - Cenários (otimista/realista/pessimista)
   - ROI projetado

4. **Cronograma Visual**
   - Gantt chart
   - Caminho crítico destacado
   - Milestones marcados

5. **Registro de Riscos**
   - Risks ranked
   - Mitigações propostas
   - Owner por risco

### Apresentação Executiva

**Estrutura típica (20-30 slides)**:

1. **Contexto** (2-3 slides)
   - Por que este projeto?
   - Alinhamento estratégico

2. **Escopo e Breakdown** (3-4 slides)
   - Iniciativas e épicos
   - Total de trabalho

3. **Timeline e Faseamento** (2-3 slides)
   - Gantt de alto nível
   - Releases planejadas

4. **Orçamento e ROI** (3-4 slides)
   - Investimento total
   - Retorno esperado
   - Payback period

5. **Riscos e Mitigações** (2-3 slides)
   - Top 5 riscos
   - Planos de mitigação

6. **Recomendações** (2-3 slides)
   - Go/No-Go
   - Próximos passos
   - Decisões necessárias

7. **Apêndices** (restante)
   - Detalhes técnicos
   - Estimativas detalhadas
   - Premissas

## Critérios de Go/No-Go

### Aprovar (Go) quando:
- ✅ Alinhado com estratégia
- ✅ ROI positivo e aceitável
- ✅ Riscos gerenciáveis
- ✅ Recursos disponíveis
- ✅ Timeline realista
- ✅ Sponsor comprometido

### Não aprovar (No-Go) quando:
- ❌ ROI negativo ou incerto
- ❌ Riscos inaceitáveis
- ❌ Recursos insuficientes
- ❌ Timeline irrealista
- ❌ Falta de alinhamento estratégico
- ❌ Alternativas melhores existem

### Condicional (Go com ressalvas):
- ⚠️ Aprovar com scope reduzido
- ⚠️ Aprovar com budget aumentado
- ⚠️ Aprovar após POC/spike
- ⚠️ Aprovar em fases (gates)

## Análise de Cenários

### Cenário Otimista (-15% effort)
- Equipe experiente
- Poucos blockers
- Tecnologia conhecida
- Requisitos estáveis

### Cenário Realista (baseline)
- Estimativas atuais
- Alguns imprevistos
- Aprendizado normal

### Cenário Pessimista (+25% effort)
- Desafios técnicos
- Mudanças de requisito
- Turnover de equipe
- Dependências atrasam

**Uso**: Mostrar range de possibilidades para stakeholders

## Boas Práticas

### ✅ Faça
- Base em dados e fatos
- Envolva especialistas técnicos
- Considere múltiplos cenários
- Documente premissas claramente
- Identifique riscos cedo
- Seja transparente sobre incertezas
- Recomende com confiança

### ❌ Evite
- Análise superficial sem validação
- Otimismo excessivo
- Ignorar riscos conhecidos
- Premissas não documentadas
- Análise isolada (sem input do time)
- Apresentar só boas notícias

## Ferramentas

- **Análise**: Excel, Google Sheets, Python
- **Visualização**: PowerPoint, Google Slides, Miro
- **Gantt**: MS Project, Smartsheet, Jira
- **Financeiro**: Spreadsheets com fórmulas
- **Riscos**: Risk register templates

## Referências

- **Business Analysis Body of Knowledge (BABOK)**
- **PMI Project Business Case**
- **Agile Estimating and Planning** (Mike Cohn)
- **The Lean Startup** (Eric Ries) - MVP thinking
