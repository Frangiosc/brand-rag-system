import os
import json
from typing import Dict, Any, List

DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "structured", "brand_config.json"
)

def load_brand_configuration(json_path: str = DEFAULT_JSON_PATH) -> Dict[str, Any]:
    """
    Carica e valida il file JSON ufficiale del brand.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File di configurazione del brand non trovato in: {json_path}")
        
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Errore di parsing nel file JSON del brand: {str(e)}")

def get_channel_templates(config_data: Dict[str, Any], channel_name: str) -> Dict[str, Any]:
    """
    Estrae i modelli, i formati di distribuzione e i vincoli geometrici del canale.
    """
    templates = config_data.get("channel_templates", {})
    target_channel = next((ch for ch in templates if ch.lower() == channel_name.lower()), None)
    
    if not target_channel:
        print(f"⚠️ Warning: Canale '{channel_name}' non trovato nei template ufficiali.")
        return {}
        
    return templates[target_channel]