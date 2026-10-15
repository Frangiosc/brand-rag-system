import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vector_store import initialize_vector_store

def debug():
    print("=== DIAGNOSI DATABASE LOCALE ===")
    vector_store = initialize_vector_store()
    
    # 1. Controlliamo quanti elementi ci sono davvero nella collection
    count = vector_store._collection.count()
    print(f"Numero di vettori registrati nella collection: {count}")
    
    if count == 0:
        print("❌ Il database è vuoto! Dobbiamo rieseguire l'ingestion da Streamlit per salvare i dati su disco.")
        return
        
    # 2. Vediamo i metadati dei primi elementi presenti per capire come sono scritti
    db_data = vector_store._collection.get(limit=5)
    print("\nPrimi metadati trovati nel database:")
    for i, meta in enumerate(db_data.get("metadatas", [])):
        print(f" -> Elemento #{i}: {meta}")

if __name__ == "__main__":
    debug()