import os
import requests
import json
from typing import Dict, Any, Optional

# Default a localhost:11434 per esecuzione nativa; sovrascritto da docker-compose in container
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_API_URL = f"{OLLAMA_HOST}/api/generate"
DEFAULT_MODEL = "llama3"

def generate_social_post(
    system_prompt: str,
    user_prompt: str,
    model_name: str = DEFAULT_MODEL,
    api_url: Optional[str] = None,
    temperature: float = 0.3
) -> str:
    current_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    target_api_url = api_url if api_url else f"{current_host}/api/generate"

    full_prompt = f"<<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt}"
    
    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_ctx": 4096
        },
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(target_api_url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        response_data = response.json()
        generated_text = response_data.get("response", "").strip()
        
        if not generated_text:
            raise ValueError("L'LLM ha restituito una risposta vuota.")
            
        return generated_text
        
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Impossibile connettersi a Ollama su {target_api_url}. "
            "Verifica che l'applicazione Ollama sia aperta sul Mac o che il container sia attivo."
        )
    except Exception as e:
        raise RuntimeError(f"Errore durante la generazione con Ollama: {str(e)}")