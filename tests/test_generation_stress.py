import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration, get_channel_templates
from src.prompt_builder import build_system_prompt, assemble_final_prompt
from src.generation import generate_social_post
from src.post_processor import clean_generated_post

def run_stress_test():
    print("=== STRESS TEST: STABILITÀ DEI LIMITI DI CARATTERI CON OLLAMA ===")
    
    # 1. Configurazione del contesto di test
    simulated_context = (
        "## CATEGORIA: TARGET_PERSONAS\n"
        "- Francesca: 21 anni, studentessa universitaria di Informatica interessata allo sviluppo backend ed intelligenza artificiale.\n\n"
        "## CATEGORIA: TONE_OF_VOICE\n"
        "- Professionale, autorevole ma accessibile. Usa elenchi puntati per favorire la leggibilità."
    )
    
    config = load_brand_configuration()
    
    # Scenari di test per i canali
    scenarios = [
        {
            "channel": "instagram",
            "format": "vertical",
            "query": "Scrivi un post molto breve ed incisivo per promuovere il nuovo laboratorio di cybersecurity di UNICAM.",
            "max_expected": 2200
        },
        {
            "channel": "linkedin",
            "format": "single_image_posts.square",  # Test su formato nidificato
            "query": "Scrivi un post lungo e dettagliato che spieghi i vantaggi accademici di scegliere la tesi sperimentale ad Informatica UNICAM.",
            "max_expected": 3000
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- [Scenario {i}/2] Canale: {scenario['channel'].upper()} ---")
        channel_data = get_channel_templates(config, scenario["channel"])
        
        # Estrarre il limite caratteri specifico dal formato configurato
        formats = channel_data.get("formats", {})
        if "." in scenario["format"]:
            parent, child = scenario["format"].split(".")
            limit = formats.get(parent, {}).get(child, {}).get("max_characters", scenario["max_expected"])
        else:
            limit = formats.get(scenario["format"], {}).get("max_characters", scenario["max_expected"])
            
        print(f"-> Limite caratteri impostato dal JSON per questo formato: {limit}")
        
        system_prompt = build_system_prompt()
        final_prompt = assemble_final_prompt(
            user_query=scenario["query"],
            retrieved_context=simulated_context,
            channel_name=scenario["channel"],
            channel_constraints=channel_data
        )
        
        start_time = time.time()
        
        try:
            # Generazione grezza
            raw_output = generate_social_post(
                system_prompt=system_prompt,
                user_prompt=final_prompt,
                model_name="llama3"
            )
            
            # Post-processing
            clean_output = clean_generated_post(raw_output)
            
            elapsed_time = time.time() - start_time
            char_count = len(clean_output)
            
            print(f"-> Tempo di risposta: {elapsed_time:.2f} secondi")
            print(f"-> Lunghezza post generato: {char_count} caratteri")
            
            # Controllo di conformità del limite
            if char_count <= limit:
                print(f"✅ CONFORMITÀ LIMITE: SUPERATA ({char_count}/{limit})")
            else:
                print(f"❌ CONFORMITÀ LIMITE: FALLITA ({char_count}/{limit})")
                
            print("\nAnteprima Copy Generato:")
            print("-" * 40)
            print(clean_output)
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ Errore durante lo scenario di test: {str(e)}")

if __name__ == "__main__":
    run_stress_test()