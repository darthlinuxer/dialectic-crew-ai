# INPUTS — Controles do Documento

Este documento lista todas as entradas necessárias para preencher o template `TEMPLATE.md`.

## 1. Metadados do Documento
| Campo | Descrição | Formato/Exemplo | Obrigatório | Fonte Esperada |
|------|-----------|----------------|-------------|----------------|
| projeto_nome | Nome completo do projeto | Texto | Sim | Sponsor/GP |
| projeto_id | Identificador único do projeto | Código alfanumérico | Sim | PMO/Portfólio |
| tipo_documento | Tipo do documento | Plano/Registro/Relatório/Baseline/Contrato/Outro | Sim | GP/PMO |
| versao | Versão do documento | X.Y | Sim | GP/PMO |
| responsavel | Autor principal | Nome + cargo | Sim | GP |
| data_criacao | Data de criação | DD/MM/AAAA | Sim | GP |
| data_ultima_revisao | Data da última revisão | DD/MM/AAAA | Sim | GP |
| data_proxima_revisao | Próxima revisão prevista | DD/MM/AAAA | Não | GP/PMO |
| status | Status do documento | Rascunho/Em Revisão/Aguardando Aprovação/Aprovado/Obsoleto/Arquivado | Sim | GP/PMO |
| confidencialidade | Nível de acesso | Público/Interno/Restrito/Confidencial | Sim | PMO/Compliance |
| ciclo_vida | Fase do documento | Iniciação/Planejamento/Execução/Encerramento | Sim | GP |

## 2. Histórico de Revisões
Para cada revisão registrada:
- rev_n_versao
- rev_n_data
- rev_n_autor
- rev_n_descricao
- rev_n_secoes
- rev_n_aprovador
- rev_n_cr_id (se aplicável)
- rev_n_justificativa
- rev_n_impactos

**Fontes**: Solicitações de mudança, atas de CCB, repositório de versões.

## 3. Distribuição e Aprovações
### 3.1 Matriz de Aprovação
Para cada aprovador/revisor:
- aprov_n_nome
- aprov_n_papel
- aprov_n_org
- aprov_n_acao (Elaborar/Revisar/Aprovar/Informar)
- aprov_n_data_solicitada
- aprov_n_data_realizada
- aprov_n_assinatura

### 3.2 Fluxo de Aprovação
- fluxo_etapa_1 a fluxo_etapa_4 (descrição de cada etapa)

### 3.3 Política de Aprovação Digital
- politica_aprovacao_digital (texto descrevendo meios aceitos)

**Fontes**: Plano de Comunicações, Registro de Stakeholders, políticas internas.

## 4. Glossário e Siglas
Para cada termo:
- gloss_n_termo
- gloss_n_definicao
- gloss_n_contexto
- gloss_n_sinonimos

Termos específicos do projeto:
- termo_especifico_n

**Fontes**: Plano de Comunicação, documentos técnicos, requisitos, normas.

## 5. Referências
- doc_proj_n (documentos do projeto)
- norma_n (normas/metodologias)
- politica_n (políticas internas)
- padrao_n (padrões técnicos e de qualidade)
- template_n (templates e modelos)

**Fontes**: PMO, compliance, documentação corporativa.

## 6. Gestão de Configuração
### 6.1 Local de Armazenamento
- repositorio_principal
- url_caminho
- politica_backup
- permissoes_acesso

### 6.2 Controle de Versão
- sistema_versionamento
- regra_versao_maior
- regra_versao_menor
- regra_versao_dev

### 6.3 Processo de Mudança
- processo_mudanca_1 a processo_mudanca_7

### 6.4 Auditoria e Conformidade
- frequencia_auditoria
- responsavel_auditoria
- checklist_item_1 a checklist_item_4

**Fontes**: Política de gestão documental, PMO, compliance.

## 7. Observações e Notas Especiais
- restricao_1, restricao_2
- dependencias_entrada
- dependencias_saida
- revisao_agendada
- pendencias_conhecidas
- pontos_em_discussao

**Fontes**: GP, PMO, comitês de governança.

## 8. Referências Externas e Recursos Adicionais
- recurso_pmbok_n
- ferramenta_template_n
- standard_n

**Fontes**: PMI, normas externas, base de conhecimento corporativa.
