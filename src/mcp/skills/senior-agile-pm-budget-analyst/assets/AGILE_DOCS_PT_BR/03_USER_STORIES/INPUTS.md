# INPUTS — User Story (História de Usuário)

Este arquivo mapeia todas as entradas necessárias para preencher o `TEMPLATE.md`.

| Chave | Descrição | Formato/Exemplo genérico | Obrigatório | Fonte esperada |
|------|-----------|--------------------------|-------------|----------------|
| user_story_id | Identificador único da user story | Texto curto (ex: US-001, US-042) | Sim | Backlog / Ferramenta de gestão |
| titulo | Título curto e descritivo da story | Texto curto (ex: "Login com email e senha") | Sim | Product Owner / Equipe |
| epico_id | ID do épico relacionado | Texto curto (ex: EP-01) | Sim | Backlog / Hierarquia |
| epico_nome | Nome do épico relacionado | Texto curto | Sim | Backlog / Hierarquia |
| iniciativa_id | ID da iniciativa relacionada | Texto curto (ex: INIT-01) | Não | Backlog / Hierarquia |
| iniciativa_nome | Nome da iniciativa relacionada | Texto curto | Não | Backlog / Hierarquia |
| sprint_numero | Número do sprint planejado | Número ou texto (ex: Sprint 5) | Não | Sprint Planning |
| prioridade | Prioridade da user story | Alta / Média / Baixa | Sim | Product Owner |
| tipo_usuario | Tipo de usuário (papel/persona) | Texto curto (ex: "cliente cadastrado", "administrador") | Sim | Product Owner / UX |
| funcionalidade | O que o usuário quer fazer | Texto curto (ex: "recuperar minha senha esquecida") | Sim | Product Owner / Requisitos |
| beneficio_razao | Por que o usuário quer isso (valor) | Texto curto (ex: "poder acessar minha conta novamente") | Sim | Product Owner / Requisitos |
| contexto_adicional | Contexto extra relevante | Parágrafo curto | Não | Product Owner / Stakeholders |
| discussoes_product_owner | Notas de discussões com PO | Texto médio / lista de pontos | Não | Reuniões / Sprint Planning |
| consideracoes_tecnicas | Considerações técnicas da equipe | Texto médio / lista de pontos | Não | Development Team |
| esclarecimentos_stakeholders | Esclarecimentos de outros stakeholders | Texto médio / lista de pontos | Não | Stakeholders / Reuniões |
| criterio_1_titulo | Título do primeiro critério de aceitação | Texto curto (ex: "Login bem-sucedido") | Sim | Product Owner / Equipe |
| criterio_1_given | Contexto inicial do critério 1 (Given) | Texto curto | Sim | Product Owner / Equipe |
| criterio_1_when | Ação ou evento do critério 1 (When) | Texto curto | Sim | Product Owner / Equipe |
| criterio_1_then_1 | Primeiro resultado esperado (Then) | Texto curto | Sim | Product Owner / Equipe |
| criterio_1_then_2 | Segundo resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_1_then_3 | Terceiro resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_2_titulo | Título do segundo critério de aceitação | Texto curto | Sim | Product Owner / Equipe |
| criterio_2_given | Contexto inicial do critério 2 (Given) | Texto curto | Sim | Product Owner / Equipe |
| criterio_2_when | Ação ou evento do critério 2 (When) | Texto curto | Sim | Product Owner / Equipe |
| criterio_2_then_1 | Primeiro resultado esperado (Then) | Texto curto | Sim | Product Owner / Equipe |
| criterio_2_then_2 | Segundo resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_2_then_3 | Terceiro resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_3_titulo | Título do terceiro critério de aceitação | Texto curto | Não | Product Owner / Equipe |
| criterio_3_given | Contexto inicial do critério 3 (Given) | Texto curto | Não | Product Owner / Equipe |
| criterio_3_when | Ação ou evento do critério 3 (When) | Texto curto | Não | Product Owner / Equipe |
| criterio_3_then_1 | Primeiro resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_3_then_2 | Segundo resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| criterio_3_then_3 | Terceiro resultado esperado (Then) | Texto curto | Não | Product Owner / Equipe |
| story_points | Pontos de story (Fibonacci) | Número (1, 2, 3, 5, 8, 13...) | Sim | Poker Planning / Equipe |
| raciocinio_estimativa | Explicação da estimativa | Texto médio | Sim | Poker Planning / Equipe |
| complexidade | Nível de complexidade | Baixa / Média / Alta | Não | Poker Planning / Equipe |
| incerteza | Nível de incerteza | Baixa / Média / Alta | Não | Poker Planning / Equipe |
| esforco_estimado | Esforço em horas | Número (ex: 16 horas) | Não | Poker Planning / Equipe |
| pontos_por_sprint | Quantos pontos equivalem a 1 sprint | Número (ex: 5) | Sim | Configuração do projeto |
| duracao_sprint | Duração do sprint em semanas | Número (ex: 2) | Sim | Configuração do projeto |
| necessita_breakdown | Se a story precisa ser quebrada | Sim / Não | Sim | Poker Planning / Equipe |
| dod_item_1 | Primeiro item do Definition of Done | Texto curto (ex: "Código revisado") | Sim | Equipe / Padrões |
| dod_item_2 | Segundo item do DoD | Texto curto (ex: "Testes unitários passaram") | Sim | Equipe / Padrões |
| dod_item_3 | Terceiro item do DoD | Texto curto (ex: "Deploy em staging") | Sim | Equipe / Padrões |
| dod_item_4 | Quarto item do DoD | Texto curto | Não | Equipe / Padrões |
| dod_item_5 | Quinto item do DoD | Texto curto | Não | Equipe / Padrões |
| dod_item_6 | Sexto item do DoD | Texto curto | Não | Equipe / Padrões |
| depende_de | User stories das quais esta depende | Lista de IDs (ex: US-001, US-003) | Não | Análise de dependências |
| bloqueia | User stories bloqueadas por esta | Lista de IDs | Não | Análise de dependências |
| relaciona_se_com | User stories relacionadas | Lista de IDs | Não | Análise de dependências |
| wireframes_designs | Links ou descrição de wireframes | Texto / Links | Não | UX / Design |
| consideracoes_ux | Considerações de experiência do usuário | Texto médio | Não | UX / Design |
| restricoes_tecnicas | Restrições técnicas específicas | Texto médio | Não | Development Team |
| observacoes | Observações adicionais | Texto médio | Não | Qualquer membro |
| versao | Versão do documento | Texto (ex: 1.0, 1.1) | Sim | Controle de versão |
| data_criacao | Data de criação da story | Data (ex: 2026-02-05) | Sim | Sistema / Autor |
| autor | Quem criou a story | Nome (ex: "Product Owner") | Sim | Sistema / Autor |
| product_owner | Nome do Product Owner | Nome | Sim | Equipe Scrum |
| scrum_master | Nome do Scrum Master | Nome | Sim | Equipe Scrum |
| development_team | Nomes do Development Team | Lista de nomes | Não | Equipe Scrum |

## Exemplo de valores preenchidos

```markdown
| Chave | Valor Exemplo |
|------|---------------|
| user_story_id | US-042 |
| titulo | Recuperação de senha por email |
| tipo_usuario | usuário cadastrado |
| funcionalidade | recuperar minha senha através de um link enviado por email |
| beneficio_razao | eu possa acessar minha conta caso esqueça a senha |
| criterio_1_titulo | Envio de email de recuperação |
| criterio_1_given | O usuário está na página de login e clica em "Esqueci minha senha" |
| criterio_1_when | Ele insere um email válido cadastrado no sistema |
| criterio_1_then_1 | Um email com link de recuperação é enviado em até 5 segundos |
| criterio_1_then_2 | A mensagem "Email enviado com sucesso" é exibida |
| criterio_1_then_3 | O link expira em 24 horas |
| story_points | 3 |
| raciocinio_estimativa | Baixa complexidade, funcionalidade bem conhecida, requer integração com serviço de email |
| dod_item_1 | Código revisado por pelo menos um desenvolvedor |
| dod_item_2 | Testes unitários e de integração passaram |
| dod_item_3 | Deploy realizado em ambiente de staging |
```
