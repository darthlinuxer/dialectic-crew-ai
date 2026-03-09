# INPUTS — Gerenciamento do Cronograma

Mapa de entradas necessárias para preencher o `TEMPLATE.md`.

| Chave | Descrição | Formato/Exemplo genérico | Obrigatório | Fonte esperada |
|------|-----------|---------------------------|-------------|----------------|
| project_name | Nome do projeto | Texto | Sim | Termo de abertura / Sponsor |
| project_code | Código do projeto | Texto | Sim | PMO / Portfólio |
| document_version | Versão do documento | X.Y | Sim | PMO |
| document_date | Data do documento | DD/MM/AAAA | Sim | GP |
| prepared_by | Responsável pela elaboração | Nome/Cargo | Sim | GP |
| schedule_methodology | Metodologia principal | Predictive / Iterative / Hybrid | Sim | GP / PMO |
| schedule_methodology_justification | Justificativa da metodologia | Texto | Sim | GP |
| requirements_stability | Estabilidade de requisitos | Alta/Média/Baixa | Sim | Negócio/PO |
| technical_complexity | Complexidade técnica | Alta/Média/Baixa | Sim | Tech Lead |
| team_experience | Experiência da equipe | Alta/Média/Baixa | Sim | GP / RH |
| client_involvement | Envolvimento do cliente | Contínuo/Periódico/Limitado | Sim | GP |
| phase_1_name | Nome da fase 1 | Texto | Sim | Plano de projeto |
| phase_1_duration | Duração fase 1 | Texto (ex.: 4 semanas) | Sim | Plano de projeto |
| phase_1_deliverable | Entrega principal fase 1 | Texto | Sim | Plano de escopo |
| phase_1_notes | Observações fase 1 | Texto | Não | GP |
| phase_2_name | Nome da fase 2 | Texto | Sim | Plano de projeto |
| phase_2_duration | Duração fase 2 | Texto | Sim | Plano de projeto |
| phase_2_deliverable | Entrega principal fase 2 | Texto | Sim | Plano de escopo |
| phase_2_notes | Observações fase 2 | Texto | Não | GP |
| phase_3_name | Nome da fase 3 | Texto | Não | Plano de projeto |
| phase_3_duration | Duração fase 3 | Texto | Não | Plano de projeto |
| phase_3_deliverable | Entrega principal fase 3 | Texto | Não | Plano de escopo |
| phase_3_notes | Observações fase 3 | Texto | Não | GP |
| phase_4_name | Nome da fase 4 | Texto | Não | Plano de projeto |
| phase_4_duration | Duração fase 4 | Texto | Não | Plano de projeto |
| phase_4_deliverable | Entrega principal fase 4 | Texto | Não | Plano de escopo |
| phase_4_notes | Observações fase 4 | Texto | Não | GP |
| gate_1_name | Nome do gate 1 | Texto | Não | Governança |
| gate_1_criteria | Critérios do gate 1 | Texto | Não | Governança |
| gate_1_approver | Aprovador gate 1 | Texto | Não | Governança |
| gate_2_name | Nome do gate 2 | Texto | Não | Governança |
| gate_2_criteria | Critérios do gate 2 | Texto | Não | Governança |
| gate_2_approver | Aprovador gate 2 | Texto | Não | Governança |
| process_plan_management | Como planejar o gerenciamento | Texto | Sim | GP |
| process_define_activities | Como definir atividades | Texto | Sim | GP / Equipe |
| process_sequence_activities | Como sequenciar atividades | Texto | Sim | GP / Equipe |
| process_estimate_durations | Como estimar durações | Texto | Sim | GP / Equipe |
| process_develop_schedule | Como desenvolver cronograma | Texto | Sim | GP |
| process_control_schedule | Como controlar cronograma | Texto | Sim | GP |
| contingency_reserve | Reserva de contingência | Percentual/Texto | Sim | GP / Riscos |
| management_reserve | Reserva de management | Percentual/Texto | Sim | Sponsor |
| baseline_event_date | Evento/data da baseline | Texto/Data | Sim | GP |
| baseline_approver | Aprovador da baseline | Texto | Sim | Sponsor/Steering |
| baseline_frozen | Baseline congelada | Sim/Não | Sim | PMO |
| change_control_process | Processo de change control | Texto | Sim | PMO |
| schedule_tool_name | Ferramenta principal | Texto | Sim | PMO |
| schedule_tool_version | Versão da ferramenta | Texto | Não | PMO |
| schedule_master_location | Local do arquivo master | Caminho/URL | Sim | PMO |
| schedule_backup_policy | Política de backup | Texto | Sim | PMO |
| activity_naming_convention | Convenção de atividades | Texto | Sim | PMO |
| milestone_naming_convention | Convenção de marcos | Texto | Sim | PMO |
| wbs_levels | Níveis de WBS | Número/Texto | Sim | PMO |
| calendar_1_name | Nome do calendário 1 | Texto | Sim | GP/PMO |
| calendar_1_workdays | Dias úteis calendário 1 | Texto | Sim | GP/PMO |
| calendar_1_hours | Horas/dia calendário 1 | Texto | Sim | GP/PMO |
| calendar_1_exceptions | Exceções calendário 1 | Texto | Não | GP/PMO |
| calendar_1_applies_to | Aplicado a (calendário 1) | Texto | Sim | GP/PMO |
| calendar_2_name | Nome do calendário 2 | Texto | Não | GP/PMO |
| calendar_2_workdays | Dias úteis calendário 2 | Texto | Não | GP/PMO |
| calendar_2_hours | Horas/dia calendário 2 | Texto | Não | GP/PMO |
| calendar_2_exceptions | Exceções calendário 2 | Texto | Não | GP/PMO |
| calendar_2_applies_to | Aplicado a (calendário 2) | Texto | Não | GP/PMO |
| project_holidays | Feriados considerados | Lista | Sim | RH/PMO |
| duration_units | Unidade de duração | Dias/Horas/Semanas | Sim | GP |
| effort_units | Unidade de esforço | Horas-homem/Homem-dia | Sim | GP |
| measurement_precision | Precisão de medição | Texto | Sim | GP |
| act_1_wbs | WBS (linha 1) | Texto | Não | WBS |
| act_1_id | ID atividade (linha 1) | Texto | Não | WBS |
| act_1_name | Nome atividade (linha 1) | Texto | Não | WBS |
| act_1_desc | Descrição atividade (linha 1) | Texto | Não | WBS |
| act_1_owner | Responsável (linha 1) | Texto | Não | GP |
| act_1_duration | Duração (linha 1) | Texto | Não | GP |
| act_1_dependencies | Dependências (linha 1) | Texto | Não | GP |
| act_1_type | Tipo (linha 1) | Texto | Não | GP |
| act_2_wbs | WBS (linha 2) | Texto | Não | WBS |
| act_2_id | ID atividade (linha 2) | Texto | Não | WBS |
| act_2_name | Nome atividade (linha 2) | Texto | Não | WBS |
| act_2_desc | Descrição atividade (linha 2) | Texto | Não | WBS |
| act_2_owner | Responsável (linha 2) | Texto | Não | GP |
| act_2_duration | Duração (linha 2) | Texto | Não | GP |
| act_2_dependencies | Dependências (linha 2) | Texto | Não | GP |
| act_2_type | Tipo (linha 2) | Texto | Não | GP |
| activity_id | ID (atributos) | Texto | Sim | WBS |
| activity_name | Nome (atributos) | Texto | Sim | WBS |
| activity_description | Descrição (atributos) | Texto | Sim | WBS |
| activity_wbs | WBS (atributos) | Texto | Sim | WBS |
| activity_owner | Responsável (atributos) | Texto | Sim | GP |
| activity_accountable | Accountable (atributos) | Texto | Não | GP |
| activity_duration | Duração (atributos) | Texto | Sim | GP |
| activity_effort | Esforço (atributos) | Texto | Sim | GP |
| activity_dependencies | Dependências (atributos) | Texto | Sim | GP |
| activity_successors | Sucessores (atributos) | Texto | Não | GP |
| activity_resources | Recursos (atributos) | Texto | Não | GP |
| activity_cost | Custo (atributos) | Texto | Não | Financeiro |
| activity_assumptions | Premissas (atributos) | Texto | Sim | GP |
| activity_risks | Riscos (atributos) | Texto | Sim | Riscos |
| activity_type | Tipo (atributos) | Texto | Sim | GP |
| activity_float | Float/Slack | Texto | Não | Scheduler |
| activity_critical_path | Caminho crítico? | Sim/Não | Não | Scheduler |
| ms_1_id | ID marco 1 | Texto | Não | Cronograma |
| ms_1_name | Nome marco 1 | Texto | Não | Cronograma |
| ms_1_baseline_date | Data baseline marco 1 | Data | Não | Cronograma |
| ms_1_criteria | Critério marco 1 | Texto | Não | GP |
| ms_1_criticality | Criticidade marco 1 | Texto | Não | GP |
| ms_2_id | ID marco 2 | Texto | Não | Cronograma |
| ms_2_name | Nome marco 2 | Texto | Não | Cronograma |
| ms_2_baseline_date | Data baseline marco 2 | Data | Não | Cronograma |
| ms_2_criteria | Critério marco 2 | Texto | Não | GP |
| ms_2_criticality | Criticidade marco 2 | Texto | Não | GP |
| sequencing_method | Método de sequenciamento | Texto | Sim | GP |
| dependency_types_allowed | Tipos de dependências permitidos | Texto | Sim | GP |
| leads_lags_policy | Política de leads/lags | Texto | Sim | GP |
| dep_1_id | ID dependência externa | Texto | Não | GP |
| dep_1_desc | Descrição dependência | Texto | Não | GP |
| dep_1_from | De (origem) | Texto | Não | GP |
| dep_1_to | Para (destino) | Texto | Não | GP |
| dep_1_status | Status | Texto | Não | GP |
| dep_1_owner | Owner | Texto | Não | GP |
| dep_1_due_date | Data compromisso | Data | Não | GP |
| est_1_type | Tipo de atividade (linha 1) | Texto | Não | GP |
| est_1_primary | Método primário (linha 1) | Texto | Não | GP |
| est_1_secondary | Método secundário (linha 1) | Texto | Não | GP |
| est_1_source | Fonte de dados (linha 1) | Texto | Não | GP |
| est_2_type | Tipo de atividade (linha 2) | Texto | Não | GP |
| est_2_primary | Método primário (linha 2) | Texto | Não | GP |
| est_2_secondary | Método secundário (linha 2) | Texto | Não | GP |
| est_2_source | Fonte de dados (linha 2) | Texto | Não | GP |
| estimate_precision_target | Precisão desejada | Texto | Sim | GP |
| contingency_by_phase | Contingência por fase | Texto | Sim | GP |
| reserve_consumption_policy | Política de consumo | Texto | Sim | GP |
| estimate_assumptions_log | Registro de premissas | Texto/Lista | Sim | GP |
| schedule_development_process | Processo de desenvolvimento | Texto | Sim | GP |
| critical_path_method | Método de CP/CC | Texto | Sim | GP |
| critical_chain_buffers | Política de buffers | Texto | Não | GP |
| baseline_version | Versão da baseline | Texto | Sim | PMO |
| baseline_date | Data da baseline | Data | Sim | PMO |
| baseline_reason | Motivo da versão | Texto | Sim | PMO |
| gantt_summary_location | Local do Gantt | Caminho/URL | Não | PMO |
| critical_path_report_location | Local relatório CP | Caminho/URL | Não | PMO |
| milestone_chart_location | Local milestone chart | Caminho/URL | Não | PMO |
| ctrl_1_activity | Atividade controle 1 | Texto | Não | GP |
| ctrl_1_frequency | Frequência controle 1 | Texto | Não | GP |
| ctrl_1_owner | Responsável controle 1 | Texto | Não | GP |
| ctrl_1_output | Saída controle 1 | Texto | Não | GP |
| ctrl_2_activity | Atividade controle 2 | Texto | Não | GP |
| ctrl_2_frequency | Frequência controle 2 | Texto | Não | GP |
| ctrl_2_owner | Responsável controle 2 | Texto | Não | GP |
| ctrl_2_output | Saída controle 2 | Texto | Não | GP |
| spi_current | SPI atual | Número | Não | Scheduler |
| sv_current | SV atual | Número | Não | Scheduler |
| milestone_variance | Variação de marcos | Texto | Não | Scheduler |
| critical_path_variance | Variação CP | Texto | Não | Scheduler |
| threshold_green | Threshold verde | Texto | Sim | GP |
| threshold_yellow | Threshold amarelo | Texto | Sim | GP |
| threshold_red | Threshold vermelho | Texto | Sim | GP |
| corrective_action_process | Processo de ação corretiva | Texto | Sim | GP |
| forecast_method | Método de previsão | Texto | Sim | GP |
| eac_t_current | EAC-T atual | Texto | Não | GP |
| checklist_development | Checklist de desenvolvimento | Lista | Sim | GP |
| checklist_control | Checklist de controle | Lista | Sim | GP |
| checklist_red_flags | Red flags | Lista | Sim | GP |
| best_practices_notes | Notas de melhores práticas | Texto | Não | GP |
| references_list | Lista de referências | Lista | Não | GP/PMO |
| conclusion_notes | Notas de conclusão | Texto | Não | GP |
