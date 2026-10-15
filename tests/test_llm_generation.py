import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration, get_channel_templates
from src.prompt_builder import build_system_prompt, assemble_final_prompt
from src.generation import generate_social_post

def test_generation_pipeline():
    print("=== TEST PIPELINE GENERATIVA CON OLLAMA (LLAMA 3) ===")
    
    # 1. Contesto fittizio di brand basato sulle tue personas
    simulated_context = (
        "## CATEGORIA: TARGET_PERSONAS\n"
        "- Lorenzo - Età: 19; Studente ITIS appassionato di codice ma spaventato dalla teoria universitaria matematica.\n\n"
        "## CATEGORIA: TONE_OF_VOICE\n"
        "- Usa un tono amichevole, informale, giovanile ed empatico. Parla in prima persona plurale ('Noi di Informatica Unicam')."
    )
    
    # 2. Caricamento vincoli e assemblaggio del prompt
    try:
        print("\n[1/3] Caricamento vincoli strutturati e creazione Prompt...")
        config = load_brand_configuration()
        channel_name = "instagram"
        channel_data = get_channel_templates(config, channel_name)
        
        system_prompt = build_system_prompt()
        final_prompt = assemble_final_prompt(
            user_query="Scrivi un post Instagram per far capire ai nuovi iscritti che ad informatica facciamo tantissimi laboratori pratici fin dal primo anno.",
            retrieved_context=simulated_context,
            channel_name=channel_name,
            channel_constraints=channel_data
        )
        
        # 3. Invio a Ollama
        print("[2/3] Connessione a Ollama locale e generazione in corso (questo può richiedere secondi)...")
        post_generato = generate_social_post(
            system_prompt=system_prompt,
            user_prompt=final_prompt,
            model_name="llama3" # Se usi un tag diverso (es: llama3.1), cambialo qui
        )
        
        print("\n[3/3] ✨ COPY GENERATO DALL'LLM LOCALE: ✨")
        print("="*60)
        print(post_generato)
        print("="*60)
        
        # Validazione formale dell'output
        assert len(post_generato) > 0, "Errore: testo generato vuoto."
        print("\n✅ TEST DI GENERAZIONE LOCALE SUPERATO CON SUCCESSO!")
        
    except Exception as e:
        print(f"\n❌ Errore durante il test generativo: {str(e)}")

if __name__ == "__main__":
    test_generation_pipeline()