# Análise de Caminho Crítico (CPM)

> **Propósito**: Identificar a sequência mais longa de tasks dependentes, calcular slack times, identificar bottlenecks e propor otimizações.

---

## 1. Informações do Projeto

- **Projeto**: [{{nome_projeto}}](INPUTS.md#inputs-cpm)
- **Data da Análise**: [{{data_analise}}](INPUTS.md#inputs-cpm)
- **Analista**: [{{analista}}](INPUTS.md#inputs-cpm)

---

## 2. Network Diagram

### Tasks e Dependências

| ID | Task | Duração (dias) | Predecessores | ES | EF | LS | LF | Slack |
|----|------|---------------|---------------|----|----|----|----|-------|
| [{{task_1_id}}](INPUTS.md#inputs-cpm) | [{{task_1_nome}}](INPUTS.md#inputs-cpm) | [{{task_1_dur}}](INPUTS.md#inputs-cpm) | [{{task_1_pred}}](INPUTS.md#inputs-cpm) | [{{task_1_es}}](INPUTS.md#inputs-cpm) | [{{task_1_ef}}](INPUTS.md#inputs-cpm) | [{{task_1_ls}}](INPUTS.md#inputs-cpm) | [{{task_1_lf}}](INPUTS.md#inputs-cpm) | [{{task_1_slack}}](INPUTS.md#inputs-cpm) |

**Legenda**:
- ES: Earliest Start
- EF: Earliest Finish
- LS: Latest Start
- LF: Latest Finish
- Slack: LF - EF (ou LS - ES)

---

## 3. Caminho Crítico Identificado

**Sequência de Tasks Críticas** (Slack = 0):

1. [{{critico_1}}](INPUTS.md#inputs-cpm) → [{{critico_2}}](INPUTS.md#inputs-cpm) → [{{critico_3}}](INPUTS.md#inputs-cpm)

**Duração Total**: [{{duracao_total}}](INPUTS.md#inputs-cpm) dias / [{{duracao_total_semanas}}](INPUTS.md#inputs-cpm) semanas

---

## 4. Bottlenecks Identificados

| Task | Problema | Impacto | Recomendação |
|------|----------|---------|--------------|
| [{{bottleneck_1}}](INPUTS.md#inputs-cpm) | [{{bottleneck_1_prob}}](INPUTS.md#inputs-cpm) | [{{bottleneck_1_impacto}}](INPUTS.md#inputs-cpm) | [{{bottleneck_1_rec}}](INPUTS.md#inputs-cpm) |

---

## 5. Estratégias de Otimização

### Fast Tracking (Paralelização)

[{{fast_tracking}}](INPUTS.md#inputs-cpm)

### Crashing (Aumento de Recursos)

[{{crashing}}](INPUTS.md#inputs-cpm)

### Outras Otimizações

[{{outras_otimizacoes}}](INPUTS.md#inputs-cpm)

---

## 6. Análise de Riscos

| Task Crítica | Risco | Probabilidade | Impacto | Mitigação |
|--------------|-------|--------------|---------|-----------|
| [{{risco_1_task}}](INPUTS.md#inputs-cpm) | [{{risco_1}}](INPUTS.md#inputs-cpm) | [{{risco_1_prob}}](INPUTS.md#inputs-cpm) | [{{risco_1_imp}}](INPUTS.md#inputs-cpm) | [{{risco_1_mit}}](INPUTS.md#inputs-cpm) |

---

## 7. Script Python para Cálculo

```python
[{{script_python}}](INPUTS.md#inputs-cpm)
```
