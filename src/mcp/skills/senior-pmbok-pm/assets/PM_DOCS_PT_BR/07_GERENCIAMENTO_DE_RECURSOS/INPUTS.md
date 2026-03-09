# Inputs para preenchimento do template de recursos

## Identificação
- **nome_projeto** | Nome do projeto | Texto | Obrigatório | Sponsor/PMO
- **versao_documento** | Versão do documento | Número/SemVer | Obrigatório | Controle de documentos
- **data_documento** | Data de emissão | dd/mm/aaaa | Obrigatório | Controle de documentos
- **aprovadores** | Lista de aprovadores | Lista | Obrigatório | Governança

## Visão geral
- **escopo_humanos** | Escopo de recursos humanos | Texto | Obrigatório | GP/RH
- **escopo_fisicos** | Escopo de recursos físicos | Texto | Obrigatório | GP/Operações
- **escopo_materiais** | Escopo de recursos materiais | Texto | Opcional | GP/Operações
- **objetivo_n** | Objetivo do plano | Texto | Obrigatório | GP

## Estrutura organizacional
- **tipo_estrutura** | Tipo de estrutura | Texto | Obrigatório | GP/PMO
- **observacoes_estrutura** | Observações | Texto | Opcional | GP

## Papéis e responsabilidades
- **papel_n** | Papel | Texto | Obrigatório | GP/PMO
- **responsabilidades_n** | Responsabilidades | Texto | Obrigatório | GP/PMO
- **disponibilidade_n** | Disponibilidade | Texto/Percentual | Obrigatório | GP/PMO
- **atividade_n** | Atividade do RACI | Texto | Obrigatório | GP
- **a_n/r_n/c_n/i_n** | A/R/C/I por atividade | Texto | Obrigatório | GP

## Requisitos de recursos
- **rh_papel_n** | Papel (RH) | Texto | Obrigatório | GP/RH
- **rh_qtd_n** | Quantidade | Número | Obrigatório | GP/RH
- **rh_inicio_n** | Início | Data/Período | Obrigatório | GP
- **rh_fim_n** | Fim | Data/Período | Obrigatório | GP
- **rh_perfil_n** | Perfil/skills | Texto | Obrigatório | GP
- **competencias_tecnicas** | Competências técnicas | Lista | Obrigatório | Tech Lead
- **competencias_comportamentais** | Competências comportamentais | Lista | Obrigatório | GP/RH
- **rf_recurso_n** | Recurso físico | Texto | Obrigatório | Operações
- **rf_qtd_n** | Quantidade | Número | Obrigatório | Operações
- **rf_custo_unit_n** | Custo unitário | Moeda | Obrigatório | Financeiro
- **rf_custo_total_n** | Custo total | Moeda | Obrigatório | Financeiro
- **rf_quando_n** | Quando | Data/Período | Obrigatório | Operações

## Alocação e liberação
- **criterios_alocacao** | Critérios de alocação | Lista | Obrigatório | GP
- **criterios_liberacao** | Critérios de liberação | Lista | Obrigatório | GP
- **processo_substituicao** | Processo de substituição | Texto | Obrigatório | GP/RH

## Desenvolvimento da equipe
- **estrategia_desenvolvimento** | Estratégia | Texto | Obrigatório | GP
- **plano_capacitacao** | Plano de capacitação | Texto | Obrigatório | GP/RH
- **team_building** | Atividades | Lista | Opcional | GP

## Desempenho
- **kpi_n** | KPI | Texto | Obrigatório | GP
- **kpi_desc_n** | Descrição | Texto | Obrigatório | GP
- **kpi_meta_n** | Meta | Texto/Percentual | Obrigatório | GP
- **kpi_freq_n** | Frequência | Texto | Obrigatório | GP
- **metodo_avaliacao** | Método de avaliação | Texto | Obrigatório | RH
- **frequencia_avaliacao** | Frequência | Texto | Obrigatório | RH
- **criterios_avaliacao** | Critérios | Lista | Obrigatório | RH
- **sistema_reconhecimento** | Sistema de reconhecimento | Texto | Opcional | RH

## Conflitos
- **tipos_conflito** | Tipos de conflito | Lista | Obrigatório | GP
- **tecnicas_resolucao** | Técnicas de resolução | Lista | Obrigatório | GP
- **processo_escalacao** | Processo de escalação | Texto | Obrigatório | GP

## Calendários
- **calendario_base** | Calendário base | Texto | Obrigatório | GP
- **excecoes_calendario** | Exceções | Lista | Opcional | GP/RH
- **restricoes_recursos** | Restrições | Lista | Obrigatório | GP
- **matriz_alocacao** | Matriz de alocação | Link/Path | Opcional | GP

## Aquisição e mobilização
- **estrategia_contratacao** | Estratégia | Texto | Obrigatório | GP/RH
- **plano_onboarding** | Plano de onboarding | Texto | Obrigatório | GP/RH
- **plano_mobilizacao** | Plano de mobilização | Texto | Obrigatório | GP

## Recursos físicos
- **infraestrutura_ti** | Infraestrutura | Texto | Obrigatório | TI
- **espaco_fisico** | Espaço físico | Texto | Opcional | Operações
- **modelo_remoto** | Modelo remoto/híbrido | Texto | Opcional | GP

## Lições e referências
- **licoes_aprendidas** | Lições aprendidas | Texto | Opcional | GP
- **referencias** | Referências | Lista | Opcional | GP/PMO
