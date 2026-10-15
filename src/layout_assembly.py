import os
import re
from PIL import Image, ImageDraw, ImageFont

def get_font(font_path: str, size: int):
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    except Exception:
        pass
    return ImageFont.load_default()

def wrap_text(text: str, max_chars: int = 26) -> list:
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) <= max_chars:
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

def compose_final_graphic(
    background_img: Image.Image = None,
    text_content: dict = None,
    channel_name: str = "instagram",
    brand_config: dict = None,
    canvas_size: tuple = (1080, 1350)
) -> Image.Image:
    width, height = canvas_size
    text_content = text_content or {}
    brand_config = brand_config or {}

    # Percorsi asset
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root_dir, "data", "assets")

    # 1. Palette Dinamica
    course_type = text_content.get("course_type", "Informatica").lower()
    if "comunicazione" in course_type or "icd" in course_type:
        bg_color = (255, 202, 72)    # Unicam Yellow
        text_primary = (23, 57, 131)  # Unicam Blue
        accent_color = (23, 57, 131)
        btn_bg = (23, 57, 131)
        btn_text = (255, 255, 255)
    elif "computer science" in course_type or "magistrale" in course_type:
        bg_color = (250, 115, 67)    # Unicam Orange
        text_primary = (255, 255, 255)
        accent_color = (19, 19, 19)
        btn_bg = (19, 19, 19)
        btn_text = (255, 255, 255)
    else:
        bg_color = (23, 57, 131)     # Unicam Blue
        text_primary = (255, 255, 255)
        accent_color = (0, 255, 102) # Neon Green
        btn_bg = (0, 255, 102)
        btn_text = (19, 19, 19)

    # Creazione Canvas
    canvas = Image.new("RGBA", (width, height), bg_color + (255,))
    
    # 2. Watermark Mascotte / Rubrica
    selected_asset = text_content.get("selected_asset", "")
    asset_path = ""
    if selected_asset:
        for sub in ["rubrics", "mascots"]:
            p = os.path.join(assets_dir, sub, selected_asset)
            if os.path.exists(p):
                asset_path = p
                break
    if not asset_path and os.path.exists(os.path.join(assets_dir, "mascots")):
        m_files = [f for f in os.listdir(os.path.join(assets_dir, "mascots")) if f.lower().endswith(('.png', '.jpg'))]
        if m_files:
            asset_path = os.path.join(assets_dir, "mascots", m_files[0])

    if asset_path and os.path.exists(asset_path):
        try:
            watermark = Image.open(asset_path).convert("RGBA")
            wm_size = int(width * 0.70)
            watermark = watermark.resize((wm_size, wm_size), Image.Resampling.LANCZOS)
            
            # Opacità 25%
            r, g, b, a = watermark.split()
            a = a.point(lambda p: int(p * 0.25))
            watermark.putalpha(a)
            
            wm_x = int(width - (wm_size * 0.85))
            wm_y = int(height - (wm_size * 0.95))
            canvas.paste(watermark, (wm_x, wm_y), watermark)
        except Exception:
            pass

    # 3. Logo Brand
    logo_cfg = brand_config.get("brand_assets", {}).get("core_branding", {}).get("main_logo", {})
    logo_fn = logo_cfg.get("file_name", "logo_unicamente.png")
    logo_path = os.path.join(assets_dir, "logos", logo_fn)
    if not os.path.exists(logo_path) and os.path.exists(os.path.join(assets_dir, "logos")):
        l_files = [f for f in os.listdir(os.path.join(assets_dir, "logos")) if f.lower().endswith(('.png', '.jpg'))]
        if l_files:
            logo_path = os.path.join(assets_dir, "logos", l_files[0])

    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_w = int(width * 0.44)
            aspect = logo_img.height / logo_img.width
            logo_h = int(logo_w * aspect)
            logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            logo_x = (width - logo_w) // 2
            logo_y = int(height * 0.05)
            canvas.paste(logo_img, (logo_x, logo_y), logo_img)
        except Exception:
            pass

    # Disegno Tipografia
    draw = ImageDraw.Draw(canvas)
    
    font_bold_path = os.path.join(assets_dir, "fonts", "Sora-Bold copia.ttf")
    font_reg_path = os.path.join(assets_dir, "fonts", "Sora-Regular copia.ttf")
    if not os.path.exists(font_bold_path):
        font_bold_path = os.path.join(assets_dir, "fonts", "Sora-Bold.ttf")
    if not os.path.exists(font_reg_path):
        font_reg_path = os.path.join(assets_dir, "fonts", "Sora-Regular.ttf")

    pad_x = int(width * 0.08)
    curr_y = int(height * 0.18)

    # Titolo
    title_text = text_content.get("title", "")
    if title_text:
        title_font = get_font(font_bold_path, int(width * 0.052))
        for line in wrap_text(title_text, max_chars=24):
            draw.text((pad_x, curr_y), line, fill=accent_color, font=title_font)
            curr_y += int(width * 0.065)
        curr_y += int(height * 0.02)

    # Sottotitolo
    sub_text = text_content.get("subtitle_or_cta", "")
    if sub_text:
        sub_font = get_font(font_bold_path, int(width * 0.034))
        for line in wrap_text(sub_text, max_chars=34):
            draw.text((pad_x, curr_y), line, fill=text_primary, font=sub_font)
            curr_y += int(width * 0.046)
        curr_y += int(height * 0.035)

    # Blocco 1
    l1_name = text_content.get("label_1_name", "")
    l1_val = text_content.get("label_1_val", "")
    if l1_name and l1_val:
        lbl_head_font = get_font(font_bold_path, int(width * 0.024))
        lbl_val_font = get_font(font_bold_path, int(width * 0.036))
        draw.text((pad_x, curr_y), l1_name.upper(), fill=accent_color, font=lbl_head_font)
        curr_y += int(width * 0.038)
        for line in wrap_text(l1_val, max_chars=34):
            draw.text((pad_x, curr_y), line, fill=text_primary, font=lbl_val_font)
            curr_y += int(width * 0.048)
        curr_y += int(height * 0.025)

    # Blocco 2
    l2_name = text_content.get("label_2_name", "")
    l2_val = text_content.get("label_2_val", "")
    if l2_name and l2_val:
        lbl_head_font = get_font(font_bold_path, int(width * 0.024))
        lbl_val_font = get_font(font_bold_path, int(width * 0.036))
        draw.text((pad_x, curr_y), l2_name.upper(), fill=accent_color, font=lbl_head_font)
        curr_y += int(width * 0.038)
        for line in wrap_text(l2_val, max_chars=34):
            draw.text((pad_x, curr_y), line, fill=text_primary, font=lbl_val_font)
            curr_y += int(width * 0.048)
        curr_y += int(height * 0.025)

    # CTA Button
    btn_text_val = text_content.get("button_text", "")
    if btn_text_val:
        btn_w = int(width * 0.84)
        btn_h = int(height * 0.068)
        btn_x = (width - btn_w) // 2
        btn_y = int(height - btn_h - (height * 0.055))
        radius = int(btn_h * 0.22)

        # Label sopra il bottone
        top_lbl_font = get_font(font_bold_path, int(width * 0.026))
        top_lbl_text = "REGISTRATI ONLINE AL LINK:" if "registra" in str(text_content).lower() or "seminario" in str(text_content).lower() else "CONSULTA IL LINK UFFICIALE:"
        draw.text((width // 2, btn_y - int(height * 0.025)), top_lbl_text, fill=accent_color, font=top_lbl_font, anchor="mm")

        # Rettangolo
        draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=radius, fill=btn_bg)

        # Testo Link
        clean_url = re.sub(r'^https?://', '', btn_text_val).upper()
        btn_font_size = int(width * 0.033)
        if len(clean_url) > 32:
            btn_font_size = int(width * 0.026)
        if len(clean_url) > 42:
            btn_font_size = int(width * 0.021)
        btn_font = get_font(font_bold_path, btn_font_size)
        draw.text((width // 2, btn_y + (btn_h // 2)), clean_url, fill=btn_text, font=btn_font, anchor="mm")

    return canvas.convert("RGB")