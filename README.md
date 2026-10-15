# Brand RAG System — Multi-Container AI Architecture

Sistema avanzato di generazione e validazione contenuti basato su architettura **RAG (Retrieval-Augmented Generation)** multimodale per il brand aziendale **@unicamente_informatica**, containerizzato tramite Docker.

---

## 🏗️ Architettura del Sistema

Il sistema è orchestrato tramite due servizi containerizzati isolati:
1. **`web` (`brand_rag_studio`)**:
   - **Frontend**: Streamlit UI interattiva (Workspace di Brand Management e Generazione Contenuti con raffinamento in chat).
   - **RAG & Orchestration**: LangChain, ChromaDB con Hard Filtering categoriale (`target_personas`, `tone_of_voice`, `brand_guidelines`), modelli di embedding semantico e motore di rendering grafico (Pillow/SVG).
2. **`ollama` (`brand_rag_ollama`)**:
   - Runtime locale per Large Language Models (LLM Llama 3) esposto sulla rete interna Docker sulla porta `11434`.
   - Modello conservato su volume persistente isolato.

---

## 📋 Requisiti di Sistema

- **Docker Desktop** installato e attivo (macOS, Windows con WSL2, o Linux).
- **Risorse minime consigliate** in Docker Desktop (*Settings > Resources*):
  - RAM: **almeno 6 GB - 8 GB** (per l'esecuzione efficiente del modello Llama 3 8B).
  - CPU: **4 Core**.
  - Spazio su disco: **~10 GB liberi** per le immagini Docker e i pesi del modello.

---

## 🚀 Guida all'Installazione e Avvio Rapido

### 1. Avviare i container Docker
Dalla cartella principale del progetto, eseguire nel terminale:

```bash
docker compose up -d --build


### 2. Download del modello LLM

```bash
docker exec -it brand_rag_ollama ollama pull llama3


### 3. Accesso all'applicazione:
Aprire il browser su http://localhost:8501