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
    ### Come utilizzare lo strumento
    1. **Preparazione dei crawl**:
       - Esegui una scansione con Screaming Frog sia del sito attualmente live che del sito staging/nuovo
       - Per ottenere risultati migliori, utilizza le sitemap XML come fonte di crawling
       - Puoi utilizzare l'URL List Mode per crawlare solo specifiche sezioni del sito

    2. **Esportazione dei dati**:
       - In Screaming Frog, applica i filtri desiderati per il tipo di contenuto:
         - HTML (per pagine web standard)
         - PDF (per documenti)
         - Images (per file immagine)
         - CSS/JavaScript (per file di risorse)
       - Esporta i risultati in formato .XLSX per entrambi i siti

    3. **Utilizzo dello strumento**:
       - Carica prima il file del sito live nella sezione "URLs attualmente live"
       - Poi carica il file del sito staging/nuovo nella sezione "URLs staging"
       - Utilizza i cursori nella sidebar per regolare le soglie di similarità:
         - Valori più alti = match più precisi ma meno risultati
         - Valori più bassi = più risultati ma possibili falsi positivi

    4. **Analisi dei risultati**:
       - Lo strumento confronterà automaticamente:
         - URL completi
         - Slug delle URL
         - Titoli delle pagine
         - Contenuto degli H1
         - Contenuto degli H2
       - Puoi visualizzare i risultati per ogni tipo di match
       - Scarica il file Excel completo con tutti i match trovati
    """)

with st.expander("Requisiti e formato dei file"):
    st.markdown("""
    ### Requisiti dei file Excel
    1. **Struttura delle colonne obbligatorie**:
       - "Address" (colonna 1): URL completi con http(s)://
       - "Title 1": Titolo della pagina
       - "H1-1": Primo heading H1
       - "H2-1": Primo heading H2

    2. **Note importanti**:
       - Tutte le colonne sopra elencate devono essere presenti in entrambi i file
       - Le colonne possono contenere celle vuote, ma le intestazioni devono esistere
       - Gli URL devono essere completi e validi
       - Si possono includere ulteriori colonne, ma non verranno utilizzate per il matching

    3. **Suggerimenti per risultati migliori**:
       - Assicurati che gli URL non contengano spazi o caratteri speciali
       - Verifica che i titoli e gli heading siano puliti da caratteri HTML
       - Per file PDF, immagini o altri tipi di contenuto, assicurati che Screaming Frog abbia accesso ai file
       - Considera di utilizzare filtri in Screaming Frog per ridurre il rumore nei dati

    4. **In caso di errori**:
       - Usa il pulsante "Resetta cache e ricarica" se noti comportamenti anomali
       - Verifica la presenza di tutte le colonne richieste
       - Controlla che non ci siano celle con formattazione speciale
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
    
    # Stile CSS personalizzato
    st.markdown("""
        <style>
        .stats-card {
            background-color: #1E1E1E;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
        }
        .metric-title {
            color: #9E9E9E;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        .metric-value {
            color: #FFFFFF;
            font-size: 1.8em;
            font-weight: bold;
            margin: 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Per ogni tipo di match
    for i, df in enumerate(match_dfs):
        st.markdown(f"### {sheet_names[i]}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
                <div class="stats-card">
                    <div class="metric-title">Match trovati</div>
                    <div class="metric-value">{len(df):,}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_similarity = df['Similarity'].mean() if len(df) > 0 else 0
            st.markdown(f"""
                <div class="stats-card">
                    <div class="metric-title">Similarità media</div>
                    <div class="metric-value">{avg_similarity:.1%}</div>
                </div>
            """, unsafe_allow_html=True)

    # Visualizzazione tabella e export
    selected_sheet = st.selectbox("Seleziona il match da visualizzare", sheet_names)
    sheet_index = sheet_names.index(selected_sheet)
    st.dataframe(match_dfs[sheet_index])

    with pd.ExcelWriter('mappatura_url.xlsx') as writer:
        for df, sheet_name in zip(match_dfs, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    with open("mappatura_url.xlsx", "rb") as file:
        st.download_button(
            label='Scarica l\'analisi del match',
            data=file,
            file_name='mappatura_url.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# Pulsante per resettare la cache
if st.button('Resetta cache e ricarica'):
    st.session_state.matched_results = None
    st.session_state.legacy_crawl = None
    st.session_state.new_crawl = None
    st.session_state.legacy_url_parse = None
    st.session_state.new_url_parse = None
    st.rerun()  # Modificato da st.experimental_rerun() a st.rerun()

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
