import streamlit as st
import os
import json
import re
import unicodedata
import random
import cairosvg
from PIL import Image

# Backend core imports
from src.ingestion import run_semantic_ingestion
from src.vector_store import initialize_vector_store
from src.orchestrator import retrieve_brand_context
from src.brand_config_loader import load_brand_configuration
from src.prompt_builder import build_system_prompt, assemble_final_prompt
from src.generation import generate_social_post
from src.post_processor import clean_generated_post
from src.svg_export import generate_brand_svg

st.set_page_config(
    page_title="@unicamente_informatica Studio - Multimodal Platform",
    page_icon="🎯",
    layout="wide"
)

# Percorsi locali
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "documents_ui")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "assets")
JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "structured")

# --- HELPER FUNCTIONS ---
def get_doc_files(subfolder):
    p = os.path.join(UPLOAD_DIR, subfolder)
    return [f for f in os.listdir(p) if not f.startswith('.') and f.lower().endswith(('.pdf', '.txt', '.json', '.png', '.jpg', '.jpeg'))] if os.path.exists(p) else []

def get_asset_files(subfolder):
    p = os.path.join(ASSETS_DIR, subfolder)
    valid_exts = ('.png', '.jpg', '.jpeg', '.ttf')
    return [f for f in os.listdir(p) if not f.startswith('.') and f.lower().endswith(valid_exts)] if os.path.exists(p) else []

def normalize_token(s: str) -> str:
    if not s: 
        return ""
    s = unicodedata.normalize('NFD', str(s))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

def get_asset_descriptions():
    catalog = {}
    for category in ["mascots", "rubrics"]:
        folder = os.path.join(ASSETS_DIR, category)
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.'):
                    clean_name = re.sub(r'^\([A-Z]\)_Asset_', '', os.path.splitext(f)[0], flags=re.IGNORECASE)
                    desc = f"Simbolo/Badge per la rubrica '{clean_name}'" if category == "rubrics" else f"Mascotte '{clean_name}'"
                    catalog[f] = f"[{category.upper()}] {desc}"
    return catalog

def extract_speaker_safely(prompt: str) -> str:
    direct_title_match = re.search(
        r'((?:Prof\.ssa|Prof\.|Dott\.ssa|Dott\.|Dr\.ssa|Dr\.|Ing\.)\s+[A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)*(?:\s+(?:di|dell\'università di|della)\s+[A-Za-zÀ-ÿ]+)?)',
        prompt
    )
    if direct_title_match:
        return direct_title_match.group(1).strip()
    
    intro_match = re.search(
        r'(?:relatore|relatrice|ospite|con la partecipazione di|a cura di|tenuto da)[^\.\n,:]*?\b(?:il|la|del|della|da|sarà)\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)*(?:\s+(?:di|dell\'università di)\s+[A-Za-zÀ-ÿ]+)?)',
        prompt,
        re.IGNORECASE
    )
    if intro_match:
        return intro_match.group(1).strip()
    return ""

def extract_interview_details(prompt: str):
    name_match = re.search(
        r'((?:Prof\.ssa|Prof\.|Dott\.ssa|Dott\.|Dr\.ssa|Dr\.|Ing\.)\s+[A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)',
        prompt
    )
    if not name_match:
        name_match = re.search(
            r'(?:intervista\s+(?:con|a|alla|all\')|ospite:?|dedicata alla|dedicato a|dedicata al)\s*(?:l\'|la|il|della|dell\')?\s*(?:ingegnere del software|ingegnera del software|ingegnere dei dati|ingegnera dei dati|ingegnere|ingegnera|ricercatrice|ricercatore|data scientist|software engineer|docente)?\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)',
            prompt,
            re.IGNORECASE
        )
    if not name_match:
        name_match = re.search(
            r'(?:intervista|ospite)[^\.\n,]*?\b(?:con|a)\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)',
            prompt,
            re.IGNORECASE
        )
    interviewee_name = name_match.group(1).strip() if name_match else ""
    interviewee_name = re.sub(r'^(?:del software|dei dati|di informatica)\s+', '', interviewee_name, flags=re.IGNORECASE).strip()

    role_parts = []
    base_role = re.search(r'(?:con|a|all\')\s*(?:l\'|la|il)?\s*((?:ingegnere del software|ingegnera del software|ingegnere dei dati|ingegnera dei dati|ingegnere|ingegnera|ricercatrice|ricercatore|data scientist|software engineer|docente)\s*(?:di|in|dei\s+dati|del\s+software)?\s*[^,\.\n]*)', prompt, re.IGNORECASE)
    if base_role:
        clean_base = base_role.group(1).strip()
        if interviewee_name:
            clean_base = re.sub(re.escape(interviewee_name), '', clean_base, flags=re.IGNORECASE).strip()
        clean_base = re.sub(r'^(?:del software|dei dati)\s+', '', clean_base, flags=re.IGNORECASE).strip()
        if clean_base:
            role_parts.append(clean_base.capitalize())

    job_match = re.search(r'([A-Za-z\s]+presso\s+[^,\.\n]+)', prompt, re.IGNORECASE)
    if job_match:
        role_parts.append(job_match.group(1).strip())
    elif not role_parts:
        gen_role = re.search(r'((?:Docente|Professoressa|Professore|PhD|Esperta|Esperto)\s+(?:di|in)\s+[^,\.\n]+)', prompt, re.IGNORECASE)
        if gen_role:
            role_parts.append(gen_role.group(1).strip())

    role_str = " • ".join(role_parts) if role_parts else ""

    focus_match = re.search(
        r'(?:vengono approfonditi|vengono approfondite|viene raccontata|viene approfondito il tema (?:dell\'|del|di|della)?|racconta|approfondisce)\s+([^,\.\n]+(?:\s+e\s+[^,\.\n]+)?)',
        prompt,
        re.IGNORECASE
    )
    if not focus_match:
        focus_match = re.search(r'(?:focus su|tema:|esperienza lavorativa (?:in|nello|su)?|sviluppo di)\s+([^,\.\n]+)', prompt, re.IGNORECASE)
    
    focus_str = focus_match.group(1).strip().capitalize() if focus_match else ""
    return interviewee_name, role_str, focus_str

# Inizializzazione Session State
if "vector_db" not in st.session_state:
    try:
        st.session_state["vector_db"] = initialize_vector_store()
    except Exception:
        st.session_state["vector_db"] = None

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "generation"

if "generated_output" not in st.session_state:
    st.session_state["generated_output"] = None

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("Navigation")
    st.write("Select your workspace:")
    
    if st.button("✍️ Content Generation Workspace", use_container_width=True, type="primary" if st.session_state["current_page"] == "generation" else "secondary"):
        st.session_state["current_page"] = "generation"
        st.rerun()
        
    if st.button("🚀 Brand Workspace", use_container_width=True, type="primary" if st.session_state["current_page"] == "onboarding" else "secondary"):
        st.session_state["current_page"] = "onboarding"
        st.rerun()
        
    st.divider()
    if st.session_state.get("generated_output"):
        if st.button("🔄 Reset Content & Chat", use_container_width=True):
            st.session_state["generated_output"] = None
            st.session_state["chat_history"] = []
            st.rerun()
    st.caption("CoreBrand Studio Engine v1.7.0 © 2026")


# ==========================================
# PAGINA 1: CONTENT GENERATION WORKSPACE
# ==========================================
if st.session_state["current_page"] == "generation":
    st.title("🎯 @unicamente_informatica Studio")
    st.subheader("Multimodal Retrieval, Copywriting & Layout Automation Platform")
    st.write("Configure channel parameters, aspect ratio, and creative inspiration to generate aligned copy and visual assets.")
    
    st.divider()

    generation_mode = st.radio(
        "Choose your work mode:",
        options=["🎨 Generate posts and graphics", "💡 Content Strategy & Brainstorming"],
        horizontal=True
    )
    st.divider()

    # --- BRAINSTORMING ---
    if generation_mode == "💡 Content Strategy & Brainstorming":
        st.markdown("### 🧠 Strategic Brainstorming Based on Personas & Funnels")
        st.caption("Request targeted content ideas. The system will analyze the Knowledge Base to align personas, funnel stages, and ideal formats.")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            target_persona_select = st.selectbox(
                "Persona Target (Optional):",
                options=[
                    "Tutte / Generica", 
                    "Francesca (Ragazze Liceo / No Basi Coding / Inclusione)", 
                    "Lorenzo (Diplomato ITIS / ICD)", 
                    "Daniela (Studentessa Fuori Regione / Sud)", 
                    "Fabio (Laureato Triennale / Magistrale CS)"
                ]
            )
        with col_p2:
            funnel_stage_select = st.multiselect(
                "Funnel Stage (Optional):",
                options=["Awareness", "Consideration", "Coinvolgimento", "Fidelizzazione"],
                default=["Consideration", "Fidelizzazione"]
            )

        strategy_prompt = st.text_area(
            "Instruction or Communication Objective:",
            height=130,
            placeholder="e.g., I would like content ideas to encourage high school girls to enroll in Computer Science, showing that the courses start from scratch and breaking down gender stereotypes.",
            key="strat_prompt"
        )

        if st.button("🚀 Generate Strategic Content Ideas", type="primary", use_container_width=True):
            if not strategy_prompt:
                st.error("Enter a goal or an instruction before proceeding!")
            else:
                with st.spinner("Knowledge Base analysis (Personas & Funnel) in progress..."):
                    try:
                        query_expanded = f"{strategy_prompt} {target_persona_select} {' '.join(funnel_stage_select)}"
                        retrieved_docs = retrieve_brand_context(
                            query=query_expanded,
                            categories=["target_personas", "funnel_stages", "rubriche"],
                            k_per_category=2
                        )
                        
                        context_str = ""
                        for doc, _ in retrieved_docs:
                            context_str += f"## CATEGORIA {doc.metadata.get('category').upper()}:\n{doc.page_content}\n\n"

                        brainstorm_system_prompt = """
Sei lo Strategist di Comunicazione della sezione di Informatica dell'Università di Camerino (UNICAM).
Il tuo compito è proporre 3 idee di contenuto fortemente targhettizzate, basate sui documenti di strategia (Personas e Funnel Stages) forniti.

REGOLE DI LINGUA E FORMATO (RIGIDISSIME):
1. DEVI SCRIVERE TUTTO ESCLUSIVAMENTE IN LINGUA ITALIANA.
2. NON aggiungere mai commenti o spiegazioni generali alla fine delle idee.
3. Rispetta tassativamente la struttura indicata senza cambiare i nomi dei campi.

Per ciascuna delle 3 idee proponi questa struttura esatta in Markdown:

### Idea [N]: [Titolo sintetico dell'Idea in Italiano]
- **Target e Bisogno:** Spiega in italiano a quale persona ti rivolgi e quale suo dubbio o paura affronta.
- **Fase del Funnel:** Indica la fase in italiano e l'obiettivo.
- **Piattaforma e Formato Consigliato:** Formato in italiano (es. Reel, Post Carosello, Storie).
- **Concept Visivo:** Descrivi in italiano cosa mostrare nel video o nella grafica.
- **Proposta di Copywriting e Gancio:** La frase di apertura (hook) e l'angolo del testo in italiano.
- **Punti di Forza UNICAM da evidenziare:** Punti chiave in italiano (es. Posizione CENSIS, interviste fuori sede, vita da studente, comunità, tutorato).
"""

                        final_brainstorm_prompt = f"""
CONTESTO STRATEGICO RECUPERATO DALLA KNOWLEDGE BASE:
{context_str}

RICHIESTA UTENTE:
"{strategy_prompt}"
Persona Selezionata: {target_persona_select}
Funnel Stages desiderati: {', '.join(funnel_stage_select)}

Genera 3 idee di contenuti originali, chiare e immediatamente operative per il team Social Media.
"""
                        ideas_output = generate_social_post(
                            system_prompt=brainstorm_system_prompt,
                            user_prompt=final_brainstorm_prompt
                        )

                        st.success("✨ Strategic content ideas generated successfully!")
                        st.markdown(ideas_output)

                    except Exception as e:
                        st.error(f"Error during content ideas generation: {str(e)}")

    # --- GENERAZIONE POST & GRAFICA ---
    elif generation_mode == "🎨 Generate posts and graphics":
        st.markdown("### 💡 Turn Your Ideas Into Brand-Aligned Content")
        st.caption("Enter your prompt below and fine-tune channel, aspect ratio, and knowledge filters before generating.")
        
        st.markdown("""
        <style>
        div[data-testid="stTextArea"] textarea { padding-bottom: 50px !important; }
        div[data-testid="stHorizontalBlock"]:has(button[aria-haspopup="dialog"]) {
            margin-top: -55px !important;
            margin-bottom: 25px !important;
            padding-right: 15px !important;
            position: relative;
            z-index: 9999 !important;
        }
        div[data-testid="stPopoverBody"], div[role="dialog"] {
            z-index: 99999 !important;
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0 !important;
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.15) !important;
        }
        div[data-baseweb="popover"] { z-index: 100000 !important; }
        </style>
        """, unsafe_allow_html=True)
        
        user_prompt = st.text_area(
            "Generation Instruction", 
            height=160,
            placeholder="e.g., Write a post informing new students about our hands-on computer science labs available from the first year...",
            label_visibility="collapsed"
        )

        col_empty, col_chan_pop, col_form_pop, col_filt_pop = st.columns([3, 1.1, 1.1, 1.2])

        with col_chan_pop:
            with st.popover("📱 Channel"):
                selected_channel = st.radio("Target Social Platform:", options=["Instagram", "LinkedIn"], index=0)

        with col_form_pop:
            with st.popover("📐 Format"):
                selected_format = st.radio("Aspect Ratio & Proportions:", options=["Vertical (4:5)", "Square (1:1)", "Stories/Reels (9:16)", "Horizontal (1.91:1)"], index=0)

        with col_filt_pop:
            with st.popover("⚙️ Filters"):
                categories_selected = st.multiselect("Knowledge Base Categories:", options=["target_personas", "social_media_voice", "tone_of_voice", "funnel_stages", "rubriche"], default=["target_personas", "tone_of_voice"])
                k_val = st.number_input("Retrieved chunks per category (k):", min_value=1, max_value=3, value=1)

        st.write("")

        col_space, col_btn_ret, col_btn_gen = st.columns([2, 1.2, 1.5])
        with col_btn_ret:
            btn_retrieve = st.button("🔍 Context Retrieval Only", use_container_width=True)
        with col_btn_gen:
            btn_generate = st.button("🚀 Generate Post & Graphic", use_container_width=True, type="primary")

        st.divider()

        few_shot_context_str = ""
        visual_asset_source = None

        if btn_retrieve or btn_generate:
            if not user_prompt:
                st.error("Please enter a prompt instruction before proceeding!")
            elif not categories_selected:
                st.error("Please select at least one filter category before proceeding!")
            else:
                with st.spinner("Processing request..."):
                    try:
                        retrieved_results = retrieve_brand_context(query=user_prompt, categories=categories_selected, k_per_category=k_val)
                        
                        few_shot_results = []
                        if st.session_state["vector_db"]:
                            few_shot_results = st.session_state["vector_db"].similarity_search(user_prompt, k=1, filter={"category": "esempi_ispirazione"})
                        
                        if few_shot_results:
                            few_shot_context_str = few_shot_results[0].page_content
                            if "visual_asset_path" in few_shot_results[0].metadata:
                                visual_asset_source = few_shot_results[0].metadata["visual_asset_path"]
                        
                        retrieved_context_str = ""
                        visual_guidelines_str = ""
                        for doc, score in retrieved_results:
                            cat = doc.metadata.get('category', '').lower()
                            retrieved_context_str += f"## CATEGORIA: {cat.upper()}\n"
                            retrieved_context_str += f"[Fonte: {doc.metadata.get('source_file')}]: {doc.page_content}\n\n"
                            
                            # Raccogliamo indicazioni specifiche per il layout grafico da rubriche, voice e tone
                            if cat in ["rubriche", "social_media_voice", "tone_of_voice"]:
                                visual_guidelines_str += f"[{cat.upper()}]: {doc.page_content}\n"
                        
                        brand_config = load_brand_configuration()
                        
                        format_mapping = {
                            "Vertical (4:5)": "vertical",
                            "Square (1:1)": "square",
                            "Stories/Reels (9:16)": "reels_and_stories",
                            "Horizontal (1.91:1)": "horizontal"
                        }
                        format_key = format_mapping[selected_format]
                        
                        channel_templates = brand_config.get("channel_templates", {}).get(selected_channel.lower(), {})
                        format_details = channel_templates.get("formats", {}).get(format_key, {})
                        
                        if not format_details and selected_channel.lower() == "linkedin":
                            format_details = channel_templates.get("formats", {}).get("single_image_posts", {}).get(format_key, {})

                        dimensions_str = format_details.get("dimensions", "1080x1350")
                        canvas_width, canvas_height = map(int, dimensions_str.split("x"))
                        
                        if btn_retrieve:
                            st.success(f"Context retrieved! Extracted parameters: {canvas_width}x{canvas_height}px.")
                            with st.expander("📂 Inspection of Format Parameters & Context", expanded=True):
                                st.json(format_details)
                                if visual_asset_source:
                                    st.info(f"Associated reference visual: {visual_asset_source}")
                                    
                        if btn_generate:
                            asset_catalog = get_asset_descriptions()
                            catalog_str = json.dumps(asset_catalog, indent=2, ensure_ascii=False)
                            
                            extraction_prompt = f"""
Sei un Information Extraction Engine rigoroso per l'Università di Camerino.
Classifica ed estrai le informazioni dal prompt utente seguendo RIGIDAMENTE uno dei 6 tipi di grafica previsti:

1. EVENTI E SEMINARI / HACKATHON:
   - "title": Titolo dell'evento in forma nominale.
   - "subtitle_or_cta": Dettagli principali (relatore/ingressi/sponsor).
   - "label_1_name": 'DATA E ORA', "label_1_val": Date estratte.
   - "label_2_name": 'LUOGO', "label_2_val": Sede/Aula estratta.
   
2. BANDI E OPPORTUNITÀ:
   - "title": Titolo dell'opportunità in forma nominale.
   - "subtitle_or_cta": Call to action a partecipare.
   - "label_1_name": 'SCADENZA CANDIDATURE', "label_1_val": Data di scadenza.
   - "label_2_name": '', "label_2_val": ''.

3. ADEMPIMENTI BUROCRATICI E PROCEDURE:
   - "title": Nome esatto della procedura in forma NOMINALE.
   - "subtitle_or_cta": Call to action d'obbligo o destinatari.
   - "label_1_name": 'SCADENZA', "label_1_val": Data di scadenza.
   - "label_2_name": 'PORTALE', "label_2_val": Circuito o Portale.

4. INTERVISTE & OSPITI DI RUBRICHE:
   - "title": Nome completo dell'ospite preceduto da 'Intervista: '.
   - "subtitle_or_cta": Ruolo, qualifica e azienda/affiliazione dell'ospite.
   - "label_1_name": 'FOCUS DELL\'INTERVISTA', "label_1_val": Argomento o tema trattato estratto dal testo.
   - "label_2_name": '', "label_2_val": ''.

5. RUBRICHE EDITORIALI GENERALI:
   - "title": Nome esatto della rubrica.
   - "subtitle_or_cta": Descrizione del tema trattato.
   - "label_1_name": 'DETTAGLI DEL CONTENUTO', "label_1_val": Risultati e ambito del progetto.
   - "label_2_name": '', "label_2_val": ''.

6. CORSI E LABORATORI / WORKSHOP:
   - "title": Nome del workshop/laboratorio.
   - "subtitle_or_cta": Dettagli completi (scadenze, gratuità, capienza posti).
   - "label_1_name": 'DATA E ORA', "label_1_val": Giorni e orari estratti.
   - "label_2_name": 'LUOGO', "label_2_val": Laboratorio/Aula estratta.

REGOLE GENERALI:
- "contact_info": Indicazioni contatti SOLO SE PRESENTI NEL PROMPT, altrimenti ''.
- "button_text": URL web se presente nel prompt, altrimenti ''.
- "selected_asset": Nome esatto file dal catalogo corrispondente alla rubrica, altrimenti ''.

PROMPT UTENTE:
"{user_prompt}"

Catalogo semantico Asset Visivi:
{catalog_str}

Rispondi ESCLUSIVAMENTE con il JSON valido.
"""
                            raw_extracted = generate_social_post(
                                system_prompt="Sei un parser JSON rigoroso ed oggettivo in lingua italiana.", 
                                user_prompt=extraction_prompt
                            )
                            
                            try:
                                json_match = re.search(r'\{.*\}', raw_extracted, re.DOTALL)
                                meta_data = json.loads(json_match.group(0)) if json_match else json.loads(raw_extracted)
                            except Exception:
                                meta_data = {
                                    "title": user_prompt[:35],
                                    "subtitle_or_cta": "",
                                    "button_text": "",
                                    "label_1_name": "",
                                    "label_1_val": "",
                                    "label_2_name": "",
                                    "label_2_val": "",
                                    "contact_info": "",
                                    "selected_asset": ""
                                }

                            def is_valid_label_val(val: str) -> bool:
                                if not val or not isinstance(val, str):
                                    return False
                                val_upper = val.upper()
                                if any(x in val_upper for x in [".PNG", ".JPG", "[RUBRICS]", "[MASCOTS]", "(B)_ASSET_"]):
                                    return False
                                if "PRESENTAZIONE DEI RISULTATI E APPROFONDIMENTO" in val_upper:
                                    return False
                                return True

                            if not is_valid_label_val(meta_data.get("label_1_val", "")):
                                meta_data["label_1_name"] = ""
                                meta_data["label_1_val"] = ""

                            if not is_valid_label_val(meta_data.get("label_2_val", "")):
                                meta_data["label_2_name"] = ""
                                meta_data["label_2_val"] = ""

                            user_lower = user_prompt.lower()

                            date_match = re.search(
                                r'(\d{1,2}(?:\s+e\s+\d{1,2})?\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+\d{4})?(?:\s+(?:dalle|alle ore|ore|dalle ore)\s+\d{1,2}(?:[:\.]\d{2})?(?:\s+alle\s+\d{1,2}(?:[:\.]\d{2})?)?)?)',
                                user_prompt,
                                re.IGNORECASE
                            )
                            extracted_date = date_match.group(0).strip() if date_match else ""

                            luogo_match = re.search(
                                r'(?:presso|in|all\'interno di)\s+((?:l\'Aula Magna|l\'Aula|l\'Edificio|modalità mista\s*\([^\)]+\)|Sede|Aula Magna|Aula|Laboratorio|Sala|Polo|Edificio)\s+[A-Za-z0-9\s\-_,\(\)]+?)(?=[,\.]|\s+nei giorni|\s+con|\s+a cura|\s+il giorno|\s+il\s+\d|\s+dalle|\s+alle|\s+per info|\s+specifica|\s+candidature|$)',
                                user_prompt,
                                re.IGNORECASE
                            )
                            if not luogo_match:
                                luogo_match = re.search(r'(?:presso|in)\s+((?:l\'Aula Magna|l\'Aula|Aula Magna|Aula|Laboratorio|Sede|Polo)\s+[^,\.\n]+?)(?=[,\.]|\s+nei giorni|\s+con|\s+dalle|\s+ore|\s+per info|\s+specifica|$)', user_prompt, re.IGNORECASE)
                            
                            citta_match = re.search(r'(?:a|in)\s+((?:Macerata|Camerino|Ascoli|Ancona|Fermo|Civitanova))', user_prompt, re.IGNORECASE)
                            citta_str = citta_match.group(1).strip() if citta_match else ""
                            
                            extracted_luogo = luogo_match.group(1).strip() if luogo_match else ""
                            if citta_str and citta_str.lower() not in extracted_luogo.lower() and extracted_luogo and "aula" not in extracted_luogo.lower():
                                extracted_luogo = f"{extracted_luogo}, {citta_str}"
                            elif citta_str and not extracted_luogo:
                                extracted_luogo = citta_str
                            
                            extracted_luogo = re.sub(r'^(?:l\')', 'L\'', extracted_luogo)
                            extracted_luogo = re.sub(r'\bPolo\s+Polo\b', 'Polo', extracted_luogo, flags=re.IGNORECASE)
                            extracted_luogo = re.sub(r'^modalità mista\s*\(([^\)]+)\)', r'\1', extracted_luogo, flags=re.IGNORECASE).strip()

                            extracted_speaker = extract_speaker_safely(user_prompt)
                            interv_name, interv_role, interv_focus = extract_interview_details(user_prompt)

                            prompt_for_quotes = re.sub(r"\b(dell|all|d|l|un|quest|sant|sull|nel|dall)'", r"\1’", user_prompt, flags=re.IGNORECASE)
                            quoted = re.search(r"['“«]([^'”»]+)['”»]", prompt_for_quotes)
                            quoted_title = quoted.group(1).strip() if quoted else ""

                            is_evento_seminario = any(w in user_lower for w in ["seminario", "evento", "hackathon", "convegno", "tavola rotonda", "webinar"])
                            cleaned_for_corso = re.sub(r'corso di laurea', '', user_lower)
                            is_corso = not is_evento_seminario and any(w in cleaned_for_corso for w in ["corso", "laboratorio", "training", "formazione", "workshop"])
                            is_laurea_adempimento = not is_evento_seminario and not is_corso and any(w in user_lower for w in [
                                "piano di studi", "piani di studio", "tasse", "rata", "pagopa", "domanda di laurea", 
                                "scadenza laurea", "sessione di laurea", "immatricolaz", "iscrizione agli appelli", "isee"
                            ])
                            is_bando_opportunita = not is_evento_seminario and not is_corso and not is_laurea_adempimento and any(w in user_lower for w in [
                                "bando", "candidatur", "erasmus", "tirocinio", "borse", "call for", "selezione"
                            ])
                            is_intervista = not is_evento_seminario and not is_corso and not is_laurea_adempimento and not is_bando_opportunita and (
                                any(w in user_lower for w in ["intervista", "ospite", "intervistat"]) or 
                                ("she codes" in user_lower and any(w in user_lower for w in ["prof", "dott", "ingegner", "ingegnar", "ricercatr"]))
                            )
                            is_rubrica_generale = not is_evento_seminario and not is_corso and not is_laurea_adempimento and not is_bando_opportunita and not is_intervista

                            url_match = re.search(r'https?://[^\s]+', user_prompt)
                            extracted_url = url_match.group(0) if url_match else ""

                            sub_test = meta_data.get("subtitle_or_cta", "")
                            if extracted_url:
                                sub_test = sub_test.replace(extracted_url, "").strip()
                            sub_test = re.sub(r'https?://[^\s]+', '', sub_test).strip()
                            sub_test = re.sub(r'al link:?\s*\w*', '', sub_test, flags=re.IGNORECASE).strip()
                            sub_test = re.sub(r'(leggi l\'articolo|leggi l\'intervista)[^\.\n]*', '', sub_test, flags=re.IGNORECASE).strip()
                            meta_data["subtitle_or_cta"] = sub_test

                            if is_corso:
                                prefix_type = "Workshop" if "workshop" in user_lower else ("Laboratorio" if "laboratorio" in user_lower else ("Training" if "training" in user_lower else "Corso"))
                                if quoted_title:
                                    meta_data["title"] = quoted_title if quoted_title.lower().startswith(prefix_type.lower()) else f"{prefix_type}: {quoted_title}"
                                elif not meta_data.get("title") or len(meta_data.get("title", "")) < 8:
                                    meta_data["title"] = f"{prefix_type} Pratico di Informatica"

                                details = []
                                reg_dead_match = re.search(r'(?:registrazione obbligatoria entro (?:il)?|iscrizioni entro (?:il)?|iscrizioni chiudono(?: tassativamente)? (?:il)?|candidature entro (?:il)?|entro (?:il)?)\s+(\d{1,2}(?:°|ª)?\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+\d{4})?)', user_prompt, re.IGNORECASE)
                                if reg_dead_match:
                                    prefix_reg = "Registrazione entro il" if "registrazion" in user_lower else "Iscrizioni entro il"
                                    details.append(f"{prefix_reg} {reg_dead_match.group(1).strip()}")
                                elif any(w in user_lower for w in ["obbligatoria", "tassativa"]):
                                    details.append("Registrazione obbligatoria")

                                if any(w in user_lower for w in ["gratuito", "gratuita", "partecipazione è gratuita", "partecipazione gratuita"]):
                                    details.append("Partecipazione gratuita")

                                posti_match = re.search(r'(?:limitat[oa]\s+a|numero chiuso di|fino a|massimo|capienza di)\s+(\d+\s+(?:partecipanti|studenti|posti))', user_prompt, re.IGNORECASE)
                                if not posti_match:
                                    posti_match = re.search(r'(\d+\s+(?:posti|partecipanti|studenti))', user_prompt, re.IGNORECASE)
                                if posti_match:
                                    details.append(f"Posti limitati a {posti_match.group(1).strip()}")
                                elif any(w in user_lower for w in ["posti limitati", "numero chiuso"]):
                                    details.append("Posti limitati")

                                if extracted_speaker:
                                    details.append(f"A cura di: {extracted_speaker}")

                                if details:
                                    meta_data["subtitle_or_cta"] = " • ".join(details)
                                elif not meta_data.get("subtitle_or_cta"):
                                    meta_data["subtitle_or_cta"] = f"{prefix_type} pratico per gli studenti di Informatica"

                                meta_data["label_1_name"] = "DATA E ORA"
                                meta_data["label_1_val"] = extracted_date if extracted_date else meta_data.get("label_1_val", "")
                                meta_data["label_2_name"] = "LUOGO"
                                meta_data["label_2_val"] = extracted_luogo if extracted_luogo else meta_data.get("label_2_val", "")

                            elif is_laurea_adempimento:
                                if quoted_title:
                                    meta_data["title"] = quoted_title
                                else:
                                    raw_title = meta_data.get("title", "").strip()
                                    raw_title = re.sub(r'^(?:La\s+|Il\s+|Lo\s+|L\'\s*)', '', raw_title, flags=re.IGNORECASE)
                                    raw_title = re.sub(r'^(?:Paga|Pagare|Presenta|Presentare|Compila|Compilare|Ricorda di|Ricorda)\s+', '', raw_title, flags=re.IGNORECASE).strip()
                                    if raw_title and len(raw_title) > 5:
                                        meta_data["title"] = raw_title.capitalize()
                                    elif "piano di studi" in user_lower or "piani di studio" in user_lower:
                                        meta_data["title"] = "Presentazione Piano di Studi"
                                    elif "tasse" in user_lower or "rata" in user_lower:
                                        meta_data["title"] = "Tasse Universitarie"
                                    else:
                                        meta_data["title"] = "Adempimento Burocratico"

                                anno_match = re.search(r'(?:a\.a\.|anno accademico)\s*(\d{4}[/\-]\d{4})', user_prompt, re.IGNORECASE)
                                if anno_match and anno_match.group(0).lower() not in meta_data["title"].lower():
                                    meta_data["title"] += f" A.A. {anno_match.group(1)}"

                                sub_raw = meta_data.get("subtitle_or_cta", "").strip()
                                if sub_raw and len(sub_raw) > 8 and "la scadenza" not in sub_raw.lower() and "per l'a" not in sub_raw.lower():
                                    meta_data["subtitle_or_cta"] = sub_raw.capitalize()
                                elif "primo anno" in user_lower:
                                    meta_data["subtitle_or_cta"] = "Compilazione online obbligatoria per gli studenti del primo anno"
                                elif "laureandi" in user_lower:
                                    meta_data["subtitle_or_cta"] = "Procedura obbligatoria per tutti gli studenti laureandi"
                                else:
                                    meta_data["subtitle_or_cta"] = "Compilazione online obbligatoria per tutti gli studenti"

                                meta_data["label_1_name"] = "SCADENZA"
                                meta_data["label_1_val"] = extracted_date if extracted_date else meta_data.get("label_1_val", "")

                                if "pagopa" in user_lower:
                                    meta_data["label_2_name"] = "MODALITÀ DI PAGAMENTO"
                                    meta_data["label_2_val"] = "Circuito PagoPA • Portale Studenti"
                                elif "esse3" in user_lower or "portale" in user_lower:
                                    meta_data["label_2_name"] = "PORTALE"
                                    meta_data["label_2_val"] = "Portale Studenti Esse3"
                                else:
                                    meta_data["label_2_name"] = ""
                                    meta_data["label_2_val"] = ""

                            elif is_bando_opportunita:
                                if quoted_title:
                                    meta_data["title"] = quoted_title
                                meta_data["label_1_name"] = "SCADENZA CANDIDATURE"
                                meta_data["label_1_val"] = extracted_date if extracted_date else meta_data.get("label_1_val", "")
                                meta_data["subtitle_or_cta"] = "Presenta la tua candidatura online entro i termini indicati"
                                meta_data["label_2_name"] = ""
                                meta_data["label_2_val"] = ""

                            elif is_intervista:
                                meta_data["title"] = f"Intervista: {interv_name}" if interv_name else "Intervista Esclusiva"
                                if interv_role:
                                    meta_data["subtitle_or_cta"] = interv_role
                                elif meta_data.get("subtitle_or_cta") and len(meta_data.get("subtitle_or_cta")) > 8:
                                    meta_data["subtitle_or_cta"] = meta_data.get("subtitle_or_cta")
                                else:
                                    meta_data["subtitle_or_cta"] = "Professionista nel settore Tech"

                                meta_data["label_1_name"] = "FOCUS DELL'INTERVISTA"
                                meta_data["label_1_val"] = interv_focus if interv_focus else meta_data.get("label_1_val", "")
                                meta_data["label_2_name"] = ""
                                meta_data["label_2_val"] = ""

                            elif is_rubrica_generale:
                                rubrica_name_match = re.search(r"rubrica\s+['“«]([^'”»]+)['”»]", user_prompt, re.IGNORECASE)
                                if rubrica_name_match:
                                    meta_data["title"] = rubrica_name_match.group(1).strip()
                                elif quoted_title:
                                    meta_data["title"] = quoted_title
                                else:
                                    meta_data["title"] = "Rubrica Informatica"

                                tema_match = re.search(r"(?:dedicato al|dedicata al|dedicato alla|su|sul)\s+([^,\.\n]+(?:\s+applicati\s+[^,\.\n]+)?)", user_prompt, re.IGNORECASE)
                                meta_data["subtitle_or_cta"] = tema_match.group(1).strip().capitalize() if tema_match else "Approfondimento scientifico e tecnologico"

                                dettagli_match = re.search(r"(?:il post|l'articolo|il contenuto)\s+((?:presenta|racconta|illustra|mostra|spiega)[^,\.\n]+)", user_prompt, re.IGNORECASE)
                                meta_data["label_1_name"] = "DETTAGLI DEL CONTENUTO"
                                meta_data["label_1_val"] = dettagli_match.group(1).strip().capitalize() if dettagli_match else "Risultati e innovazioni a cura del team di Informatica UNICAM"
                                meta_data["label_2_name"] = ""
                                meta_data["label_2_val"] = ""

                            elif is_evento_seminario:
                                if "hackathon" in user_lower:
                                    meta_data["title"] = f"Hackathon: {quoted_title}" if quoted_title and not quoted_title.lower().startswith("hackathon") else (quoted_title or "Hackathon 2026")
                                elif "seminario" in user_lower:
                                    meta_data["title"] = f"Seminario: {quoted_title}" if quoted_title and not quoted_title.lower().startswith("seminario") else (quoted_title or "Seminario Formativo")
                                elif quoted_title:
                                    meta_data["title"] = quoted_title

                                event_details = []
                                sponsor_match = re.search(r'(sponsorizzato da\s+[^,\.\n]+|in collaborazione con\s+[^,\.\n]+)', user_prompt, re.IGNORECASE)
                                if sponsor_match:
                                    event_details.append(sponsor_match.group(1).strip().capitalize())

                                if extracted_speaker:
                                    label_rel = "Relatrice dell'evento" if "relatrice" in user_lower else "Relatore dell'evento"
                                    event_details.append(f"{label_rel}: {extracted_speaker}")
                                
                                reg_dead_match = re.search(r'(?:iscrizioni chiudono(?: tassativamente)?|iscrizioni entro (?:il)?)\s+(\d{1,2}(?:°|ª)?\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+\d{4})?)', user_prompt, re.IGNORECASE)
                                if reg_dead_match:
                                    event_details.append(f"Iscrizioni entro il {reg_dead_match.group(1).strip()}")
                                elif any(w in user_lower for w in ["ingresso è libero", "ingresso libero", "aperto a tutti", "aperta a tutti"]):
                                    event_details.append("Ingresso libero per tutti gli studenti")
                                elif any(w in user_lower for w in ["obbligatoria", "posti limitati", "numero chiuso"]):
                                    event_details.append("Registrazione obbligatoria • Posti limitati")
                                
                                if event_details:
                                    meta_data["subtitle_or_cta"] = " • ".join(event_details)
                                elif "comunicazione digitale" in user_lower:
                                    meta_data["subtitle_or_cta"] = "Iniziativa per il Corso di Laurea in Informatica per la Comunicazione Digitale"
                                elif "computer science" in user_lower:
                                    meta_data["subtitle_or_cta"] = "Iniziativa per il Corso di Laurea Magistrale in Computer Science"
                                elif not meta_data.get("subtitle_or_cta"):
                                    meta_data["subtitle_or_cta"] = "Iniziativa aperta a tutti gli studenti"

                                meta_data["label_1_name"] = "DATA E ORA"
                                meta_data["label_1_val"] = extracted_date if extracted_date else meta_data.get("label_1_val", "")
                                meta_data["label_2_name"] = "LUOGO"
                                meta_data["label_2_val"] = extracted_luogo if extracted_luogo else meta_data.get("label_2_val", "")

                            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_prompt)
                            meta_data["contact_info"] = f"Per info: {email_match.group(0)}" if email_match else ""

                            rubrics_list = get_asset_files("rubrics")
                            mascots_list = get_asset_files("mascots")
                            user_clean_token = normalize_token(user_prompt)
                            selected_asset_name = ""

                            if is_rubrica_generale or is_intervista:
                                base_rubrics_dir = os.path.join(ASSETS_DIR, "rubrics")
                                if os.path.exists(base_rubrics_dir):
                                    rubric_files = [f for f in os.listdir(base_rubrics_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')]
                                    for r_file in rubric_files:
                                        clean_base = re.sub(r'^\([A-Z]\)_Asset_', '', os.path.splitext(r_file)[0], flags=re.IGNORECASE)
                                        file_token = normalize_token(clean_base)
                                        if file_token and file_token in user_clean_token:
                                            selected_asset_name = r_file
                                            break

                            if not selected_asset_name and mascots_list:
                                valid_mascots = [m for m in mascots_list if m.lower().endswith(('.png', '.jpg', '.jpeg')) and not m.startswith('.')]
                                if valid_mascots:
                                    selected_asset_name = random.choice(valid_mascots)

                            meta_data["selected_asset"] = selected_asset_name
                            button_txt = extracted_url if extracted_url else meta_data.get("button_text", "").strip()

                            system_prompt = build_system_prompt()
                            final_user_prompt = assemble_final_prompt(
                                user_query=user_prompt,
                                retrieved_context=retrieved_context_str,
                                few_shot_context=few_shot_context_str,
                                channel_name=selected_channel,
                                channel_constraints=format_details
                            )
                            
                            raw_post = generate_social_post(
                                system_prompt=system_prompt, 
                                user_prompt=final_user_prompt
                            )
                            post_generato = clean_generated_post(raw_post)

                            course_type = "Informatica"
                            if any(w in user_lower for w in ["comunicazione digitale", " icd", "(icd)", "l-31 icd"]):
                                course_type = "Informatica per la comunicazione digitale"
                            elif any(w in user_lower for w in ["computer science", " cs", "(cs)", "magistrale", "laurea magistrale", "master", "lm-18", "msc"]):
                                course_type = "Computer Science"

                            graphic_data = {
                                "title": meta_data.get("title", ""),
                                "subtitle_or_cta": meta_data.get("subtitle_or_cta", ""),
                                "button_text": button_txt,
                                "label_1_name": meta_data.get("label_1_name", ""),
                                "label_1_val": meta_data.get("label_1_val", ""),
                                "label_2_name": meta_data.get("label_2_name", ""),
                                "label_2_val": meta_data.get("label_2_val", ""),
                                "contact_info": meta_data.get("contact_info", ""),
                                "selected_asset": selected_asset_name,
                                "course_type": course_type
                            }

                            actual_logo_path = ""
                            logos_avail = get_asset_files("logos")
                            if logos_avail:
                                actual_logo_path = os.path.join(ASSETS_DIR, "logos", logos_avail[0])

                            actual_asset_path = ""
                            if selected_asset_name:
                                for sub in ["rubrics", "mascots"]:
                                    test_p = os.path.join(ASSETS_DIR, sub, selected_asset_name)
                                    if os.path.exists(test_p):
                                        actual_asset_path = test_p
                                        break

                            # 1. GENERAZIONE SVG PRIMA DI QUALSIASI CONVERSIONE
                            svg_code = generate_brand_svg(
                                text_content=graphic_data,
                                channel_name=selected_channel.lower(),
                                brand_config=brand_config,
                                canvas_size=(canvas_width, canvas_height),
                                logo_path=actual_logo_path,
                                asset_path=actual_asset_path,
                                visual_guidelines_context=visual_guidelines_str,
                                use_ai_design=True
                            )
                            output_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "generated", "ui_output_post.svg")
                            os.makedirs(os.path.dirname(output_svg_path), exist_ok=True)
                            with open(output_svg_path, "w", encoding="utf-8") as f_svg:
                                f_svg.write(svg_code)

                            # 2. CONVERSIONE DIRETTA SVG -> JPEG AD ALTA RISOLUZIONE TRAMITE CAIROSVG
                            output_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "generated", "ui_output_post.png")
                            cairosvg.svg2png(
                                bytestring=svg_code.encode("utf-8"),
                                write_to=output_img_path,
                                output_width=canvas_width,
                                output_height=canvas_height
                            )

                            st.session_state["generated_output"] = {
                                "post_text": post_generato,
                                "img_path": output_img_path,
                                "svg_path": output_svg_path,
                                "svg_code": svg_code,
                                "format_name": selected_format,
                                "channel_name": selected_channel,
                                "canvas_size": (canvas_width, canvas_height),
                                "char_count": len(post_generato),
                                "max_allowed": format_details.get("max_characters", 2200),
                                "visual_source": visual_asset_source,
                                "visual_guidelines_str": visual_guidelines_str,
                                "graphic_data": graphic_data,
                                "actual_logo_path": actual_logo_path,
                                "actual_asset_path": actual_asset_path
                            }
                            
                            st.session_state["chat_history"] = [
                                {"role": "user", "content": user_prompt},
                                {"role": "assistant", "content": "Ho generato il post e la cartolina grafica secondo le tue indicazioni. Cosa vorresti modificare o rifinire?"}
                            ]

                    except Exception as e:
                        st.error(f"Error during execution: {str(e)}")

        # =========================================================
        # SEZIONE OUTPUT & CHAT INTERATTIVA DI MODIFICA
        # =========================================================
        if st.session_state.get("generated_output"):
            out_data = st.session_state["generated_output"]
            
            st.success("✨ Multimodal post ready!")
            
            # Griglia a due colonne: 55% Testo a sinistra, 45% Grafica a destra
            col_output_text, col_output_visual = st.columns([5.5, 4.5], gap="large")
            
            # --- COLONNA SINISTRA: TESTO E METRICHE ---
            with col_output_text:
                tab_preview, tab_copy = st.tabs(["👁️ Copy Preview", "📋 Quick Copy"])
                with tab_preview:
                    st.markdown(out_data["post_text"])
                with tab_copy:
                    st.text_area("Copy clean text from here:", value=out_data["post_text"], height=320)
                    
                st.caption(f"📏 **Geometric Analysis:** `{out_data['char_count']}` characters (Format Limit: `{out_data['max_allowed']}`).")
                
            # --- COLONNA DESTRA: GRAFICA RIDIMENSIONATA E DOWNLOAD ---
            with col_output_visual:
                if out_data.get("visual_source") and os.path.exists(out_data["visual_source"]):
                    st.markdown("##### 🔍 Historical Visual Reference:")
                    st.image(out_data["visual_source"], use_container_width=True)
                    st.divider()

                st.markdown("##### 🎨 Generated Graphic Card")
                
                # Visualizzazione dell'immagine limitata alla larghezza della colonna destra
                if os.path.exists(out_data.get("img_path", "")):
                    st.image(
                        out_data["img_path"], 
                        use_container_width=True, 
                        caption=f"Layout rendered for {out_data['format_name']}"
                    )

                # Pulsanti di Download allineati sotto la card
                c_down1, c_down2 = st.columns(2)
                with c_down1:
                    if os.path.exists(out_data.get("img_path", "")):
                        with open(out_data["img_path"], "rb") as file:
                            st.download_button(
                                label="💾 Download PNG",
                                data=file,
                                file_name=f"brand_post_{out_data['format_name'].replace(' ', '_').lower()}.png",
                                mime="image/png",
                                use_container_width=True,
                                type="secondary"
                            )
                with c_down2:
                    if os.path.exists(out_data.get("svg_path", "")):
                        with open(out_data["svg_path"], "r", encoding="utf-8") as svg_file:
                            st.download_button(
                                label="📐 Download Vector SVG",
                                data=svg_file.read(),
                                file_name=f"brand_post_{out_data['format_name'].replace(' ', '_').lower()}.svg",
                                mime="image/svg+xml",
                                use_container_width=True,
                                type="primary"
                            )

            st.divider()

            # --- SEZIONE CHAT ITERATIVA ---
            st.markdown("### 💬 Refine Copy & Graphic Interactively")
            st.caption("Chiedi all'AI di modificare il testo, aggiornare i dati della grafica (orari, relatori, titoli), cambiare la tonalità o la palette cromatica senza ricominciare da zero.")

            # Visualizzazione storico chat
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            chat_instruction = st.chat_input("Es. 'Rendi il testo più coinvolgente per le storie e cambia l'orario alle 11:30' oppure 'Imposta lo sfondo per la laurea magistrale'")

            if chat_instruction:
                st.session_state["chat_history"].append({"role": "user", "content": chat_instruction})
                with st.chat_message("user"):
                    st.markdown(chat_instruction)

                with st.chat_message("assistant"):
                    with st.spinner("Aggiornamento del post e rigenerazione del layout in corso..."):
                        try:
                            current_post = out_data["post_text"]
                            current_graphic = out_data["graphic_data"]

                            # 1. Recupero catalogo asset aggiornato
                            asset_catalog = get_asset_descriptions()
                            catalog_str = json.dumps(asset_catalog, indent=2, ensure_ascii=False)

                            refinement_prompt = f"""
Sei un motore di modifica ed editing JSON per il Brand-RAG Studio di UNICAM.
Il tuo compito è aggiornare i campi del layout grafico o il post social ESCLUSIVAMENTE secondo la richiesta dell'utente.

STRUTTURA ATTUALE DEI CAMPI:
- "post_text": {json.dumps(current_post, ensure_ascii=False)}
- "title": {json.dumps(current_graphic.get("title", ""), ensure_ascii=False)}
- "subtitle_or_cta": {json.dumps(current_graphic.get("subtitle_or_cta", ""), ensure_ascii=False)}
- "label_1_name": {json.dumps(current_graphic.get("label_1_name", ""), ensure_ascii=False)}
- "label_1_val": {json.dumps(current_graphic.get("label_1_val", ""), ensure_ascii=False)}
- "label_2_name": {json.dumps(current_graphic.get("label_2_name", ""), ensure_ascii=False)}
- "label_2_val": {json.dumps(current_graphic.get("label_2_val", ""), ensure_ascii=False)}
- "button_text": {json.dumps(current_graphic.get("button_text", ""), ensure_ascii=False)}
- "selected_asset": {json.dumps(current_graphic.get("selected_asset", ""), ensure_ascii=False)}
- "course_type": {json.dumps(current_graphic.get("course_type", "Informatica"), ensure_ascii=False)}

CATALOGO ASSET DISPONIBILI:
{catalog_str}

RICHIESTA UTENTE:
"{chat_instruction}"

REGOLE FERREE:
1. Se l'utente chiede di modificare il "Focus dell'intervista", l'argomento trattato o il valore sotto l'etichetta 1, DEVI aggiornare "label_1_val". NON aggiungere quel testo dentro "subtitle_or_cta".
2. Se l'utente vuole sostituire un valore di default o generico (es. "Carriera e innovazione tecnologica"), sovrascrivi integralmente "label_1_val" con il nuovo valore richiesto.
3. Se l'utente chiede di modificare il sottotitolo o le note, modifica "subtitle_or_cta".
4. Se l'utente chiede di modificare date/orari, modifica "label_1_val" (se label_1_name è DATA E ORA).
5. Se l'utente chiede di cambiare asset/badge/rubrica, seleziona il nome file esatto dal catalogo in "selected_asset".
6. Restituisci ESCLUSIVAMENTE un blocco JSON valido.

Rispondi con un SINGOLO oggetto JSON valido:
{{
  "new_post_text": "testo aggiornato del post",
  "updated_graphic_data": {{
    "title": "...",
    "subtitle_or_cta": "...",
    "button_text": "{current_graphic.get('button_text', '')}",
    "label_1_name": "{current_graphic.get('label_1_name', '')}",
    "label_1_val": "...",
    "label_2_name": "{current_graphic.get('label_2_name', '')}",
    "label_2_val": "{current_graphic.get('label_2_val', '')}",
    "contact_info": "{current_graphic.get('contact_info', '')}",
    "selected_asset": "{current_graphic.get('selected_asset', '')}",
    "course_type": "{current_graphic.get('course_type', 'Informatica')}"
  }},
  "assistant_message": "Descrizione sintetica delle modifiche effettuate."
}}
"""
                            raw_reply = generate_social_post(
                                system_prompt="Rispondi ESCLUSIVAMENTE con un JSON valido ben formato. Non aggiungere commenti discorsivi.",
                                user_prompt=refinement_prompt
                            )

                            parsed_reply = None
                            try:
                                json_match = re.search(r'\{.*\}', raw_reply, re.DOTALL)
                                if json_match:
                                    clean_json = re.sub(r'[\r\n\t]+', ' ', json_match.group(0).strip())
                                    parsed_reply = json.loads(clean_json)
                            except Exception:
                                parsed_reply = None

                            if parsed_reply and isinstance(parsed_reply, dict):
                                new_post = clean_generated_post(parsed_reply.get("new_post_text", current_post))
                                new_graphic = parsed_reply.get("updated_graphic_data", current_graphic.copy())
                                asst_msg = parsed_reply.get("assistant_message", "Modifiche applicate con successo!")
                            else:
                                new_graphic = current_graphic.copy()
                                new_post = current_post
                                asst_msg = "Modifica applicata."

                            focus_sub_match = re.search(r'(?:sotto\s+a\s+focus|al\s+posto\s+di\s+["\']?carriera|focus dell\'intervista[:\s]+)\s*["\']?([^"\'\n\.]+)["\']?', chat_instruction, re.IGNORECASE)
                            if focus_sub_match:
                                new_graphic["label_1_name"] = "FOCUS DELL'INTERVISTA"
                                new_graphic["label_1_val"] = focus_sub_match.group(1).strip().capitalize()

                            chat_lower = normalize_token(chat_instruction)
                            for sub in ["rubrics", "mascots"]:
                                folder = os.path.join(ASSETS_DIR, sub)
                                if os.path.exists(folder):
                                    for f in os.listdir(folder):
                                        if not f.startswith('.'):
                                            token_name = normalize_token(f)
                                            if token_name and token_name in chat_lower:
                                                new_graphic["selected_asset"] = f
                                                break

                            new_asset_name = new_graphic.get("selected_asset", "")
                            updated_asset_path = ""
                            if new_asset_name:
                                for sub in ["rubrics", "mascots"]:
                                    test_p = os.path.join(ASSETS_DIR, sub, new_asset_name)
                                    if os.path.exists(test_p):
                                        updated_asset_path = test_p
                                        break

                            brand_cfg = load_brand_configuration()
                            c_w, c_h = out_data["canvas_size"]

                            # 1. RIGENERAZIONE SVG PRIMA
                            svg_upd = generate_brand_svg(
                                text_content=new_graphic,
                                channel_name=out_data["channel_name"].lower(),
                                brand_config=brand_cfg,
                                canvas_size=(c_w, c_h),
                                logo_path=out_data.get("actual_logo_path"),
                                asset_path=updated_asset_path,
                                visual_guidelines_context=out_data.get("visual_guidelines_str", ""),
                                use_ai_design=True
                            )
                            with open(out_data["svg_path"], "w", encoding="utf-8") as f_svg:
                                f_svg.write(svg_upd)

                            # 2. CONVERSIONE DIRETTA IN JPEG/PNG
                            cairosvg.svg2png(
                            bytestring=svg_upd.encode("utf-8"),
                            write_to=out_data["img_path"],
                            output_width=c_w,
                            output_height=c_h
                        )

                            # 3. Aggiornamento dello stato di sessione
                            st.session_state["generated_output"]["post_text"] = new_post
                            st.session_state["generated_output"]["char_count"] = len(new_post)
                            st.session_state["generated_output"]["graphic_data"] = new_graphic
                            st.session_state["generated_output"]["actual_asset_path"] = updated_asset_path
                            st.session_state["generated_output"]["svg_code"] = svg_upd

                            st.session_state["chat_history"].append({"role": "assistant", "content": asst_msg})
                            st.rerun()

                        except Exception as e:
                            st.error(f"Errore durante l'aggiornamento: {str(e)}")


# ==========================================
# PAGINA 2: BRAND WORKSPACE
# ==========================================
elif st.session_state["current_page"] == "onboarding":
    st.title("🚀 Brand Workspace")
    st.write("Manage all your strategic brand knowledge, visual identity assets, and design parameters in one unified workspace.")
    st.divider()

    json_path = os.path.join(JSON_DIR, "brand_config.json")
    saved_colors = []
    saved_names = []
    has_saved_palette = False
    
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cached_json = json.load(f)
                primary_colors_cached = cached_json.get("visual_identity", {}).get("color_palette", {}).get("primary_colors", [])
                if primary_colors_cached:
                    saved_colors = [c.get("hex", "#FFFFFF") for c in primary_colors_cached]
                    saved_names = [c.get("name", f"Color {i+1}") for i, c in enumerate(primary_colors_cached)]
                    has_saved_palette = True
        except Exception:
            pass

    if "edit_states" not in st.session_state:
        st.session_state["edit_states"] = {}

    def toggle_edit(slot_key):
        st.session_state["edit_states"][slot_key] = not st.session_state["edit_states"].get(slot_key, False)

    def render_active_files_display(files, folder_category, is_image_slot=False, is_asset_folder=False):
        if not files:
            return
        st.success(f"📄 Active: {len(files)} file(s)")
        
        base_target_dir = os.path.join(ASSETS_DIR, folder_category) if is_asset_folder else os.path.join(UPLOAD_DIR, folder_category)
        
        if is_image_slot:
            cols = st.columns(min(len(files), 3))
            for idx, fn in enumerate(files):
                with cols[idx % 3]:
                    img_p = os.path.join(base_target_dir, fn)
                    img_valid = False
                    if os.path.exists(img_p):
                        try:
                            with Image.open(img_p) as test_img:
                                test_img.verify()
                            img_valid = True
                        except Exception:
                            img_valid = False
                            
                    if img_valid:
                        st.image(img_p, caption=fn, use_container_width=True)
                    else:
                        st.caption(f"▪️ `{fn}`")
                        
                    if st.button(f"🗑️ Delete", key=f"del_img_{folder_category}_{fn}_{idx}"):
                        try:
                            if os.path.exists(img_p):
                                os.remove(img_p)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            for idx, fn in enumerate(files):
                c_txt, c_del = st.columns([4, 1.2])
                with c_txt:
                    st.caption(f"▪️ `{fn}`")
                with c_del:
                    file_p = os.path.join(base_target_dir, fn)
                    if st.button(f"🗑️", key=f"del_doc_{folder_category}_{fn}_{idx}"):
                        try:
                            if os.path.exists(file_p):
                                os.remove(file_p)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.markdown("### 📦 Unified Brand Knowledge & Assets Repository")
    st.caption("Upload or manage individual files. Active saved assets are displayed directly within their respective slots.")

    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("##### 👥 Target Personas")
        existing_personas = get_doc_files("1_personas")
        if existing_personas:
            render_active_files_display(existing_personas, "1_personas")
            if st.button("✏️ Add Files", key="btn_edit_personas"): toggle_edit("personas")
        else:
            st.caption("❌ No file uploaded yet")
            st.session_state["edit_states"]["personas"] = True

        personas_files = None
        if st.session_state["edit_states"].get("personas", False):
            personas_files = st.file_uploader("Upload Personas (PDF)", type=["pdf"], accept_multiple_files=True, key="up_personas")

    with c2:
        st.markdown("##### 💬 Social Media Voice")
        existing_voice = get_doc_files("2_social_voice")
        if existing_voice:
            render_active_files_display(existing_voice, "2_social_voice")
            if st.button("✏️ Add Files", key="btn_edit_voice"): toggle_edit("voice")
        else:
            st.caption("❌ No file uploaded yet")
            st.session_state["edit_states"]["voice"] = True

        social_voice_files = None
        if st.session_state["edit_states"].get("voice", False):
            social_voice_files = st.file_uploader("Upload Social Voice (PDF)", type=["pdf"], accept_multiple_files=True, key="up_voice")

    with c3:
        st.markdown("##### 🎭 Tone of Voice")
        existing_tone = get_doc_files("3_tone_of_voice")
        if existing_tone:
            render_active_files_display(existing_tone, "3_tone_of_voice")
            if st.button("✏️ Add Files", key="btn_edit_tone"): toggle_edit("tone")
        else:
            st.caption("❌ No file uploaded yet")
            st.session_state["edit_states"]["tone"] = True

        tone_files = None
        if st.session_state["edit_states"].get("tone", False):
            tone_files = st.file_uploader("Upload Tone of Voice (PDF)", type=["pdf"], accept_multiple_files=True, key="up_tone")

    st.divider()

    c4, c5, c6 = st.columns(3)

    with c4:
        st.markdown("##### 📢 Funnel Stages")
        existing_funnel = get_doc_files("4_funnel_stages")
        if existing_funnel:
            render_active_files_display(existing_funnel, "4_funnel_stages")
            if st.button("✏️ Add Files", key="btn_edit_funnel"): toggle_edit("funnel")
        else:
            st.caption("❌ No file uploaded yet")
            st.session_state["edit_states"]["funnel"] = True

        funnel_files = None
        if st.session_state["edit_states"].get("funnel", False):
            funnel_files = st.file_uploader("Upload Funnel Stages (PDF)", type=["pdf"], accept_multiple_files=True, key="up_funnel")

    with c5:
        st.markdown("##### 📐 Editorial Rubrics")
        existing_rubrics = get_doc_files("5_rubrics")
        if existing_rubrics:
            render_active_files_display(existing_rubrics, "5_rubrics")
            if st.button("✏️ Add Files", key="btn_edit_rubrics"): toggle_edit("rubrics")
        else:
            st.caption("❌ No file uploaded yet")
            st.session_state["edit_states"]["rubrics"] = True

        rubrics_files = None
        if st.session_state["edit_states"].get("rubrics", False):
            rubrics_files = st.file_uploader("Upload Editorial Rubrics (PDF)", type=["pdf"], accept_multiple_files=True, key="up_rubrics")

    with c6:
        st.markdown("##### 📝 Examples of Copy")
        existing_copy_ex = get_doc_files("6_esempi_ispirazione")
        copy_doc_files = [f for f in existing_copy_ex if not f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if copy_doc_files:
            render_active_files_display(copy_doc_files, "6_esempi_ispirazione")
            if st.button("✏️ Add Files", key="btn_edit_copy_ex"): toggle_edit("copy_ex")
        else:
            st.caption("❌ No copy example uploaded yet")
            st.session_state["edit_states"]["copy_ex"] = True

        few_shot_mass_files = None
        if st.session_state["edit_states"].get("copy_ex", False):
            few_shot_mass_files = st.file_uploader("Upload Copy Examples (TXT/JSON/PDF)", type=["txt", "json", "pdf"], accept_multiple_files=True, key="up_copy_ex")

    st.divider()

    c7, c8 = st.columns(2)

    with c7:
        st.markdown("##### 🖼️ Graphics Examples")
        existing_gfx = get_doc_files("6_esempi_ispirazione")
        gfx_img_files = [f for f in existing_gfx if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if gfx_img_files:
            render_active_files_display(gfx_img_files, "6_esempi_ispirazione", is_image_slot=True)
            if st.button("✏️ Add Graphics", key="btn_edit_gfx_ex"): toggle_edit("gfx_ex")
        else:
            st.caption("❌ No graphic example uploaded yet")
            st.session_state["edit_states"]["gfx_ex"] = True

        few_shot_image_files = None
        if st.session_state["edit_states"].get("gfx_ex", False):
            few_shot_image_files = st.file_uploader("Upload Graphic Examples (PNG/JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="up_gfx_ex")

    with c8:
        st.markdown("##### 🎨 Brand Color Palette")
        if has_saved_palette and not st.session_state["edit_states"].get("palette", False):
            st.success(f"🎨 Active Palette ({len(saved_colors)} colors):")
            cols_p = st.columns(min(len(saved_colors), 5))
            for idx, hex_val in enumerate(saved_colors):
                with cols_p[idx % 5]:
                    st.color_picker(saved_names[idx], value=hex_val, disabled=True, key=f"preview_p_{idx}")
                    if st.button("🗑️", key=f"del_color_{idx}"):
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                            colors_list = cfg.get("visual_identity", {}).get("color_palette", {}).get("primary_colors", [])
                            if idx < len(colors_list):
                                colors_list.pop(idx)
                                cfg["visual_identity"]["color_palette"]["primary_colors"] = colors_list
                                with open(json_path, "w", encoding="utf-8") as f:
                                    json.dump(cfg, f, indent=2)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error removing color: {e}")
            if st.button("✏️ Edit Palette", key="btn_edit_palette"): toggle_edit("palette")
        else:
            if not has_saved_palette:
                st.info("No color palette saved yet.")
            
            show_palette_editor = st.checkbox("➕ Configure / Edit Color Palette", value=not has_saved_palette, key="chk_palette")
            
            colori_scelti = []
            if show_palette_editor:
                num_colori = st.number_input("Number of colors (max 10):", min_value=1, max_value=10, value=len(saved_colors) if saved_colors else 4, step=1)
                cols_pick = st.columns(5)
                for i in range(num_colori):
                    col_idx = i % 5
                    val_hex = saved_colors[i] if i < len(saved_colors) else "#FFFFFF"
                    val_name = saved_names[i] if i < len(saved_names) else f"Color {i+1}"
                    with cols_pick[col_idx]:
                        colore_hex = st.color_picker(f"Color #{i+1}", value=val_hex, key=f"palette_picker_{i}")
                        nome_colore = st.text_input(f"Name #{i+1}", value=val_name, key=f"palette_name_{i}")
                        colori_scelti.append({"name": nome_colore, "hex": colore_hex, "semantic_meaning": "Custom color"})

    st.divider()

    c9, c10, c11, c12 = st.columns(4)

    with c9:
        st.markdown("##### 🔤 Fonts")
        fonts_in_mem = get_asset_files("fonts")
        if fonts_in_mem:
            render_active_files_display(fonts_in_mem, "fonts", is_asset_folder=True)
            if st.button("✏️ Add Fonts", key="btn_edit_fonts"): toggle_edit("fonts")
        else:
            st.caption("❌ No .ttf font uploaded")
            st.session_state["edit_states"]["fonts"] = True

        font_files = None
        if st.session_state["edit_states"].get("fonts", False):
            font_files = st.file_uploader("Upload Fonts (.ttf)", type=["ttf"], accept_multiple_files=True, key="up_fonts")

    with c10:
        st.markdown("##### 🖼️ Brand Logo")
        logos_in_mem = get_asset_files("logos")
        if logos_in_mem:
            render_active_files_display(logos_in_mem, "logos", is_image_slot=True, is_asset_folder=True)
            if st.button("✏️ Add Logos", key="btn_edit_logos"): toggle_edit("logos")
        else:
            st.caption("❌ No logo uploaded")
            st.session_state["edit_states"]["logos"] = True

        logo_files = None
        if st.session_state["edit_states"].get("logos", False):
            logo_files = st.file_uploader("Upload Logos (.png)", type=["png"], accept_multiple_files=True, key="up_logos")

    with c11:
        st.markdown("##### 🦊 Mascots")
        mascots_in_mem = get_asset_files("mascots")
        if mascots_in_mem:
            render_active_files_display(mascots_in_mem, "mascots", is_image_slot=True, is_asset_folder=True)
            if st.button("✏️ Add Mascots", key="btn_edit_mascots"): toggle_edit("mascots")
        else:
            st.caption("❌ No mascot uploaded")
            st.session_state["edit_states"]["mascots"] = True

        mascot_files = None
        if st.session_state["edit_states"].get("mascots", False):
            mascot_files = st.file_uploader("Upload Mascots (.png)", type=["png"], accept_multiple_files=True, key="up_mascots")

    with c12:
        st.markdown("##### 📐 Assets (Rubric Symbols)")
        rubrics_in_mem = get_asset_files("rubrics")
        if rubrics_in_mem:
            render_active_files_display(rubrics_in_mem, "rubrics", is_image_slot=True, is_asset_folder=True)
            if st.button("✏️ Add Assets", key="btn_edit_rubric_assets"): toggle_edit("rubric_assets")
        else:
            st.caption("❌ No rubric symbol uploaded")
            st.session_state["edit_states"]["rubric_assets"] = True

        rubric_files = None
        if st.session_state["edit_states"].get("rubric_assets", False):
            rubric_files = st.file_uploader("Upload Assets (.png)", type=["png"], accept_multiple_files=True, key="up_rubric_assets")

    st.divider()

    btn_ingest = st.button("💾 Save & Index Brand Knowledge Base", use_container_width=True, type="primary")
    
    if btn_ingest:
        with st.spinner("Saving physical assets and processing vector indexing..."):
            try:
                for slot_folder in ["1_personas", "2_social_voice", "3_tone_of_voice", "4_funnel_stages", "5_rubrics", "6_esempi_ispirazione"]:
                    os.makedirs(os.path.join(UPLOAD_DIR, slot_folder), exist_ok=True)
                    
                for asset_folder in ["fonts", "logos", "mascots", "rubrics"]:
                    os.makedirs(os.path.join(ASSETS_DIR, asset_folder), exist_ok=True)
                os.makedirs(JSON_DIR, exist_ok=True)
                
                multi_save_map = {
                    "1_personas": personas_files,
                    "2_social_voice": social_voice_files,
                    "3_tone_of_voice": tone_files,
                    "4_funnel_stages": funnel_files,
                    "5_rubrics": rubrics_files,
                    "6_esempi_ispirazione": few_shot_mass_files
                }
                
                for folder_name, file_list in multi_save_map.items():
                    if file_list:
                        for f_data in file_list:
                            t_path = os.path.join(UPLOAD_DIR, folder_name, f_data.name)
                            with open(t_path, "wb") as f:
                                f.write(f_data.getbuffer())

                if 'few_shot_image_files' in locals() and few_shot_image_files:
                    t_gfx_folder = os.path.join(UPLOAD_DIR, "6_esempi_ispirazione")
                    for single_img in few_shot_image_files:
                        t_img_path = os.path.join(t_gfx_folder, single_img.name)
                        with open(t_img_path, "wb") as f:
                            f.write(single_img.getbuffer())
                            
                        txt_desc_path = os.path.splitext(t_img_path)[0] + ".txt"
                        with open(txt_desc_path, "w", encoding="utf-8") as f:
                            f.write(f"Layout grafico istituzionale basato sull'immagine di successo {single_img.name}.")

                if font_files:
                    for f_file in font_files:
                        with open(os.path.join(ASSETS_DIR, "fonts", f_file.name), "wb") as f:
                            f.write(f_file.getbuffer())
                
                if logo_files:
                    for l_file in logo_files:
                        with open(os.path.join(ASSETS_DIR, "logos", l_file.name), "wb") as f:
                            f.write(l_file.getbuffer())

                if mascot_files:
                    for m_file in mascot_files:
                        with open(os.path.join(ASSETS_DIR, "mascots", m_file.name), "wb") as f:
                            f.write(m_file.getbuffer())
                            
                if rubric_files:
                    for r_file in rubric_files:
                        with open(os.path.join(ASSETS_DIR, "rubrics", r_file.name), "wb") as f:
                            f.write(r_file.getbuffer())

                current_logos = get_asset_files("logos")
                primary_logo_name = current_logos[0] if current_logos else "logo_unicamente.png"

                final_colors = colori_scelti if 'colori_scelti' in locals() and colori_scelti else [
                    {"name": saved_names[i], "hex": saved_colors[i], "semantic_meaning": "Custom color"}
                    for i in range(len(saved_colors))
                ] if saved_colors else [
                    {"name": "Default Blue", "hex": "#173983", "semantic_meaning": "Primary"}
                ]

                generated_config = {
                    "brand_id": "unicamente_informatica",
                    "brand_name": "University of Camerino - Computer Science Division",
                    "meta": {"project_context": "unicamente_Informatica brand", "target_channels": ["instagram", "linkedin"]},
                    "visual_identity": {
                        "color_palette": {
                            "primary_colors": final_colors,
                            "neutral_colors": [
                                {"name": "Unicam Black", "hex": "#131313", "semantic_meaning": "Primary typography"},
                                {"name": "Unicam White", "hex": "#FFFFF0", "semantic_meaning": "Canvas backgrounds"}
                            ]
                        },
                        "typography": {
                            "heading_font": {"family": "Sora", "allowed_weights": ["Bold"], "file_name": "Sora-Bold copia.ttf"},
                            "body_font": {"family": "Sora", "allowed_weights": ["Regular"], "file_name": "Sora-Regular copia.ttf"},
                            "fallback_font": "Helvetica"
                        }
                    },
                    "brand_assets": {
                        "core_branding": {
                            "main_logo": {"file_name": primary_logo_name, "path": f"data/assets/logos/{primary_logo_name}", "type": "image/png"}
                        }
                    },
                    "channel_templates": {
                        "instagram": {
                            "handle": "@unicamente_informatica",
                            "formats": {
                                "vertical": {"aspect_ratio": "4:5", "dimensions": "1080x1350", "max_characters": 2200},
                                "square": {"aspect_ratio": "1:1", "dimensions": "1080x1080", "max_characters": 2200},
                                "horizontal": {"aspect_ratio": "1.91:1", "dimensions": "1080x566", "max_characters": 2200},
                                "reels_and_stories": {"aspect_ratio": "9:16", "dimensions": "1080x1920", "max_characters": 2200}
                            }
                        },
                        "linkedin": {
                            "company_page_url": "https://www.linkedin.com/company/informatica-unicam",
                            "formats": {
                                "vertical": {"aspect_ratio": "4:5", "dimensions": "1080x1350", "max_characters": 3000},
                                "square": {"aspect_ratio": "1:1", "dimensions": "1080x1080", "max_characters": 3000},
                                "horizontal": {"aspect_ratio": "1.91:1", "dimensions": "1200x627", "max_characters": 3000}
                            }
                        }
                    }
                }
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(generated_config, f, indent=2)
                    
                st.write("⚙️ Configuration JSON aligned successfully.")
                
                run_semantic_ingestion()
                st.session_state["vector_db"] = initialize_vector_store()
                
                st.success("✅ Brand Knowledge Base saved and indexed successfully!")
                st.session_state["edit_states"] = {}
                st.rerun()
                
            except Exception as e:
                st.error(f"Critical error during Brand onboarding: {str(e)}")