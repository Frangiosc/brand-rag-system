# src/image_generation.py
import os
import requests
from io import BytesIO
from PIL import Image
from typing import Tuple, Optional
from src.brand_config_loader import load_brand_configuration

def generate_brand_background(
    post_context: str,
    dimensions: Tuple[int, int] = (1080, 1350)
) -> Image.Image:
    """
    Genera uno sfondo grafico coerente basato sul contesto del post o sull'esempio few-shot fornito.
    Evita rendering 3D complessi a favore di pattern tech minimalisti e piatti.
    """
    width, height = dimensions
    print(f"🎨 Generazione sfondo multimodale in corso ({width}x{height}px)...")
    
    # --- 1. IDENTIFICAZIONE DEL MOOD VISIVO (FEW-SHOT VS REGOLE FISSE) ---
    # Se il testo in ingresso contiene esplicitamente indicazioni stilistiche dall'Hub Few-Shot,
    # lo usiamo direttamente per guidare il modello di diffusione.
    if "sfondo" in post_context.lower() or "pattern" in post_context.lower() or "grafica" in post_context.lower():
        print("💡 Hub Ispirazione Rilevato: Utilizzo della descrizione stilistica few-shot.")
        tech_theme = post_context.strip()
        color_accents = "respecting corporate brand identity color palette"
    else:
        # Fallback sulle regole euristiche standard basate sulle keyword del post
        print("⚙️ Analisi semantica del copy per determinazione euristica dello stile.")
        tech_theme = "software development, abstract digital network, coding pattern"
        color_accents = "deep blue background #173983, subtle glowing cyan and orange accents"
        
        if "cybersecurity" in post_context.lower() or "sicurezza" in post_context.lower():
            tech_theme = "abstract cybersecurity matrix, digital nodes, glowing network connections, data protection flow"
            color_accents = "dark deep blue #131313, electric blue and green cyber details"
        elif "ux" in post_context.lower() or "design" in post_context.lower() or "comunicazione" in post_context.lower():
            tech_theme = "clean flat geometric vector shapes, digital workspace wireframe, abstract creative flow"
            color_accents = "minimalist white and light blue #FFFFF0, soft golden yellow accents #FFCA48"
        elif "orientamento" in post_context.lower() or "studiare" in post_context.lower() or "laboratori" in post_context.lower():
            tech_theme = "abstract computer science network, high-tech server nodes, minimalist vector binary code background, clean geometric grid"
            color_accents = "deep academic blue base #173983, tech yellow accents #FFCA48"

    # --- 2. INGEGNERIA DEL PROMPT CON NEGATIVE PROMPTING IMPLICITO ---
    # Forziamo una struttura flat/2D per evitare rendering di corridoi 3D e stanze vuote fuori target.
    refined_prompt = (
        f"flat vector graphic background, {tech_theme}, corporate tech style, "
        f"clean layout, {color_accents}, modern minimalist corporate design, "
        f"soft digital grid, elegant professional background, "
        f"no 3D rooms, no realistic hallways, no doors, no humans, no text, no letters, clean empty center for overlay text"
    )
    
    encoded_prompt = requests.utils.quote(refined_prompt)
    
    # Utilizziamo Flux/Stable Diffusion tramite endpoint Pollinations configurando seed fisso per la riproducibilità
    request_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&seed=101&nologo=true"
    
    try:
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        if img.size != dimensions:
            img = img.resize(dimensions, Image.Resampling.LANCZOS)
        return img
        
    except Exception as e:
        print(f"⚠️ Errore durante la generazione dell'immagine via API: {str(e)}")
        print("🛠️ Attivazione Fallback Deterministico Locale: Generazione texture a tinta unita dal JSON.")
        
        # --- 3. MECCANISMO DI RESILIENZA LOCALE DINAMICO (DAL JSON REALE) ---
        fallback_hex = "#173983" # Default Unicam Blue
        try:
            config = load_brand_configuration()
            primary_colors = config.get("visual_identity", {}).get("color_palette", {}).get("primary_colors", [])
            for color in primary_colors:
                if color.get("name") == "Unicam Blue":
                    fallback_hex = color.get("hex")
                    break
        except Exception:
            pass
            
        # Converte l'HEX letto in tupla RGB per Pillow
        hex_str = fallback_hex.lstrip('#')
        r, g, b = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        
        # Restituisce uno sfondo solido istituzionale a prova di crash
        fallback_img = Image.new("RGBA", dimensions, (r, g, b, 255))
        return fallback_img.convert("RGB")