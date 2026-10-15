import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration
from src.image_generation import generate_brand_background
from src.layout_assembly import compose_final_graphic

def test_composition():
    print("=== TEST COMPOSIZIONE GEOMETRICA CON SCHELETRO JSON REALE ===")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, "data", "generated", "test_final_post.jpg")
    
    # 1. Carichiamo la configurazione
    config = load_brand_configuration()
    
    # 2. Generiamo lo sfondo (Instagram Vertical: 1080x1350)
    dimensions = (1080, 1350)
    bg_image = generate_brand_background("Post orientamento informatica", dimensions)
    
    # 3. Testo del post da incidere
    testo_post = (
        "Studiare Informatica a UNICAM significa vivere "
        "i laboratori fin dal primo giorno. Progetta il tuo futuro "
        "con noi e sviluppa le tue idee!"
    )
    
    # 4. Esecuzione del montaggio dinamico (prende logo, colori e font direttamente dal JSON)
    print("\n🛠️ Assemblaggio grafico in corso...")
    final_graphic = compose_final_graphic(
        background_img=bg_image,
        text_content=testo_post,
        channel_name="instagram",
        brand_config=config
    )
    
    # 5. Salvataggio
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_graphic.save(output_path, "JPEG", quality=95)
    
    print(f"\n✅ COMPOSIZIONE COMPLETATA CON SUCCESSO!")
    print(f" -> Output salvato in: {output_path}")
    print(f" -> Dimensioni: {final_graphic.size[0]}x{final_graphic.size[1]}px")

if __name__ == "__main__":
    test_composition()