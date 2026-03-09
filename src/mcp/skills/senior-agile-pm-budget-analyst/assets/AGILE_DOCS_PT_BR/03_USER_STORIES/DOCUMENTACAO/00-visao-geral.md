# Visão Geral - User Stories

## O que são User Stories?

User Stories (Histórias de Usuário) são unidades básicas de trabalho no Scrum. Representam uma funcionalidade ou requisito descrito do ponto de vista do usuário final, focando no **valor** que será entregue.

## Propósito

- Capturar requisitos de forma simples e centrada no usuário
- Facilitar a comunicação entre Product Owner, equipe e stakeholders
- Manter o foco no valor de negócio
- Servir como base para planejamento e estimativas
- Guiar o desenvolvimento e testes

## Princípios fundamentais

1. **User-centric**: Sempre do ponto de vista do usuário
2. **Value-focused**: Claramente ligada a um benefício ou valor
3. **Negotiable**: Detalhes são discutidos durante o desenvolvimento
4. **Valuable**: Entrega valor mensurável
5. **Estimable**: Pode ser estimada pela equipe
6. **Small**: Pequena o suficiente para ser completada em um sprint
7. **Testable**: Tem critérios claros de aceitação

## Formato padrão

**Como** [tipo de usuário],
**eu quero** [funcionalidade]
**para que** [benefício/razão].

Este formato garante que toda user story responda:
- **Quem?** (tipo de usuário)
- **O quê?** (funcionalidade)
- **Por quê?** (valor/benefício)

## Metodologia dos 3 Cs

Toda user story deve seguir os 3 Cs:

1. **Card** (Cartão): Descrição escrita da história
2. **Conversation** (Conversação): Discussões para esclarecer detalhes
3. **Confirmation** (Confirmação): Critérios de aceitação

## BDD - Behavior-Driven Development

Os critérios de aceitação devem usar o formato **Given-When-Then**:

- **Given** (Dado): Contexto inicial ou pré-condição
- **When** (Quando): Ação ou evento que ocorre
- **Then** (Então): Resultado esperado

Este formato facilita:
- Clareza e entendimento compartilhado
- Automação de testes
- Validação objetiva

## INVEST - Características de boa User Story

- **I**ndependent: Independente de outras stories (quando possível)
- **N**egotiable: Flexível para discussão de detalhes
- **V**aluable: Entrega valor ao usuário/negócio
- **E**stimable: Pode ser estimada pela equipe
- **S**mall: Pequena o suficiente para um sprint
- **T**estable: Pode ser testada objetivamente

## Definition of Done

Cada user story deve ter uma checklist clara do que significa "pronto":
- Código escrito e revisado
- Testes automatizados criados e passando
- Documentação atualizada
- Deploy em ambiente de staging
- Critérios de aceitação validados
- Product Owner aprovou

## Estimativas

User stories são estimadas usando **story points** (geralmente escala Fibonacci: 1, 2, 3, 5, 8, 13...).

Story points representam:
- Complexidade
- Esforço
- Incerteza

**Não** representam tempo diretamente, mas sim esforço relativo.

## Quando quebrar uma User Story

Quebre uma user story se:
- Pontos > threshold configurado (ex: > 5 pontos)
- Não pode ser completada em um sprint
- Tem múltiplas funcionalidades independentes
- Parte do valor pode ser entregue separadamente

## Referências

- Scrum Guide (scrum.org)
- User Stories Applied - Mike Cohn
- Behavior-Driven Development (cucumber.io)
- INVEST principle - Bill Wake
