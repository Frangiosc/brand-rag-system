import os
import re
import base64
import html

def image_to_base64_data_uri(image_path: str) -> str:
    """Converte un file PNG/JPG in Base64 Data URI valido per Illustrator."""
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

def wrap_text_lines(text: str, max_chars_per_line: int = 28) -> list:
    """Word-wrapping del testo per il rendering vettoriale multilinea."""
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
    **kwargs
) -> str:
    width, height = canvas_size

    # 1. Determinazione cromatica in base al corso di studi
    course_type = text_content.get("course_type", "Informatica").lower()
    if "comunicazione" in course_type or "icd" in course_type:
        bg_color = "#FFCA48"      # Unicam Yellow
        text_primary = "#173983"  # Unicam Blue scuro
        accent_color = "#173983"
        btn_bg = "#173983"
        btn_text = "#FFFFFF"
    elif "computer science" in course_type or "magistrale" in course_type:
        bg_color = "#FA7343"      # Unicam Orange
        text_primary = "#FFFFFF"  # Bianco per testi
        accent_color = "#FFFFFF"  # Bianco per Titolo ed elementi di accento
        btn_bg = "#FFFFFF"        # Bianco per il box CTA
        btn_text = "#131313"      # Nero per il link
    else:
        bg_color = "#173983"      # Unicam Blue classico
        text_primary = "#FFFFFF"
        accent_color = "#00FF66"  # Verde Neon
        btn_bg = "#00FF66"
        btn_text = "#131313"

    pad_x = int(width * 0.08)
    curr_y = int(height * 0.18)

    # 2. Risoluzione e Conversione Base64 per Logo Dinamico
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, "data", "assets")

    if not logo_path or not os.path.exists(logo_path):
        if "computer science" in course_type or "magistrale" in course_type:
            target_logo = "Logotipo UI Black - Green.png"
        else:
            target_logo = brand_config.get("brand_assets", {}).get("core_branding", {}).get("main_logo", {}).get("file_name", "logo_unicamente.png")
        
        computed_path = os.path.join(assets_dir, "logos", target_logo)
        if os.path.exists(computed_path):
            logo_path = computed_path
        elif os.path.exists(os.path.join(assets_dir, "logos")):
            l_files = [f for f in os.listdir(os.path.join(assets_dir, "logos")) if f.lower().endswith(('.png', '.jpg'))]
            if l_files:
                logo_path = os.path.join(assets_dir, "logos", l_files[0])

    logo_uri = image_to_base64_data_uri(logo_path)
    logo_w = int(width * 0.44)
    logo_h = int(height * 0.08)
    logo_x = int((width - logo_w) / 2)
    logo_y = int(height * 0.045)

    # 3. Conversione Base64 per Mascotte / Badge
    asset_uri = image_to_base64_data_uri(asset_path)

    # 4. Generazione XML SVG compatibile Adobe Illustrator
    svg = []
    svg.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg.append(
        f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}px" height="{height}px" viewBox="0 0 {width} {height}" '
        f'xml:space="preserve">'
    )
    
    svg.append('  <defs>')
    svg.append('    <style type="text/css">')
    svg.append('      @import url("https://fonts.googleapis.com/css2?family=Sora:wght@400;700;800&amp;display=swap");')
    svg.append('      .title-text { font-family: "Sora", "Arial", sans-serif; font-weight: 800; }')
    svg.append('      .body-text { font-family: "Sora", "Arial", sans-serif; font-weight: 700; }')
    svg.append('      .label-head { font-family: "Sora", "Arial", sans-serif; font-weight: 700; letter-spacing: 1.5px; }')
    svg.append('      .btn-text { font-family: "Sora", "Arial", sans-serif; font-weight: 800; }')
    svg.append('    </style>')
    svg.append('  </defs>')

    # LIVELLO 1: Background
    svg.append('  <g id="Layer_Background">')
    svg.append(f'    <rect x="0" y="0" width="{width}" height="{height}" fill="{bg_color}" />')
    svg.append('  </g>')

    # LIVELLO 2: Mascotte / Badge (Riallineamento con margine destro)
    if asset_uri and asset_uri.startswith("data:image/"):
        is_rubric = "rubric" in str(asset_path).lower()
        if is_rubric:
            wm_w = int(width * 0.40)
            wm_h = int(width * 0.40)
            wm_x = int(width - wm_w - (width * 0.05))
            wm_y = int(height * 0.48)
            op = "0.22"
        else:
            wm_w = int(width * 0.44)
            wm_h = int(width * 0.44)
            wm_x = int(width - wm_w - (width * 0.06))
            wm_y = int(height - wm_h - (height * 0.10))
            op = "0.25"

        svg.append(f'  <g id="Layer_Watermark_Asset" opacity="{op}">')
        svg.append(
            f'    <image width="{wm_w}" height="{wm_h}" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'xlink:href="{asset_uri}" href="{asset_uri}" '
            f'x="{wm_x}" y="{wm_y}" />'
        )
        svg.append('  </g>')

    # LIVELLO 3: Logo Brand
    if logo_uri and logo_uri.startswith("data:image/"):
        svg.append('  <g id="Layer_Brand_Logo">')
        svg.append(
            f'    <image width="{logo_w}" height="{logo_h}" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'xlink:href="{logo_uri}" href="{logo_uri}" '
            f'x="{logo_x}" y="{logo_y}" />'
        )
        svg.append('  </g>')

    # LIVELLO 4: Tipografia
    svg.append('  <g id="Layer_Typography">')

    # Titolo
    title_raw = text_content.get("title", "")
    if title_raw:
        title_font_size = int(width * 0.052)
        line_height = int(title_font_size * 1.25)
        for line in wrap_text_lines(title_raw, max_chars_per_line=24):
            svg.append(
                f'    <text x="{pad_x}" y="{curr_y}" font-size="{title_font_size}" fill="{accent_color}" class="title-text">{html.escape(line)}</text>'
            )
            curr_y += line_height
        curr_y += int(height * 0.02)

    # Sottotitolo
    sub_raw = text_content.get("subtitle_or_cta", "")
    if sub_raw:
        sub_font_size = int(width * 0.034)
        sub_line_height = int(sub_font_size * 1.35)
        for line in wrap_text_lines(sub_raw, max_chars_per_line=36):
            svg.append(
                f'    <text x="{pad_x}" y="{curr_y}" font-size="{sub_font_size}" fill="{text_primary}" class="body-text">{html.escape(line)}</text>'
            )
            curr_y += sub_line_height
        curr_y += int(height * 0.035)

    # Blocco 1
    l1_name = text_content.get("label_1_name", "")
    l1_val = text_content.get("label_1_val", "")
    if l1_name and l1_val:
        lbl_head_size = int(width * 0.024)
        lbl_val_size = int(width * 0.036)
        svg.append(
            f'    <text x="{pad_x}" y="{curr_y}" font-size="{lbl_head_size}" fill="{accent_color}" class="label-head">{html.escape(l1_name.upper())}</text>'
        )
        curr_y += int(lbl_head_size * 1.6)
        for line in wrap_text_lines(l1_val, max_chars_per_line=34):
            svg.append(
                f'    <text x="{pad_x}" y="{curr_y}" font-size="{lbl_val_size}" fill="{text_primary}" class="body-text">{html.escape(line)}</text>'
            )
            curr_y += int(lbl_val_size * 1.3)
        curr_y += int(height * 0.025)

    # Blocco 2
    l2_name = text_content.get("label_2_name", "")
    l2_val = text_content.get("label_2_val", "")
    if l2_name and l2_val:
        lbl_head_size = int(width * 0.024)
        lbl_val_size = int(width * 0.036)
        svg.append(
            f'    <text x="{pad_x}" y="{curr_y}" font-size="{lbl_head_size}" fill="{accent_color}" class="label-head">{html.escape(l2_name.upper())}</text>'
        )
        curr_y += int(lbl_head_size * 1.6)
        for line in wrap_text_lines(l2_val, max_chars_per_line=34):
            svg.append(
                f'    <text x="{pad_x}" y="{curr_y}" font-size="{lbl_val_size}" fill="{text_primary}" class="body-text">{html.escape(line)}</text>'
            )
            curr_y += int(lbl_val_size * 1.3)
        curr_y += int(height * 0.025)

    # Contatti
    contact = text_content.get("contact_info", "")
    if contact:
        c_size = int(width * 0.028)
        svg.append(
            f'    <text x="{pad_x}" y="{curr_y}" font-size="{c_size}" fill="{text_primary}" class="body-text">{html.escape(contact)}</text>'
        )

    svg.append('  </g>')

    # LIVELLO 5: Pulsante CTA
    btn_text_val = text_content.get("button_text", "")
    if btn_text_val:
        svg.append('  <g id="Layer_CTA_Button">')
        btn_w = int(width * 0.84)
        btn_h = int(height * 0.068)
        btn_x = int((width - btn_w) / 2)
        btn_y = int(height - btn_h - (height * 0.055))
        radius = int(btn_h * 0.22)

        top_lbl_y = int(btn_y - (height * 0.018))
        top_lbl_text = "REGISTRATI ONLINE AL LINK:" if "registra" in str(text_content).lower() or "seminario" in str(text_content).lower() else "CONSULTA IL LINK UFFICIALE:"
        svg.append(
            f'    <text x="{int(width / 2)}" y="{top_lbl_y}" font-size="{int(width * 0.026)}" fill="{accent_color}" text-anchor="middle" class="label-head">{top_lbl_text}</text>'
        )

        svg.append(
            f'    <rect x="{btn_x}" y="{btn_y}" width="{btn_w}" height="{btn_h}" rx="{radius}" ry="{radius}" fill="{btn_bg}" />'
        )

        clean_url = re.sub(r'^https?://', '', btn_text_val).upper()
        btn_font_size = int(width * 0.033)
        if len(clean_url) > 32:
            btn_font_size = int(width * 0.026)
        if len(clean_url) > 42:
            btn_font_size = int(width * 0.021)

        text_y_center = int(btn_y + (btn_h / 2) + (btn_font_size * 0.35))
        svg.append(
            f'    <text x="{int(width / 2)}" y="{text_y_center}" font-size="{btn_font_size}" fill="{btn_text}" text-anchor="middle" class="btn-text">{html.escape(clean_url)}</text>'
        )
        svg.append('  </g>')

    svg.append('</svg>')
    return "\n".join(svg)