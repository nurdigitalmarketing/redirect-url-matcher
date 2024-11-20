import advertools as adv
import pandas as pd
import streamlit as st
import time
from openpyxl import load_workbook
from polyfuzz import PolyFuzz
from polyfuzz.models import RapidFuzz

# Imposta il matcher e il modello
matcher = RapidFuzz(n_jobs=-1)  # Utilizzo di tutti i core disponibili
model = PolyFuzz(matcher)

# Configurazione della pagina con titolo e icona
st.set_page_config(page_title="Redirect URL Mapper • NUR® Digital Marketing", page_icon="./Nur-simbolo-1080x1080.png")

# Aggiungi il logo di Nur Digital Marketing
st.image("./logo_nur_vettoriale.svg", width=100)

# Aggiungi il titolo della pagina
st.markdown("# Redirect URL Mapper")

# Aggiungi il sottotitolo
st.markdown("Strumento per la mappatura automatica dei reindirizzamenti, che confronta gli URL precedenti e quelli nuovi in base a vari elementi della pagina (percorsi, slug, titoli, H1 e H2). Supporta l'importazione tramite *Screaming Frog* ed *advertools spider* per il crawling.")

# Slider per la soglia di similarità
similarity_threshold = st.slider(
    'Imposta la soglia di similarità (da 0.0 a 1.0)',
    min_value=0.0,
    max_value=1.0,
    value=0.80,  # Valore predefinito
    step=0.01
)

# Funzione per il caching del parsing degli URL
@st.cache_data
def parse_urls(urls):
    return adv.url_to_df(urls)

# Funzione per l'analisi incrementale del matching
@st.cache_data
def perform_initial_matching(legacy_data, new_data):
    model.match(legacy_data, new_data)
    return model.get_matches()

# Sezione per istruzioni e requisiti in blocchi espandibili uno sopra l'altro
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

# Caricamento file legacy
legacy_file = st.file_uploader('Carica il file degli ***URLs attualmente live***', type='xlsx', key='legacy')

input_files = []
crawl_columns = ['Address', 'Title 1', 'H1-1', 'H2-1']

# Funzione per analizzare i crawl
def analyze_crawls(crawls, threshold):
    with st.spinner('Elaborazione dei crawl del sito in corso...'):
        progress_bar = st.progress(0)
        for crawl_index, crawl in enumerate(crawls):
            wb = load_workbook(filename=crawl)
            sheet_name = wb.sheetnames
            input_files.append([crawl, sheet_name])
            progress_bar.progress((crawl_index + 1) / len(crawls))
            time.sleep(0.01)

        legacy_crawl = pd.read_excel(input_files[0][0], sheet_name=input_files[0][1][0])
        legacy_crawl = legacy_crawl.dropna(subset=['Address'])[crawl_columns]
        new_crawl = pd.read_excel(input_files[1][0], sheet_name=input_files[1][1][0])
        new_crawl = new_crawl.dropna(subset=['Address'])[crawl_columns]

        legacy_urls = legacy_crawl['Address'].tolist()
        new_urls = new_crawl['Address'].tolist()

    url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl, threshold)

# Funzioni di match
def generic_match(data_legacy, data_new, legacy_crawl, new_crawl, column_name, threshold):
    with st.spinner(f"Analisi dei dati: {column_name} in corso..."):
        # Caching del matching iniziale
        initial_matches = perform_initial_matching(data_legacy, data_new)
        filtered_matches = initial_matches[initial_matches['Similarity'] >= threshold]
        join_df = pd.merge(filtered_matches, legacy_crawl, left_on='From', right_on=column_name)
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on=column_name).drop_duplicates()
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        return join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']].drop_duplicates()

# Funzione di parsing degli URL
def url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl, threshold):
    with st.spinner('Decomposizione degli URL in corso...'):
        url_parse_cols = ['url', 'path', 'last_dir']
        legacy_url_parse = parse_urls(legacy_urls)[url_parse_cols]
        new_url_parse = parse_urls(new_urls)[url_parse_cols]

        legacy_paths = legacy_url_parse['path']
        new_paths = new_url_parse['path']
        legacy_slug = legacy_url_parse['last_dir']
        new_slug = new_url_parse['last_dir']
        legacy_titles = legacy_crawl['Title 1']
        new_titles = new_crawl['Title 1']
        legacy_h1 = legacy_crawl['H1-1']
        new_h1 = new_crawl['H1-1']
        legacy_h2 = legacy_crawl['H2-1']
        new_h2 = new_crawl['H2-1']

    match_dfs = [
        generic_match(legacy_paths, new_paths, legacy_url_parse, new_url_parse, 'path', threshold),
        generic_match(legacy_slug, new_slug, legacy_url_parse, new_url_parse, 'last_dir', threshold),
        generic_match(legacy_titles, new_titles, legacy_crawl, new_crawl, 'Title 1', threshold),
        generic_match(legacy_h1, new_h1, legacy_crawl, new_crawl, 'H1-1', threshold),
        generic_match(legacy_h2, new_h2, legacy_crawl, new_crawl, 'H2-1', threshold)
    ]
    export_dfs(match_dfs)

# Funzione per esportare e visualizzare le tabelle
def export_dfs(match_dfs):
    sheet_names = ['URL Match', 'Slug Match', 'Title Match', 'H1 Match', 'H2 Match']
    
    # Aggiungi un selettore a schede per visualizzare i fogli separatamente
    selected_sheet = st.selectbox("Seleziona il match da visualizzare", sheet_names)

    # Mostra la tabella selezionata
    sheet_index = sheet_names.index(selected_sheet)
    st.dataframe(match_dfs[sheet_index])  # Visualizza la tabella interattiva

    # Salva il file Excel
    with pd.ExcelWriter('mappatura_url.xlsx') as writer:
        for df, sheet_name in zip(match_dfs, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Aggiungi il pulsante per il download del file
    with open("mappatura_url.xlsx", "rb") as file:
        st.download_button(label='Scarica l\'analisi del match',
                           data=file,
                           file_name='mappatura_url.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Controlla se i file sono stati caricati e avvia l'analisi
if legacy_file is not None:
    new_file = st.file_uploader('Carica il file degli ***URLs staging***', type='xlsx', key='new')
    if new_file is not None:
        crawl_files = [legacy_file, new_file]
        analyze_crawls(crawl_files, similarity_threshold)

# Branding e footer
st.markdown("---")
st.markdown("© 2024 [NUR® Digital Marketing](https://www.nur.it/). Tutti i diritti riservati.")
