"""
Flow principal com retry automático até quality_score >= 9.0
Implementa a dialética: Tese → Antítese → Síntese → Validação → Loop
Usa CrewAI Flow API com estado persistente
"""

import json
import os
from datetime import datetime
from crewai.flow import Flow, start, listen, router
from pydantic import BaseModel
from crewai import Task, Crew
from agents import visionario, critico_socratico, sintetizador, validador_macro
from schemas import PRDSchema


# Configuração
MAX_RETRIES = 5
OUTPUT_DIR = "prd_output"


class DialecticState(BaseModel):
    """Estado persistente do fluxo dialético"""
    feature_objective: str = ""
    vision_content: str = ""
    prd_data: dict = {}
    quality_score: float = 0.0
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    consensus_reached: bool = False
    final_validation_notes: str = ""


class DialecticFlow(Flow[DialecticState]):
    """Fluxo dialético com retry automático"""
    
    @start()
    def iniciar_dialetica(self):
        """Inicia o fluxo dialético"""
        print(f"\n{'='*60}")
        print(f"🚀 INICIANDO FLUXO DIALÉTICO")
        print(f"{'='*60}")
        print(f"Feature: {self.state.feature_objective}")
        print(f"Max retries: {self.state.max_retries}")
        print(f"{'='*60}\n")
        return "rodar_rodada"
    
    @listen("rodar_rodada")
    def rodar_rodada_dialetica(self):
        """Executa uma rodada completa: tese → antítese → síntese → validação"""
        
        print(f"\n{'🔄'*20}")
        print(f"📍 RODADA {self.state.retry_count + 1}/{self.state.max_retries}")
        print(f"{'🔄'*20}\n")
        
        # ---------------------------------------------------------
        # TAREFA 1: TESE - Visionário propõe
        # ---------------------------------------------------------
        print("📝 FASE 1: TESE - Visionário proposing...")
        
        task_vision = Task(
            description=f"""
Objetivo: {self.state.feature_objective}

VISÃO MACRO DO SISTEMA:
{self.state.vision_content}

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
        
        # ---------------------------------------------------------
        # TAREFA 2: ANTÍTESE - Crítico ataca
        # ---------------------------------------------------------
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
        
        # ---------------------------------------------------------
        # TAREFA 3: SÍNTESE - Sintetizador funde
        # ---------------------------------------------------------
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
        
        # ---------------------------------------------------------
        # TAREFA 4: VALIDAÇÃO - Validador aprova
        # ---------------------------------------------------------
        print("📝 FASE 4: VALIDAÇÃO - Validador evaluating...")
        
        task_validacao = Task(
            description=f"""
Avalie a síntese final e retorne EXATAMENTE o schema PRDSchema.

Responda com:
- quality_score: float (exatamente uma casa decimal)
- consensus_reached: true/false
- final_validation_notes: explicação detalhada

Se score < 9.0, explique EXATAMENTE o que ainda precisa melhorar.

Checklist:
1. ✅ Feature alinhada com visão macro?
2. ✅ Módulos afetados considerados?
3. ✅ Riscos mitigados?
4. ✅ Requisitos não-funcionais cobertos?
5. ✅ User stories consistentes?
6. ✅ 5+ perguntas anti-drift respondidas?
""",
            expected_output="JSON válido do PRDSchema com quality_score",
            agent=validador_macro,
            output_pydantic=PRDSchema
        )
        
        # ---------------------------------------------------------
        # EXECUTA CREW HIERÁRQUICO
        # ---------------------------------------------------------
        crew = Crew(
            agents=[visionario, critico_socratico, sintetizador, validador_macro],
            tasks=[task_vision, task_critica, task_sintese, task_validacao],
            process="hierarchical",
            manager_llm="gpt-4o",  # Ou outro LLM configurado
            verbose=2
        )
        
        resultado = crew.kickoff(
            inputs={
                "feature_objective": self.state.feature_objective,
                "vision_content": self.state.vision_content
            }
        )
        
        # ---------------------------------------------------------
        # ATUALIZA ESTADO
        # ---------------------------------------------------------
        if hasattr(resultado, 'pydantic'):
            # Resultado é Pydantic
            self.state.prd_data = resultado.pydantic.model_dump()
            self.state.quality_score = resultado.pydantic.quality_score
            self.state.consensus_reached = resultado.pydantic.consensus_reached
            self.state.final_validation_notes = resultado.pydantic.final_validation_notes
        elif hasattr(resultado, 'raw'):
            # Resultado tem .raw
            self.state.prd_data = resultado.raw
            self.state.quality_score = getattr(resultado, 'pydantic', {}).get('quality_score', 5.0) if hasattr(resultado, 'pydantic') else 5.0
        else:
            # Fallback
            self.state.prd_data = {"raw": str(resultado)}
            self.state.quality_score = 5.0
        
        print(f"\n{'='*60}")
        print(f"📊 QUALITY SCORE: {self.state.quality_score}/10.0")
        print(f"{'='*60}")
        
        return "avaliar"
    
    @router(avaliar)
    def decidir_proximo_passo(self):
        """Decide se aprova ou faz retry"""
        
        if self.state.quality_score >= 9.0:
            print(f"🎉 APROVADO! Quality score: {self.state.quality_score}")
            return "aprovar"
        elif self.state.retry_count >= self.state.max_retries:
            print(f"⚠️ Max retries atingido. Finalizando com score: {self.state.quality_score}")
            return "aprovar"  # Força aprovação após max retries
        else:
            self.state.retry_count += 1
            print(f"❌ Reprovado. Retry #{self.state.retry_count}")
            print(f"   O que falta: {self.state.final_validation_notes[:200]}...")
            return "retry"
    
    @listen("retry")
    def fazer_retry(self):
        """Reinicia o fluxo para nova rodada"""
        return "rodar_rodada"
    
    @listen("aprovar")
    def salvar_prd_final(self):
        """Salva o PRD aprovado em arquivo JSON"""
        from schemas import PRDSchema
        
        # Garante diretório existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{OUTPUT_DIR}/PRD_{timestamp}.json"
        
        # Cria PRD com validação
        try:
            prd = PRDSchema.model_validate(self.state.prd_data)
        except Exception:
            # Se não validar, cria básico
            prd = PRDSchema(
                feature_name=self.state.feature_objective,
                objective=self.state.feature_objective,
                macro_impact=self.state.prd_data.get("macro_impact", {}),
                user_stories=self.state.prd_data.get("user_stories", []),
                anti_drift_questions=self.state.prd_data.get("anti_drift_questions", []),
                quality_score=self.state.quality_score,
                consensus_reached=self.state.consensus_reached,
                final_validation_notes=self.state.final_validation_notes
            )
        
        # Sobrescreve com dados do estado
        prd.quality_score = self.state.quality_score
        prd.consensus_reached = self.state.consensus_reached
        prd.final_validation_notes = self.state.final_validation_notes
        
        # Salva
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(prd.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ PRD APROVADO com nota {self.state.quality_score}!")
        print(f"💾 Salvo em: {filename}")
        
        return prd


def run_dialectic_flow(feature_request: str, vision_content: str) -> dict:
    """
    Executa o fluxo dialético completo.
    
    Args:
        feature_request: Descrição da feature a ser desenvolvida
        vision_content: Conteúdo do arquivo VISION.md
    
    Returns:
        Dicionário com o resultado final
    """
    
    state = DialecticState(
        feature_objective=feature_request,
        vision_content=vision_content,
        max_retries=MAX_RETRIES
    )
    
    flow = DialecticFlow(state)
    result = flow.kickoff()
    
    return {
        "success": result.consensus_reached or result.quality_score >= 9.0,
        "quality_score": result.quality_score,
        "iterations": result.retry_count + 1,
        "prd": result.prd_data,
        "consensus_reached": result.consensus_reached,
        "validation": result.final_validation_notes
    }


if __name__ == "__main__":
    # Teste rápido - usado internamente
    pass
