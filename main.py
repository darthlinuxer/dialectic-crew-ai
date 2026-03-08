"""
Ponto de entrada principal do Dialectic Crew AI
用法: python main.py "sua feature request"
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa o fluxo
from flow import DialecticFlow, OUTPUT_DIR


def main():
    """Função principal"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🔷 DIALECTIC CREW AI - PRD Generator v1.0 🔷           ║
║                                                              ║
║     Dialética Socrática/Hegeliana:                         ║
║     Tese → Antítese → Síntese → Validação → Loop           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Verifica API key
    has_api_key = bool(
        os.getenv("OPENAI_API_KEY") or 
        os.getenv("ANTHROPIC_API_KEY") or 
        os.getenv("MINIMAX_API_KEY") or
        os.getenv("GROQ_API_KEY")
    )
    
    if not has_api_key:
        print("⚠️  Configure sua API key primeiro!")
        print("   Copie .env.example para .env e adicione a key\n")
    
    # Obtém a feature request
    if len(sys.argv) > 1:
        feature_request = " ".join(sys.argv[1:])
    else:
        print("📝 Informe a feature: python main.py 'sua feature aqui'")
        sys.exit(1)
    
    print(f"\n🚀 Feature: {feature_request}")
    print("="*60)
    
    # Cria e executa o fluxo
    flow = DialecticFlow()
    flow.state.feature_objective = feature_request
    
    # Lê VISION.md
    if os.path.exists("VISION.md"):
        with open("VISION.md", "r", encoding="utf-8") as f:
            flow.state.vision_content = f.read()
    else:
        print("⚠️  VISION.md não encontrado!")
        sys.exit(1)
    
    # Executa
    resultado = flow.kickoff()
    
    print("\n" + "="*60)
    print("🎉 PROCESSO DIALÉTICO CONCLUÍDO!")
    print("="*60)
    print(f"📈 Quality Score: {resultado.quality_score}/10.0")
    print(f"🔄 Total rodadas: {resultado.retry_count + 1}")
    print(f"✅ Consensus: {resultado.consensus_reached}")
    print("="*60)


if __name__ == "__main__":
    main()
