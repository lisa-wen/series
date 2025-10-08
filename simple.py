import streamlit as st
import tantivy
import toml
import re
from pathlib import Path

# --- Konstanten -------------------------------------------------------------
TMDB_PATH = "https://image.tmdb.org/t/p/original"
TMDB_PATH_SMALL = "https://image.tmdb.org/t/p/w200"
INDEX_PATH = "test"  # bestehendes Tantivy-Index-Verzeichnis
TOP_K = 20           # wie viele Ergebnisse angezeigt werden sollen

# --- Seiteneinstellungen ----------------------------------------------------
st.set_page_config(page_title="Empfehlungsstudie — Einfache Suche", page_icon="🔎", layout="wide")

# Themenfarben (optional; Standardwerte, falls keine Konfiguration vorhanden)
try:
    config = toml.load(".streamlit/config.toml")
    primary_color = config.get("theme", {}).get("primaryColor", "#31356e")
except Exception:
    primary_color = "#31356e"

# --- Minimales Styling (optional) ------------------------------------------
st.markdown(
    f"""
    <style>
    .result-card {{
        display: grid;
        grid-template-columns: 120px 1fr;
        gap: 1rem;
        padding: 0.75rem 0;
        border-bottom: 1px solid rgba(0,0,0,0.08);
    }}
    .result-card img {{
        width: 120px; height: 180px; object-fit: cover; border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,.15);
    }}
    .result-title a {{
        color: {primary_color};
        text-decoration: none; font-weight: 700; font-size: 1.05rem;
    }}
    .result-title a:hover {{ text-decoration: underline; }}
    .muted {{ color: #666; font-size: 0.95rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Tantivy-Schema (entspricht dem bestehenden Index) ---------------------
schema_builder = tantivy.SchemaBuilder()
schema_builder.add_text_field("id", stored=True)
schema_builder.add_text_field("url", stored=True)
schema_builder.add_text_field("title", stored=True, tokenizer_name="en_stem")
schema_builder.add_text_field("description", stored=True, tokenizer_name="en_stem")
schema_builder.add_text_field("image", stored=True)
schema_builder.add_integer_field("follower", stored=True, fast=True)
schema_builder.add_integer_field("score", stored=True, fast=True)
schema_builder.add_integer_field("start", stored=True, fast=True)
schema_builder.add_text_field("locations", stored=True)
schema_builder.add_text_field("countries", stored=True)
schema_builder.add_text_field("genres", stored=True)
schema_builder.add_integer_field("males", stored=True, fast=True)
schema_builder.add_integer_field("females", stored=True, fast=True)
schema_builder.add_integer_field("other", stored=True, fast=True)
schema_builder.add_float_field("non_males", stored=True, fast=True)
schema_builder.add_text_field("tmdb_overview", stored=True, tokenizer_name="en_stem")
schema_builder.add_text_field("tmdb_poster_path", stored=True)
schema_builder.add_integer_field("tmdb_genre_ids", stored=True, indexed=True)
schema_builder.add_float_field("tmdb_popularity", stored=True, fast=True)
schema_builder.add_float_field("tmdb_vote_average", stored=True, fast=True)
schema_builder.add_integer_field("tmdb_vote_count", stored=True, fast=True)
schema = schema_builder.build()

# Öffne bestehenden Index
index = tantivy.Index(schema, path=str(INDEX_PATH))
searcher = index.searcher()

# --- Benutzeroberfläche ----------------------------------------------------
st.title("Suche nach TV-Serien")
query_text = st.text_input("Suchbegriff eingeben", placeholder="z. B. Breaking Bad, Detektiv, Weltraumoper…")

if st.button("Suchen", type="primary"):
    if not query_text.strip():
        st.info("Bitte gib einen Suchbegriff ein.")
    else:
        # Einfache, fehlertolerante Suche über Titel und Beschreibung
        # Verwende einen RAW STRING, damit Regex-Zeichen wie \w oder \s nicht interpretiert werden
        cleaned = re.sub(r"[^\w\s]", " ", query_text).strip()
        q = index.parse_query(cleaned, ["title", "description"])  # Suche in beiden Feldern
        hits = searcher.search(q, TOP_K).hits

        if not hits:
            st.warning("Keine Ergebnisse gefunden.")
        else:
            st.subheader("Ergebnisse")

            seen_ids = set()
            for score, addr in hits:
                doc = searcher.doc(addr)
                doc_id = doc["id"][0]
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)

                title = doc["title"][0]
                url = doc["url"][0]
                poster = doc["tmdb_poster_path"]
                poster_url = (TMDB_PATH_SMALL + poster[0]) if poster else ""

                overview = doc["tmdb_overview"] or doc["description"]
                overview = overview[0] if overview else ""

                # HTML ohne Backslash-Escapes erstellen (einfach Anführungszeichen in Attributen verwenden)
                img_html = f"<img src='{poster_url}' alt='poster'>" if poster_url else ""
                st.markdown(
                    f'''
                    <div class='result-card'>
                        <div>{img_html}</div>
                        <div>
                            <div class='result-title'><a href='{url}' target='_blank'>{title}</a></div>
                            <div class='muted'>{overview}</div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

# Tipp beim ersten Öffnen der App
if not st.session_state.get("_shown_tip", False):
    st.caption("Gib oben ein Stichwort oder einen Serientitel ein und klicke auf **Suchen**, um passende Serien anzuzeigen.")
    st.session_state["_shown_tip"] = True

