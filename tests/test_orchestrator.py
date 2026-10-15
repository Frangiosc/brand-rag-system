import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator import retrieve_brand_context, build_prompt_context

def main():
    print("=== TEST ORCHESTRATORE: RETRIEVAL MULTI-PARTIZIONE ===")
    
    # Chiediamo informazioni per creare un post, richiedendo Personas e Tone of Voice
    query = "Crea un post per presentare la UX ad un ex studente ITIS"
    categories_to_retrieve = ["target_personas", "tone_of_voice"]
    
    results = retrieve_brand_context(
        query=query, 
        categories=categories_to_retrieve, 
        k_per_category=1
    )
    
    print("\n" + "="*60)
    print("CONTESTO FORMATTATO PRONTO PER L'LLM:")
    print("="*60)
    
    context_prompt = build_prompt_context(results)
    print(context_prompt)
    
    # Validazione di sicurezza
    assert len(results) == 2, f"Errore: ci aspettavamo 2 chunk totali, ne abbiamo ricevuti {len(results)}"
    print("✅ TEST COMPLETATO CON SUCCESSO: L'orchestratore ha bilanciato il contesto senza rumore!")

if __name__ == "__main__":
    main()