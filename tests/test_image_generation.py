import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration, get_channel_templates
from src.image_generation import generate_brand_background

def test_image_background_pipeline():
    print("=== TEST BACKEND: GENERAZIONE SFONDO GRAFICO (TEXT-TO-IMAGE) ===")
    
    # 1. Carichiamo le dimensioni geometriche direttamente dal tuo JSON del WP3 per Instagram Vertical (1080x1350)
    config = load_brand_configuration()
    insta_data = get_channel_templates(config, "instagram")
    vertical_format = insta_data.get("formats", {}).get("vertical", {})
    
    dimensions_str = vertical_format.get("dimensions", "1080x1350")
    width, height = map(int, dimensions_str.split("x"))
    
    # 2. Testiamo il generatore passando il contesto del post di cybersecurity
    simulated_post_context = (
        "Il nuovo laboratorio di cybersecurity di UNICAM è finalmente aperto! "
        "In questo spazio innovativo potrai imparare a sviluppare strategie di difesa digitale."
    )
    
    try:
        # Generiamo lo sfondo
        bg_image = generate_brand_background(
            post_context=simulated_post_context,
            dimensions=(width, height)
        )
        
        # 3. Salviamo il file generato nella cartella di output temporanea
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "generated")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, "test_background.jpg")
        bg_image.save(output_path, "JPEG", quality=95)
        
        print("\n✅ GENERAZIONE COMPLETATA!")
        print(f" -> Dimensioni finali: {bg_image.size[0]}x{bg_image.size[1]}px (Attese: {width}x{height}px)")
        print(f" -> File salvato con successo in: {output_path}")
        
        assert bg_image.size == (width, height), "Le dimensioni generate non corrispondono alle specifiche JSON!"
        
    except Exception as e:
        print(f"\n❌ Errore durante il test di generazione: {str(e)}")

if __name__ == "__main__":
    test_image_background_pipeline()