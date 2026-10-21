from typing import Dict, Any, List

def detect_language(text: str) -> str:
    """
    Rileva la lingua richiesta. Default prioritario su ITALIANO 
    a meno che il testo non contenga un'esplicita richiesta in inglese.
    """
    text_lower = text.lower()
    if any(phrase in text_lower for phrase in ["in english", "write in english", "english version"]):
        return "INGLESE"
    
    return "ITALIANO"

def build_system_prompt() -> str:
    return (
        "Sei l'assistente AI ufficiale di UNICAM (Università di Camerino), "
        "un Social Media Manager esperto specializzato nella creazione di copy "
        "istituzionali e coinvolgenti per i canali digitali dell'ateneo (@unicamente_informatica).\n\n"
        "REGOLE TASSATIVE PER LA GENERAZIONE DEL COPY:\n"
        "1. DENOMINAZIONE UFFICIALE: L'ateneo è l''Università di Camerino' (o 'UNICAM'). È TASSATIVAMENTE VIETATO usare espressioni errate come 'Politecnico di Camerino'.\n"
        "2. DIVIETO ASSOLUTO DI ALLUCINAZIONI: Non inventare mai date, orari, aule, scadenze o relatori fittizi se non sono presenti nella richiesta dell'utente.\n"
        "3. ZERO ETICHETTE TECNICHE E PLACEHOLDER: Non usare stringhe come 'Titolo:', 'Corpo:', 'Dettagli:', '[nome relatore]' o parentesi quadre. Scrivi direttamente il copy pronto da pubblicare.\n"
        "4. REGISTRO E TONO DI VOCE:\n"
        "   - Per RICERCA / INNOVAZIONE / RUBRICHE: Tono entusiasta, divulgativo, autorevole ed elegante.\n"
        "   - Per AVVISI / BANDI / TASSE / PROCEDURE: Tono formale, chiaro, rassicurante ed istituzionale.\n"
        "5. CALL TO ACTION E LINK: Se è presente un link web, introducilo in modo fluido e visivamente distinto "
        "(es. '👉 Scopri tutti i dettagli al link:', '🔗 Consulta la procedura sul portale:'). Non incollare URL nudi senza contesto.\n"
        "6. EMOJI E HASHTAG: Uso moderato di emoji pertinenti (max 2-3). Concludi il post con 3-4 hashtag istituzionali rilevanti (es. #UNICAM #InformaticaUNICAM)."
    )

def assemble_final_prompt(
    user_query: str,
    retrieved_context: str,
    few_shot_context: str,
    channel_name: str,
    channel_constraints: Dict[str, Any]
) -> str:
    detected_lang = detect_language(user_query)
    
    # Rilevamento flessibile dei vincoli di formato (singolo formato o dict multi-formato)
    if "max_characters" in channel_constraints or "aspect_ratio" in channel_constraints:
        char_limit = channel_constraints.get("max_characters", 2200)
        aspect_ratio = channel_constraints.get("aspect_ratio", "N/D")
        dimensions = channel_constraints.get("dimensions", "1080x1350")
        formats_specification = f"- Formato attivo: Aspect Ratio {aspect_ratio} ({dimensions}) | Limite caratteri: {char_limit}\n"
        max_chars = f"Fino a {char_limit}"
    else:
        formats = channel_constraints.get("formats", {})
        formats_specification = ""
        unique_limits = set()
        for format_name, details in formats.items():
            if isinstance(details, dict):
                c_lim = details.get("max_characters", "N/D")
                if c_lim != "N/D":
                    unique_limits.add(str(c_lim))
                formats_specification += (
                    f"- Formato '{format_name}': Aspect Ratio {details.get('aspect_ratio')} "
                    f"({details.get('dimensions')}) | Limite caratteri: {c_lim}\n"
                )
        max_chars = " / ".join(unique_limits) if unique_limits else "Standard (max 2200)"

    few_shot_section = few_shot_context if few_shot_context.strip() else "Nessun esempio specifico fornito. Mantieni un layout editoriale pulito e istituzionale."

    final_prompt = f"""=== CONFIGURAZIONE OUTPUT ===
- LINGUA DI OUTPUT RICHIESTA: {detected_lang}

=== CONTESTO STRATEGICO DI BRAND (Dati dal Vector DB) ===
{retrieved_context}

=== MODELLI ED ESEMPI DI ISPIRAZIONE (Few-Shot Learning) ===
{few_shot_section}

=== VINCOLI GEOMETRICI E DI CANALE ===
- Canale di destinazione: {channel_name.upper()}
- Limite caratteri: {max_chars} caratteri
- Specifiche grafiche:
{formats_specification}

=== ISTRUZIONE OPERATIVA DELL'UTENTE ===
Query: {user_query}

=== OUTPUT RICHIESTO (LEGGERE ATTENTAMENTE) ===
Genera esclusivamente il testo del post pronto per la pubblicazione su {channel_name.upper()} in lingua {detected_lang}.

DIVIETI TASSATIVI:
1. NON INSERIRE ETICHETTE TECNICHE come 'Titolo:', 'Corpo del post:', 'Hashtag:'.
2. NON INSERIRE PLACEHOLDER come '[Specificare data]' o '[Inserire link]'.
3. Scrivi un testo unico, fluido, suddiviso solo da paragrafi naturali.
"""
    return final_prompt