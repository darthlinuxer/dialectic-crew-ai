# Visão Geral - Orçamento do Projeto

## Propósito

O orçamento do projeto em metodologia Agile/Scrum deve estabelecer uma estimativa realista de custos baseada em:
- **Story points** (estimativas de esforço relativo)
- **Composição e taxas da equipe** (custos de recursos humanos)
- **Custos fixos** (infraestrutura, licenças, ferramentas)
- **Overhead** (gestão, suporte, indiretos)
- **Contingência** (reserva para riscos e incertezas)

## Princípios fundamentais

1. **Rastreabilidade**: Cada custo deve ser rastreável até user stories específicas
2. **Transparência**: Premissas e cálculos claramente documentados
3. **Adaptabilidade**: Orçamento revisado conforme velocity real da equipe
4. **Iterativo**: Ajustado a cada sprint com base em dados reais

## Metodologia de cálculo

### Passo 1: Configurar poker planning
- Definir relação pontos-sprint (ex: 5 pontos = 2 semanas)
- Calcular horas por ponto: `horas_sprint / pontos_sprint`

### Passo 2: Estimar story points
- Usar poker planning para estimar todas user stories
- Somar pontos por épico e iniciativa
- Obter total de story points do projeto

### Passo 3: Calcular horas
- Total de horas = story points × horas por ponto
- Distribuir por sprint, épico, iniciativa

### Passo 4: Calcular custo base
- Definir composição da equipe (funções, quantidades)
- Definir taxas horárias/diárias por função
- Calcular taxa média ponderada
- Custo base = total horas × taxa média

### Passo 5: Adicionar overhead
- Overhead típico: 15-30% do custo base
- Inclui: gestão, suporte, indiretos, administrativo

### Passo 6: Adicionar custos fixos
- Licenças de software
- Infraestrutura (cloud, servidores)
- Ferramentas e plataformas
- Treinamentos

### Passo 7: Calcular contingência
- Contingência típica: 10-20% do subtotal
- Reserva para riscos e incertezas
- Ajustar baseado em complexidade do projeto

### Passo 8: Obter custo total
```
custo_total = custo_base + overhead + custos_fixos + contingência
```

## Rastreabilidade

Hierarquia de custos deve seguir a estrutura Agile:

```
Projeto
├── Iniciativa 1
│   ├── Épico 1.1
│   │   ├── User Story US-001 (X pontos → Y horas → Z reais)
│   │   ├── User Story US-002
│   │   └── ...
│   └── Épico 1.2
│       └── ...
├── Iniciativa 2
│   └── ...
└── Iniciativa 3
    └── ...
```

Cada nível deve ter:
- Story points totais
- Horas estimadas
- Custo calculado
- Percentual do orçamento total

## Análise de sensibilidade

Criar cenários:
- **Otimista**: -10 a -20% story points (equipe mais eficiente)
- **Realista**: baseline (estimativas atuais)
- **Pessimista**: +20 a +30% story points (desafios técnicos, mudanças)

Calcular impacto no custo total para cada cenário.

## Atualização contínua

O orçamento deve ser atualizado:
- **Por sprint**: Ajustar com base em velocity real
- **Por épico**: Refinar estimativas conforme detalhamento
- **Por mudanças**: Atualizar quando escopo muda

### Métricas de acompanhamento
- **Burn rate**: Custo consumido por sprint
- **Cost variance**: Diferença entre planejado e real
- **Earned value**: Valor entregue vs. custo consumido

## Boas práticas

1. **Documente premissas**: Taxa de câmbio, disponibilidade de recursos, etc.
2. **Considere sazonalidade**: Férias, feriados, licenças
3. **Inclua treinamento**: Ramp-up de novos membros
4. **Preveja rotatividade**: Buffer para substituições
5. **Atualize regularmente**: A cada 2-3 sprints no mínimo
6. **Comunique mudanças**: Stakeholders devem ser informados de variações significativas

## Aprovações necessárias

- **Product Owner**: Valida priorização e valor de negócio
- **Sponsor**: Aprova orçamento total e alinhamento estratégico
- **CFO/Financeiro**: Valida cálculos e disponibilidade de recursos

## Ferramentas recomendadas

- Planilhas (Excel, Google Sheets) para cálculos detalhados
- Scripts Python para automação e visualização
- Jira/Azure DevOps para rastreamento de story points
- Power BI/Tableau para dashboards de acompanhamento

## Referências

- Agile Estimating and Planning - Mike Cohn
- Scrum Guide - scrum.org
- Project Management Body of Knowledge (PMBOK) - Cost Management
- Earned Value Management (EVM) principles
