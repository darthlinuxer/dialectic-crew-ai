# 📚 Documentação Técnica - Dialectic Crew AI

> Documentação completa com diagramas Mermaid

---

## 1. Arquitetura Geral do Sistema

```mermaid
graph TB
    subgraph "Camada de Entrada"
        CLI[("main.py<br/>CLI")]
        AR[("Argument<br/>Request")]
    end
    
    subgraph "Camada de Processamento"
        DF["DialecticFlow<br/>flow.py"]
    end
    
    subgraph "Camada de Agentes"
        V["Visionário<br/>TESE"]
        C["Crítico<br/>ANTÍTESE"]
        S["Sintetizador<br/>SÍNTESE"]
        G["Validador<br/>GATE"]
    end
    
    subgraph "Camada de Dados"
        VM[("VISION.md")]
        JSON[("prd_output<br/>.json")]
    end
    
    subgraph "Camada de Validação"
        PYD[("Pydantic<br/>Schema")]
    end
    
    CLI --> AR
    AR --> DF
    DF --> VM
    DF --> V
    V --> C
    C --> S
    S --> G
    G --> PYD
    PYD --> JSON
```

---

## 2. Fluxo Dialético Completo

```mermaid
flowchart TD
    START([INÍCIO]) --> READ_VISION["📖 Ler VISION.md"]
    READ_VISION --> TESE["<b>TESE</b><br/>Visionário propõe<br/>solução inicial"]
    TESE --> ANTITESE["<b>ANTÍTESE</b><br/>Crítico Socrático<br/>destrói com críticas"]
    ANTITESE --> SINTESE["<b>SÍNTESE</b><br/>Sintetizador<br/>funde as ideias"]
    SINTESE --> VALIDACAO["<b>VALIDAÇÃO</b><br/>Gate aprova<br/>se score >= 9.0"]
    
    VALIDACAO --> CHECK{"score >= 9.0?"}
    
    CHECK -->|SIM| APPROVE["✅ Aprovar & Salvar"]
    CHECK -->|NÃO| RETRY{"retry < max?"}
    
    RETRY -->|SIM| RETRY_INC["retry + 1"]
    RETRY_INC --> TESE
    
    RETRY -->|NÃO| FORCE_APPROVE["⚠️ Forçar aprovação<br/>após max retries"]
    
    APPROVE --> SAVE["💾 Salvar JSON"]
    FORCE_APPROVE --> SAVE
    
    SAVE --> END([FIM])
```

---

## 3. Diagrama de Sequência

```mermaid
sequenceDiagram
    participant U as Usuário
    participant M as main.py
    participant F as DialecticFlow
    participant V as Visionário
    participant C as Crítico
    participant S as Sintetizador
    participant G as Validador
    participant DB as VISION.md
    participant O as prd_output/

    U->>M: python main.py "feature"
    M->>F: run_dialectic_flow()
    F->>DB: Lê VISION.md
    DB-->>F: Conteúdo da visão
    
    loop Para cada rodada (max 5x)
        F->>V: Task: Gerar TESE
        V->>DB: Lê VISION.md
        V-->>F: Proposta inicial
        
        F->>C: Task: Gerar ANTÍTESE
        C->>DB: Lê VISION.md
        C-->>F: Crítica + score
        
        F->>S: Task: Gerar SÍNTESE
        S->>DB: Lê VISION.md
        S-->>F: PRD refinado
        
        F->>G: Task: Validar PRD
        G->>DB: Lê VISION.md
        G-->>F: Score final
    end
    
    F->>O: Salvar PRD_YYYYMMDD.json
    O-->>U: ✅ Concluído!
```

---

## 4. Agentes e Suas Responsabilidades

```mermaid
mindmap
  root((Dialectic<br/>Crew AI))
    Visionário
      TESE
      Proposta inicial
      Alinhado com VISION
      18 anos experiência
      Holístico
    Crítico
      ANTÍTESE
      Método socrático
      Contradições
      Riscos de drift
      Rigoroso
    Sintetizador
      SÍNTESE
      Hegelian synthesis
      Elimina fraquezas
      Melhor que ambas
      Criativo
    Validador
      GATE
      Score 0-10
      Checklist
      Aprova/Reprova
      Rigoroso
```

---

## 5. Máquina de Estados do Fluxo

```mermaid
stateDiagram-v2
    [*] --> iniciar_dialetica
    iniciar_dialetica --> rodar_rodada
    
    state rodar_rodada {
        [*] --> tese
        tese --> antítese
        antítese --> síntese
        síntese --> validação
        validação --> [*]
    }
    
    rodar_rodada --> avaliar
    
    state avaliar {
        [*] --> check_score
        check_score --> retry: score < 9.0
        check_score --> aprovar: score >= 9.0
    }
    
    retry --> rodar_rodada: retry + 1
    retry --> aprovar: max retries
    
    state aprobar {
        [*] --> salvar_prd
        salvar_prd --> [*]
    }
    
    aprobar --> [*]
```

---

## 6. Estrutura de Dados - Schema Pydantic

```mermaid
classDiagram
    class PRDSchema {
        +str feature_name
        +str version
        +str objective
        +MacroImpact macro_impact
        +List~UserStory~ user_stories
        +List~AntiDriftQuestion~ anti_drift_questions
        +float quality_score
        +bool consensus_reached
        +str final_validation_notes
    }
    
    class UserStory {
        +str id
        +str title
        +str description
        +List~str~ acceptance_criteria
        +Literal effort
        +List~str~ dependencies
    }
    
    class MacroImpact {
        +List~str~ modules_affected
        +Literal risk_level
        +str performance_impact
        +str security_impact
    }
    
    class AntiDriftQuestion {
        +str question
        +str answer
    }
    
    PRDSchema *-- UserStory
    PRDSchema *-- MacroImpact
    PRDSchema *-- AntiDriftQuestion
```

---

## 7. Fluxo de Retry Automático

```mermaid
flowchart LR
    subgraph "Retry Loop"
        R1[Rodada 1<br/>Score: 6.5] --> R2[Rodada 2<br/>Score: 7.8]
        R2 --> R3[Rodada 3<br/>Score: 8.4]
        R3 --> R4[Rodada 4<br/>Score: 9.2]
    end
    
    R1 -.->|"Reprovar<br/>retry + 1"| R2
    R2 -.->|"Reprovar<br/>retry + 1"| R3
    R3 -.->|"Reprovar<br/>retry + 1"| R4
    R4 ==>"✅ Aprovar<br/>score >= 9.0"| AP[Approved]
```

---

## 8. Integrações e APIs Suportadas

```mermaid
graph LR
    subgraph "Provedores LLM"
        O[OpenAI<br/>gpt-4o]
        A[Anthropic<br/>claude-3-5]
        G[Groq<br/>llama-3.3]
        M[MiniMax<br/>M2.1]
    end
    
    subgraph "CrewAI"
        O --> C[CrewAI]
        A --> C
        G --> C
        M --> C
    end
    
    C --> PRD[("PRD<br/>Output")]
```

---

## 9. Checklist de Validação

```mermaid
flowchart TD
    START([Início Validação]) --> Q1{Feature alinhada<br/>com VISION?}
    Q1 -->|❌| FAIL[Reprovar]
    Q1 -->|✅| Q2{Módulos<br/>afetados?}
    
    Q2 -->|❌| FAIL
    Q2 -->|✅| Q3{Riscos<br/>mitigados?}
    
    Q3 -->|❌| FAIL
    Q3 -->|✅| Q4{RNFs<br/>cobertos?}
    
    Q4 -->|❌| FAIL
    Q4 -->|✅| Q5{User stories<br/>completas?}
    
    Q5 -->|❌| FAIL
    Q5 -->|✅| Q6{Anti-drift<br/>>= 5?}
    
    Q6 -->|❌| FAIL
    Q6 -->|✅| Q7{Zero<br/>contradições?}
    
    Q7 -->|❌| FAIL
    Q7 -->|✅| CHECK_SCORE{"score >= 9.0?"}
    
    CHECK_SCORE -->|❌| FAIL
    CHECK_SCORE -->|✅| PASS[✅ Aprovar]
    
    FAIL --> NOTE[Nota: X.X<br/>Motivo: ...]
    PASS --> OUTPUT[💾 Salvar JSON]
```

---

## 10. Estrutura de Diretórios

```mermaid
graph TD
    ROOT["dialectic-crew-ai/"] --> MAIN["main.py"]
    ROOT --> FLOW["flow.py"]
    ROOT --> AGENTS["agents.py"]
    ROOT --> SCHEMAS["schemas.py"]
    ROOT --> TOOLS["tools.py"]
    ROOT --> VISION["VISION.md"]
    ROOT --> README["README.md"]
    
    ROOT --> DOCS["docs/"]
    DOCS --> DOC_README["README.md"]
    
    ROOT --> OUTPUT["prd_output/"]
    OUTPUT --> PRD_1["PRD_20260308_1430.json"]
    OUTPUT --> PRD_2["PRD_20260309_0915.json"]
    
    ROOT --> ENV[".env.example"]
    ROOT --> REQ["requirements.txt"]
```

---

## 11. Exemplo de Execução

```mermaid
sequenceDiagram
    participant U as Usuário
    participant C as Terminal
    
    Note over U,C: Comando executado
    U->>C: python main.py "Sistema de pagamentos com Pix"
    
    Note over C: Saída no terminal
    C->>U: ╔══════════════════════════════════╗
    C->>U: ║  🔷 DIALECTIC CREW AI v1.0       ║
    C->>U: ╚══════════════════════════════════╝
    C->>U: 🚀 Feature: Sistema de pagamentos...
    C->>U: ════════════════════════════════════
    C->>U: 🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄
    C->>U: 📍 RODADA 1/5
    C->>U: 📝 FASE 1: TESE...
    C->>U: 📝 FASE 2: ANTÍTESE...
    C->>U: 📝 FASE 3: SÍNTESE...
    C->>U: 📝 FASE 4: VALIDAÇÃO...
    C->>U: ════════════════════════════════════
    C->>U: 📊 QUALITY SCORE: 9.2/10.0
    C->>U: ════════════════════════════════════
    C->>U: 🎉 APROVADO!
    C->>U: 💾 Salvo em: prd_output/PRD_20260308_1500.json
```

---

## 12. Métricas do Sistema

```mermaid
gauge
    title "Quality Score Target"
    0-5: "Reprovado"
    5-7: "Precisa melhorar"
    7-9: "Quase lá"
    9-10: "✅ Aprovado"
    9.0
```

| Métrica | Valor |
|---------|-------|
| Score Mínimo | 9.0 |
| Max Retries | 5 |
| Mín. User Stories | 3 |
| Mín. Anti-Drift | 5 |
| Módulos por feature | Variável |

---

## 📖 Ver Também

- [VISION.md](../VISION.md) - Visão macro do sistema
- [README.md](../README.md) - Documentação principal
- [agents.py](../agents.py) - Código dos agentes
- [flow.py](../flow.py) - Implementação do fluxo
- [schemas.py](../schemas.py) - Schemas Pydantic
