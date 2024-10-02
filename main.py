import advertools as adv
import pandas as pd
import streamlit as st
import time
from openpyxl import load_workbook
from polyfuzz import PolyFuzz
from polyfuzz.models import RapidFuzz

# Imposta il matcher e il modello
matcher = RapidFuzz(n_jobs=1, score_cutoff=0.80)
model = PolyFuzz(matcher)

# Configurazione della pagina con titolo e icona
st.set_page_config(page_title="Redirect URL Mapper • NUR® Digital Marketing", page_icon="./Nur-simbolo-1080x1080.png")

# Aggiungi il logo di Nur Digital Marketing
st.image("./logo_nur_vettoriale.svg", width=100)

# Aggiungi l'intestazione e le istruzioni in italiano
st.markdown("""
# Redirect URL Mapper

**Istruzioni:**
- Carica il crawl degli URL legacy (ovvero "old")
- Carica il crawl degli URL nuovi (ovvero "new")
- Scarica il file xlsx dopo che l'app ha terminato (l'elaborazione potrebbe richiedere alcuni minuti per crawl di grandi dimensioni)

**Requisiti:**
- La colonna 1 deve essere denominata "Address" e contenere URL completi, inclusi http(s)://
- Le seguenti intestazioni di colonna devono essere presenti in entrambi i file, anche se le celle sono vuote:
  - "Title 1", "H1-1", "H2-1"
""")

# Caricamento file legacy
legacy_file = st.file_uploader('Carica il crawl degli URL LEGACY', type='xlsx', key='legacy')

input_files = []
crawl_columns = ['Address', 'Title 1', 'H1-1', 'H2-1']

# Funzione per analizzare i crawl
def analyze_crawls(crawls):
    with st.spinner('Elaborazione dei crawl del sito in corso...'):
        progress_bar = st.progress(0)
        for crawl_index, crawl in enumerate(crawls):
            wb = load_workbook(filename=crawl)
            sheet_name = wb.sheetnames
            input_files.append([crawl, sheet_name])
            progress_bar.progress((crawl_index + 1) / len(crawls))
            time.sleep(0.01)

        legacy_crawl = pd.read_excel(input_files[0][0], sheet_name=input_files[0][1][0])
        legacy_crawl = legacy_crawl[crawl_columns]
        new_crawl = pd.read_excel(input_files[1][0], sheet_name=input_files[1][1][0])
        new_crawl = new_crawl[crawl_columns]
        legacy_urls = legacy_crawl['Address'].tolist()
        new_urls = new_crawl['Address'].tolist()
    url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl)

# Funzioni di match
def url_match(legacy_paths, new_paths, legacy_url_parse, new_url_parse):
    with st.spinner('Analisi dei percorsi degli URL in corso...'):
        model.match(legacy_paths, new_paths)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .800]
        
        join_df = pd.merge(pfuzz_df, legacy_url_parse, left_on='From', right_on='path')
        join_df_2 = pd.merge(join_df, new_url_parse, left_on='To', right_on='path')
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
        url_df = join_df_2[['From', 'To', 'Similarity', 'Percorso Legacy', 'Percorso Nuovo', 'URL Legacy', 'URL Nuovo']]
        url_df = url_df.drop_duplicates()
    return url_df

def slug_match(legacy_slugs, new_slugs, legacy_url_parse, new_url_parse):
    with st.spinner('Analisi degli slug degli URL in corso...'):
        model.match(legacy_slugs, new_slugs)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .800]
        
        join_df = pd.merge(pfuzz_df, legacy_url_parse, left_on='From', right_on='last_dir')
        join_df_2 = pd.merge(join_df, new_url_parse, left_on='To', right_on='last_dir')
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
        slug_df = join_df_2[['From', 'To', 'Similarity', 'Percorso Legacy', 'Percorso Nuovo', 'URL Legacy', 'URL Nuovo']]
        slug_df = slug_df.drop_duplicates()
    return slug_df

def title_match(legacy_titles, new_titles, legacy_crawl, new_crawl):
    with st.spinner('Analisi dei titoli in corso...'):
        model.match(legacy_titles, new_titles)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .700]
        
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='Title 1')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='Title 1').drop_duplicates()
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        title_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        title_df = title_df.drop_duplicates()
    return title_df

def h1_match(legacy_h1, new_h1, legacy_crawl, new_crawl):
    with st.spinner('Analisi degli H1 in corso...'):
        model.match(legacy_h1, new_h1)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .900]
        
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='H1-1')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='H1-1')
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        h1_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        h1_df = h1_df.drop_duplicates()
    return h1_df

def h2_match(legacy_h2, new_h2, legacy_crawl, new_crawl):
    with st.spinner('Analisi degli H2 in corso...'):
        model.match(legacy_h2, new_h2)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .900]
        
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='H2-1')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='H2-1').drop_duplicates()
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        h2_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        h2_df = h2_df.drop_duplicates()
    return h2_df

# Funzione di parsing degli URL
def url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl):
    with st.spinner('Decomposizione degli URL in corso...'):
        url_parse_cols = ['url', 'path', 'last_dir']
        legacy_url_parse = adv.url_to_df(legacy_urls)
        legacy_url_parse = legacy_url_parse[url_parse_cols]
        new_url_parse = adv.url_to_df(new_urls)
        new_url_parse = new_url_parse[url_parse_cols]

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
        url_match(legacy_paths, new_paths, legacy_url_parse, new_url_parse),
        slug_match(legacy_slug, new_slug, legacy_url_parse, new_url_parse),
        title_match(legacy_titles, new_titles, legacy_crawl, new_crawl),
        h1_match(legacy_h1, new_h1, legacy_crawl, new_crawl),
        h2_match(legacy_h2, new_h2, legacy_crawl, new_crawl)
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
    new_file = st.file_uploader('Carica il crawl degli URL NUOVI', type='xlsx', key='new')
    if new_file is not None:
        crawl_files = [legacy_file, new_file]
        analyze_crawls(crawl_files)

# Branding e footer
st.markdown("---")
st.markdown("© 2024 [NUR® Digital Marketing](https://www.nur.it/). Tutti i diritti riservati.")
