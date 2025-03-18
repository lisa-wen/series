import random
import streamlit as st
import tantivy
import toml
from streamlit_extras.stylable_container import stylable_container
import plotly.express as px
import pandas as pd
from streamlit_card import card

TMDB_PATH = "https://image.tmdb.org/t/p/original"
TMDB_PATH_SMALL = "https://image.tmdb.org/t/p/w200"
config = toml.load('.streamlit/config.toml')
primary_color = config['theme']['primaryColor']
primary_button = config['theme']['primaryButton']
secondary_button = config['theme']['secondaryButton']
container_style = f"""
                 {{

                    box-shadow: 2.5px 2.5px 5px rgba(0, 0, 0, 0.2);
                    #border: 1px solid ; 
                    #background-color: rgb(240, 240, 242);
                }}

                .rec {{
                    background-color: white;
                    height: 250px;
                    overflow-y: auto !important;  /* Enable vertical scrolling */
                    background: linear-gradient(to bottom, transparent, white 90%);
                    z-index: 0;

                }}

                .rec > p {{
                    margin: 10px;
                }}



                .rec > .title > a {{
                    color: {primary_button} !important;
                }}

                .rec > div {{
                    padding-left: 5px;
                }}

                .rec  > img {{
                    padding-left: 10px;
                }}


                .rec:after {{
                    content: '⇩';
                    position: absolute;
                    bottom: 5px;
                    right: 10px;
                    pointer-events: none; /* Ensure it doesn't interfere with scrolling */
                }}

                .title {{
                    font-weight: bold;
                    color: {primary_button};
                    text-align: left;
                }}

                """


def rank(searcher, hits, exclude_address, field_name, sim):
    """
        Rank documents by a given numeric field (e.g., 'tmdb_popularity').

        Args:
            searcher (tantivy.Searcher): The Tantivy searcher object.
            hits (list): List of search results [(score, doc_address), ...].
            exclude_address (int): Document address to exclude from ranking.
            field_name (str): Name of the numeric field to sort by.

        Returns:
            list: Sorted list of documents based on the numeric field.
        """
    # List to store valid documents with their field value
    docs_with_field = []

    for score, doc_address in hits:
        # Exclude the specified address
        if doc_address == exclude_address:
            continue

        # Retrieve the document from the searcher
        doc = searcher.doc(doc_address)

        # Safely extract the numeric field value
        try:
            # Get the field values (list) and convert the first value to a float
            field_values = doc[field_name]
            if field_values:  # Ensure the field is not empty or missing
                field_value = float(field_values[0])
                docs_with_field.append((doc, field_value))
        except (KeyError, ValueError, TypeError):
            # Skip documents without the field or with invalid data
            continue

    # Sort the documents by the extracted field value in descending order
    sorted_docs = sorted(docs_with_field, key=lambda x: x[1], reverse=True)
    # Return only the sorted documents (exclude the numeric values)
    if sim:
        return [doc for doc, _ in docs_with_field]
    else:
        return [doc for doc, _ in sorted_docs]


def re_rank(ranked_docs_1, ranked_docs_2, factor):
    reranked_list = []
    outcomes = [True, False]
    weights = [factor, 1 - factor]

    # Generate a single random boolean value
    #replace = random.choices(outcomes, weights=weights, k=1)[0]

    for doc in ranked_docs_1:
        if random.random() < factor:
            candidate = ranked_docs_2.pop(0)
            # if candidate not in reranked_list:
            if candidate not in ranked_docs_1:
                reranked_list.append(candidate)
            else:
                reranked_list.append(doc)
        else:
            reranked_list.append(doc)

    return reranked_list


def print_recommendations(sort_docs, selected, gender_flag):
    males = []
    females = []
    other = []
    for doc in sort_docs:
        males.append(doc["males"][0])
        females.append(doc["females"][0])
        other.append(doc["other"][0])
    data = {
        'Category': ['male', 'female', 'non-binary'],
        'Creators': [sum(males), sum(females), sum(other)]
    }
    df = pd.DataFrame(data)
    fig = px.pie(
        df,
        values='Creators',
        names='Category',
        title='',
        hole=0.3,  # Optional: creates a donut chart effect
        color_discrete_sequence=["#31356e", "#2d8bba", "#cb6ce6"]
    )
    # Customize layout
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
    )
    fig.update_layout(
        height=330,
    )

    selected_image = ""
    if len(selected["tmdb_poster_path"]) > 0:
        selected_image = TMDB_PATH_SMALL + selected["tmdb_poster_path"][0]
    col1, col2 = st.columns([1, 1])
    with col1:
        hasClicked = card(
            key=str(gender_flag) + selected["id"][0],
            title=selected["title"],
            text="",
            image=selected_image,
            url=selected["url"],
            styles={
                "card": {
                    "margin-top": "20px",
                    #"height": "150px",
                    "border-radius": "0px",
                    "color": "rgb(240, 240, 242)",  # Set background color
                    "box-shadow": "0 0 5px rgba(0,0,0,0.5)",
                    "width": "200px"

                }
            }
        )
    with col2:
        st.plotly_chart(fig, key=gender_flag)

    st.markdown("**You might also like...**")
    # Iterate through the results to extract documents and scores
    ids = []
    for doc in sort_docs:
        if doc["id"][0] not in ids:
            ids.append(doc["id"][0])
            url = doc["url"][0]
            title = doc["title"][0]
            if len(doc["tmdb_poster_path"]) > 0:
                image = TMDB_PATH_SMALL + doc["tmdb_poster_path"][0]
            else:
                image = ""
            if len(doc["tmdb_overview"]) > 0:
                desc = doc["tmdb_overview"][0]
            else:
                desc = doc["description"][0]

            with stylable_container(key="dark_blue", css_styles=container_style):
                column1, column2 = st.columns([2, 1])
                with column1:
                    html = (f'<div class="rec" id="scrollableContent">'
                            f'<p class="title"><a href="{url}">{title}</a></p>'
                            f'<p>{desc}</p>'
                            f'</div>')
                    st.markdown(html, unsafe_allow_html=True)
                with column2:
                    hasClicked = card(
                        key=str(gender_flag) + doc["id"][0],
                        title=title,
                        text="",
                        image=image,
                        url=url,
                        styles={
                            "card": {
                                "border-radius": "0px",
                                "box-shadow": "0 0 5px rgba(0,0,0,0.5)",
                                "margin": "0px",
                                "width": "200px"
                            }
                        }
                    )

                st.write("")
