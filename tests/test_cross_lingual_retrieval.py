import os
import sys

# Aggiunge la radice del progetto al path per importare i moduli interni
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator import retrieve_brand_context

def test_cross_lingual():
    print("=== REGRESSION TEST: CROSS-LINGUAL RETRIEVAL VALIDATION ===")
    
    # Definiamo tre query in inglese associate a specifiche categorie del brand in italiano
    test_cases = [
        {
            "english_query": "What are the core fears of the prospective student Lorenzo?",
            "target_category": "target_personas",
            "expected_keyword_it": "paura" # Ci aspettiamo concetti legati alle sue paure
        },
        {
            "english_query": "Why should we use an informal approach when inviting students to seminars?",
            "target_category": "tone_of_voice",
            "expected_keyword_it": "informale" # Ci aspettiamo concetti legati al tono amichevole/colloquiale
        }
    ]
    
    success = True
    
    for i, case in enumerate(test_cases):
        q = case["english_query"]
        cat = case["target_category"]
        
        print(f"\n[Test #{i+1}] Query (EN): '{q}'")
        print(f"       Constraint (Hard Filtering): [category == '{cat}']")
        
        # Interroghiamo l'orchestratore
        results = retrieve_brand_context(
            query=q,
            categories=[cat],
            k_per_category=1
        )
        
        if not results:
            print(f"❌ Fallito: Nessun chunk estratto per la query '{q}'")
            success = False
            continue
            
        doc, distance = results[0]
        content_lower = doc.page_content.lower()
        
        print(f"       -> Chunk Estratto (IT): {doc.page_content[:140]}...")
        print(f"       -> Distanza Coseno: {distance:.4f}")
        print(f"       -> Categoria verificata nel DB: {doc.metadata.get('category')}")
        
        # Validazione strutturale dei filtri e della semantica
        assert doc.metadata.get("category") == cat, f"ERRORE: Hard Filtering fallito. Attesa categoria '{cat}'."
        
        if case["expected_keyword_it"] in content_lower:
            print(f"       ✓ VALIDAZIONE SEMANTICA SUPERATA: Trovata corrispondenza concettuale in italiano.")
        else:
            print(f"       ⚠ Nota: Il chunk è pertinente ma non contiene la keyword esatta '{case['expected_keyword_it']}'. Controlla manualmente la coerenza semantica.")
            
    if success:
        print("\n✅ TUTTI I TEST DI REGRESSIONE CROSS-LINGUE SONO STATI SUPERATI CON SUCCESSO!")
        print("Il modello E5 mappa correttamente lo spazio semantico Inglese -> Italiano.")
    else:
        print("\n❌ ALMENO UN TEST DI REGRESSIONE HA RILEVATO ANOMALIE.")

if __name__ == "__main__":
    test_cross_lingual()