import os
import sys
from typing import List, Dict, Any, Tuple

# Assicuriamoci che la radice del progetto sia accessibile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vector_store import initialize_vector_store

def retrieve_brand_context(
    query: str, 
    categories: List[str], 
    k_per_category: int = 2
) -> List[Tuple[Any, float]]:
    """
    Esegue un recupero contestuale multi-partizione applicando l'Hard Filtering.
    
    Per evitare che una categoria dominante saturi i risultati (es. solo chunk 
    delle Personas), la funzione interroga ChromaDB partizionando la ricerca 
    per ciascuna categoria richiesta, garantendo un contesto bilanciato.
    
    Args:
        query: La richiesta testuale (es. "Scrivi un post per presentare il corso")
        categories: Lista di categorie da includere (es. ["target_personas", "tone_of_voice"])
        k_per_category: Numero di chunk da recuperare per singola categoria
        
    Returns:
        Lista di tuple (Document, Score/Distance) dei chunk estratti
    """
    vector_store = initialize_vector_store()
    all_retrieved_documents = []
    
    # Prepariamo la query con il prefisso formale per il modello E5
    formatted_query = f"query: {query}"
    
    print(f"\n[Orchestrator] Avvio recupero semantico per query: '{query}'")
    
    for category in categories:
        # Applichiamo l'operatore nativo $eq di ChromaDB per l'Hard Filtering
        metadata_filter = {"category": {"$eq": category}}
        
        print(f" -> Esecuzione Hard Filtering per categoria: '{category}'")
        
        # Interrogazione mirata alla singola partizione
        category_results = vector_store.similarity_search_with_score(
            query=formatted_query,
            k=k_per_category,
            filter=metadata_filter
        )
        
        print(f"    Trovati {len(category_results)} chunk pertinenti.")
        all_retrieved_documents.extend(category_results)
        
    return all_retrieved_documents

def build_prompt_context(retrieved_results: List[Tuple[Any, float]]) -> str:
    """
    Formatta i chunk recuperati e validati in un blocco di testo strutturato 
    da iniettare nel prompt di sistema dell'LLM, strutturandoli per categoria.
    """
    context_sections = {}
    
    for doc, score in retrieved_results:
        category = doc.metadata.get("category", "generic")
        if category not in context_sections:
            context_sections[category] = []
        context_sections[category].append(doc.page_content)
        
    formatted_context = "=== CONTESTO DI BRAND AZIENDALE STRUTTURATO ===\n\n"
    for category, contents in context_sections.items():
        formatted_context += f"## CATEGORIA: {category.upper()}\n"
        for i, content in enumerate(contents):
            formatted_context += f"[Documento {i+1}]:\n{content}\n\n"
            
    return formatted_context