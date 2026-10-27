import os
from src.brand_config_loader import load_brand_configuration
from src.svg_export import generate_brand_svg

# Carichiamo la configurazione di brand attiva
cfg = load_brand_configuration()

# Dati fittizi di prova per una rubrica o evento
mock_content = {
    "title": "Workshop Pratico di Machine Learning",
    "subtitle_or_cta": "Laboratorio intensivo aperto a tutti gli studenti di Informatica",
    "label_1_name": "DATA E ORA",
    "label_1_val": "15 Novembre 2026 ore 14:30",
    "label_2_name": "LUOGO",
    "label_2_val": "Laboratorio Didattico Alfa, Polo Lodovici",
    "button_text": "https://unicam.it/iscrizioni-ml",
    "contact_info": "Per info: info.informatica@unicam.it",
    "course_type": "Informatica"
}

print("[Test] Generazione SVG con Qwen 2.5 14B in corso...")

svg_result = generate_brand_svg(
    text_content=mock_content,
    channel_name="instagram",
    brand_config=cfg,
    canvas_size=(1080, 1350),
    visual_guidelines_context="Stile minimalista, blocchi ad alto contrasto, badge in evidenza.",
    use_ai_design=True
)

output_path = "data/generated/test_output.svg"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(svg_result)

print(f"[Test Completato] File SVG salvato in: {output_path}")
print(f"Primi 300 caratteri dell'output:\n{svg_result[:300]}")
