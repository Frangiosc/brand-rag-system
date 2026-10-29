import os
import json
from datetime import datetime, date

CALENDAR_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "structured", "editorial_calendar.json")

# Festività italiane fisse e mobili principali
def get_italian_holidays(year: int) -> dict:
    holidays = {
        f"{year}-01-01": "Capodanno",
        f"{year}-01-06": "Epifania",
        f"{year}-04-25": "Festa della Liberazione",
        f"{year}-05-01": "Festa dei Lavoratori",
        f"{year}-06-02": "Festa della Repubblica",
        f"{year}-08-15": "Ferragosto",
        f"{year}-11-01": "Ognissanti",
        f"{year}-12-08": "Immacolata Concezione",
        f"{year}-12-25": "Natale",
        f"{year}-12-26": "Santo Stefano",
    }
    # Calcolo Pasqua e Pasquetta (Algoritmo di Butcher / Meeus)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    pasqua = date(year, month, day)
    from datetime import timedelta
    pasquetta = pasqua + timedelta(days=1)
    
    holidays[pasqua.strftime("%Y-%m-%d")] = "Pasqua"
    holidays[pasquetta.strftime("%Y-%m-%d")] = "Lunedì dell'Angelo"
    return holidays

def load_calendar_data() -> dict:
    if os.path.exists(CALENDAR_DB_PATH):
        try:
            with open(CALENDAR_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"posts": {}, "month_notes": {}}

def save_calendar_data(data: dict):
    os.makedirs(os.path.dirname(CALENDAR_DB_PATH), exist_ok=True)
    with open(CALENDAR_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_post_to_date(date_str: str, post_info: dict):
    data = load_calendar_data()
    if date_str not in data["posts"]:
        data["posts"][date_str] = []
    data["posts"][date_str].append(post_info)
    save_calendar_data(data)

def save_month_note(year_month: str, note_text: str):
    data = load_calendar_data()
    data["month_notes"][year_month] = note_text
    save_calendar_data(data)

def get_month_note(year_month: str) -> str:
    data = load_calendar_data()
    return data.get("month_notes", {}).get(year_month, "")

def get_posts_for_date(date_str: str) -> list:
    data = load_calendar_data()
    return data.get("posts", {}).get(date_str, [])

def delete_post_from_date(date_str: str, post_index: int):
    """Rimuove un post programmato in base al suo indice nella lista."""
    data = load_calendar_data()
    if date_str in data.get("posts", {}):
        posts = data["posts"][date_str]
        if 0 <= post_index < len(posts):
            posts.pop(post_index)
            # Se la lista per quel giorno si svuota, puliamo la chiave
            if not posts:
                del data["posts"][date_str]
            save_calendar_data(data)