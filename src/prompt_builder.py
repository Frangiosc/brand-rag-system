from typing import Dict, Any, List

def detect_language(text: str) -> str:
    """
    Rileva la lingua richiesta. Default prioritario su ITALIANO 
    a meno che il testo non contenga un'esplicita richiesta in inglese.
    """
    text_lower = text.lower()
    if "in english" in text_lower or "write in english" in text_lower or "english version" in text_lower:
        return "INGLESE"
    
    return "ITALIANO"

def build_system_prompt() -> str:
    return (
        "Sei l'assistente AI ufficiale di UNICAM (Università di Camerino), "
        "un Social Media Manager esperto specializzato nella creazione di copy "
        "istituzionali e coinvolgenti per i canali digitali dell'ateneo.\n\n"
        "REGOLE TASSATIVE PER LA GENERAZIONE DEL COPY:\n"
        "1. DENOMINAZIONE UFFICIALE: L'ateneo è l' 'Università di Camerino' (o 'UNICAM'). È TASSATIVAMENTE VIETATO usare espressioni errate come 'Politecnico di Camerino'.\n"
        "2. DIVIETO DI ALLUCINAZIONI E ETICHETTE RIGIDE: Non inventare dati non presenti nel prompt e non usare stringhe come 'Titolo:', 'Corpo:', '[nome]'.\n"
        "3. INTEGRITÀ E TONO: Adatta il tono al contesto (formale per avvisi e bandi, dinamico per eventi e rubriche)."
        "4. DIVIETO ASSOLUTO DI ALLUCINAZIONE DI DATE/LUOGHI: Se il post riguarda un articolo, una rubrica o una ricerca e NON menziona un evento con data/ora/aula, NON INVENTARE MAI date, orari, aule o relatori fittizi!\n"
        "5. INTEGRAZIONE NATURALE DELLA CALL TO ACTION: Integra il link in modo fluido e invitante nel testo (es. 'Leggi l'articolo completo sul nostro portale:', 'Per scoprire tutti i dettagli della ricerca, visita il link:'). Avoid link incollati senza contesto.\n"
        "6. ZERO ETICHETTE RIGIDE E ZERO PLACEHOLDER: Non usare stringhe come 'Titolo:', 'Corpo:', 'Dettagli:', '[nome relatore]' o parentesi quadre.\n"
        "7. ADATTAMENTO DEL TONO:\n"
        "   - Per RICERCA / INNOVAZIONE / RUBRICHE: Tono entusiasta, divulgativo, autorevole ed elegante.\n"
        "   - Per AVVISI / TASSE: Tono formale ed istituzionale.\n"
        "8. USO MODERATO DI EMOJI: Max 2-3 emoji tematiche e pertinenti.\n"
        "9. HASHTAG: Inserisci max 3-4 hashtag pertinenti in fondo al post."
        "10. CALL TO ACTION E LINK: Introduci il link in modo chiaro e visivamente distinto "
        "(es. '👉 Leggi l'estratto dell'articolo completo sul nostro portale:' oppure '🔗 Consulta la pubblicazione al link:')."
    )

def assemble_final_prompt(
    user_query: str,
    retrieved_context: str,
    few_shot_context: str,
    channel_name: str,
    channel_constraints: Dict[str, Any]
) -> str:
    detected_lang = detect_language(user_query)
    
    formats = channel_constraints.get("formats", {})
    formats_specification = ""
    unique_limits = set()
    
    for format_name, details in formats.items():
        if isinstance(details, dict):
            if "aspect_ratio" in details:
                char_limit = details.get("max_characters", "N/D")
                if char_limit != "N/D":
                    unique_limits.add(str(char_limit))
                
                formats_specification += (
                    f"- Formato '{format_name}': Aspect Ratio {details.get('aspect_ratio')} "
                    f"({details.get('dimensions')}) | Limite caratteri: {char_limit}\n"
                )

    max_chars = " / ".join(unique_limits) if unique_limits else "Non specificato"
    few_shot_section = few_shot_context if few_shot_context.strip() else "Nessun esempio specifico fornito. Mantieni un layout editoriale pulito e istituzionale."

    final_prompt = f"""=== CONFIGURAZIONE OUTPUT ===
- LINGUA DI OUTPUT RICHIESTA: {detected_lang}

=== CONTESTO STRATEGICO DI BRAND (Dati dal Vector DB) ===
{retrieved_context}

=== MODELLI ED ESEMPI DI ISPIRAZIONE (Few-Shot Learning) ===
{few_shot_section}

=== VINCOLI GEOMETRICI E DI CANALE ===
- Canale di destinazione: {channel_name.upper()}
- Limite caratteri generico rilevato: {max_chars} caratteri
- Specifiche grafiche e formati consigliati:
{formats_specification}

=== ISTRUZIONE OPERATIVA DELL'UTENTE ===
Query: {user_query}

=== OUTPUT RICHIESTO (LEGGERE ATTENTAMENTE) ===
Genera esclusivamente il testo del post pronto per la pubblicazione su {channel_name.upper()} in lingua {detected_lang}.

DIVIETI TASSATIVI:
1. NON INSERIRE ETICHETTE TECNICHE come 'Titolo:', 'Corpo del post:', 'Dettagli chiave:', 'Call to Action:', 'Hashtag:'.
2. NON INSERIRE PLACEHOLDER come '[Specificare data]' o '[Inserire ora]'.
3. Scrivi un testo unico, fluido, suddiviso solo da a capo naturali.
4. Se l'avviso riguarda tasse o adempimenti, usa un tono formale, chiaro ed istituzionale.
"""
    return final_prompt