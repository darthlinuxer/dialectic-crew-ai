# INPUTS — Orçamento do Projeto

Este arquivo mapeia todas as entradas necessárias para preencher o `TEMPLATE.md`.

| Chave | Descrição | Formato/Exemplo | Obrigatório | Fonte esperada |
|------|-----------|-----------------|-------------|----------------|
| nome_projeto | Nome do projeto | Texto | Sim | Iniciação |
| versao_orcamento | Versão do orçamento | Texto (ex: 1.0) | Sim | Controle |
| data_criacao | Data de criação | Data (YYYY-MM-DD) | Sim | Sistema |
| responsavel | Responsável pelo orçamento | Nome | Sim | PMO |
| moeda | Moeda usada | Texto (ex: BRL, USD) | Sim | Financeiro |
| pontos_por_sprint | Pontos por sprint | Número (ex: 5) | Sim | Configuração |
| duracao_sprint | Duração do sprint | Número de semanas | Sim | Configuração |
| horas_por_sprint | Horas por sprint | Número (ex: 80) | Sim | Configuração |
| horas_por_ponto | Horas por ponto | Número calculado | Sim | Cálculo |
| funcao_1 | Nome da função 1 | Texto (ex: Dev Senior) | Sim | RH/Equipe |
| qtd_1 | Quantidade função 1 | Número | Sim | RH/Equipe |
| taxa_horaria_1 | Taxa horária função 1 | Número | Sim | Financeiro |
| taxa_diaria_1 | Taxa diária função 1 | Número | Não | Financeiro |
| dedicacao_1 | Dedicação função 1 | Percentual | Não | Planejamento |
| funcao_2 | Nome da função 2 | Texto | Não | RH/Equipe |
| qtd_2 | Quantidade função 2 | Número | Não | RH/Equipe |
| taxa_horaria_2 | Taxa horária função 2 | Número | Não | Financeiro |
| taxa_media_ponderada | Taxa média ponderada | Número calculado | Sim | Cálculo |
| total_story_points | Total de story points | Número | Sim | Poker Planning |
| total_horas_estimadas | Total de horas | Número calculado | Sim | Cálculo |
| custo_base_recursos | Custo base de recursos | Número calculado | Sim | Cálculo |
| percentual_overhead | Percentual de overhead | Número (ex: 20) | Sim | Padrão/PMO |
| custo_overhead | Custo de overhead | Número calculado | Sim | Cálculo |
| custos_fixos_total | Total de custos fixos | Número | Sim | Levantamento |
| percentual_contingencia | Percentual de contingência | Número (ex: 15) | Sim | Padrão/PMO |
| custo_contingencia | Custo de contingência | Número calculado | Sim | Cálculo |
| custo_total_projeto | Custo total do projeto | Número calculado | Sim | Cálculo |
| iniciativa_1_nome | Nome da iniciativa 1 | Texto | Sim | Backlog |
| iniciativa_1_id | ID da iniciativa 1 | Texto | Sim | Backlog |
| iniciativa_1_pontos | Pontos da iniciativa 1 | Número | Sim | Estimativas |
| iniciativa_1_horas | Horas da iniciativa 1 | Número calculado | Sim | Cálculo |
| iniciativa_1_custo_base | Custo base iniciativa 1 | Número calculado | Sim | Cálculo |
| iniciativa_1_custo_total | Custo total iniciativa 1 | Número calculado | Sim | Cálculo |
| iniciativa_1_percentual | Percentual do orçamento | Número calculado | Sim | Cálculo |
| sprint_1_pontos | Pontos do sprint 1 | Número | Não | Sprint Planning |
| sprint_1_horas | Horas do sprint 1 | Número calculado | Não | Cálculo |
| sprint_1_custo_base | Custo base sprint 1 | Número calculado | Não | Cálculo |
| sprint_1_custo_total | Custo total sprint 1 | Número calculado | Não | Cálculo |
| sprint_1_periodo | Período do sprint 1 | Texto/Data | Não | Cronograma |
| total_sprints | Total de sprints | Número | Sim | Planejamento |
| custo_fixo_1_item | Item de custo fixo 1 | Texto | Não | Levantamento |
| custo_fixo_1_descricao | Descrição custo fixo 1 | Texto | Não | Levantamento |
| custo_fixo_1_valor | Valor custo fixo 1 | Número | Não | Levantamento |
| custo_fixo_1_frequencia | Frequência custo fixo 1 | Texto | Não | Levantamento |
| premissa_1 | Premissa 1 | Texto | Não | Análise |
| premissa_2 | Premissa 2 | Texto | Não | Análise |
| restricao_1 | Restrição 1 | Texto | Não | Análise |
| cenario_otimista_variacao | Variação otimista | Texto (ex: -15%) | Não | Análise |
| cenario_otimista_pontos | Pontos cenário otimista | Número | Não | Cálculo |
| cenario_otimista_custo | Custo cenário otimista | Número | Não | Cálculo |
| cenario_pessimista_variacao | Variação pessimista | Texto (ex: +25%) | Não | Análise |
| cenario_pessimista_pontos | Pontos cenário pessimista | Número | Não | Cálculo |
| cenario_pessimista_custo | Custo cenário pessimista | Número | Não | Cálculo |
| product_owner | Nome do Product Owner | Nome | Sim | Equipe |
| sponsor | Nome do Sponsor | Nome | Sim | Stakeholders |
| cfo | Nome do CFO | Nome | Não | Stakeholders |
| data_aprovacao_po | Data aprovação PO | Data | Não | Aprovação |
| data_aprovacao_sponsor | Data aprovação Sponsor | Data | Não | Aprovação |
| data_aprovacao_cfo | Data aprovação CFO | Data | Não | Aprovação |

## Fórmulas de cálculo

```
horas_por_ponto = horas_por_sprint / pontos_por_sprint

total_horas_estimadas = total_story_points × horas_por_ponto

custo_base_recursos = total_horas_estimadas × taxa_media_ponderada

custo_overhead = custo_base_recursos × (percentual_overhead / 100)

subtotal = custo_base_recursos + custo_overhead + custos_fixos_total

custo_contingencia = subtotal × (percentual_contingencia / 100)

custo_total_projeto = subtotal + custo_contingencia
```

## Exemplo de valores

```
pontos_por_sprint: 5
duracao_sprint: 2
horas_por_sprint: 80
horas_por_ponto: 16 (calculado: 80/5)

funcao_1: Desenvolvedor Senior
qtd_1: 3
taxa_horaria_1: 150.00 BRL

taxa_media_ponderada: 135.00 BRL/hora

total_story_points: 89
total_horas_estimadas: 1424 (calculado: 89 × 16)

custo_base_recursos: 192240.00 (calculado: 1424 × 135)
percentual_overhead: 20%
custo_overhead: 38448.00 (calculado: 192240 × 0.20)
custos_fixos_total: 25000.00
percentual_contingencia: 15%
custo_contingencia: 38353.20 (calculado: (192240+38448+25000) × 0.15)

custo_total_projeto: 294041.20 BRL
```
