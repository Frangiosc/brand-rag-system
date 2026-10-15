import os
import sys

# Aggiunge la radice del progetto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vector_store import query_semantic_with_filter

def test_filters():
    print("=== TEST HARD FILTERING (METADATA CLASSIFICATION) ===")
    
    # Cerchiamo informazioni su "Lorenzo" filtrando rigidamente solo sulla categoria "target_personas"
    query = "Chi è Lorenzo?"
    category = "target_personas"
    
    print(f"\n🔍 Query: '{query}' | Filtro applicato: [category == '{category}']")
    
    results = query_semantic_with_filter(query_text=query, category_filter=category, k=2)
    
    if not results:
        print("❌ Nessun risultato trovato. Verifica l'ingestion.")
        return
        
    for i, (doc, distance) in enumerate(results):
        print(f"\n[Risultato #{i+1}] (Distanza Coseno: {distance:.4f})")
        print(f" -> File: {doc.metadata.get('source_file')}")
        print(f" -> Categoria reale nel DB: {doc.metadata.get('category')}")
        print(f" -> Testo estratto: {doc.page_content[:150]}...")
        
        # Verifica di sicurezza: la categoria deve corrispondere al filtro
        assert doc.metadata.get('category') == category, "ERRORE: Il filtro ha fallito! Estratto chunk non pertinente."
        
    print("\n✅ TEST SUPERATO: L'Hard Filtering nativo funziona perfettamente e isola il contesto!")

if __name__ == "__main__":
    test_filters()