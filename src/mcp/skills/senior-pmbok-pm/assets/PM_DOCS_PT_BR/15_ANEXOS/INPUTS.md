# Inputs necessários — Anexos

## Glossário e acrônimos

- **glossario_termos**
  - Descrição: lista de termos e definições do domínio do projeto.
  - Formato/Exemplo: `[{"termo":"[Termo]","definicao":"[Definição]","observacoes":"[Opcional]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: documentação funcional/técnica, backlog, stakeholders.

- **acronimos**
  - Descrição: lista de siglas usadas no projeto e seus significados.
  - Formato/Exemplo: `[{"acronimo":"[Sigla]","significado":"[Expansão]","observacoes":"[Opcional]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: artefatos do projeto, padrões internos.

## Inventário de documentos

- **documentos_iniciacao**
  - Descrição: documentos da fase de iniciação.
  - Formato/Exemplo: `[{"id":"DOC-001","nome":"[Documento]","localizacao":"[Link]","versao":"vX.Y","data":"AAAA-MM-DD","owner":"[Responsável]","status":"[Status]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: repositório de governança.

- **documentos_planejamento**
  - Descrição: documentos da fase de planejamento.
  - Formato/Exemplo: mesma estrutura de `documentos_iniciacao`.
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: repositórios de planejamento.

- **documentos_execucao_controle**
  - Descrição: documentos de execução e controle.
  - Formato/Exemplo: mesma estrutura de `documentos_iniciacao`.
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: relatórios, atas, logs.

- **documentos_tecnicos**
  - Descrição: documentos técnicos e de arquitetura.
  - Formato/Exemplo: mesma estrutura de `documentos_iniciacao`.
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: repositórios técnicos.

- **documentos_qualidade**
  - Descrição: documentos de qualidade e testes.
  - Formato/Exemplo: mesma estrutura de `documentos_iniciacao`.
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: QA, dashboards.

- **documentos_encerramento**
  - Descrição: documentos de encerramento.
  - Formato/Exemplo: mesma estrutura de `documentos_iniciacao`.
  - Obrigatoriedade: Condicional (na fase de encerramento)
  - Fonte esperada: PMO/GP.

## Artefatos e evidências

- **artefatos_escopo**
  - Descrição: lista de artefatos de escopo (WBS, dicionário, backlog).
  - Formato/Exemplo: `[{"tipo":"[WBS]","localizacao":"[Arquivo/Link]","versao":"vX.Y","observacoes":"[Texto]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: planejamento de escopo.

- **artefatos_cronograma**
  - Descrição: cronograma master, baseline, gantt e roadmap.
  - Formato/Exemplo: `[{"tipo":"[Cronograma]","localizacao":"[Arquivo]","baseline":"[Baseline]","observacoes":"[Texto]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: ferramenta de cronograma.

- **artefatos_custos**
  - Descrição: orçamento detalhado e relatórios financeiros.
  - Formato/Exemplo: `[{"tipo":"[Orçamento]","localizacao":"[Arquivo]","versao":"vX.Y","metricas":"[Lista]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: controle financeiro.

- **artefatos_qualidade**
  - Descrição: plano de testes, matriz de rastreabilidade e relatórios.
  - Formato/Exemplo: `[{"tipo":"[Plano de Testes]","localizacao":"[Arquivo]","observacoes":"[Texto]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: QA.

- **artefatos_riscos**
  - Descrição: registro de riscos, matriz e planos de resposta.
  - Formato/Exemplo: `[{"tipo":"[Registro de Riscos]","localizacao":"[Arquivo]","versao":"vX.Y"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: gestão de riscos.

- **artefatos_stakeholders**
  - Descrição: registro de stakeholders e matrizes de engajamento.
  - Formato/Exemplo: `[{"tipo":"[Registro de Stakeholders]","localizacao":"[Arquivo]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: gestão de stakeholders.

- **artefatos_aquisicoes**
  - Descrição: contratos, SOWs e scorecards de fornecedores.
  - Formato/Exemplo: `[{"tipo":"[Contrato]","localizacao":"[Link]","observacoes":"[Texto]"}]`
  - Obrigatoriedade: Condicional (se houver aquisições)
  - Fonte esperada: procurement/legal.

## Templates e formulários

- **templates_gestao**
  - Descrição: lista de templates de governança e gestão.
  - Formato/Exemplo: `[{"nome":"[Template]","localizacao":"[Link]","finalidade":"[Uso]","frequencia":"[Periodicidade]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: repositório de templates.

- **templates_tecnicos**
  - Descrição: lista de templates técnicos (ADR, user story, bug report).
  - Formato/Exemplo: `[{"nome":"[Template]","formato":"[Formato]","estrutura":"[Seções]","ferramenta":"[Ferramenta]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: engenharia.

- **formularios**
  - Descrição: formulários usados no projeto.
  - Formato/Exemplo: `[{"nome":"[Formulário]","link":"[URL]","finalidade":"[Uso]"}]`
  - Obrigatoriedade: Condicional (se houver)
  - Fonte esperada: ferramentas de formulários.

## Diagramas e modelos visuais

- **diagramas_arquitetura**
  - Descrição: diagramas de arquitetura (C4, deployment).
  - Formato/Exemplo: `[{"nome":"[Diagrama]","nivel":"[Contexto/Container/Componente]","localizacao":"[Arquivo]","ferramenta":"[Ferramenta]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: arquitetura.

- **diagramas_dados**
  - Descrição: modelos de dados (ER, DFD).
  - Formato/Exemplo: `[{"nome":"[Diagrama]","escopo":"[Escopo]","localizacao":"[Arquivo]","versao":"vX.Y"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: dados/arquitetura.

- **diagramas_processos**
  - Descrição: fluxos de processos (BPMN, swimlane).
  - Formato/Exemplo: `[{"nome":"[Processo]","tipo":"[BPMN]","localizacao":"[Arquivo]","observacoes":"[Texto]"}]`
  - Obrigatoriedade: Condicional (se aplicável)
  - Fonte esperada: análise de processos.

## Referências externas

- **referencias_standards**
  - Descrição: normas e frameworks relevantes.
  - Formato/Exemplo: `[{"nome":"[Standard]","versao":"[Versão]","aplicabilidade":"[Uso]","link":"[URL]"}]`
  - Obrigatoriedade: Opcional
  - Fonte esperada: governança/compliance.

- **referencias_ferramentas**
  - Descrição: ferramentas/plataformas e suas documentações.
  - Formato/Exemplo: `[{"nome":"[Ferramenta]","versao":"[Versão]","uso":"[Uso]","link":"[URL]"}]`
  - Obrigatoriedade: Opcional
  - Fonte esperada: engenharia/ops.

- **referencias_livros**
  - Descrição: livros e publicações recomendados.
  - Formato/Exemplo: `[{"titulo":"[Título]","autor":"[Autor]","tema":"[Tema]"}]`
  - Obrigatoriedade: Opcional
  - Fonte esperada: PMO/gestão.

- **referencias_cursos_certificacoes**
  - Descrição: cursos e certificações relevantes.
  - Formato/Exemplo: `[{"tipo":"[Curso/Certificação]","publico":"[Público]","carga_horaria":"[Horas]","periodo":"[Data]"}]`
  - Obrigatoriedade: Opcional
  - Fonte esperada: RH/PMO.

## Histórico e governança

- **historico_versoes_anexos**
  - Descrição: evolução dos principais anexos.
  - Formato/Exemplo: `[{"documento":"[Nome]","versao":"vX.Y","data":"AAAA-MM-DD","mudancas":"[Descrição]","autor":"[Responsável]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: controle de versões.

- **matriz_permissoes**
  - Descrição: matriz de acesso por papel/local.
  - Formato/Exemplo: tabela com colunas de papéis e níveis (R/W/RW).
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: governança/segurança.

- **politica_retencao**
  - Descrição: política de retenção por tipo de documento.
  - Formato/Exemplo: `[{"tipo":"[Documento]","retencao":"[Tempo]","local":"[Local]","responsavel":"[Papel]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: compliance/legal/PMO.

- **checklist_anexos**
  - Descrição: status dos itens do checklist final.
  - Formato/Exemplo: `[{"item":"[Descrição]","status":"[ok/pendente]","responsavel":"[Papel]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: gerente de projeto.

- **responsavel_manutencao**
  - Descrição: papel ou pessoa responsável pela manutenção dos anexos.
  - Formato/Exemplo: `"[Papel]"`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: governança do projeto.

- **frequencia_revisao**
  - Descrição: periodicidade da revisão dos anexos.
  - Formato/Exemplo: `"Mensal"`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: governança do projeto.

- **aprovacoes**
  - Descrição: registros de aprovação do documento.
  - Formato/Exemplo: `[{"papel":"[Papel]","nome":"[Nome]","assinatura":"[Assinatura]","data":"AAAA-MM-DD"}]`
  - Obrigatoriedade: Condicional
  - Fonte esperada: stakeholders de aprovação.

- **controle_versoes_documento**
  - Descrição: histórico de versões do documento de anexos.
  - Formato/Exemplo: `[{"versao":"vX.Y","data":"AAAA-MM-DD","autor":"[Nome]","descricao":"[Mudanças]"}]`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: controle de versões.

- **proxima_revisao**
  - Descrição: data prevista para próxima revisão.
  - Formato/Exemplo: `"AAAA-MM-DD"`
  - Obrigatoriedade: Obrigatório
  - Fonte esperada: governança do projeto.