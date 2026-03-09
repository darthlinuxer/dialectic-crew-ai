# Orçamento do Projeto

> **Propósito**: Calcular o orçamento total do projeto baseado em estimativas de story points, composição da equipe, taxas de recursos e custos fixos. Fornecer rastreabilidade completa entre custos e entregas (iniciativas → épicos → user stories).

## Mapa de links da documentação

- Visão geral: [DOCUMENTACAO/00-visao-geral.md](DOCUMENTACAO/00-visao-geral.md)
- Metodologia de cálculo: [DOCUMENTACAO/01-metodologia-calculo.md](DOCUMENTACAO/01-metodologia-calculo.md)
- Composição de custos: [DOCUMENTACAO/02-composicao-custos.md](DOCUMENTACAO/02-composicao-custos.md)
- Rastreabilidade: [DOCUMENTACAO/03-rastreabilidade.md](DOCUMENTACAO/03-rastreabilidade.md)

---

## 1. Informações do Projeto

- **Nome do Projeto**: [{{nome_projeto}}](INPUTS.md#inputs-orcamento-projeto)
- **Versão do Orçamento**: [{{versao_orcamento}}](INPUTS.md#inputs-orcamento-projeto)
- **Data de Criação**: [{{data_criacao}}](INPUTS.md#inputs-orcamento-projeto)
- **Responsável**: [{{responsavel}}](INPUTS.md#inputs-orcamento-projeto)
- **Moeda**: [{{moeda}}](INPUTS.md#inputs-orcamento-projeto)

---

## 2. Configuração de Poker Planning

- **Relação pontos-sprint**: [{{pontos_por_sprint}}](INPUTS.md#inputs-orcamento-projeto) pontos = 1 sprint
- **Duração do sprint**: [{{duracao_sprint}}](INPUTS.md#inputs-orcamento-projeto) semanas
- **Horas por sprint**: [{{horas_por_sprint}}](INPUTS.md#inputs-orcamento-projeto) horas
- **Relação pontos-horas**: [{{horas_por_ponto}}](INPUTS.md#inputs-orcamento-projeto) horas/ponto

### Cálculo

```
horas_por_ponto = horas_por_sprint / pontos_por_sprint
Exemplo: 80 horas / 5 pontos = 16 horas/ponto
```

---

## 3. Composição da Equipe

| Função | Quantidade | Taxa Horária ({{moeda}}) | Taxa Diária ({{moeda}}) | Dedicação (%) |
|--------|-----------|------------------------|----------------------|--------------|
| [{{funcao_1}}](INPUTS.md#inputs-orcamento-projeto) | [{{qtd_1}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_horaria_1}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_diaria_1}}](INPUTS.md#inputs-orcamento-projeto) | [{{dedicacao_1}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{funcao_2}}](INPUTS.md#inputs-orcamento-projeto) | [{{qtd_2}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_horaria_2}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_diaria_2}}](INPUTS.md#inputs-orcamento-projeto) | [{{dedicacao_2}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{funcao_3}}](INPUTS.md#inputs-orcamento-projeto) | [{{qtd_3}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_horaria_3}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_diaria_3}}](INPUTS.md#inputs-orcamento-projeto) | [{{dedicacao_3}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{funcao_4}}](INPUTS.md#inputs-orcamento-projeto) | [{{qtd_4}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_horaria_4}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_diaria_4}}](INPUTS.md#inputs-orcamento-projeto) | [{{dedicacao_4}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{funcao_5}}](INPUTS.md#inputs-orcamento-projeto) | [{{qtd_5}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_horaria_5}}](INPUTS.md#inputs-orcamento-projeto) | [{{taxa_diaria_5}}](INPUTS.md#inputs-orcamento-projeto) | [{{dedicacao_5}}](INPUTS.md#inputs-orcamento-projeto) |

**Taxa Média Ponderada**: [{{taxa_media_ponderada}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}}/hora

---

## 4. Resumo Executivo do Orçamento

| Métrica | Valor |
|---------|-------|
| **Total de Story Points** | [{{total_story_points}}](INPUTS.md#inputs-orcamento-projeto) pontos |
| **Total de Horas Estimadas** | [{{total_horas_estimadas}}](INPUTS.md#inputs-orcamento-projeto) horas |
| **Custo Base (Recursos)** | [{{custo_base_recursos}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Overhead ({{percentual_overhead}}%)** | [{{custo_overhead}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Custos Fixos** | [{{custos_fixos_total}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Contingência ({{percentual_contingencia}}%)** | [{{custo_contingencia}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **CUSTO TOTAL DO PROJETO** | **[{{custo_total_projeto}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}}** |

### Fórmula de cálculo

```
1. total_horas_estimadas = total_story_points × horas_por_ponto
2. custo_base_recursos = total_horas_estimadas × taxa_media_ponderada
3. custo_overhead = custo_base_recursos × (percentual_overhead / 100)
4. custo_contingencia = (custo_base_recursos + custo_overhead + custos_fixos) × (percentual_contingencia / 100)
5. custo_total_projeto = custo_base_recursos + custo_overhead + custos_fixos + custo_contingencia
```

---

## 5. Detalhamento por Iniciativa

### Iniciativa 1: [{{iniciativa_1_nome}}](INPUTS.md#inputs-orcamento-projeto)

| Métrica | Valor |
|---------|-------|
| **ID** | [{{iniciativa_1_id}}](INPUTS.md#inputs-orcamento-projeto) |
| **Story Points** | [{{iniciativa_1_pontos}}](INPUTS.md#inputs-orcamento-projeto) |
| **Horas Estimadas** | [{{iniciativa_1_horas}}](INPUTS.md#inputs-orcamento-projeto) |
| **Custo Base** | [{{iniciativa_1_custo_base}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Custo Total (com overhead)** | [{{iniciativa_1_custo_total}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **% do Orçamento** | [{{iniciativa_1_percentual}}](INPUTS.md#inputs-orcamento-projeto)% |

### Iniciativa 2: [{{iniciativa_2_nome}}](INPUTS.md#inputs-orcamento-projeto)

| Métrica | Valor |
|---------|-------|
| **ID** | [{{iniciativa_2_id}}](INPUTS.md#inputs-orcamento-projeto) |
| **Story Points** | [{{iniciativa_2_pontos}}](INPUTS.md#inputs-orcamento-projeto) |
| **Horas Estimadas** | [{{iniciativa_2_horas}}](INPUTS.md#inputs-orcamento-projeto) |
| **Custo Base** | [{{iniciativa_2_custo_base}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Custo Total (com overhead)** | [{{iniciativa_2_custo_total}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **% do Orçamento** | [{{iniciativa_2_percentual}}](INPUTS.md#inputs-orcamento-projeto)% |

### Iniciativa 3: [{{iniciativa_3_nome}}](INPUTS.md#inputs-orcamento-projeto) *(se aplicável)*

| Métrica | Valor |
|---------|-------|
| **ID** | [{{iniciativa_3_id}}](INPUTS.md#inputs-orcamento-projeto) |
| **Story Points** | [{{iniciativa_3_pontos}}](INPUTS.md#inputs-orcamento-projeto) |
| **Horas Estimadas** | [{{iniciativa_3_horas}}](INPUTS.md#inputs-orcamento-projeto) |
| **Custo Base** | [{{iniciativa_3_custo_base}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **Custo Total (com overhead)** | [{{iniciativa_3_custo_total}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}} |
| **% do Orçamento** | [{{iniciativa_3_percentual}}](INPUTS.md#inputs-orcamento-projeto)% |

---

## 6. Detalhamento por Sprint

| Sprint | Story Points | Horas | Custo Base ({{moeda}}) | Custo Total ({{moeda}}) | Período |
|--------|-------------|-------|---------------------|---------------------|---------|
| Sprint 1 | [{{sprint_1_pontos}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_1_horas}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_1_custo_base}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_1_custo_total}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_1_periodo}}](INPUTS.md#inputs-orcamento-projeto) |
| Sprint 2 | [{{sprint_2_pontos}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_2_horas}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_2_custo_base}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_2_custo_total}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_2_periodo}}](INPUTS.md#inputs-orcamento-projeto) |
| Sprint 3 | [{{sprint_3_pontos}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_3_horas}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_3_custo_base}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_3_custo_total}}](INPUTS.md#inputs-orcamento-projeto) | [{{sprint_3_periodo}}](INPUTS.md#inputs-orcamento-projeto) |
| ... | ... | ... | ... | ... | ... |

**Total de Sprints**: [{{total_sprints}}](INPUTS.md#inputs-orcamento-projeto)

---

## 7. Custos Fixos

| Item | Descrição | Valor ({{moeda}}) | Frequência |
|------|-----------|---------------|-----------|
| [{{custo_fixo_1_item}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_1_descricao}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_1_valor}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_1_frequencia}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{custo_fixo_2_item}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_2_descricao}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_2_valor}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_2_frequencia}}](INPUTS.md#inputs-orcamento-projeto) |
| [{{custo_fixo_3_item}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_3_descricao}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_3_valor}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_fixo_3_frequencia}}](INPUTS.md#inputs-orcamento-projeto) |

**Total de Custos Fixos**: [{{custos_fixos_total}}](INPUTS.md#inputs-orcamento-projeto) {{moeda}}

---

## 8. Premissas e Restrições

### Premissas

- [{{premissa_1}}](INPUTS.md#inputs-orcamento-projeto)
- [{{premissa_2}}](INPUTS.md#inputs-orcamento-projeto)
- [{{premissa_3}}](INPUTS.md#inputs-orcamento-projeto)

### Restrições

- [{{restricao_1}}](INPUTS.md#inputs-orcamento-projeto)
- [{{restricao_2}}](INPUTS.md#inputs-orcamento-projeto)
- [{{restricao_3}}](INPUTS.md#inputs-orcamento-projeto)

---

## 9. Análise de Sensibilidade

### Cenários

| Cenário | Variação Story Points | Total Story Points | Custo Total ({{moeda}}) | Variação (%) |
|---------|---------------------|-------------------|---------------------|------------|
| Otimista | [{{cenario_otimista_variacao}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_otimista_pontos}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_otimista_custo}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_otimista_percentual}}](INPUTS.md#inputs-orcamento-projeto) |
| Realista (baseline) | 0% | [{{total_story_points}}](INPUTS.md#inputs-orcamento-projeto) | [{{custo_total_projeto}}](INPUTS.md#inputs-orcamento-projeto) | 0% |
| Pessimista | [{{cenario_pessimista_variacao}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_pessimista_pontos}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_pessimista_custo}}](INPUTS.md#inputs-orcamento-projeto) | [{{cenario_pessimista_percentual}}](INPUTS.md#inputs-orcamento-projeto) |

---

## 10. Rastreabilidade

### Hierarquia de custos

```
Projeto: {{nome_projeto}}
├── Iniciativa 1: {{iniciativa_1_nome}} ({{iniciativa_1_custo_total}} {{moeda}})
│   ├── Épico 1.1 ({{epico_1_1_custo}} {{moeda}})
│   │   ├── US-001 ({{us_001_pontos}} pts → {{us_001_custo}} {{moeda}})
│   │   ├── US-002 ({{us_002_pontos}} pts → {{us_002_custo}} {{moeda}})
│   │   └── ...
│   └── Épico 1.2 ({{epico_1_2_custo}} {{moeda}})
│       └── ...
├── Iniciativa 2: {{iniciativa_2_nome}} ({{iniciativa_2_custo_total}} {{moeda}})
│   └── ...
└── Iniciativa 3: {{iniciativa_3_nome}} ({{iniciativa_3_custo_total}} {{moeda}})
    └── ...
```

---

## 11. Aprovações

- **Product Owner**: [{{product_owner}}](INPUTS.md#inputs-orcamento-projeto) - Data: [{{data_aprovacao_po}}](INPUTS.md#inputs-orcamento-projeto)
- **Sponsor**: [{{sponsor}}](INPUTS.md#inputs-orcamento-projeto) - Data: [{{data_aprovacao_sponsor}}](INPUTS.md#inputs-orcamento-projeto)
- **CFO/Financeiro**: [{{cfo}}](INPUTS.md#inputs-orcamento-projeto) - Data: [{{data_aprovacao_cfo}}](INPUTS.md#inputs-orcamento-projeto)
