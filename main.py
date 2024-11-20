import advertools as adv
import pandas as pd
import streamlit as st
import time
from openpyxl import load_workbook
from polyfuzz import PolyFuzz
from polyfuzz.models import RapidFuzz

# Inizializzazione della sessione Streamlit per cache
if 'matched_results' not in st.session_state:
    st.session_state.matched_results = None
    st.session_state.legacy_crawl = None
    st.session_state.new_crawl = None
    st.session_state.legacy_url_parse = None
    st.session_state.new_url_parse = None

# Imposta il matcher e il modello
matcher = RapidFuzz(n_jobs=1)
model = PolyFuzz(matcher)

# Configurazione della pagina
st.set_page_config(page_title="Redirect URL Mapper • NUR® Digital Marketing", page_icon="./Nur-simbolo-1080x1080.png")
st.image("./logo_nur_vettoriale.svg", width=100)
st.markdown("# Redirect URL Mapper")
st.markdown("Strumento per la mappatura automatica dei reindirizzamenti, che confronta gli URL precedenti e quelli nuovi in base a vari elementi della pagina (percorsi, slug, titoli, H1 e H2).")

# Sezione per istruzioni e requisiti in blocchi espandibili
with st.expander("Istruzioni"):
    st.markdown("""
    - Esegui una scansione su Screaming Frog dei siti live e staging (utilizza le sitemap come fonte di crawling)
    - Filtra per Content Type "HTML" ed esporta entrambi i crawling in formato .XLSX 
    - Carica i file separati nelle apposite sezioni dello strumento
    """)

with st.expander("Requisiti"):
    st.markdown("""
    - La colonna 1 deve essere denominata "Address" e contenere URL completi, inclusi http(s)://
    - Le seguenti intestazioni di colonna devono essere presenti in entrambi i file, anche se le celle sono vuote:
      - "Title 1", "H1-1", "H2-1"
    """)

# Configurazione soglie nella sidebar con valori di default modificabili
st.sidebar.header("Configurazione Soglie di Similarità")
threshold_url = st.sidebar.slider("Soglia similarità URL", 0.0, 1.0, 0.65, 0.01)
threshold_slug = st.sidebar.slider("Soglia similarità Slug", 0.0, 1.0, 0.65, 0.01)
threshold_title = st.sidebar.slider("Soglia similarità Titoli", 0.0, 1.0, 0.70, 0.01)
threshold_h1 = st.sidebar.slider("Soglia similarità H1", 0.0, 1.0, 0.90, 0.01)
threshold_h2 = st.sidebar.slider("Soglia similarità H2", 0.0, 1.0, 0.90, 0.01)

# Funzione per eseguire il match iniziale e salvare i risultati
def perform_initial_match(data_type, from_data, to_data):
    model.match(from_data, to_data)
    matches = model.get_matches()
    matches["Similarity"] = matches["Similarity"].round(3)
    matches = matches.sort_values('Similarity', ascending=False)
    return matches

# Funzione per filtrare i risultati in base alla soglia
def filter_and_join_results(matches_df, threshold, legacy_data, new_data, match_type='url'):
    filtered_df = matches_df[matches_df['Similarity'] >= threshold].copy()
    
    if match_type == 'url':
        join_df = pd.merge(filtered_df, legacy_data, left_on='From', right_on='path')
        join_df_2 = pd.merge(join_df, new_data, left_on='To', right_on='path')
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 
                    'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
        result_df = join_df_2[['From', 'To', 'Similarity', 
                              'Percorso Legacy', 'Percorso Nuovo', 
                              'URL Legacy', 'URL Nuovo']]
    elif match_type == 'slug':
        join_df = pd.merge(filtered_df, legacy_data, left_on='From', right_on='last_dir')
        join_df_2 = pd.merge(join_df, new_data, left_on='To', right_on='last_dir')
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 
                    'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
        result_df = join_df_2[['From', 'To', 'Similarity', 
                              'Percorso Legacy', 'Percorso Nuovo', 
                              'URL Legacy', 'URL Nuovo']]
    else:  # title, h1, h2
        join_df = pd.merge(filtered_df, legacy_data, 
                          left_on='From', 
                          right_on=f'{match_type.capitalize()}-1' if match_type != 'title' else 'Title 1')
        join_df_2 = pd.merge(join_df, new_data, 
                            left_on='To', 
                            right_on=f'{match_type.capitalize()}-1' if match_type != 'title' else 'Title 1')
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        result_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
    
    return result_df.drop_duplicates()

# Funzione principale per l'analisi dei crawl
def analyze_crawls(crawls):
    with st.spinner('Elaborazione dei crawl del sito in corso...'):
        progress_bar = st.progress(0)
        input_files = []
        
        for crawl_index, crawl in enumerate(crawls):
            wb = load_workbook(filename=crawl)
            sheet_name = wb.sheetnames
            input_files.append([crawl, sheet_name])
            progress_bar.progress((crawl_index + 1) / len(crawls))
            time.sleep(0.01)

        # Carica i crawl solo se non sono già in cache
        if st.session_state.legacy_crawl is None:
            st.session_state.legacy_crawl = pd.read_excel(
                input_files[0][0], 
                sheet_name=input_files[0][1][0]
            )[['Address', 'Title 1', 'H1-1', 'H2-1']]
            
            st.session_state.new_crawl = pd.read_excel(
                input_files[1][0], 
                sheet_name=input_files[1][1][0]
            )[['Address', 'Title 1', 'H1-1', 'H2-1']]

            # Parse URL
            legacy_urls = st.session_state.legacy_crawl['Address'].tolist()
            new_urls = st.session_state.new_crawl['Address'].tolist()
            
            st.session_state.legacy_url_parse = adv.url_to_df(legacy_urls)[['url', 'path', 'last_dir']]
            st.session_state.new_url_parse = adv.url_to_df(new_urls)[['url', 'path', 'last_dir']]

            # Esegui i match iniziali e salva i risultati
            st.session_state.matched_results = {
                'url': perform_initial_match(
                    'url',
                    st.session_state.legacy_url_parse['path'],
                    st.session_state.new_url_parse['path']
                ),
                'slug': perform_initial_match(
                    'slug',
                    st.session_state.legacy_url_parse['last_dir'],
                    st.session_state.new_url_parse['last_dir']
                ),
                'title': perform_initial_match(
                    'title',
                    st.session_state.legacy_crawl['Title 1'],
                    st.session_state.new_crawl['Title 1']
                ),
                'h1': perform_initial_match(
                    'h1',
                    st.session_state.legacy_crawl['H1-1'],
                    st.session_state.new_crawl['H1-1']
                ),
                'h2': perform_initial_match(
                    'h2',
                    st.session_state.legacy_crawl['H2-1'],
                    st.session_state.new_crawl['H2-1']
                )
            }

    # Applica i filtri sui risultati cached
    filtered_results = [
        filter_and_join_results(
            st.session_state.matched_results['url'],
            threshold_url,
            st.session_state.legacy_url_parse,
            st.session_state.new_url_parse,
            'url'
        ),
        filter_and_join_results(
            st.session_state.matched_results['slug'],
            threshold_slug,
            st.session_state.legacy_url_parse,
            st.session_state.new_url_parse,
            'slug'
        ),
        filter_and_join_results(
            st.session_state.matched_results['title'],
            threshold_title,
            st.session_state.legacy_crawl,
            st.session_state.new_crawl,
            'title'
        ),
        filter_and_join_results(
            st.session_state.matched_results['h1'],
            threshold_h1,
            st.session_state.legacy_crawl,
            st.session_state.new_crawl,
            'h1'
        ),
        filter_and_join_results(
            st.session_state.matched_results['h2'],
            threshold_h2,
            st.session_state.legacy_crawl,
            st.session_state.new_crawl,
            'h2'
        )
    ]
    
    export_dfs(filtered_results)

# Funzione per esportare e visualizzare le tabelle
def export_dfs(match_dfs):
    sheet_names = ['URL Match', 'Slug Match', 'Title Match', 'H1 Match', 'H2 Match']
    
    # Aggiungi statistiche per ogni tipo di match
    for i, df in enumerate(match_dfs):
        st.subheader(f"Statistiche {sheet_names[i]}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Numero di match trovati", len(df))
        with col2:
            if len(df) > 0:
                st.metric("Similarità media", f"{df['Similarity'].mean():.2%}")
    
    # Aggiungi un selettore a schede per visualizzare i fogli separatamente
    selected_sheet = st.selectbox("Seleziona il match da visualizzare", sheet_names)
    
    # Mostra la tabella selezionata
    sheet_index = sheet_names.index(selected_sheet)
    st.dataframe(match_dfs[sheet_index])

    # Salva il file Excel
    with pd.ExcelWriter('mappatura_url.xlsx') as writer:
        for df, sheet_name in zip(match_dfs, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Aggiungi il pulsante per il download del file
    with open("mappatura_url.xlsx", "rb") as file:
        st.download_button(
            label='Scarica l\'analisi del match',
            data=file,
            file_name='mappatura_url.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# Pulsante per resettare la cache
if st.button('Resetta Cache e Ricarica'):
    st.session_state.matched_results = None
    st.session_state.legacy_crawl = None
    st.session_state.new_crawl = None
    st.session_state.legacy_url_parse = None
    st.session_state.new_url_parse = None
    st.experimental_rerun()

# File uploader e avvio analisi
legacy_file = st.file_uploader('Carica il file degli ***URLs attualmente live***', type='xlsx', key='legacy')
if legacy_file is not None:
    new_file = st.file_uploader('Carica il file degli ***URLs staging***', type='xlsx', key='new')
    if new_file is not None:
        crawl_files = [legacy_file, new_file]
        analyze_crawls(crawl_files)

# Branding e footer
st.markdown("---")
st.markdown("© 2024 [NUR® Digital Marketing](https://www.nur.it/). Tutti i diritti riservati.")
