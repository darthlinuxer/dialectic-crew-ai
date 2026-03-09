# Rede e Sequenciamento

## Método do Diagrama de Precedência (PDM)
Atividades são representadas como nós (Activity-on-Node). Dependências indicam a ordem lógica de execução.

## Tipos de Relacionamentos
- **Finish-to-Start (FS)**: sucessor inicia após o término do predecessor (padrão).
- **Start-to-Start (SS)**: sucessor inicia quando o predecessor inicia.
- **Finish-to-Finish (FF)**: sucessor termina quando o predecessor termina.
- **Start-to-Finish (SF)**: sucessor termina quando o predecessor inicia (uso raro).

## Leads e Lags
- **Lead**: permite iniciar antes do término do predecessor.
- **Lag**: impõe espera entre atividades.

Leads e lags devem ter justificativa documentada. Quando possível, prefira modelar com atividades intermediárias para maior clareza.

## Dependências Externas
Dependências externas são fatores fora do controle direto do projeto (fornecedores, aprovações, outros projetos). Devem ser registradas em um log e monitoradas regularmente.

## Boas Práticas
- Garanta que a maioria das dependências seja FS, salvo justificativas.
- Revise a lógica da rede para evitar ciclos ou relações incoerentes.
- Mantenha um processo formal para gestão de dependências externas.
