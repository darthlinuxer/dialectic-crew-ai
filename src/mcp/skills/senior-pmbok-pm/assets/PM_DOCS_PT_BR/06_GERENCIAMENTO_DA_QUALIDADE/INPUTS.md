# Inputs para preenchimento do template de qualidade

## Identificação do documento
- **nome_projeto** | Nome do projeto | Texto | Obrigatório | Termo de abertura / sponsor
- **versao_documento** | Versão do documento | SemVer ou número | Obrigatório | Controle de documentos
- **data_documento** | Data de emissão | dd/mm/aaaa | Obrigatório | Controle de documentos
- **aprovadores** | Lista de aprovadores | Lista de nomes/cargos | Obrigatório | Governança

## Política de qualidade
- **declaracao_politica_qualidade** | Declaração da política de qualidade | Texto | Obrigatório | Política organizacional
- **objetivo_n** | Objetivos de qualidade (múltiplos) | Texto | Obrigatório | PMO / Sponsor
- **metrica_n** | Métrica associada | Texto | Obrigatório | PMO / Qualidade
- **meta_n** | Meta numérica/qualitativa | Texto/Percentual | Obrigatório | PMO / Qualidade
- **prazo_n** | Prazo para atingir | Data/Período | Opcional | Plano do projeto
- **responsavel_n** | Responsável pelo objetivo | Nome/Cargo | Obrigatório | GP / Qualidade

## Padrões aplicáveis
- **padrao_n** | Padrão internacional aplicável | Texto | Opcional | Compliance / Qualidade
- **descricao_padrao_n** | Descrição do padrão | Texto | Opcional | Compliance
- **aplicacao_padrao_n** | Aplicação no projeto | Texto | Opcional | Qualidade
- **padrao_corporativo_n** | Padrão interno | Texto | Opcional | PMO
- **regulacao_n** | Regulamentação aplicável | Texto | Opcional | Jurídico/Compliance

## Métricas e critérios
- **dimensao_n** | Dimensão de qualidade | Texto | Obrigatório | Qualidade
- **metrica_produto_n** | Métrica de produto | Texto | Obrigatório | Qualidade
- **formula_n** | Fórmula/descrição | Texto | Opcional | Qualidade
- **meta_produto_n** | Meta | Texto/Percentual | Obrigatório | Qualidade
- **fonte_n** | Fonte de dados | Texto | Obrigatório | PMO/Qualidade
- **frequencia_n** | Frequência de coleta | Texto | Obrigatório | Qualidade
- **responsavel_n** | Responsável pela coleta | Nome/Cargo | Obrigatório | GP/Qualidade

## Quality gates
- **gate_n_criterios** | Critérios por gate | Lista/Texto | Obrigatório | Qualidade/Engenharia

## Checklists e auditorias
- **checklist_code_review_link** | Link/artefato do checklist de code review | URL/Path | Opcional | Engenharia
- **checklist_testes_link** | Link/artefato do checklist de testes | URL/Path | Opcional | QA
- **checklist_auditoria_link** | Link/artefato do checklist de auditoria | URL/Path | Opcional | Qualidade
- **periodicidade_auditorias** | Frequência | Texto | Obrigatório | Qualidade
- **escopo_auditorias** | Escopo | Texto | Obrigatório | Qualidade
- **responsaveis_auditorias** | Responsáveis | Lista | Obrigatório | Qualidade

## Organização da qualidade
- **papel_n** | Papel | Texto | Obrigatório | GP/PMO
- **responsabilidades_n** | Responsabilidades do papel | Texto | Obrigatório | GP/PMO
- **atividade_n** | Atividade do RACI | Texto | Obrigatório | GP/PMO
- **a_n/r_n/c_n/i_n** | A/R/C/I por atividade | Texto | Obrigatório | GP/PMO

## Ferramentas de qualidade
- **ferramentas_analise_estatica** | Ferramentas de análise estática | Lista | Opcional | Engenharia
- **ferramentas_testes** | Ferramentas de testes | Lista | Opcional | QA
- **ferramentas_seguranca** | Ferramentas de segurança | Lista | Opcional | Segurança
- **ferramentas_performance** | Ferramentas de performance | Lista | Opcional | DevOps
- **ferramentas_defeitos** | Ferramentas de gestão de defeitos | Lista | Opcional | QA
- **ferramentas_cicd** | Ferramentas de CI/CD | Lista | Opcional | DevOps

## Custo da qualidade
- **custo_prevencao** | Valor de prevenção | Moeda | Obrigatório | Financeiro/Qualidade
- **custo_avaliacao** | Valor de avaliação | Moeda | Obrigatório | Financeiro/Qualidade
- **custo_falhas_internas** | Valor de falhas internas | Moeda | Obrigatório | Financeiro/Qualidade
- **custo_falhas_externas** | Valor de falhas externas | Moeda | Obrigatório | Financeiro/Qualidade
- **custo_total** | COQ total | Moeda | Obrigatório | Financeiro/Qualidade

## Plano de testes
- **estrategia_testes** | Estratégia geral | Texto | Obrigatório | QA
- **tipo_teste_n** | Tipo de teste | Texto | Obrigatório | QA
- **objetivo_teste_n** | Objetivo do teste | Texto | Obrigatório | QA
- **responsavel_teste_n** | Responsável | Texto | Obrigatório | QA
- **ferramenta_teste_n** | Ferramenta | Texto | Opcional | QA
- **cobertura_teste_n** | Cobertura | Texto | Opcional | QA
- **criterios_entrada** | Critérios de entrada | Lista | Obrigatório | QA
- **criterios_saida** | Critérios de saída | Lista | Obrigatório | QA

## Rastreabilidade
- **req_id_n** | ID do requisito | Texto | Obrigatório | BA/PO
- **req_desc_n** | Descrição | Texto | Obrigatório | BA/PO
- **artefato_n** | Código/artefato associado | Texto | Obrigatório | Engenharia
- **testes_n** | Testes associados | Texto | Obrigatório | QA
- **status_n** | Status | Texto | Obrigatório | QA/GP
