# Visão Geral - Sprint Planning

## O que é Sprint Planning?

Sprint Planning é o evento que inicia o Sprint. O Scrum Team define o trabalho a ser realizado no Sprint e cria um plano colaborativo para entregar o Increment.

**Duração máxima**: 8 horas para Sprint de 1 mês (proporcionalmente menor para sprints mais curtos)

## Participantes

- **Product Owner**: Presente e disponível para esclarecer requisitos
- **Development Team**: Todo o time participa ativamente
- **Scrum Master**: Facilita o evento e garante time-box

## Objetivos do Sprint Planning

1. **Definir Sprint Goal**: Por que este Sprint tem valor?
2. **Selecionar itens**: Quais itens do Backlog serão feitos?
3. **Criar plano**: Como o trabalho será realizado?

## Estrutura do Sprint Planning

### Parte 1: O QUE será feito? (Sprint Goal + Seleção)

**Entrada**:
- Product Backlog priorizado e refinado
- Velocity histórica do time
- Capacidade da equipe neste sprint

**Atividades**:
1. Product Owner apresenta objetivo proposto para o Sprint
2. Time discute e refina o Sprint Goal
3. Time seleciona itens do topo do Product Backlog
4. Verifica se itens atendem Definition of Ready
5. Confirma que cabe na capacidade do Sprint

**Saída**: Sprint Goal + Lista inicial de itens selecionados

### Parte 2: COMO será feito? (Planejamento técnico)

**Atividades**:
1. Time quebra User Stories em tasks (opcional)
2. Identifica dependências técnicas
3. Discute abordagem de implementação
4. Identifica riscos e impedimentos
5. Define owner ou responsáveis (se aplicável)
6. Confirma que todos entendem o trabalho

**Saída**: Sprint Backlog completo com plano de ação

## Sprint Goal

### O que é?

O Sprint Goal é o **objetivo único** do Sprint que fornece coerência e foco para o Scrum Team.

**Exemplo bom**: "Permitir que usuários façam checkout com cartão de crédito"
**Exemplo ruim**: "Completar stories US-101, US-102, US-103"

### Características de um bom Sprint Goal

- ✅ **Orientado a valor**: Foca no benefício, não nas tarefas
- ✅ **Específico**: Claro e mensurável
- ✅ **Atingível**: Realista para o Sprint
- ✅ **Coerente**: Itens do Sprint contribuem para o goal
- ✅ **Flexível**: Permite negociação de escopo

### Benefícios

- **Foco**: Time sabe o que é mais importante
- **Flexibilidade**: Pode ajustar itens se contribuírem para o goal
- **Comunicação**: Stakeholders entendem o que esperar
- **Motivação**: Time se compromete com objetivo compartilhado

## Calculando Capacidade

### Fatores que Afetam Capacidade

1. **Disponibilidade dos membros**
   - Férias planejadas
   - Licenças
   - Treinamentos
   - Reuniões fixas

2. **Dias úteis**
   - Feriados
   - Duração do sprint (dias)

3. **Trabalho não-sprint**
   - Support/hotfixes
   - Reuniões fora do time
   - Overhead administrativo

### Fórmula de Capacidade

```
Capacidade = (Membros × Horas Disponíveis × Focus Factor) / Horas por Story Point

Exemplo:
- 5 membros do time
- 80 horas por pessoa (2 semanas × 40h)
- 70% focus factor (30% em meetings, imprevistos)
- 16 horas por story point

Capacidade = (5 × 80 × 0.70) / 16 = 17.5 story points
```

### Focus Factor

Percentual de tempo dedicado a trabalho produtivo no sprint:
- **Novo time**: 60-70%
- **Time maduro**: 70-80%
- **Time muito experiente**: 80-85%

Nunca assuma 100%!

## Selecionando Itens do Backlog

### Critérios de Seleção

1. **Prioridade**: Sempre comece pelo topo do backlog
2. **Capacidade**: Some story points até atingir capacidade
3. **Definition of Ready**: Item está pronto para começar?
4. **Dependências**: Há bloqueadores externos?
5. **Skills**: Time tem conhecimento necessário?

### Quando Parar de Adicionar

- ✅ Capacity atingida (velocity histórica)
- ✅ Sprint Goal satisfeito
- ✅ Time sente confidence no commitment

### Commitment vs Forecast

- **Scrum Guide atual**: Time faz "Forecast" (previsão)
- **Anteriormente**: "Commitment" (comprometimento)
- **Na prática**: Time se compromete a fazer seu melhor para atingir o Sprint Goal

## Riscos e Mitigações

### Identificando Riscos no Planning

| Tipo de Risco | Exemplo | Mitigação |
|--------------|---------|-----------|
| **Técnico** | Tecnologia desconhecida | Spike no início do sprint |
| **Dependência** | API externa não pronta | Plano B com mock |
| **Capacidade** | Membro chave de férias | Pair programming antes |
| **Requisito** | Regra de negócio unclear | Sessão com PO no dia 1 |

## Definition of Done do Sprint

Todo Sprint deve ter uma Definition of Done clara que se aplica ao Increment:

**Exemplo**:
- [ ] Código revisado por pelo menos um dev
- [ ] Testes unitários escritos e passando (>80% coverage)
- [ ] Testes de integração passando
- [ ] Deploy realizado em ambiente de staging
- [ ] Documentação atualizada (se aplicável)
- [ ] Product Owner revisou e aprovou
- [ ] Sem bugs críticos conhecidos

## Sprint Backlog

### O que é?

Sprint Backlog = Sprint Goal + Itens selecionados + Plano

É o plano **do time, para o time**. Somente o Development Team pode alterá-lo durante o Sprint.

### Evolução Durante o Sprint

- Items podem ser re-estimados
- Tasks podem ser adicionadas
- Novas descobertas incorporadas
- **Mas**: Sprint Goal não muda (salvo exceções raras)

## Ferramentas

### Planejamento de Capacidade
- Planilhas (Excel, Google Sheets)
- Jira Capacity Planning
- Azure DevOps Capacity
- Miro/Mural para visualização

### Sprint Board
- Jira Sprint Board
- Trello
- Physical board (post-its)
- Azure DevOps Sprint Board

## Boas Práticas

### ✅ Faça
- Prepare o backlog antes (refinement)
- Use velocity histórica como guia
- Crie Sprint Goal inspirador
- Envolva todo o Development Team
- Identifique riscos e dependências
- Termine no time-box

### ❌ Evite
- Product Owner ditando o que cabe
- Over-commitment (> velocity)
- Items sem DoR no planning
- Pular discussão de COMO
- Sprint Goal vago ou inexistente
- Planning > 8h (1 month sprint)

## Outputs do Sprint Planning

### Documentação Mínima

1. **Sprint Goal**: Uma frase clara
2. **Sprint Backlog**: Lista de items comprometidos
3. **Capacity vs Commitment**: Story points capacity e committed
4. **Risks**: Principais riscos identificados
5. **Team Availability**: Quem está disponível quando

### Comunicação

Após Planning, comunique:
- Sprint Goal para stakeholders
- Capacity e commitment para Product Owner
- Riscos para management (se aplicável)

## Referências

- **Scrum Guide** (scrum.org): Definição oficial
- **Mike Cohn**: "Succeeding with Agile" - Sprint Planning
- **Roman Pichler**: Sprint Goal patterns
- **Henrik Kniberg**: "Scrum and XP from the Trenches"
