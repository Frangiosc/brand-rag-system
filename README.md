# Brand RAG System — Multimodal Retrieval & Brand Layout Engine

Piattaforma avanzata di generazione, validazione e orchestrazione di contenuti social basata su architettura **RAG (Retrieval-Augmented Generation)** multimodale per i canali ufficiali di **@unicamente_informatica** (Dipartimento di Informatica — Università di Camerino).

Il sistema combina un motore di semantic retrieval partizionato (ChromaDB + Hard Filtering), un'interfaccia di copy generation alimentata da LLM open-weight ad alte prestazioni (**Qwen 2.5 14B**) e un layout engine programmatico (Pillow + esportazione SVG nativa) per la produzione automatizzata di asset visivi coordinati e tipograficamente validati.

---

## 🏗️ Architettura del Sistema

```text
[ Knowledge Base ] -> [ Ingestion & Vector Store (ChromaDB) ]
       |                            |
       v                            v
[ Brand Config JSON ] ---> [ Dynamic Orchestrator ] <--- [ User Prompt ]
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
           [ Qwen 2.5 14B ]               [ Layout Engine ]
        (Copywriting & Context)           (Pillow & SVG Generator)
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                     [ Streamlit UI Interactive Studio ]
```

Il sistema è strutturato su pipeline modulari indipendenti:
1. **Frontend & Interactive Studio (`Streamlit`)**:
   - **Content Generation Workspace**: Configurazione canale (Instagram/LinkedIn), selezione aspect ratio geometrico (4:5, 1:1, 9:16, 1.91:1) e generazione simultanea di testo + cartolina grafica coordinata.
   - **Interactive Refinement Chat**: Modifica conversazionale dei campi (titoli, relatori, orari, date, asset e palette) con re-render in tempo reale.
   - **Brand Workspace**: Upload, catalogazione e re-indexing vettoriale della Knowledge Base istituzionale (Personas, Social Voice, Tone of Voice, Funnel Stages, Rubriche, Asset visivi).
2. **Retrieval & Semantic Ingestion**:
   - Embedding multilingua ad alta densità informativa.
   - Hard Filtering partizionato tramite metadati ChromaDB per prevenire la saturazione del contesto tra categorie eterogenee.
3. **Inference Backend (LLM)**:
   - **Default Model**: `qwen2.5:14b` (gestito nativamente o in container tramite Ollama).
   - Prompt engineering ChatML nativo con iniezione di vincoli geometrici (character limits per canale), divieto di allucinazioni e zero-placeholder enforcement.
4. **Programmatic Graphics Engine**:
   - Motore tipografico basato su Pillow con supporto font istituzionali (*Sora*), wrapping dinamico, calibrazione watermark/mascotte e switch dinamico delle palette per corso di laurea (*Informatica*, *Informatica per la Comunicazione Digitale*, *Computer Science*).
   - Generatore vettoriale parallelo con esportazione standard `.svg`.

---

## 📋 Requisiti di Sistema

### Esecuzione Locale Nativa (Consigliata per Sviluppo)
- **macOS** (Apple Silicon M1/M2/M3/M4 consigliato, min. 16–18 GB RAM per Qwen 14B Q4) o **Linux / Windows WSL2** con GPU dedicata (>= 12 GB VRAM).
- **Python 3.10+**.
- **Ollama** installato e configurato a livello di sistema.

### Esecuzione Containerizzata (Docker)
- **Docker Desktop** attivo con allocazione minima consigliata:
  - RAM: **almeno 12 GB** (se si esegue Ollama con modello 14B all'interno del container).
  - CPU: **4–6 Core**.
  - Spazio libero su disco: **~15 GB** per pesi del modello e immagini.

---

## 🚀 Guida all'Avvio

### Opzione A: Esecuzione Locale (Sviluppo Rapido)

1. **Clonare il repository e creare l'ambiente virtuale:**
   ```bash
   git clone [https://github.com/Frangiosc/brand-rag-system.git](https://github.com/Frangiosc/brand-rag-system.git)
   cd brand-rag-system
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt


2. **Scaricare e avviare il modello su Ollama**
Assicurati che Ollama sia attivo in background, quindi scarica il modello:

```bash
ollama pull qwen2.5:14b
```


3. **Scaricare la variabili d'ambiente (opzionale)**
Crea o verifica il file .env nella radice del progetto:

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

4. **Avviare la piattaforma**

```bash
streamlit run app.py
```

### Opzione B: Esecuzione tramite Docker Compose

1. **Compilare e avviare i container**

```bash
docker compose up -d --build
```


2. **Scaricare i pesi di Qwen all'interno del container Ollama:**

```bash
docker exec -it brand_rag_ollama ollama pull qwen2.5:14b
```

3. **Accesso alla Web UI:**
Apri il browser su http://localhost:8501.

### Esecuzione dei test🧪
Il progetto include una suite completa di test unitari e di stress per validare ogni componente della pipeline:

```bash
# Esecuzione completa di tutti i test
pytest tests/

# Test specifici per retrieval e generation
pytest tests/test_hard_filtering.py tests/test_llm_generation.py tests/test_orchestrator.py
```

### Struttura del progetto📂

```text
brand-rag-system/
├── app.py                      # Applicazione principale Streamlit (Frontend & State)
├── Dockerfile                  # Specifica di containerizzazione per il servizio Web
├── docker-compose.yml          # Orchestrazione multi-servizio (Web + Ollama)
├── requirements.txt            # Dipendenze Python
├── src/
│   ├── brand_config_loader.py  # Gestione schemi colore, loghi e specifiche canali
│   ├── generation.py           # Layer client HTTP per inferenza Ollama
│   ├── ingestion.py            # Pipeline di caricamento e chunking documenti
│   ├── layout_assembly.py      # Composizione e calcolo quote grafiche raster
│   ├── orchestrator.py         # Multi-partition context retrieval & Hard Filtering
│   ├── post_processor.py       # Pulizia euristica del testo generato
│   ├── prompt_builder.py       # Costruzione ed assemblaggio prompt ChatML
│   ├── svg_export.py           # Motore di rendering ed export vettoriale SVG
│   └── vector_store.py         # Inizializzazione e gestione ChromaDB
├── tests/                      # Suite di test automatizzati (Pytest)
└── data/                       # Storage locale (Knowledge Base, font e asset di brand)
```                     # Storage locale (Knowledge Base, font e asset di brand)

### Licenza e Attribution📄
Progetto sviluppato per la sezione di Informatica dell'Università di Camerino (UNICAM). Tutti i diritti sui marchi e sui materiali istituzionali appartengono ai rispettivi proprietari.
