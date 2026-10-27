import os
import re
import json
import base64
import html
from typing import Dict, Any, Optional

def image_to_base64_data_uri(image_path: str) -> str:
    """Converte un file PNG/JPG in Base64 Data URI valido."""
    if not image_path or not isinstance(image_path, str):
        return ""
    if not os.path.isabs(image_path):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_path = os.path.join(root, image_path)
    
    if not os.path.exists(image_path) or os.path.isdir(image_path):
        return ""
        
    try:
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        mime = "image/png" if "png" in ext else "image/jpeg"
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        if len(encoded) > 50:
            return f"data:{mime};base64,{encoded}"
    except Exception as e:
        print(f"[SVG Export Error] Impossibile convertire {image_path}: {e}")
    return ""

def wrap_text_lines(text: str, max_chars_per_line: int = 24) -> list:
    """Word-wrapping rigoroso per evitare qualsiasi sbordamento visivo."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) <= max_chars_per_line:
            current_line.append(w)
            current_len += len(w) + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def generate_brand_svg(
    text_content: dict,
    channel_name: str,
    brand_config: dict,
    canvas_size: tuple = (1080, 1350),
    logo_path: str = None,
    asset_path: str = None,
    visual_guidelines_context: str = "",
    use_ai_design: bool = True,
    **kwargs
) -> str:
    width, height = canvas_size

    # 1. Palette ufficiale UNICAM
    course_type = text_content.get("course_type", "Informatica").lower()
    if "comunicazione" in course_type or "icd" in course_type:
        bg_primary = "#173983"
        card_bg = "#FFFFFF"
        accent_color = "#FFCA48"    # Giallo ICD
        text_on_card = "#173983"
        btn_bg = "#FFCA48"
        btn_text = "#173983"
    elif "computer science" in course_type or "magistrale" in course_type:
        bg_primary = "#131313"
        card_bg = "#1F242D"
        accent_color = "#FA7343"    # Arancione Unicam
        text_on_card = "#FFFFFF"
        btn_bg = "#FA7343"
        btn_text = "#FFFFFF"
    else:
        bg_primary = "#0E2352"      # Blu Notte Unicam
        card_bg = "#FFFFFF"
        accent_color = "#00FF66"    # Verde Neon Brand
        text_on_card = "#173983"
        btn_bg = "#00FF66"
        btn_text = "#131313"

    # 2. Risoluzione Asset (Base64)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, "data", "assets")

    if not logo_path or not os.path.exists(logo_path):
        target_logo = "Logotipo UI Black - Green.png" if "computer science" in course_type else "logo_unicamente.png"
        test_path = os.path.join(assets_dir, "logos", target_logo)
        if os.path.exists(test_path):
            logo_path = test_path
        elif os.path.exists(os.path.join(assets_dir, "logos")):
            l_files = [f for f in os.listdir(os.path.join(assets_dir, "logos")) if f.lower().endswith(('.png', '.jpg'))]
            if l_files:
                logo_path = os.path.join(assets_dir, "logos", l_files[0])

    logo_uri = image_to_base64_data_uri(logo_path)
    asset_uri = image_to_base64_data_uri(asset_path)

    # 3. Struttura Geometrica Solida
    card_x = int(width * 0.06)
    card_y = int(height * 0.16)
    card_w = int(width * 0.88)
    card_h = int(height * 0.76)

    pad_internal = int(card_w * 0.08)
    content_x = card_x + pad_internal
    content_w = card_w - (pad_internal * 2)
    curr_y = card_y + int(card_h * 0.09)

    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xml:space="preserve">'
    )
    
    # Stili & Font Sora Ufficiale
    svg.append('  <defs>')
    svg.append('    <style>')
    svg.append('      @import url("https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&amp;display=swap");')
    svg.append('      text { font-family: "Sora", sans-serif; }')
    svg.append('      .title { font-weight: 800; }')
    svg.append('      .subtitle { font-weight: 600; }')
    svg.append('      .label-title { font-weight: 700; letter-spacing: 1.5px; }')
    svg.append('      .label-value { font-weight: 600; }')
    svg.append('      .btn-text { font-weight: 800; letter-spacing: 0.5px; }')
    svg.append('    </style>')
    svg.append('    <filter id="card-shadow" x="-5%" y="-5%" width="110%" height="110%">')
    svg.append('      <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.25"/>')
    svg.append('    </filter>')
    svg.append('  </defs>')

    # 1. LIVELLO SFONDO: Solo gradiente/campitura pulita senza linee oblique
    svg.append(f'  <rect width="{width}" height="{height}" fill="{bg_primary}"/>')
    svg.append(f'  <circle cx="{width}" cy="0" r="{int(width * 0.40)}" fill="{accent_color}" opacity="0.08"/>')
    svg.append(f'  <circle cx="0" cy="{height}" r="{int(width * 0.35)}" fill="#FFFFFF" opacity="0.04"/>')

    # 2. LIVELLO CARD CENTRALE
    svg.append(f'  <rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="32" ry="32" fill="{card_bg}" filter="url(#card-shadow)"/>')
    
    # Barra superiore colorata della card
    svg.append(f'  <path d="M {card_x} {card_y + 32} Q {card_x} {card_y} {card_x + 32} {card_y} L {card_x + card_w - 32} {card_y} Q {card_x + card_w} {card_y} {card_x + card_w} {card_y + 32} L {card_x + card_w} {card_y + 12} L {card_x} {card_y + 12} Z" fill="{accent_color}"/>')

    # 3. LIVELLO MASCOTTE / RUBRICA
    if asset_uri and asset_uri.startswith("data:image/"):
        is_rubric = "rubric" in str(asset_path).lower()
        if is_rubric:
            wm_size = int(width * 0.28)
            wm_x = card_x + card_w - wm_size - int(card_w * 0.05)
            wm_y = card_y + card_h - wm_size - int(card_h * 0.16)
            wm_op = "0.90"
        else:
            # Dimensioni calibrate per non toccare i testi a sinistra
            wm_size = int(width * 0.34)
            wm_x = card_x + card_w - wm_size - int(card_w * 0.02)
            wm_y = card_y + card_h - wm_size - int(card_h * 0.11)
            wm_op = "0.90"

        svg.append(f'  <g id="Layer_Asset_Visible" opacity="{wm_op}">')
        svg.append(f'    <image href="{asset_uri}" width="{wm_size}" height="{wm_size}" x="{wm_x}" y="{wm_y}" preserveAspectRatio="xMidYMid meet"/>')
        svg.append(f'  </g>')

    # 4. LIVELLO LOGO (In alto centrato, con filtro per risaltare su fondo scuro)
    if logo_uri and logo_uri.startswith("data:image/"):
        logo_w = int(width * 0.44)
        logo_h = int(height * 0.08)
        logo_x = int((width - logo_w) / 2)
        logo_style = 'style="filter: brightness(0) invert(1);"' if bg_primary in ["#0E2352", "#131313", "#173983"] else ''
        svg.append(f'  <image href="{logo_uri}" width="{logo_w}" height="{logo_h}" x="{logo_x}" y="{int(height * 0.045)}" preserveAspectRatio="xMidYMid meet" {logo_style}/>')

    # 5. LIVELLO TIPOGRAFIA
    title_raw = text_content.get("title", "")
    if title_raw:
        font_size = int(width * 0.048)
        line_height = int(font_size * 1.25)
        for line in wrap_text_lines(title_raw, max_chars_per_line=22):
            svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{font_size}" fill="{text_on_card}" class="title">{html.escape(line)}</text>')
            curr_y += line_height
        curr_y += int(height * 0.02)

    sub_raw = text_content.get("subtitle_or_cta", "")
    if sub_raw:
        sub_size = int(width * 0.032)
        sub_line_height = int(sub_size * 1.35)
        for line in wrap_text_lines(sub_raw, max_chars_per_line=32):
            svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{sub_size}" fill="{text_on_card}" opacity="0.80" class="subtitle">{html.escape(line)}</text>')
            curr_y += sub_line_height
        curr_y += int(height * 0.035)

    # Linea separatrice orizzontale
    svg.append(f'  <line x1="{content_x}" y1="{curr_y}" x2="{content_x + content_w}" y2="{curr_y}" stroke="{text_on_card}" stroke-opacity="0.15" stroke-width="2"/>')
    curr_y += int(height * 0.04)

    # Dettagli 1 (es. Data e Ora)
    l1_name = text_content.get("label_1_name", "")
    l1_val = text_content.get("label_1_val", "")
    if l1_name and l1_val:
        svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{int(width * 0.024)}" fill="{text_on_card}" opacity="0.60" class="label-title">{html.escape(l1_name.upper())}</text>')
        curr_y += int(width * 0.040)
        # max_chars_per_line impostato a 20 per lasciare spazio alla mascotte
        for line in wrap_text_lines(l1_val, max_chars_per_line=20):
            svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{int(width * 0.034)}" fill="{text_on_card}" class="label-value">{html.escape(line)}</text>')
            curr_y += int(width * 0.044)
        curr_y += int(height * 0.025)

    # Dettagli 2 (es. Luogo)
    l2_name = text_content.get("label_2_name", "")
    l2_val = text_content.get("label_2_val", "")
    if l2_name and l2_val:
        svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{int(width * 0.024)}" fill="{text_on_card}" opacity="0.60" class="label-title">{html.escape(l2_name.upper())}</text>')
        curr_y += int(width * 0.040)
        # max_chars_per_line impostato a 20 per lasciare spazio alla mascotte
        for line in wrap_text_lines(l2_val, max_chars_per_line=20):
            svg.append(f'  <text x="{content_x}" y="{curr_y}" font-size="{int(width * 0.034)}" fill="{text_on_card}" class="label-value">{html.escape(line)}</text>')
            curr_y += int(width * 0.044)

    # 6. LIVELLO BOTTONE CTA
    btn_text_val = text_content.get("button_text", "")
    if btn_text_val:
        btn_w = content_w
        btn_h = int(height * 0.065)
        btn_x = content_x
        btn_y = card_y + card_h - btn_h - int(card_h * 0.07)
        radius = int(btn_h * 0.25)
        clean_url = re.sub(r'^https?://', '', btn_text_val).upper()

        svg.append(f'  <rect x="{btn_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="{radius}" ry="{radius}" fill="{btn_bg}"/>')
        svg.append(f'  <text x="{btn_x + (btn_w / 2)}" y="{btn_y + (btn_h / 2) + 8}" font-size="{int(width * 0.028)}" fill="{btn_text}" text-anchor="middle" class="btn-text">{html.escape(clean_url)}</text>')

    svg.append('</svg>')
    return "\n".join(svg)