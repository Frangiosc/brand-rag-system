import re

def clean_generated_post(text: str) -> str:
    """
    Pulisce e normalizza il testo generato dall'LLM per rimuovere artefatti di formattazione,
    spaziature verticali eccessive, introduzioni fittizie ed errori negli hashtag.
    """
    if not text:
        return ""

    # 1. Rimozione di blocchi di codice markdown (es. ```, ```markdown, ```text)
    text = re.sub(r"^```[a-zA-Z]*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)
    text = text.strip("`").strip()

    # 2. Rimozione di frasi introduttive tipiche degli LLM (case-insensitive)
    intro_patterns = [
        r"^(ecco|here is|sure|certamente|di seguito|questo è).*?:\s*\n*",
        r"^ecco il copy.*?:\s*\n*",
        r"^post pronto.*?:\s*\n*",
        r"^ecco un post.*?:\s*\n*",
        r"^ecco il post.*?:\s*\n*"
    ]
    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 3. Normalizzazione delle interruzioni di riga eccessive (massimo 2 consecutive per layout pulito)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 4. Pulizia e ottimizzazione degli hashtag
    text = re.sub(r"##+", "#", text)       # Corregge eventuali doppi hashtag accidentali (es. ##UNICAM -> #UNICAM)
    text = re.sub(r"(?<=\w)#", " #", text) # Assicura uno spazio vuoto prima di un hashtag se è attaccato a una parola

    # Correzione allucinazioni sulla denominazione dell'ateneo
    text = re.sub(r'(?i)politecnico\s+di\s+camerino', 'Università di Camerino', text)
    text = re.sub(r'(?i)politecnico\s+unicam', 'UNICAM', text)
    
    # Rimuove eventuali etichette rigide residue
    text = re.sub(r'^(Titolo|Corpo del post|Dettagli|Call to Action|Hashtag):\s*', '', text, flags=re.MULTILINE)

    return text.strip()