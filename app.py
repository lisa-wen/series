import streamlit as st
import tantivy
import toml
from tantivy import Occur, Query
import re
from streamlit_card import card
import utils

TMDB_PATH = "https://image.tmdb.org/t/p/original"
TMDB_PATH_SMALL = "https://image.tmdb.org/t/p/w200"

st.set_page_config(
    page_title="Empfehlungsstudie",
    page_icon="🔎"
)
config = toml.load('.streamlit/config.toml')
primary_color = config['theme']['primaryColor']
primary_button = config['theme']['primaryButton']
secondary_button = config['theme']['secondaryButton']

states = ["series", "selected"]

for state in states:
    if state not in st.session_state:
        st.session_state[state] = None

st.markdown(
    f"""
    <style>

    [data-testid="stSidebar"]  {{
        background-color: rgb(240, 240, 242);
        width: 25%;
        float: left
    }}

     [data-testid="stAppViewBlockContainer"] {{
        margin: 0 auto;
    }}

    .item > a {{
        color: {primary_color};
        font-weight: bold;
    }}

    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background-color:  white;
        max-height: 400px !important;  /* Set the maximum height */
        overflow-y: auto !important;  /* Enable vertical scrolling */
        box-shadow: 2.5px 2.5px 5px rgba(0, 0, 0, 0.2);
    }}

    [data-testid="stExpander"] > details {{
        border-width: 0;
        border-style: none;
        border: none !important;

    }}

    [data-testid="stSidebar"] [data-testid="stExpander"] > details > summary  {{
        height: 120px;
    }}

     [data-testid="stSidebar"] [data-testid="stExpander"] > details > summary > span > div > p  {{
        font-size: 1rem;
        font-weight: bold;
        color: {primary_color};
        margin-bottom: 1em;
        text-align: left;
    }}

    [data-testid="stSidebar"] [data-testid="stExpander"] > details > summary > span > div > p:hover  {{
        text-decoration: underline;
    }}


    [data-testid="baseButton-primary"] {{
        background-color: {secondary_button};
        color: white ;
        border: none;
        margin-bottom: 1px;
    }}

    [data-testid="baseButton-primary"]:hover {{
        background-color: {secondary_button};
    }}

     [data-testid="baseButton-secondary"]  {{
        background-color: {secondary_button};
        color: white;
        margin-top: 0px;

    }}

    [data-testid="baseButton-secondary"]:hover  {{
        background-color: rgb(240, 240, 242);
    }}

    [data-testid="baseButton-secondary"]:focus  {{
        background-color: rgb(240, 240, 242);
    }}

    [data-testid="baseButton-secondary"]:active  {{
        background-color: rgb(240, 240, 242);
    }}

    </style>

    """,
    unsafe_allow_html=True
)

schema_builder = tantivy.SchemaBuilder()
schema_builder.add_text_field("id", stored=True)
schema_builder.add_text_field("url", stored=True)
schema_builder.add_text_field("title", stored=True, tokenizer_name='en_stem')
schema_builder.add_text_field("description", stored=True, tokenizer_name='en_stem')  # Multi-valued text field
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
schema_builder.add_text_field("tmdb_overview", stored=True, tokenizer_name='en_stem')
schema_builder.add_text_field("tmdb_poster_path", stored=True)
schema_builder.add_integer_field("tmdb_genre_ids", stored=True, indexed=True)
schema_builder.add_float_field("tmdb_popularity", stored=True, fast=True)
schema_builder.add_float_field("tmdb_vote_average", stored=True, fast=True)
schema_builder.add_integer_field("tmdb_vote_count", stored=True, fast=True)
schema = schema_builder.build()
index_path = "test"
index = tantivy.Index(schema, path=str(index_path))
searcher = index.searcher()
TOP_K_SIM = 25
TOP_K_OUTPUT = 5

with st.sidebar:
    st.title('Search for TV series')
    user_input = st.text_input("Enter search term")
    if st.button("Search", type="primary"):
        st.session_state['series'] = []
        query = index.parse_query(user_input, ['title'])
        hits = searcher.search(query, 5).hits

        for (score, address) in hits:
            hit = searcher.doc(address)
            item = {
                "metadata": hit,
                "address": address
            }
            st.session_state['series'].append(item)

    if st.session_state["series"]:
        id_list = []
        for series in st.session_state['series']:
            item = series["metadata"]
            if item["id"] not in id_list:
                id_list.append(item["id"])
                item_card = card(
                    key="card-" + item["id"][0],
                    title=item["title"][0],
                    text="",
                    image=TMDB_PATH_SMALL + item["tmdb_poster_path"][0] if len(item["tmdb_poster_path"]) > 0 else '',
                    url=item["url"][0],
                    styles={
                        "card": {
                            "border-radius": "0px",
                            "box-shadow": "0 0 5px rgba(0,0,0,0.5)",
                            "margin": "0px",
                            "width": "200px",
                        }
                    }
                )
                col1, col2 = st.columns([2, 3])

                with col2:
                    if st.button('Mehr', key="button-" + item["id"][0]):
                        st.session_state['selected'] = series
                st.divider()

if st.session_state['selected']:
    st.title("TV Series and Gender")
    selected = st.session_state["selected"]["metadata"]
    queries = []
    description = selected["tmdb_overview"][0]+" "+selected["description"][0]
    clean_description = "\n".join(line for line in description.splitlines() if line.strip()).replace(":", "")
    query_str = re.sub(r'[^a-zA-Z0-9\s]', '', clean_description)
    cleaned_text = re.sub(r'\[[^\]]*\]', '', query_str)
    mlt_query = index.parse_query(cleaned_text, ['description'])
    queries.append((Occur.Should, mlt_query))
    genres = []
    for i, genre in enumerate(selected["genres"]):
        query = index.parse_query(f'{genre}', ["genres"])
        queries.append((Occur.Should, query))
        genres.append(genre)
    for i, genre in enumerate(selected["tmdb_genre_ids"]):
        query = index.parse_query(f'{genre}', ["tmdb_genre_ids"])
        queries.append((Occur.Should, query))
    boolean_query = Query.boolean_query(queries)
    results = searcher.search(boolean_query, limit=TOP_K_SIM)
    males = []
    females = []
    other = []
    tab1, tab2, tab3, tab4 = st.tabs(["Ranked by Similarity", "Ranked by Popularity", "Reranked Gender", "Ranked by Quality"])
    sim_docs = utils.rank(searcher, results.hits, st.session_state["selected"]["address"], "tmdb_vote_average", True)
    pop_docs = utils.rank(searcher, results.hits, st.session_state["selected"]["address"], "tmdb_popularity", False)
    qual_docs = utils.rank(searcher, results.hits, st.session_state["selected"]["address"], "tmdb_vote_average", False)
    with tab1:
        utils.print_recommendations(sim_docs[:TOP_K_OUTPUT], selected, "s")
    with tab2:
        utils.print_recommendations(pop_docs[:TOP_K_OUTPUT], selected,"p")
    with tab3:
        gender_docs = utils.rank(searcher, results.hits, st.session_state["selected"]["address"], "females", False)
        sort_docs = utils.re_rank(pop_docs[:TOP_K_OUTPUT], gender_docs[:TOP_K_OUTPUT], 0.5)
        utils.print_recommendations(sort_docs, selected, "g")
    with tab4:
        utils.print_recommendations(qual_docs[:TOP_K_OUTPUT], selected, "q")