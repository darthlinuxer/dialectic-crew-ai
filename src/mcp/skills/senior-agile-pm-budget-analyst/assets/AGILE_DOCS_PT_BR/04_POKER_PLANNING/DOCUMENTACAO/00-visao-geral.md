# Visão Geral - Poker Planning

## O que é Poker Planning?

Poker Planning (ou Planning Poker) é uma técnica colaborativa de estimativa baseada em consenso, onde a equipe usa cartas numeradas (tipicamente seguindo a sequência Fibonacci) para estimar o esforço relativo de user stories.

## Por que usar Poker Planning?

### Benefícios
- **Estimativas mais precisas**: Sabedoria coletiva supera estimativas individuais
- **Engajamento da equipe**: Todos participam ativamente
- **Discussão de complexidade**: Divergências revelam riscos e mal-entendidos
- **Consenso**: Equipe se compromete com as estimativas
- **Rapidez**: Mais rápido que estimativas detalhadas tradicionais

## Como Funciona

### 1. Preparação
- **Facilitador**: Geralmente Scrum Master ou Product Owner
- **Participantes**: Development Team completo
- **Materiais**: Cartas de planning poker (físicas ou digitais)
- **Backlog**: User stories refinadas e prontas para estimar

### 2. Processo de Estimativa

**Passo a Passo:**

1. **Apresentação**: Product Owner apresenta user story
2. **Discussão**: Time faz perguntas para entender a story
3. **Votação**: Cada membro escolhe uma carta em segredo
4. **Revelação**: Todos revelam cartas simultaneamente
5. **Discussão de divergências**: Estimativas muito diferentes são discutidas
6. **Re-votação**: Se necessário, vota-se novamente
7. **Consenso**: Time concorda com uma estimativa final

### 3. Escala Fibonacci

**Valores típicos**: 0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ?

**Por quê Fibonacci?**
- Reflete incerteza crescente em itens maiores
- Evita falsa precisão (não há diferença real entre 7 e 8)
- Força a equipe a pensar em ordens de magnitude

**Cartas especiais:**
- **0**: Trivial, já está feito, ou sem esforço
- **?**: Sem informação suficiente para estimar
- **∞**: Muito grande, precisa ser quebrada
- **☕**: Pausa para café

## Configuração: Pontos por Sprint

### Relação Pontos-Tempo

A configuração mais importante é definir: **Quantos story points = 1 sprint?**

**Exemplo comum**: 5 pontos = 1 sprint de 2 semanas

Esta relação é usada para:
- Calcular velocity da equipe
- Planejar quantas stories cabem em um sprint
- Estimar duração total do projeto
- Calcular orçamento baseado em esforço

### Determinando a Capacidade

```
Capacity = (Team Size × Hours per Sprint × Efficiency) / Hours per Point

Exemplo:
- Time de 5 pessoas
- 80 horas por sprint (2 semanas × 40h)
- 70% de eficiência (meetings, imprevistos)
- Assumindo 16 horas por ponto

Capacity = (5 × 80 × 0.70) / 16 = 17.5 pontos/sprint
```

## Threshold: Quando Quebrar Stories

### Regra do Threshold

**Threshold** é o limite acima do qual uma story deve ser quebrada em stories menores.

**Exemplo**: Se threshold = 5 pontos
- Story de 3 pontos: OK, cabe em um sprint
- Story de 8 pontos: QUEBRAR em stories de 3 + 5 ou 2 + 3 + 3

### Por que Quebrar?

- **Risk**o: Stories grandes têm mais incerteza
- **Entrega**: Difícil completar em um sprint
- **Feedback**: Sem entregas incrementais
- **Planejamento**: Difícil de estimar com precisão
- **Blockers**: Mais chances de ser bloqueada

## Story Points vs. Horas

### O que Story Points Representam?

Story points são **medida relativa** de:
1. **Complexidade**: Quão difícil tecnicamente?
2. **Esforço**: Quanto trabalho é necessário?
3. **Incerteza**: Quão claro é o requisito?

### Não são Horas!

❌ **Errado**: "5 pontos = 40 horas"
✅ **Certo**: "Esta story é 5× mais complexa que nossa story de referência de 1 ponto"

### Calibração da Equipe

**Story de referência (1 ponto):**
- "Alterar texto de um botão" = 1 ponto
- "Adicionar novo campo em formulário" = 1 ponto

**Stories mais complexas são comparadas:**
- "Implementar validação de CPF" = 2 pontos (2× mais complexo)
- "Integração com API de pagamento" = 8 pontos (8× mais complexo)

## Estimando Stories Complexas

### T-Shirt Sizing Primeiro

Para stories/épicos muito grandes, use primeiro tamanhos de camiseta:
- **XS**: < 2 pontos
- **S**: 2-5 pontos
- **M**: 5-13 pontos
- **L**: 13-21 pontos
- **XL**: 21+ pontos (precisa quebrar!)

Depois refine para números Fibonacci.

### Técnica da Decomposição

Se story parece > 13 pontos:

1. **Liste subtasks**
2. **Estime cada subtask**
3. **Se total ainda > threshold, quebre em multiple stories**
4. **Estime cada nova story independentemente**

## Tratando Divergências

### Por que Estimativas Diferem?

- **Entendimento diferente**: Story não está clara
- **Experiência diferente**: Alguns já fizeram similar
- **Abordagem diferente**: Diferentes soluções técnicas
- **Riscos percebidos**: Alguns veem problemas que outros não

### Processo de Convergência

1. **Quem deu menor estimativa explica** (otimista)
2. **Quem deu maior estimativa explica** (pessimista)
3. **Time discute** riscos, abordagens, clarificações
4. **Re-vota**
5. **Repete até consenso** (geralmente 2-3 rodadas)

### Quando Parar?

- **Consenso alcançado**: Maioria concorda
- **Diferença pequena**: 3 vs 5 → escolher 5 (conservador)
- **Sem mais informação**: Marcar com "?" e refinar depois

## Documentando a Sessão

### O que registrar:

1. **Data e participantes**
2. **Stories estimadas** (ID, título, pontos)
3. **Raciocínio**: Por que esta estimativa?
4. **Divergências**: O que causou discussão?
5. **Stories quebradas**: Quais foram divididas?
6. **Decisões**: Premissas assumidas

### Template de Notas

```markdown
Story US-042: Recuperação de senha

Votação inicial: 2, 3, 3, 5, 8
Discussão: Desenvolvedor que votou 8 lembrou de integração com serviço de email que pode ser complexa
Votação final: 5, 5, 5, 5, 5
Estimativa: 5 pontos
Raciocínio: Inclui integração com serviço de email, validações e testes
```

## Ferramentas

### Presenciais
- **Cartas físicas**: Baralho de planning poker
- **Whiteboard**: Para notas e discussões

### Remotas
- **Planning Poker Online**: planningpokeronline.com
- **Scrum Poker**: scrumpoker.online
- **Jira**: Plugin de planning poker
- **Miro/Mural**: Templates de planning poker

## Boas Práticas

### ✅ Faça
- Estime baseado em complexidade relativa, não horas
- Envolva todo o Development Team
- Discuta divergências para aprender
- Quebre stories > threshold
- Re-estime se entendimento mudar
- Use referência de stories anteriores

### ❌ Evite
- Converter pontos em horas diretamente
- Deixar uma pessoa dominar as estimativas
- Pular discussão quando há divergência
- Estimar sob pressão de prazo
- Mudar estimativas depois de comprometidas
- Comparar velocity entre times diferentes

## Velocity e Planejamento

### Calculando Velocity

```
Velocity = Story Points Completados por Sprint

Exemplo:
Sprint 1: 18 pontos
Sprint 2: 21 pontos
Sprint 3: 19 pontos
Velocity média: (18+21+19)/3 = 19.3 pontos/sprint
```

### Previsão de Duração

```
Sprints necessários = Total Story Points / Velocity

Exemplo:
Total: 89 pontos
Velocity: 19 pontos/sprint
Duração: 89/19 = 4.7 sprints ≈ 5 sprints
```

## Referências

- **Scrum Guide**: scrum.org
- **Planning Poker**: Original technique by Mike Cohn
- **Agile Estimating and Planning** (Mike Cohn)
- **Relative Estimation**: Comparing complexity, not predicting time
