import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.post_processor import clean_generated_post

def test_post_processor_rules():
    print("=== TEST REGRESSIONE: POST-PROCESSORI DI TESTO ===")
    
    # Prepariamo un testo fittizio sporco con tutti i tipici errori dell'LLM
    dirty_text = (
        "```markdown\n"
        "Ecco il post che hai richiesto:\n\n"
        "Vuoi studiare Informatica ad UNICAM? 🚀\n\n\n\n" # Troppe righe vuote
        "Scopri i nostri laboratori pratici!💻\n"
        "Unisciti alla nostra community##UNICAM #Informatica\n" # Doppio hashtag e attaccato alla parola
        "```"
    )
    
    clean_text = clean_generated_post(dirty_text)
    
    print("\n--- TESTO DI INPUT (SPORCO) ---")
    print(repr(dirty_text))
    
    print("\n--- TESTO DI OUTPUT (ELABORATO) ---")
    print(repr(clean_text))
    print("\nVisualizzazione reale:")
    print(clean_text)
    
    # Asserzioni di sicurezza
    assert "```" not in clean_text, "Errore: blocchi di codice markdown non rimossi!"
    assert "Ecco il post" not in clean_text, "Errore: frasi introduttive non rimosse!"
    assert "\n\n\n" not in clean_text, "Errore: spaziature vuote eccessive non normalizzate!"
    assert "##" not in clean_text, "Errore: doppi hashtag non corretti!"
    assert "community #" in clean_text, "Errore: mancato spazio di separazione prima dell'hashtag!"
    
    print("\n✅ TEST DI REGRESSIONE SUPERATO: Il post-processore corregge ogni difetto di layout!")

if __name__ == "__main__":
    test_post_processor_rules()