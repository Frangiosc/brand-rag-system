# src/ingestion.py
import os
import json
import pdfplumber

def run_semantic_ingestion(base_dir="documents_ui"):
    """
    Scansiona i 6 slot della UI (incluso il nuovo slot per gli esempi few-shot), 
    estrae il testo tramite pdfplumber (PDF) o lettori nativi (TXT/JSON), 
    applica il chunking ricorsivo e inietta automaticamente i metadati tassonomici.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Mappatura delle cartelle-slot ai rispettivi metadati (Hard Filtering)
    # Aggiunto il sesto slot dedicato agli esempi di ispirazione per il Few-Shot Learning
    ui_mapping = {
        "1_personas": {"category": "target_personas"},
        "2_social_voice": {"category": "social_media_voice"},
        "3_tone_of_voice": {"category": "tone_of_voice"},
        "4_funnel_stages": {"category": "funnel_stages"},
        "5_rubrics": {"category": "rubriche"},
        "6_esempi_ispirazione": {"category": "esempi_ispirazione"} 
    }
    
    # Configurazione dello splitter ricorsivo (500 caratteri, 10% overlap)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    
    all_chunks = []
    
    print("=== INIZIO ESTRAZIONE SEMANTICA DA FILE DI COMPRENSIONE ===")
    
    for folder_name, base_metadata in ui_mapping.items():
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        # Legge tutti i file all'interno dello slot specifico
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            testo_estratto = ""
            
            # --- CASO 1: Gestione file PDF standard ---
            if file_name.endswith('.pdf'):
                print(f"\n[Loader - pdfplumber] Estrazione testo dal PDF: {file_name}")
                testo_estratto_pdf = ""
                with pdfplumber.open(file_path) as pdf:
                    for pagina in pdf.pages:
                        testo_pagina = pagina.extract_text()
                        if testo_pagina:
                            testo_estratto_pdf += testo_pagina + "\n"
                testo_estratto = " ".join(testo_estratto_pdf.split())
            
            # --- CASO 2: Gestione file TXT (Comodo per copiare/incollare post storici) ---
            elif file_name.endswith('.txt'):
                print(f"\n[Loader - Native] Estrazione testo dal file TXT: {file_name}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    testo_estratto = " ".join(f.read().split())
                    
            # --- CASO 3: Gestione file JSON (Ideale per coppie strutturate Post + Descrizione Grafica) ---
            elif file_name.endswith('.json'):
                print(f"\n[Loader - JSON] Estrazione ed formattazione dati dal file JSON: {file_name}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Formattiamo il JSON in una stringa esplicita leggibile semanticamente dall'LLM
                        if isinstance(data, dict):
                            post_text = data.get("post_text", data.get("copy", ""))
                            img_desc = data.get("image_description", data.get("grafica", ""))
                            label = data.get("label", file_name)
                            testo_estratto = (
                                f"ESEMPIO DI POST DI SUCCESSO ({label}):\n"
                                f"--- TESTO COPY ---\n{post_text}\n"
                                f"--- STILE GRAFICA DI RIFERIMENTO ---\n{img_desc}"
                            )
                except Exception as e:
                    print(f"⚠️ Errore nel parsing del file JSON {file_name}: {e}")
                    continue

            # --- CASO 4: Gestione immagini di riferimento (PNG) ---
            elif file_name.endswith('.png') and base_metadata["category"] == "esempi_ispirazione":
                print(f"\n[Loader - Vision Asset] Rilevata immagine di riferimento layout: {file_name}")
                
                # Cerchiamo se esiste un file .txt o .json con lo stesso nome che ne descrive il layout
                # Es: se hai 'post_cyber.png', puoi avere 'post_cyber.txt' con la descrizione geometrica
                base_name = os.path.splitext(file_name)[0]
                desc_path = os.path.join(folder_path, f"{base_name}.txt")
                
                if os.path.exists(desc_path):
                    with open(desc_path, 'r', encoding='utf-8') as f:
                        descrizione_layout = f.read()
                else:
                    # Fallback autogenerato se non c'è una descrizione manuale
                    descrizione_layout = f"Esempio visivo di brand asset denominato {base_name}. Struttura grafica ufficiale coordinata."
                
                testo_estratto = (
                    f"RICEVUTO ASSET VISIVO DI RIFERIMENTO GRAFICO:\n"
                    f"- Nome File Immagine: {file_name}\n"
                    f"- Percorso Asset: {file_path}\n"
                    f"- Descrizione Geometrica del Layout: {descrizione_layout}"
                )
                
                # In questo caso iniettiamo direttamente nei metadati il percorso del PNG
                base_metadata["visual_asset_path"] = file_path
            
            # Se il file non rientra nelle estensioni supportate o è vuoto, saltalo
            if not testo_estratto:
                continue
                
            # Esecuzione del Chunking
            chunks = text_splitter.split_text(testo_estratto)
            
            # Iniezione Deterministica dei Metadati
            for i, chunk_text in enumerate(chunks):
                meta = base_metadata.copy()
                meta["source_file"] = file_name
                meta["chunk_index"] = i
                
                all_chunks.append({
                    "page_content": chunk_text,
                    "metadata": meta
                })
                print(f" -> Creato Chunk #{i} ({len(chunk_text)} caratteri) per lo slot '{folder_name}'")
                    
    print(f"\n[Ingestion Core] Elaborazione completata. Generati {len(all_chunks)} chunk pronti per il Vector DB.")
    return all_chunks