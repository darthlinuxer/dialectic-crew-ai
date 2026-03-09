# Visão Geral - Épicos

## O que são Épicos?

Épicos são **grandes funcionalidades ou capacidades** que são muito extensas para serem completadas em um único sprint. Representam conjuntos de user stories relacionadas que, juntas, entregam um valor de negócio significativo.

### Hierarquia no Scrum/Agile

```
Iniciativa Estratégica
    ↓
ÉPICO (este nível)
    ↓
User Stories (trabalho de 1-2 sprints)
    ↓
Tasks (trabalho de horas/dias)
```

## Características de um Épico

### Tamanho e Escopo
- **Grande demais para um sprint**: Tipicamente 3-10 sprints
- **Múltiplas user stories**: Geralmente 5-20 stories
- **Story points**: Soma > 20-50 pontos (dependendo do threshold)
- **Entrega iterativa**: Pode ser entregue em partes ao longo do tempo

### Formato de Épico

Épicos também seguem o formato de user story:

**Como** [tipo de usuário],
**eu quero** [funcionalidade em alto nível]
**para que** [benefício significativo].

**Exemplo**:
> Como **cliente da loja online**,
> eu quero **um sistema completo de pagamento multi-método**
> para que **eu possa pagar minhas compras com flexibilidade e segurança**.

Este épico seria quebrado em stories como: integração com cartão de crédito, PIX, boleto, carteira digital, etc.

## Quando Criar um Épico?

### ✅ Crie um épico quando:
- A funcionalidade é muito grande para 1-2 sprints
- Há múltiplas user stories relacionadas
- Representa uma capacidade significativa do sistema
- Tem valor de negócio claro mas precisa ser detalhado
- Pode ser quebrado em entregas independentes

### ❌ Não crie um épico se:
- Pode ser completado em 1-2 sprints → é uma user story grande
- Não tem coesão entre as partes → podem ser épicos separados
- É apenas uma lista de tarefas → organize em stories
- Não entrega valor de negócio claro → refine o escopo

## Ciclo de Vida de um Épico

### 1. Criação e Refinamento Inicial
- Identificado a partir de iniciativa ou necessidade de negócio
- Descrito em alto nível com formato de user story
- Critérios de aceitação de alto nível definidos
- Estimativa inicial grosseira (t-shirt sizing: S, M, L, XL)

### 2. Análise e Breakdown
- Product Owner e equipe analisam em detalhe
- Quebra em user stories menores e independentes
- Identificação de dependências técnicas
- Refinamento de critérios de aceitação

### 3. Priorização no Backlog
- Épico priorizado em relação a outros épicos
- Stories dentro do épico priorizadas
- Decisão de quando começar (roadmap)

### 4. Desenvolvimento Iterativo
- Stories são implementadas em sprints sucessivos
- Entregas incrementais de partes do épico
- Aprendizado contínuo e ajustes
- Possibilidade de cancelar épico se não agregar valor

### 5. Conclusão
- Todas as stories do épico completadas
- Critérios de aceitação validados
- Valor de negócio entregue e medido
- Épico marcado como "Done"

## Quebrando Épicos em User Stories

### Estratégias de Breakdown

1. **Por Fluxo de Usuário** (User Workflow)
   - Epic: "Sistema de Checkout"
   - Story 1: Selecionar itens no carrinho
   - Story 2: Aplicar cupom de desconto
   - Story 3: Escolher método de pagamento
   - Story 4: Confirmar pedido

2. **Por CRUD** (Create, Read, Update, Delete)
   - Epic: "Gerenciamento de Produtos"
   - Story 1: Criar novo produto
   - Story 2: Listar produtos
   - Story 3: Editar produto existente
   - Story 4: Deletar produto

3. **Por Regra de Negócio**
   - Epic: "Cálculo de Frete"
   - Story 1: Cálculo básico por peso e distância
   - Story 2: Aplicar desconto por volume
   - Story 3: Frete grátis acima de valor X
   - Story 4: Opções de entrega expressa

4. **Por Complexidade Técnica**
   - Epic: "Integração com Sistema Legado"
   - Story 1: Criar API de conexão básica
   - Story 2: Sincronizar dados de clientes
   - Story 3: Sincronizar pedidos
   - Story 4: Tratamento de erros e retry

5. **Por Personas/Tipos de Usuário**
   - Epic: "Dashboard de Relatórios"
   - Story 1: Dashboard para vendedores
   - Story 2: Dashboard para gerentes
   - Story 3: Dashboard para executivos

### Princípios do Breakdown

- **Independência**: Stories devem ser o mais independentes possível
- **Valor**: Cada story deve entregar valor testável
- **Testável**: Critérios de aceitação claros
- **Estimável**: Pequena o suficiente para estimar com precisão
- **Small**: Cabe em 1 sprint (tipicamente 1-5 story points)

## Estimando Épicos

### Estimativa Inicial (T-Shirt Sizing)
- **S (Small)**: 5-13 story points (~1-2 sprints)
- **M (Medium)**: 13-21 story points (~2-4 sprints)
- **L (Large)**: 21-40 story points (~4-8 sprints)
- **XL (Extra Large)**: 40+ story points (~8+ sprints)

### Refinamento da Estimativa
1. Quebrar épico em stories
2. Estimar cada story com poker planning
3. Somar story points das stories
4. Total = estimativa do épico

### Cone de Incerteza
- Início: ±50-75% de incerteza
- Após análise: ±25-35% de incerteza
- Após breakdown: ±10-15% de incerteza

## Critérios de Aceitação para Épicos

### Formato BDD em Alto Nível

Épicos devem ter critérios de aceitação de alto nível usando Given-When-Then:

**Exemplo - Epic: Sistema de Notificações**

```
Critério 1: Notificações por Email
- Given: Um evento importante ocorre no sistema
- When: O usuário tem notificações por email habilitadas
- Then: Um email é enviado com detalhes do evento

Critério 2: Notificações in-app
- Given: Usuário está logado no app
- When: Uma notificação é gerada
- Then: Badge de contagem e lista de notificações são atualizados
```

Estes serão detalhados nas user stories individuais.

## Gerenciando Dependências

### Tipos de Dependências

1. **Dependências Técnicas**
   - Infraestrutura deve existir antes
   - APIs devem estar disponíveis
   - Bibliotecas/frameworks necessários

2. **Dependências de Conhecimento**
   - Time precisa aprender tecnologia
   - Spike/POC necessário primeiro

3. **Dependências de Negócio**
   - Aprovações regulatórias
   - Decisões de stakeholders
   - Processos de negócio

4. **Dependências entre Épicos**
   - Épico A deve completar antes de Épico B
   - Funcionalidades compartilhadas

### Visualizando Dependências

```
[Épico A] ──depends on──> [Épico B]
    ↓                          ↓
[Story A1]              [Story B1]
[Story A2]              [Story B2]
```

## Métricas e Acompanhamento

### Métricas de Progresso
- **% Stories Completadas**: Quantas stories do épico foram entregues?
- **Story Points Completados**: Pontos entregues vs. total
- **Sprints Consumidos**: Quantos sprints foram necessários?
- **Velocity**: Pontos por sprint neste épico

### Métricas de Qualidade
- **Bugs encontrados**: Qualidade das entregas
- **Retrabalho**: Stories refeitas ou ajustadas
- **Satisfação**: Feedback de stakeholders/usuários

## Boas Práticas

### ✅ Faça
- Mantenha épicos focados em um objetivo de negócio claro
- Quebre em stories independentes sempre que possível
- Revise e ajuste o épico conforme aprendizado
- Use critérios de aceitação de alto nível
- Documente dependências claramente
- Comunique progresso regularmente

### ❌ Evite
- Épicos que misturam múltiplos objetivos desconexos
- Manter épicos intactos por meses sem breakdown
- Épicos muito pequenos (que na verdade são stories)
- Iniciar épico antes de ter clareza do valor
- Ignorar feedback durante a execução
- Criar dependências desnecessárias

## Ferramentas

- **Jira**: Hierarquia Epic → Story → Subtask
- **Azure DevOps**: Feature → User Story → Task
- **Trello**: Labels e boards para épicos
- **GitHub Projects**: Milestones para épicos
- **Miro/Mural**: Story mapping visual

## Relação com Outros Artefatos

- **Iniciativa** ← Épico faz parte de uma iniciativa
- **User Stories** ← Épico é quebrado em stories
- **Product Backlog** ← Épicos são priorizados no backlog
- **Roadmap** ← Épicos aparecem no roadmap de produto
- **Sprint Planning** ← Stories de épicos entram em sprints

## Referências

- **User Story Mapping** (Jeff Patton) - Técnica de organizar épicos e stories
- **Scrum Guide** - Conceito de Product Backlog items
- **SAFe** - Épicos em scaled agile
- **Mike Cohn** - "User Stories Applied" e "Agile Estimating and Planning"

---

**Lembre-se**: Um épico bem definido é grande o suficiente para ter impacto, mas pequeno o suficiente para ser gerenciável. Foque no valor de negócio e quebre em incrementos entregáveis.
