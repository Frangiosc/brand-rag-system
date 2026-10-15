import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration, get_channel_templates
from src.prompt_builder import build_system_prompt, assemble_final_prompt

def test_prompt_builder():
    print("=== TEST PROMPT BUILDER: FUSIONE DATI STRUTTURATI E NON STRUTTURATI ===")
    
    # 1. Simuliamo l'estrazione di contesto dal Vector DB (Dati non strutturati)
    simulated_context = (
        "## CATEGORIA: TARGET_PERSONAS\n"
        "[Documento 1]: - Lorenzo - Età: 19; Studente ITIS appassionato di informatica, ma ha paura della complessità dell'università.\n\n"
        "## CATEGORIA: TONE_OF_VOICE\n"
        "[Documento 1]: Usa un tono informale e amichevole. Coinvolgi direttamente gli studenti parlando in modo semplice e diretto."
    )
    
    # 2. Carichiamo i vincoli strutturati dal JSON ufficiale (Instagram)
    try:
        config = load_brand_configuration()
        channel_name = "instagram"
        channel_data = get_channel_templates(config, channel_name)
        
        # 3. Generiamo i prompt
        system_prompt = build_system_prompt()
        final_prompt = assemble_final_prompt(
            user_query="Scrivi un post per invitare Lorenzo a scoprire il corso di UX Design.",
            retrieved_context=simulated_context,
            channel_name=channel_name,
            channel_constraints=channel_data
        )
        
        print("\n--- SYSTEM PROMPT (SYSTEM ROLE) ---")
        print(system_prompt)
        
        print("\n--- USER PROMPT ASSEMBLATO ---")
        print(final_prompt)
        
        # Asserzioni di sicurezza (corrette per essere case-insensitive)
        assert "lorenzo" in final_prompt.lower(), "Errore: contesto mancante!"
        assert "instagram" in final_prompt.lower(), "Errore: canale mancante!"
        assert "2200" in final_prompt, "Errore: limite caratteri del JSON non incorporato!"
        print("\n✅ TEST SUPERATO: Il Prompt Builder fonde perfettamente i due mondi informativi!")
        
    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione del test: {str(e)}")

if __name__ == "__main__":
    test_prompt_builder()