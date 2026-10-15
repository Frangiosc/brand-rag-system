import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Configurazione percorsi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data", "vector_store")

def initialize_vector_store():
    """Inizializza il Vector Store locale ChromaDB con metrica di similarità COSINE."""
    # Definiamo lo stesso modello di embedding configurato nella fase di ingestion
    embedding_model = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        model_kwargs={'device': 'cpu'}, # Puoi impostare 'cuda' o 'mps' se hai accelerazione hardware
        encode_kwargs={'normalize_embeddings': True} # Ottimizza per la similarità coseno
    )
    
    # Connessione al database persistente
    vector_store = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embedding_model,
        collection_name="brand_knowledge_core",
        collection_metadata={"hnsw:space": "cosine"} # Forza la metrica di similarità geometrica
    )
    return vector_store

def query_semantic_with_filter(query_text: str, category_filter: str = None, k: int = 3):
    """
    Esegue una ricerca semantica nel Vector Store applicando un Hard Filtering
    sui metadati (category) tramite gli operatori nativi di ChromaDB ($eq).
    """
    vector_store = initialize_vector_store()
    
    # Applichiamo il prefisso "query: " richiesto dal modello E5 per la fase di retrieval
    formatted_query = f"query: {query_text}"
    
    # Costruiamo il filtro sui metadati se specificato
    metadata_filter = None
    if category_filter:
        metadata_filter = {
            "category": {"$eq": category_filter}
        }
    
    # MODIFICA: Usiamo similarity_search_with_score per evitare il filtro di soglia automatico
    results = vector_store.similarity_search_with_score(
        query=formatted_query,
        k=k,
        filter=metadata_filter
    )
    
    return results