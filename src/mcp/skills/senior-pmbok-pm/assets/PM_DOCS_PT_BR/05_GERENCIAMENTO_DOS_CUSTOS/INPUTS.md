# INPUTS — Plano de Gerenciamento dos Custos

> Mapeamento das entradas necessárias para preencher o `TEMPLATE.md`.

| Chave | Descrição | Formato/Exemplo genérico | Obrigatório | Fonte esperada |
|---|---|---|---|---|
| projeto_nome | Nome do projeto | Texto livre | Sim | Sponsor/PMO |
| versao_documento | Versão do plano | `1.0` | Sim | PMO |
| data_documento | Data de emissão | `dd/mm/aaaa` | Sim | PMO |
| aprovadores | Lista de aprovadores | Lista de nomes/cargos | Sim | Sponsor/Steering |
| moeda_base | Moeda principal | `BRL` | Sim | Financeiro |
| moedas_secundarias | Moedas adicionais | Lista (`USD`, `EUR`) | Não | Financeiro |
| politica_cambio | Política de câmbio | Texto curto | Não | Financeiro |
| precisao_por_fase | Precisão esperada por fase | Tabela (fase, faixa) | Sim | PMO |
| regras_arredondamento | Regras de arredondamento | Lista de faixas | Não | Financeiro |
| tecnicas_por_tipo_custo | Técnica de estimativa por tipo | Tabela (tipo, técnica) | Sim | GP/Controller |
| criterios_uso_tecnicas | Critérios de seleção | Texto curto | Sim | GP |
| premissas_gerais | Premissas globais | Lista | Não | GP |
| categorias_custo | Categorias e subcategorias | Tabela | Sim | GP/Financeiro |
| percentuais_orcamento | Percentuais-alvo | Tabela | Não | GP |
| aprovadores_categorias | Aprovadores por categoria | Tabela | Sim | Sponsor/PMO |
| contas_controle_wbs | Contas de controle | Lista estruturada | Sim | GP |
| limites_variacao | Faixas verde/amarelo/vermelho | Tabela | Sim | GP/PMO |
| gatilhos_escalonamento | Gatilhos de escalonamento | Lista | Sim | GP |
| limites_aprovacao_mudanca | Limites por valor | Tabela | Sim | PMO |
| metodo_medicao_progresso | Método de medição | Texto/Lista | Sim | GP/PMO |
| formulas_evm | Fórmulas aplicadas | Lista | Sim | PMO |
| frequencia_evm | Periodicidade de atualização | Texto | Sim | GP |
| ciclo_controle | Passos do ciclo de controle | Lista sequencial | Sim | GP |
| relatorios_periodicidade | Relatórios e cadência | Tabela | Sim | GP |
| fluxo_mudancas_custo | Fluxo de mudança | Texto/Diagrama | Sim | PMO |
| requisitos_doc_mudanca | Requisitos mínimos | Lista | Sim | PMO |
| ferramentas_principais | Ferramentas usadas | Lista | Sim | GP/PMO |
| integracoes_dados | Integrações e fluxos | Texto | Não | TI/PMO |
| responsabilidades_papeis | Papéis e responsabilidades | Tabela | Sim | PMO |
| checklist_plano | Checklist de qualidade do plano | Lista | Sim | PMO |
| tecnicas_estimativa | Técnicas adotadas | Lista | Sim | GP |
| estrutura_custos | Diretos/Indiretos/Fixos/Variáveis | Texto/Lista | Sim | GP/Financeiro |
| base_estimativas | Base das estimativas | Texto estruturado | Sim | GP |
| reservas_contingencia | Política e cálculo | Texto/Percentual | Sim | GP |
| reservas_gerencial | Política e cálculo | Texto/Percentual | Sim | Sponsor |
| checklist_estimativas | Checklist de qualidade | Lista | Sim | PMO |
| metodo_agregacao | Método de agregação | Texto | Sim | GP |
| definicao_baseline | Definição e componentes | Texto | Sim | GP/PMO |
| itens_fora_baseline | Itens fora da baseline | Lista | Não | GP |
| metodo_curva_s | Método de construção | Texto | Não | GP |
| uso_curva_s | Uso na análise | Texto | Não | GP |
| projecao_fluxo_caixa | Projeção de fluxo de caixa | Tabela | Não | Financeiro |
| necessidade_capital | Necessidade máxima de capital | Valor/Texto | Não | Financeiro |
| processo_aprovacao_baseline | Processo de aprovação | Texto | Sim | PMO |
| versionamento_baseline | Política de versionamento | Texto | Sim | PMO |
| coleta_pv_ev_ac | Procedimento de coleta | Texto | Sim | GP/Controller |
| calculo_metricas | Procedimento de cálculo | Texto | Sim | Controller |
| metodo_forecast | Método de EAC/ETC | Texto | Sim | GP |
| indicadores_dashboard | Indicadores do dashboard | Lista | Sim | GP |
| conteudo_relatorios | Conteúdo mínimo dos relatórios | Lista | Sim | PMO |
| metodo_causa_raiz | Método de análise | Texto | Sim | GP |
| registro_acoes | Como registrar ações | Texto | Sim | PMO |
| checklist_semanal | Checklist semanal | Lista | Sim | GP |
| unidade_valor_agil | Unidade de valor ágil | Texto | Não | GP/PO |
| metricas_sprint | Métricas por sprint | Lista | Não | GP/PO |
| componentes_capex_opex | Componentes financeiros | Lista | Não | Financeiro |
| metricas_financeiras | ROI/NPV/IRR/Payback | Lista | Não | Financeiro |
| variaveis_sensibilidade | Variáveis críticas | Lista | Não | GP/Financeiro |
| metodo_sensibilidade | Método de avaliação | Texto | Não | GP |
| referencias_bibliografia | Referências | Lista | Não | PMO |
| referencias_ferramentas | Ferramentas de apoio | Lista | Não | PMO |
| conclusao_sintese | Síntese final | Texto | Não | GP |
