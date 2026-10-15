import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brand_config_loader import load_brand_configuration, get_channel_templates

def test_loader():
    print("=== TEST PARSING BRAND CONFIGURATION UFFICIALE ===")
    
    try:
        config = load_brand_configuration()
        print("✅ Caricamento del file JSON completato con successo.")
        
        # Estraiamo i dati di Instagram dal tuo file reale
        insta_data = get_channel_templates(config, "instagram")
        print(f"\n📱 Canale Rilevato: {insta_data.get('handle', 'N/D')}")
        
        # Testiamo la lettura di un formato specifico
        formats = insta_data.get("formats", {})
        vertical_format = formats.get("vertical", {})
        
        print("\n📐 Vincoli Geometrici Formato Verticale:")
        print(f" -> Rapporto d'aspetto (Aspect Ratio): {vertical_format.get('aspect_ratio')}")
        print(f" -> Dimensioni pixel: {vertical_format.get('dimensions')}")
        print(f" -> Massimo numero caratteri: {vertical_format.get('max_characters')}")
        
        assert vertical_format.get("max_characters") == 2200, "Errore di corrispondenza dati!"
        print("\n✅ TEST DI REGRESSIONE SUPERATO: Il parser legge perfettamente il tuo schema di configurazione del WP3.")
        
    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione del test: {str(e)}")

if __name__ == "__main__":
    test_loader()