"""
Script simplificado para executar o fluxo dialético usando Crew direto
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Task, Crew
from agents import visionario, critico_socratico, sintetizador, validador_macro, LLM
from schemas import PRDSchema

MAX_RETRIES = 1
OUTPUT_DIR = "prd_output"


def run_dialectic(feature_request: str, vision_content: str) -> dict:
    """Executa o fluxo dialético completo"""
    
    print(f"\n{'='*60}")
    print(f"🚀 INICIANDO FLUXO DIALÉTICO")
    print(f"{'='*60}")
    print(f"Feature: {feature_request}")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"{'='*60}\n")
    
    for retry in range(MAX_RETRIES):
        print(f"\n{'🔄'*20}")
        print(f"📍 RODADA {retry + 1}/{MAX_RETRIES}")
        print(f"{'🔄'*20}\n")
        
        # TESE
        print("📝 FASE 1: TESE - Visionário proposing...")
        task_vision = Task(
            description=f"""
Objetivo: {feature_request}

VISÃO MACRO DO SISTEMA:
{vision_content}

Leia VISION.md inteiro. Gere a tese inicial completa (proposta de PRD) incluindo:
1. Nome da feature
2. Objetivo claro
3. Módulos afetados
4. User stories (mínimo 3)
5. Requisitos não-funcionais
6. Riscos identificados
7. Impacto macro
""",
            expected_output="Proposta inicial completa em formato PRD estruturado",
            agent=visionario
        )
        
        # ANTÍTESE
        print("📝 FASE 2: ANTÍTESE - Crítico Socrático attacking...")
        task_critica = Task(
            description=f"""
Aplique método socrático completo.

Analise a proposta do Visionário e liste TODAS:
1. Falhas e pontos fracos
2. Contradições com VISION.md
3. Riscos de drift
4. Overscope e dívida técnica
5. Requisitos não-funcionais esquecidos
6. User stories fracas ou incompletas

Seja implacável. Cada crítica deve ser específica e acionável.
""",
            expected_output="Crítica detalhada com lista de problemas e nota",
            agent=critico_socratico
        )
        
        # SÍNTESE
        print("📝 FASE 3: SÍNTESE - Sintetizador fusing...")
        task_sintese = Task(
            description=f"""
Produza a síntese final incorporando TODAS as críticas.

A síntese deve:
1. Preservar o que havia de bom na tese
2. Incoporar TODAS as críticas da antítese
3. Eliminar TODAS as fraquezas identificadas
4. Ser melhor que ambas as propostas individuais
5. Estar alinhada com VISION.md

Output: PRD completo com user stories corrigidas.
""",
            expected_output="Versão final refinada do PRD",
            agent=sintetizador
        )
        
        # VALIDAÇÃO - Recebe contexto das tarefas anteriores
        print("📝 FASE 4: VALIDAÇÃO - Validador evaluating...")
        task_validacao = Task(
            description=f"""
Analise a síntese final do Sintetizador e retorne JSON PURO.

O PRD gerado está disponível no contexto. Avalie e retorne:

{{
    "quality_score": 8.5,
    "consensus_reached": true,
    "final_validation_notes": "notas"
}}

Calcule quality_score (média 1-10 dos itens abaixo):
1. Feature alinhada com visão macro?
2. Módulos afetados considerados?
3. Riscos mitigados?
4. Requisitos não-funcionais cobertos?
5. User stories consistentes?
6. 5+ perguntas anti-drift?

Se média >= 9.0, consensus_reached = true

RETORNE APENAS O JSON.
""",
            expected_output="JSON puro com quality_score",
            agent=validador_macro,
            context=[task_vision, task_critica, task_sintese]  # Recebe output das outras tasks
        )
        
        # Executa Crew
        crew = Crew(
            agents=[visionario, critico_socratico, sintetizador, validador_macro],
            tasks=[task_vision, task_critica, task_sintese, task_validacao],
            process="sequential",
            verbose=True
        )
        
        resultado = crew.kickoff(
            inputs={
                "feature_objective": feature_request,
                "vision_content": vision_content
            }
        )
        
        # Extrai resultado (sem Pydantic para evitar problemas)
        resultado_raw = str(resultado)
        
        # Remove markdown code blocks se houver
        import re
        resultado_clean = re.sub(r'```json\s*', '', resultado_raw)
        resultado_clean = re.sub(r'```\s*$', '', resultado_clean)
        
        # Tenta extrair quality_score do resultado
        score_match = re.search(r'quality_score["\s:]+([0-9]+\.?[0-9]*)', resultado_clean, re.IGNORECASE)
        quality_score = float(score_match.group(1)) if score_match else 5.0
        
        # Verifica se consensus_reached
        consensus = "consensus_reached" in resultado_clean.lower() and "true" in resultado_clean.lower()
        
        # Extrai notas
        notes_match = re.search(r'final_validation_notes["\s:]+["\']?([^"\']{10,500})', resultado_clean, re.IGNORECASE)
        notes = notes_match.group(1) if notes_match else "Validação concluída"
        
        # Salva o PRD completo
        prd_data = {
            "feature_request": feature_request,
            "quality_score": quality_score,
            "consensus_reached": consensus,
            "final_validation_notes": notes,
            "full_output": resultado_clean[:10000]  # Primeiros 10k chars
        }
        
        print(f"\n{'='*60}")
        print(f"📊 QUALITY SCORE: {quality_score}/10.0")
        print(f"{'='*60}")
        
        if quality_score >= 9.0:
            print(f"🎉 APROVADO!")
            break
        else:
            print(f"❌ Reprovado. Tentativa {retry + 1}")
            print(f"   O que falta: {notes[:200]}...")
    
    # Salva resultado
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{OUTPUT_DIR}/PRD_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(prd_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ PRD Salvo em: {filename}")
    
    return {
        "quality_score": quality_score,
        "consensus_reached": consensus,
        "prd": prd_data,
        "filename": filename
    }


if __name__ == "__main__":
    import sys
    
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Teste"
    
    # Lê VISION.md
    if os.path.exists("VISION.md"):
        with open("VISION.md", "r") as f:
            vision = f.read()
    else:
        vision = "Projeto de gestão de projetos ágeis"
    
    result = run_dialectic(feature, vision)
    print(f"\n📈 Score Final: {result['quality_score']}/10.0")
