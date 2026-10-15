import os
import sys
from PIL import Image, ImageDraw

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.layout_assembly import get_safety_margins, load_brand_font, wrap_text_to_width

def test_layout_assembly_logic():
    print("=== TEST BACKEND: AUTOMATED LAYOUT ASSEMBLY MODULE ===")
    
    # 1. Dimensioni di test (Instagram Vertical dal JSON: 1080x1350)
    dimensions = (1080, 1350)
    print(f"\n[1/3] Calcolo dei margini su risoluzione {dimensions[0]}x{dimensions[1]}px:")
    
    left, top, right, bottom = get_safety_margins(dimensions, margin_pct=0.08)
    max_text_width = right - left
    
    print(f" -> Margini di sicurezza calcolati (8%):")
    print(f"    - Margine Sinistro: {left}px")
    print(f"    - Margine Destro: {right}px (Larghezza utile di scrittura: {max_text_width}px)")
    print(f"    - Margine Superiore: {top}px")
    print(f"    - Margine Inferiore: {bottom}px")
    
    # 2. Caricamento Font
    print("\n[2/3] Caricamento del font del brand o dei fallback di sistema:")
    font = load_brand_font(font_size=36, font_name="Proxima Nova")
    print(f" -> Caricato font di tipo: {type(font).__name__}")
    
    # 3. Test andata a capo automatica (Word Wrap)
    print("\n[3/3] Simulazione andata a capo automatica su testo di brand lungo:")
    test_text = (
        "Il nuovo laboratorio di cybersecurity dell'Università di Camerino (UNICAM) "
        "rappresenta un punto di riferimento strategico e all'avanguardia per la formazione di giovani "
        "professionisti nel panorama dello sviluppo backend e della difesa digitale."
    )
    
    # Creiamo un'immagine temporanea in memoria per ottenere il contesto ImageDraw
    dummy_img = Image.new("RGB", dimensions)
    draw = ImageDraw.Draw(dummy_img)
    
    wrapped_lines = wrap_text_to_width(test_text, font, max_text_width, draw)
    
    print("-" * 60)
    print(f"Testo originale spezzato in {len(wrapped_lines)} righe:")
    for i, line in enumerate(wrapped_lines, 1):
        # Misuriamo l'ingombro visivo effettivo della riga generata
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        print(f" Riga {i} ({line_width}px / max {max_text_width}px): {line}")
        assert line_width <= max_text_width, f"La riga {i} supera la larghezza massima!"
    print("-" * 60)
    
    print("\n✅ TEST DEL LAYOUT ASSEMBLY SUPERATO: I vincoli geometrici sono preservati matematicamente!")

if __name__ == "__main__":
    test_layout_assembly_logic()