# Inputs para preenchimento do template de riscos

## Identificação
- **nome_projeto** | Nome do projeto | Texto | Obrigatório | Sponsor/PMO
- **versao_documento** | Versão | Número/SemVer | Obrigatório | Controle de documentos
- **data_documento** | Data | dd/mm/aaaa | Obrigatório | Controle de documentos
- **aprovadores** | Aprovadores | Lista | Obrigatório | Governança

## Metodologia
- **processo_riscos** | Processo de risco | Texto | Obrigatório | GP
- **tecnicas_riscos** | Técnicas | Lista | Obrigatório | GP
- **cadencia_riscos** | Cadência | Texto | Obrigatório | GP

## Papéis
- **papel_n** | Papel | Texto | Obrigatório | GP/PMO
- **responsabilidades_n** | Responsabilidades | Texto | Obrigatório | GP/PMO

## RBS e escalas
- **categorias_risco** | Categorias | Lista | Obrigatório | GP
- **escalas_prob_imp** | Escalas | Texto | Obrigatório | GP
- **dimensoes_impacto** | Dimensões | Lista | Obrigatório | GP

## Matriz e apetite
- **criterios_classificacao** | Critérios | Texto | Obrigatório | GP
- **apetite_risco** | Apetite | Texto | Obrigatório | Sponsor
- **tolerancia_risco** | Tolerância | Texto | Obrigatório | Sponsor
- **thresholds_escalacao** | Thresholds | Texto | Obrigatório | Sponsor/PMO

## Reservas
- **contingencia** | Reserva de contingência | Moeda/Percentual | Obrigatório | Financeiro/GP
- **management_reserve** | Management reserve | Moeda/Percentual | Opcional | Sponsor
- **schedule_reserve** | Schedule reserve | Período | Opcional | GP

## Ferramentas
- **ferramenta_principal** | Ferramenta principal | Texto | Obrigatório | GP
- **localizacao_repositorio** | Link/Path | Texto | Obrigatório | GP

## Risk register
- **risk_id_n** | ID | Texto | Obrigatório | GP
- **titulo_n** | Título | Texto | Obrigatório | GP
- **categoria_n** | Categoria | Texto | Obrigatório | GP
- **prob_n** | Probabilidade | Número | Obrigatório | GP
- **impacto_n** | Impacto | Número | Obrigatório | GP
- **score_n** | Score | Número | Obrigatório | GP
- **resposta_n** | Resposta | Texto | Obrigatório | GP
- **owner_n** | Owner | Texto | Obrigatório | GP
- **status_n** | Status | Texto | Obrigatório | GP

## Identificação/Análise/Resposta
- **tecnicas_identificacao** | Técnicas | Lista | Obrigatório | GP
- **momentos_identificacao** | Momentos | Lista | Obrigatório | GP
- **analise_qualitativa** | Qualitativa | Texto | Obrigatório | GP
- **analise_quantitativa** | Quantitativa | Texto | Opcional | GP
- **priorizacao** | Priorização | Texto | Obrigatório | GP
- **estrategias_negativas** | Estratégias negativas | Lista | Obrigatório | GP
- **estrategias_positivas** | Estratégias positivas | Lista | Obrigatório | GP
- **planos_contingencia** | Contingência/Fallback | Texto | Obrigatório | GP

## Monitoramento e comunicação
- **gatilhos** | Gatilhos | Lista | Obrigatório | GP
- **revisoes** | Revisões | Texto | Obrigatório | GP
- **auditorias** | Auditorias | Texto | Opcional | PMO
- **audiencias** | Audiências | Lista | Obrigatório | GP
- **frequencia** | Frequência | Texto | Obrigatório | GP
- **dashboards** | Dashboards | Texto | Opcional | GP

## Integração
- **integracoes_processos** | Integrações | Lista | Opcional | GP

## Lições e referências
- **licoes_aprendidas** | Lições | Texto | Opcional | GP
- **referencias** | Referências | Lista | Opcional | PMO
