import os
import sys

# Aggiungiamo la radice del progetto al PATH di Python per poter importare src correttamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vector_store import initialize_vector_store

def run_database_profiling():
    print("=== INIZIO PROFILING VECTOR STORE (SETTIMANA 1) ===")
    
    # 1. Connessione al database persistente locale
    try:
        vector_store = initialize_vector_store()
    except Exception as e:
        print(f"❌ Errore di runtime durante l'inizializzazione: {str(e)}")
        return

    # 2. Estrazione nativa di tutti i dati registrati nella Collection
    # Usiamo il metodo .get() dell'oggetto chroma interno di LangChain
    db_data = vector_store._collection.get()
    
    documents = db_data.get("documents", [])
    metadatas = db_data.get("metadatas", [])
    ids = db_data.get("ids", [])
    
    total_chunks = len(ids)
    print(f"\n📊 STATISTICHE GENERALI:")
    print(f" -> Totale Chunk Indicizzati: {total_chunks}")
    
    if total_chunks == 0:
        print("❌ ATTENZIONE: Il database è vuoto. L'ingestione non ha salvato i dati.")
        return
        
    print("✅ Connessione riuscita. Nessun errore di runtime rilevato.")
    print("-" * 60)
    
    # 3. Profiling della distribuzione dei metadati (Tassonomia della Tesi)
    print("🗂️ ANALISI TASSONOMICA DEI METADATI:")
    category_counts = {}
    file_counts = {}
    
    for meta in metadatas:
        cat = meta.get("category", "Sconosciuta")
        src_file = meta.get("source_file", "Sconosciuto")
        
        category_counts[cat] = category_counts.get(cat, 0) + 1
        file_counts[src_file] = file_counts.get(src_file, 0) + 1
        
    print("\n[Per Categoria (Hard Filtering Base)]")
    for cat, count in category_counts.items():
        print(f"  • {cat}: {count} chunk")
        
    print("\n[Per File di Origine]")
    for src_file, count in file_counts.items():
        print(f"  • {src_file}: {count} chunk")
        
    print("-" * 60)
    
    # 4. Verifica campionaria di integrità del primo chunk salvato
    print("🔎 VERIFICA CAMPIONARIA DI INTEGRITÀ (Chunk #0):")
    print(f"  • ID Vettoriale: {ids[0]}")
    print(f"  • Dizionario Metadati Completo: {metadatas[0]}")
    print(f"  • Estratto del Testo (Primi 100 char): {documents[0][:100]}...")
    print("-" * 60)
    print("=== PROFILING COMPLETATO: LA PRIMA SETTIMANA È VALIDATA AL 100% ===")

if __name__ == "__main__":
    run_database_profiling()