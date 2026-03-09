# Gráfico de Gantt

> **Propósito**: Visualizar cronograma do projeto com tasks, dependências, milestones e sprints, identificando o caminho crítico.

---

## 1. Informações do Projeto

- **Projeto**: [{{nome_projeto}}](INPUTS.md#inputs-gantt)
- **Início**: [{{data_inicio}}](INPUTS.md#inputs-gantt)
- **Término Previsto**: [{{data_termino}}](INPUTS.md#inputs-gantt)
- **Duração Total**: [{{duracao_total}}](INPUTS.md#inputs-gantt) semanas

---

## 2. Cronograma

| ID | Task/User Story | Início | Término | Duração | Dependências | Sprint | Status | No Caminho Crítico? |
|----|----------------|---------|---------|---------|--------------|--------|--------|-------------------|
| [{{task_1_id}}](INPUTS.md#inputs-gantt) | [{{task_1_nome}}](INPUTS.md#inputs-gantt) | [{{task_1_inicio}}](INPUTS.md#inputs-gantt) | [{{task_1_fim}}](INPUTS.md#inputs-gantt) | [{{task_1_duracao}}](INPUTS.md#inputs-gantt) | [{{task_1_dep}}](INPUTS.md#inputs-gantt) | [{{task_1_sprint}}](INPUTS.md#inputs-gantt) | [{{task_1_status}}](INPUTS.md#inputs-gantt) | [{{task_1_critico}}](INPUTS.md#inputs-gantt) |

---

## 3. Milestones

| Milestone | Data | Descrição | Status |
|-----------|------|-----------|--------|
| [{{milestone_1}}](INPUTS.md#inputs-gantt) | [{{milestone_1_data}}](INPUTS.md#inputs-gantt) | [{{milestone_1_desc}}](INPUTS.md#inputs-gantt) | [{{milestone_1_status}}](INPUTS.md#inputs-gantt) |

---

## 4. Sprints

| Sprint | Início | Término | Story Points | Tasks |
|--------|--------|---------|--------------|-------|
| Sprint [{{sprint_1_num}}](INPUTS.md#inputs-gantt) | [{{sprint_1_inicio}}](INPUTS.md#inputs-gantt) | [{{sprint_1_fim}}](INPUTS.md#inputs-gantt) | [{{sprint_1_pontos}}](INPUTS.md#inputs-gantt) | [{{sprint_1_tasks}}](INPUTS.md#inputs-gantt) |

---

## 5. Caminho Crítico

**Tasks no Caminho Crítico**:
- [{{critico_1}}](INPUTS.md#inputs-gantt)
- [{{critico_2}}](INPUTS.md#inputs-gantt)
- [{{critico_3}}](INPUTS.md#inputs-gantt)

**Duração Total do Caminho Crítico**: [{{duracao_caminho_critico}}](INPUTS.md#inputs-gantt) semanas

---

## 6. Script Python para Visualização

```python
[{{script_python}}](INPUTS.md#inputs-gantt)
```
