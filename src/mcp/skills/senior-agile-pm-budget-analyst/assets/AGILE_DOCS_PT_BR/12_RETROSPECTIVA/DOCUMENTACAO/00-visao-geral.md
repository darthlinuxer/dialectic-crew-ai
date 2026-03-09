# Visão Geral - Sprint Retrospective

## O que é Sprint Retrospective?

A Sprint Retrospective é uma oportunidade para o Scrum Team **inspecionar a si mesmo** e criar um plano para melhorias a serem implementadas no próximo Sprint. Acontece após a Sprint Review e antes do próximo Sprint Planning.

**Duração máxima**: 3 horas para Sprint de 1 mês (proporcionalmente menor para sprints curtos)

## Propósito

### Objetivos
1. **Refletir**: Como foi o último Sprint?
2. **Identificar**: O que funcionou? O que pode melhorar?
3. **Planejar**: Quais melhorias implementar no próximo Sprint?
4. **Comprometer**: Action items concretos

### Escopo da Inspeção
- **Pessoas**: Colaboração, comunicação
- **Processos**: Como trabalhamos, cerimônias
- **Ferramentas**: Tech stack, automação, plataformas
- **Definition of Done**: Está adequada?
- **Relações**: Com stakeholders, outros times

## Participantes

### Obrigatórios
- **Scrum Master**: Facilita
- **Development Team**: Participação ativa
- **Product Owner**: Participação esperada

### Opcional/Convidados
- Stakeholders (se o time concordar)
- Outros times (para tópicos cross-team)

## Estrutura Básica

### 1. Set the Stage (5-10 min)
- Preparar ambiente psicologicamente seguro
- Relembrar objetivo da retro
- Check-in: Como cada um está se sentindo?

### 2. Gather Data (15-30 min)
- Coletar fatos sobre o sprint
- Métricas: Velocity, completion rate, bugs
- Eventos significativos: O que aconteceu?

### 3. Generate Insights (30-45 min)
- **O que funcionou bem?** ✅
- **O que pode melhorar?** 📈
- **O que vamos tentar no próximo sprint?** 🎯

### 4. Decide What to Do (15-30 min)
- Priorizar melhorias
- Criar action items específicos
- Definir owners e prazos

### 5. Close (5-10 min)
- Recap de decisões
- Apreciações
- Feedback sobre a retro

## Formatos e Técnicas

### 1. Start/Stop/Continue

**Categorias**:
- **Start**: O que devemos começar a fazer?
- **Stop**: O que devemos parar de fazer?
- **Continue**: O que está funcionando e deve continuar?

### 2. Glad/Sad/Mad

**Emoções sobre o sprint**:
- **Glad** (Feliz): O que nos deixou contentes?
- **Sad** (Triste): O que nos entristeceu?
- **Mad** (Irritado): O que nos frustrou?

### 3. 4Ls

- **Liked**: O que gostamos?
- **Learned**: O que aprendemos?
- **Lacked**: O que faltou?
- **Longed for**: O que desejamos?

### 4. Sailboat/Speedboat

**Metáfora**:
- **Vento** (Wind): O que nos impulsiona?
- **Âncora** (Anchor): O que nos segura?
- **Rochas** (Rocks): Riscos à frente
- **Ilha** (Island): Nosso objetivo

### 5. Timeline

Criar timeline visual do sprint:
- Eventos importantes marcados
- Emocional highs e lows
- Discussão de padrões

### 6. 5 Whys

Para problemas específicos:
- "Por que isso aconteceu?"
- "Por que?" (5 vezes)
- Chegar à causa raiz

## Action Items

### Características de Bons Action Items

✅ **SMART**:
- **Specific**: Claro e específico
- **Measurable**: Mensurável
- **Achievable**: Atingível em 1 sprint
- **Relevant**: Impacta o problema
- **Time-bound**: Prazo definido

### Exemplos

❌ **Ruim**: "Melhorar comunicação"
✅ **Bom**: "Daily standup às 9h diariamente, com max 15min" (Owner: SM, Prazo: próximo sprint)

❌ **Ruim**: "Escrever mais testes"
✅ **Bom**: "Coverage >80% para novas features antes de PR" (Owner: Tech Lead + time, Prazo: início próximo sprint)

### Quantidade
- **Ideal**: 1-3 action items por retrospective
- **Foco**: Qualidade > Quantidade
- **Follow-up**: Revisar action items anteriores

## Princípios da Retrospectiva

### 1. Prime Directive (Norma Kerth)

> "Independentemente do que descobrimos, entendemos e acreditamos verdadeiramente que todos fizeram o melhor trabalho possível, dado o que sabiam na época, suas habilidades e capacidades, os recursos disponíveis e a situação."

**Propósito**: Criar segurança psicológica, evitar blame game.

### 2. Segurança Psicológica

Time deve sentir-se seguro para:
- Admitir erros
- Compartilhar vulnerabilidades
- Desafiar status quo
- Propor ideias não convencionais

### 3. Foco em Melhoria Contínua

- Kaizen: Pequenas melhorias constantes
- Não buscar perfeição, buscar progresso
- Experimentação: Testar ideias

### 4. Toda Voz é Ouvida

- Evitar dominação de vozes altas
- Técnicas silenciosas (post-its, votos)
- Facilitador garante participação equilibrada

## Métricas para Discussão

### Dados Objetivos
- **Velocity**: Comparada com média histórica
- **Completion Rate**: % de stories done
- **Bugs**: Quantos bugs criados/resolvidos
- **Cycle Time**: Tempo de story em progresso

### Dados Subjetivos
- **Satisfação do time**: Escala 1-5
- **Confiança em DoD**: Stories realmente Done?
- **Colaboração**: Time trabalhou bem junto?

### Eventos
- **Blockers**: Quantos? Duração?
- **Scope changes**: Mid-sprint additions
- **Interrupções**: Hotfixes, support

## Antipadrões

### 1. "Same Old, Same Old"
**Problema**: Retro repetitiva, sem energia
**Solução**: Variar formatos, mudar facilitador

### 2. "No Action Items"
**Problema**: Discussão sem comprometimento
**Solução**: Sempre sair com pelo menos 1 action item

### 3. "Blame Game"
**Problema**: Apontar dedos, defensividade
**Solução**: Prime Directive, foco em sistema não pessoas

### 4. "Too Many Action Items"
**Problema**: 10+ itens, nada é feito
**Solução**: Máx 3 itens, priorizados por impacto

### 5. "Management Present"
**Problema**: Time não se sente seguro
**Solução**: Retro só para o Scrum Team (geralmente)

### 6. "Skipping Retrospective"
**Problema**: "Sem tempo", "nada a melhorar"
**Solução**: Retro é obrigatória no Scrum, sempre há aprendizado

## Follow-up de Action Items

### Rastreamento

| Action Item | Owner | Status | Sprint | Notes |
|-------------|-------|--------|--------|-------|
| Daily às 9h fixo | SM | ✅ Done | Sprint 23 | Funcionou bem |
| Code review <24h | Tech Lead | ⚠️ In Progress | Sprint 23 | Ainda ajustando |
| Pair programming 2x/semana | Time | ❌ Not Started | Sprint 22 | Faltou tempo |

### Revisão na Próxima Retro

- **Check-in**: Action items anteriores foram feitos?
- **Impacto**: Melhorias fizeram diferença?
- **Ajuste**: Continuar, ajustar, ou parar?

## Retrospectiva de Retrospectivas

A cada 3-4 sprints, fazer **meta-retro**:

**Perguntas**:
- O formato de retro está funcionando?
- Todos se sentem confortáveis participando?
- Action items estão sendo implementados?
- Estamos melhorando como time?

## Ferramentas

### Presencial
- **Post-its e whiteboard**: Clássico
- **Dots para votar**: Priorização visual
- **Timers**: Manter time-box

### Remoto
- **Miro/Mural**: Templates de retro
- **MetroRetro**: Especializado em retros
- **FunRetro**: Simples e gratuito
- **Trello**: Boards de retro
- **Google Jamboard**: Quadro virtual

### Async
- **Forms (Google, Typeform)**: Coleta antes da retro
- **Slack polls**: Quick check-ins

## Variações de Retrospectiva

### 1. Retro Temática
Foco em um aspecto específico:
- Technical practices retro
- Communication retro
- Quality retro

### 2. Retro de Release
Após release major, mais longa (3-4h):
- Múltiplos sprints revisados
- Lições maiores
- Celebração de conquistas

### 3. Futurespective
Imaginário de um sprint futuro perfeito:
- "No sprint perfeito, o que estaríamos fazendo?"
- Trabalhar backwards para action items

### 4. Appreciations Retro
Foco em reconhecimento:
- O que cada pessoa contribuiu bem?
- Builds team morale

## Boas Práticas

### ✅ Faça
- Varie formatos regularmente
- Crie segurança psicológica
- Foque em 1-3 action items
- Revise action items anteriores
- Time-box each section
- Celebre wins e aprendizados
- Documente decisões

### ❌ Evite
- Pular retrospectiva
- Mesmo formato sempre
- Sem action items concretos
- Blame individuals
- Management intrusive presence
- Action items sem owner
- Não revisar action items

## Evoluindo Como Time

### Indicadores de Maturidade

**Time Novato**:
- Foca em problemas de processo
- Action items sobre cerimônias
- Discussões superficiais

**Time Experiente**:
- Foca em colaboração e qualidade
- Experimenta práticas novas
- Discussões profundas sobre efetividade

**Time de Alta Performance**:
- Foca em impacto e valor
- Auto-organização forte
- Melhoria contínua embedded

## Referências

- **Scrum Guide** (scrum.org): Definição oficial
- **Esther Derby & Diana Larsen**: "Agile Retrospectives: Making Good Teams Great"
- **Norman Kerth**: Project retrospectives (origem do Prime Directive)
- **Retromat**: retromat.org - 100+ activities
- **Fun Retrospectives**: funretrospectives.com
