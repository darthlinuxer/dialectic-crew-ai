# User Story (História de Usuário)

> **Propósito**: Descrever uma funcionalidade ou requisito do ponto de vista do usuário final, seguindo a metodologia Scrum com formato "Como/Quero/Para que" e critérios de aceitação em formato BDD (Given-When-Then).

## Mapa de links da documentação

- Visão geral: [DOCUMENTACAO/00-visao-geral.md](DOCUMENTACAO/00-visao-geral.md)
- Metodologia dos 3 Cs: [DOCUMENTACAO/01-metodologia-3cs.md](DOCUMENTACAO/01-metodologia-3cs.md)
- Formato de User Story: [DOCUMENTACAO/02-formato-user-story.md](DOCUMENTACAO/02-formato-user-story.md)
- BDD e Given-When-Then: [DOCUMENTACAO/03-bdd-given-when-then.md](DOCUMENTACAO/03-bdd-given-when-then.md)
- Definition of Done: [DOCUMENTACAO/04-definition-of-done.md](DOCUMENTACAO/04-definition-of-done.md)
- Critérios de qualidade: [DOCUMENTACAO/05-criterios-qualidade.md](DOCUMENTACAO/05-criterios-qualidade.md)

---

## 1. Identificação

> **Documentação**: [DOCUMENTACAO/01-metodologia-3cs.md](DOCUMENTACAO/01-metodologia-3cs.md)

- **ID**: [{{user_story_id}}](INPUTS.md#inputs-user-story)
- **Título**: [{{titulo}}](INPUTS.md#inputs-user-story)
- **Épico relacionado**: [{{epico_id}}](INPUTS.md#inputs-user-story) - [{{epico_nome}}](INPUTS.md#inputs-user-story)
- **Iniciativa relacionada**: [{{iniciativa_id}}](INPUTS.md#inputs-user-story) - [{{iniciativa_nome}}](INPUTS.md#inputs-user-story)
- **Sprint**: [{{sprint_numero}}](INPUTS.md#inputs-user-story)
- **Prioridade**: [{{prioridade}}](INPUTS.md#inputs-user-story) (Alta / Média / Baixa)

---

## 2. Card (Cartão) - Descrição da User Story

> **Documentação**: [DOCUMENTACAO/02-formato-user-story.md](DOCUMENTACAO/02-formato-user-story.md)

### Formato padrão: "Como/Quero/Para que"

**Como** [{{tipo_usuario}}](INPUTS.md#inputs-user-story),
**eu quero** [{{funcionalidade}}](INPUTS.md#inputs-user-story)
**para que** [{{beneficio_razao}}](INPUTS.md#inputs-user-story).

### Contexto adicional

[{{contexto_adicional}}](INPUTS.md#inputs-user-story)

---

## 3. Conversation (Conversação) - Notas de Colaboração

> **Documentação**: [DOCUMENTACAO/01-metodologia-3cs.md](DOCUMENTACAO/01-metodologia-3cs.md)

### Discussões com Product Owner

[{{discussoes_product_owner}}](INPUTS.md#inputs-user-story)

### Considerações Técnicas

[{{consideracoes_tecnicas}}](INPUTS.md#inputs-user-story)

### Esclarecimentos de Stakeholders

[{{esclarecimentos_stakeholders}}](INPUTS.md#inputs-user-story)

---

## 4. Confirmation (Confirmação) - Critérios de Aceitação (BDD)

> **Documentação**: [DOCUMENTACAO/03-bdd-given-when-then.md](DOCUMENTACAO/03-bdd-given-when-then.md)

### Critério 1: [{{criterio_1_titulo}}](INPUTS.md#inputs-user-story)

- **Given** (Dado): [{{criterio_1_given}}](INPUTS.md#inputs-user-story)
- **When** (Quando): [{{criterio_1_when}}](INPUTS.md#inputs-user-story)
- **Then** (Então):
  - [{{criterio_1_then_1}}](INPUTS.md#inputs-user-story)
  - [{{criterio_1_then_2}}](INPUTS.md#inputs-user-story)
  - [{{criterio_1_then_3}}](INPUTS.md#inputs-user-story)

### Critério 2: [{{criterio_2_titulo}}](INPUTS.md#inputs-user-story)

- **Given** (Dado): [{{criterio_2_given}}](INPUTS.md#inputs-user-story)
- **When** (Quando): [{{criterio_2_when}}](INPUTS.md#inputs-user-story)
- **Then** (Então):
  - [{{criterio_2_then_1}}](INPUTS.md#inputs-user-story)
  - [{{criterio_2_then_2}}](INPUTS.md#inputs-user-story)
  - [{{criterio_2_then_3}}](INPUTS.md#inputs-user-story)

### Critério 3: [{{criterio_3_titulo}}](INPUTS.md#inputs-user-story) *(opcional)*

- **Given** (Dado): [{{criterio_3_given}}](INPUTS.md#inputs-user-story)
- **When** (Quando): [{{criterio_3_when}}](INPUTS.md#inputs-user-story)
- **Then** (Então):
  - [{{criterio_3_then_1}}](INPUTS.md#inputs-user-story)
  - [{{criterio_3_then_2}}](INPUTS.md#inputs-user-story)
  - [{{criterio_3_then_3}}](INPUTS.md#inputs-user-story)

---

## 5. Estimativa (Poker Planning)

> **Documentação**: [DOCUMENTACAO/01-metodologia-3cs.md](DOCUMENTACAO/01-metodologia-3cs.md)

- **Story Points**: [{{story_points}}](INPUTS.md#inputs-user-story) pontos
- **Escala**: Fibonacci (1, 2, 3, 5, 8, 13, 21...)
- **Raciocínio da estimativa**: [{{raciocinio_estimativa}}](INPUTS.md#inputs-user-story)
- **Complexidade**: [{{complexidade}}](INPUTS.md#inputs-user-story) (Baixa / Média / Alta)
- **Incerteza**: [{{incerteza}}](INPUTS.md#inputs-user-story) (Baixa / Média / Alta)
- **Esforço estimado**: [{{esforco_estimado}}](INPUTS.md#inputs-user-story) horas

### Configuração de Poker Planning

- **Relação pontos-sprint**: [{{pontos_por_sprint}}](INPUTS.md#inputs-user-story) pontos = 1 sprint de [{{duracao_sprint}}](INPUTS.md#inputs-user-story) semanas
- **Breakdown necessário?**: [{{necessita_breakdown}}](INPUTS.md#inputs-user-story) (Sim / Não)

---

## 6. Definition of Done (Definição de Pronto)

> **Documentação**: [DOCUMENTACAO/04-definition-of-done.md](DOCUMENTACAO/04-definition-of-done.md)

Checklist para considerar esta user story como "pronta":

- [ ] [{{dod_item_1}}](INPUTS.md#inputs-user-story)
- [ ] [{{dod_item_2}}](INPUTS.md#inputs-user-story)
- [ ] [{{dod_item_3}}](INPUTS.md#inputs-user-story)
- [ ] [{{dod_item_4}}](INPUTS.md#inputs-user-story)
- [ ] [{{dod_item_5}}](INPUTS.md#inputs-user-story)
- [ ] [{{dod_item_6}}](INPUTS.md#inputs-user-story)

---

## 7. Dependências

- **Depende de**: [{{depende_de}}](INPUTS.md#inputs-user-story)
- **Bloqueia**: [{{bloqueia}}](INPUTS.md#inputs-user-story)
- **Relaciona-se com**: [{{relaciona_se_com}}](INPUTS.md#inputs-user-story)

---

## 8. Notas Adicionais

### Wireframes / Designs

[{{wireframes_designs}}](INPUTS.md#inputs-user-story)

### Considerações de UX

[{{consideracoes_ux}}](INPUTS.md#inputs-user-story)

### Restrições Técnicas

[{{restricoes_tecnicas}}](INPUTS.md#inputs-user-story)

### Observações

[{{observacoes}}](INPUTS.md#inputs-user-story)

---

## 9. Histórico de Mudanças

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| [{{versao}}](INPUTS.md#inputs-user-story) | [{{data_criacao}}](INPUTS.md#inputs-user-story) | [{{autor}}](INPUTS.md#inputs-user-story) | Criação inicial |

---

## 10. Aprovações

- **Product Owner**: [{{product_owner}}](INPUTS.md#inputs-user-story)
- **Scrum Master**: [{{scrum_master}}](INPUTS.md#inputs-user-story)
- **Development Team**: [{{development_team}}](INPUTS.md#inputs-user-story)
