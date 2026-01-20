import streamlit as st
from bs4 import BeautifulSoup
from openai import OpenAI
#from dotenv import load_dotenv
import os
import re
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.service import Service as ChromeService
import pathlib


with open('assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
st.set_page_config(
    page_title="Angebotsgenerator",  
    page_icon="🧠",
    layout='wide'
)


if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "product_data" not in st.session_state:
    st.session_state["product_data"] = ""

if "target_language" not in st.session_state:
    st.session_state['target_language'] = "Deutsch"  

if "translation" not in st.session_state:
    st.session_state["translation"] = ""

if "generated_variants" not in st.session_state:
    st.session_state["generated_variants"] = ""

if "3_prompts" not in st.session_state:
    st.session_state["3_prompts"] = ""

if "sk_google" not in st.session_state:
    st.session_state["sk_google"] = ""

# --- FUNKCJE ---

def describe_image(image_file):
    try:
        import base64
        image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        response = st.session_state.openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": "Du bist ein E-Commerce-Experte. Du erstellst professionelle Produktbeschreibungen."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analysiere das Bild und erstelle eine professionelle und präzise Produktbeschreibung. Beschreibe nur das, was du siehst, erfinde nichts. Maximal 200 Wörter. Antwort auf Deutsch."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Fehler bei der Bildanalyse: {e}")
        return None

# def clean_text(raw_html):
#     clean = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ", strip=True)
#     clean = re.sub(r'\s+', ' ', clean)
#     return (clean[:10000].rsplit(" ", 1)[0] + "...") if len(clean) > 10000 else clean

# def scrape_leviatan(url: str) -> dict:
#     opts = webdriver.ChromeOptions()
#     opts.add_argument("--headless=new")
#     opts.add_argument("--no-sandbox")
#     opts.add_argument("--disable-dev-shm-usage")
#     opts.add_argument("--disable-gpu")
#     opts.add_argument("--window-size=1920,1080")
#     # Zmiana języka przeglądarki na niemiecki
#     opts.add_argument("--lang=de-DE,de")
#     opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
#     opts.add_experimental_option("excludeSwitches", ["enable-automation"])
#     opts.add_experimental_option("useAutomationExtension", False)

#     if os.getenv("CHROME_BIN") or os.path.exists("/usr/bin/chromium"):
#         opts.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
#         service = ChromeService(executable_path=os.getenv("CHROMEDRIVER", "/usr/bin/chromedriver"))
#         driver = webdriver.Chrome(service=service, options=opts)
#     else:
#         driver = webdriver.Chrome(options=opts)

#     try:
#         driver.set_page_load_timeout(25)
#         driver.get(url)

#         WebDriverWait(driver, 20).until(
#             EC.presence_of_all_elements_located(
#                 (By.CSS_SELECTOR, ".tabs .nav-tabs a[role='tab'][aria-controls]")
#             )
#         )
#         html = driver.page_source
#     finally:
#         driver.quit()

#     soup = BeautifulSoup(html, "html.parser")

#     h1 = soup.find("h1") or soup.find("title")
#     title = clean_text(h1.get_text()) if h1 else "Keine Überschrift."

#     def tab_text(label_part: str) -> str:
#         a = soup.find("a", {"role": "tab"}, string=lambda s: s and label_part.lower() in s.lower())
#         if not a or not a.has_attr("aria-controls"):
#             return ""
#         pane = soup.find(id=a["aria-controls"])
#         return clean_text(pane.decode_contents()) if pane else ""

#     return {
#         "title": title,
#         "Opis produktu": tab_text("Opis") or tab_text("Beschreibung"), 
#         "Opis karty produktu": tab_text("Karta") or tab_text("Datenblatt"),
#         "Detale": tab_text("Detale") or tab_text("Details"),
#     }

def generate_content(product_data, lang, verb_lvl, sk_google):
    prompt = f"""
    Du bist ein Spezialist für E-Commerce-Content. Deine Aufgabe ist es, eine Produktbeschreibung in einem streng definierten technischen Format zu erstellen.
    
    EINGABEDATEN:
    - Produkt: {product_data}
    - Zielsprache: {lang}
    - Stil: {verb_lvl}
    - SEO-Keywords: {sk_google}

    === ERFORDERLICHE STRUKTUR (Halte dich genau daran) ===
    
    [Zeile 1: Vollständiger Produktname, Hauptmerkmal, Farbe]
    [Zeile 2: Maße, Material, Form, Menge im Set (falls zutreffend)]
    [Beschreibungsblock: 4-5 Sätze, jeder in einer neuen Zeile. Keine Aufzählungszeichen/Bindestriche am Anfang. Beschreibe Anwendung, Vorteile und einzigartige Merkmale. Binde Keywords natürlich ein.]
    ----------------------------------------
    [Überschrift: Übersetze das Wort "Merkmale" oder "Features" in {lang}]:
    [Attributname (z.B. Typ/Version)]: [Wert]
    [Attributname (z.B. Farbe)]: [Wert]
    [Attributname (z.B. Material)]: [Wert]
    [Attributname (z.B. Form)]: [Wert]
    ----------------------------------------
    [Überschrift: Übersetze "Produktinformationen" in {lang}]:
    [Attributname (z.B. Motiv/Muster)]: [Wert]
    [Attributname (z.B. Maße)]: (B x H x T) [Wert]

    
    === FAQ-BEREICH (SEO BOOST) ===
    Erstelle einen FAQ-Bereich (Häufig gestellte Fragen) zur Verbesserung des Google-Rankings.
    - Frage 1: (Sollte ein Keyword aus {sk_google} enthalten)
      Antwort: (Kurz, konkret, max. 2 Sätze)
    - Frage 2: (Bezüglich Anwendung oder Material)
      Antwort: (Konkrete Antwort)
    
    === REGELN ===
    1. Verwende keine Fettdruck (**Text**) im ersten Teil der Beschreibung (Zeilen 1-2 und Beschreibungsblock). Es soll wie reiner Text aussehen.
    2. Behalte die Trennlinien "----------------------------------------" bei.
    3. Extrahiere in den Abschnitten "Merkmale" und "Produktinformationen" nur harte Daten. Wenn Daten fehlen, schreibe "Keine Daten" oder überspringe die Zeile, erfinde nichts.
    4. Der gesamte Text muss in der Sprache {lang} sein.
    """
    try:
        response = st.session_state.openai_client.chat.completions.create(
            model='gpt-4o',  
            messages=[
                {"role": "system", "content": "Du bist ein Spezialist für SEO-Marketing auf verschiedenen Marktplätzen."},
                {"role": "user", "content": prompt}
            ]
        )
        return [choice.message.content.strip() for choice in response.choices] 
    except Exception as e:
        st.error(f"Fehler bei der Content-Generierung durch KI: {e}")
        return None
  
def three_prompts(opis):
    prompt = f"""
    Your task is to create **3 detailed prompts** for the Nano Banana model based on the product description below.
    The prompts will be used to generate **product images** for marketplace listings (e.g. Amazon, Allegro).

    ❗ Important:
    - The prompts will be used *together with an existing product photo*, so **do not describe the product itself**.
    - Focus only on people, context, background, environment, and visual style.
    - Each prompt must be precise, realistic, and professional, following the Nano Banana structure.

    🔹 **Prompts to generate:**
    1. A model (man or woman) with the product — the AI should imagine the person naturally holding or using the product.
    2. The product in use — e.g., a hand holding or interacting with the product.
    3. The product presented on an attractive background fitting its purpose or function.

    🔹 **Guidelines:**
    1. Always write prompts in **English**.
    2. The first two prompts should have a **white background** (for later editing).
    3. Use the Nano Banana structure:
       **Subject**, **Action/Context**, **Environment**, **Style & Aesthetics**, **Composition & Quality**.
    4. Photographic style: professional product photography, studio or lifestyle lighting,
       clean composition, photorealistic, 8K, high texture detail.
    5. Do NOT add comments, extra text, or code formatting — only return pure prompts.

    🔹 **Output format:**
    Return the results in this exact format:
    Prompt 1: <prompt in English>
    Prompt 2: <prompt in English>
    Prompt 3: <prompt in English>

    Here is the product description (source data):
    {opis}
    """
    response = st.session_state.openai_client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": "You are a professional prompt engineer for product sessions"},
                {"role": "user", "content": prompt}
            ],
        )
    return response.choices[0].message.content.strip()

def translate(text):
    # Funkcja tłumacząca NA NIEMIECKI (dla weryfikacji)
    prompt = f"""
    Du erhältst einen Text in einer anderen Sprache als Deutsch. Deine Aufgabe ist es, ihn zu analysieren, die Sprache zu erkennen und diese Auktion aus dieser Sprache ins Deutsche zu übersetzen.
    Der Text ist eine auf SEO und Marketing abgestimmte Auktion, also bewahre den Sinn und den Marketing-Tonfall der Übersetzung.
    Füge keine Kommentare oder Markierungen hinzu – gib nur den reinen übersetzten Text zurück.
    
    Text:
    {text}
    """
    try:
        response = st.session_state.openai_client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": "Du bist ein auf Marktplatz-Auktionen spezialisierter Übersetzer."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Fehler bei der KI-Generierung: {e}")
        return None


# --- INTERFEJS ---
pageTitle = st.container(key='page-title')
column1, column2 = st.columns([2,1])
cols1, cols2 = st.columns([1, 1], border=False)

with column1.container(key="col1-title"):
    st.title('App zur Erstellung von Auktionen')

with column2.container(key="col2"):
    st.image("assets/img/logo.png", width = 200)

# st.title("App zur Erstellung von Auktionen 📝")

if st.session_state.get("clear_pd"):
    st.session_state["product_data"] = ""
    st.session_state["clear_pd"] = False

with cols1.container(key="col1-insert"):
    st.header("1. Eingabedatenquellen",divider="rainbow",help="Wir platzieren den Hilfetext",text_alignment="center")
    # input_method = st.radio(
    #     "Wählen Sie die Eingabemethode:",
    #     ("Webseite", "Bild"),
    #     key="input_method",
    # )

    # if input_method == "Webseite":
    #     url = st.text_input("Geben Sie die URL der Produktseite ein:")
    #     if st.button("Seite durchsuchen 🔎"):
    #         scraped_data = scrape_leviatan(url)
    #         if scraped_data:
    #             scraped_text = "\n\n".join([
    #                 scraped_data["title"],
    #                 scraped_data["Opis produktu"],
    #                 "Produktkartenbeschreibung:",
    #                 scraped_data["Opis karty produktu"],
    #                 scraped_data["Detale"],
    #             ])
    #             base = st.session_state["product_data"].rstrip()
    #             st.session_state["product_data"] = (base + ("\n\n" if base else "") + scraped_text)
    #             st.session_state["scraped_done"] = True
    #             st.success("Daten von der Seite abgerufen ✅")
    #             st.rerun()

    # elif input_method == "Bild":
    uploaded_file = st.file_uploader("Datei auswählen:", type=["jpg", "jpeg", "png"], key="insert-image")
    if st.button("Beschreibung basierend auf Bild generieren",key="button-1", icon=":material/photo_camera:"):
        if uploaded_file:
            with st.spinner("Analysiere Bild..."):
                desc = describe_image(uploaded_file)
            if desc:
                base = st.session_state["product_data"].rstrip()
                st.session_state["product_data"] = (desc + ("\n\n" + base if base else ""))
                st.session_state["image_done"] = True
                st.success("Produktbeschreibung wurde generiert ✅")
                st.rerun()
        else:
            st.warning("Bitte laden Sie zuerst eine Datei hoch.")

    st.divider()
    st.markdown("### Inhaltseditor")
    st.text_area(
        "Produktbeschreibung eingeben / bearbeiten:",
        key="product_data",   
        height=200,
        placeholder="Beschreibung eingeben oder einfügen...",
    )

    if st.button("Text löschen",key="button-2", icon=":material/add_notes:"):
        st.session_state["clear_pd"] = True
        st.rerun()

with cols2.container(key="col2-insert"):
    st.header("2. Personalisierungsparameter",divider="rainbow",help="Wir platzieren den Hilfetext",text_alignment="center")

    # Lista języków z nazwami po niemiecku
    st.session_state['target_language'] = st.selectbox(
        "Wählen Sie die Zielsprache:", 
        ("Deutsch", "Polnisch", "Englisch", "Tschechisch", "Slowakisch", "Ungarisch", "Rumänisch", "Bulgarisch", "Französisch", "Italienisch", "Spanisch", "Schwedisch", "Niederländisch", "Ukrainisch"),
        key="target-lang"
    )

    st.divider()
    #marketplace_type = st.selectbox("Marktplatz wählen:", ('E-commerce', "Amazon", "Allegro", "Ebay"))
    verb_lvl = st.selectbox("Wählen Sie den Schreibstil:", ('locker', 'werblich', 'professionell'),key="target-verb")
    st.divider()
    st.session_state['sk_google'] = st.text_input('Keywords für Google eingeben:', key="target-gogle")


    if st.button("Auktionsinhalt generieren",key="button-3", icon=":material/hourglass_top:"):
        with st.spinner("Inhalte werden generiert..."):
            # Generujemy w wybranym języku (np. po Francusku)
            variants = generate_content(st.session_state["product_data"], st.session_state['target_language'], verb_lvl, st.session_state['sk_google'])
        
        if variants:
            st.session_state["generated_variants"] = variants
            
            if st.session_state['target_language'] != "Deutsch":
                with st.spinner("Erstelle Übersetzung zur Überprüfung..."):
                    st.session_state["translation"] = translate(variants[0]) # Tłumaczymy pierwszy wariant
            else:
                st.session_state["translation"] = "" # Czyścimy jeśli wybrano niemiecki
        else:
            st.warning("Das Modell hat keinen Inhalt zurückgegeben.")

if "generated_variants" in st.session_state and st.session_state["generated_variants"]:
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.header("3. Ergebnisse")
        for i, content in enumerate(st.session_state["generated_variants"], 1):
            st.markdown(content)

    with col2:
        # Wyświetlamy tłumaczenie tylko jeśli język docelowy był inny niż Niemiecki
        if st.session_state['target_language'] != "Deutsch" and st.session_state["translation"]:
            st.header("Übersetzung (Deutsch)")
            st.markdown(st.session_state["translation"])

    st.subheader("Prompts zur Bilderstellung")
    if st.button("Prompts generieren",key="button-4", icon=":material/quiz:"):
        with st.spinner("Erstelle Prompts..."):
            st.session_state["3_prompts"] = three_prompts(st.session_state["product_data"])
        st.rerun()

    if st.session_state["3_prompts"]:

        st.markdown(st.session_state["3_prompts"])
