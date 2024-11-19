import advertools as adv
import pandas as pd
import streamlit as st
import time
from openpyxl import load_workbook
from polyfuzz import PolyFuzz
from polyfuzz.models import RapidFuzz

# Inizializzazione del matcher con ID specifico per evitare warning
matcher = RapidFuzz(n_jobs=1, score_cutoff=0.80)
model = PolyFuzz(matcher, model_id="rapidfuzz_matcher")

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Redirect URL Mapper • NUR® Digital Marketing", page_icon="./Nur-simbolo-1080x1080.png")
st.image("./logo_nur_vettoriale.svg", width=100)
st.markdown("# Redirect URL Mapper")
st.markdown("Strumento per la mappatura automatica dei reindirizzamenti...")

# Definizione delle colonne necessarie per il crawl
crawl_columns = ['Address', 'Title 1', 'H1-1', 'H2-1']
input_files = []

def analyze_crawls(crawls):
    """Analizza i file di crawl e prepara i DataFrame"""
    with st.spinner('Elaborazione dei crawl del sito in corso...'):
        progress_bar = st.progress(0)
        
        # Caricamento dei file Excel
        for crawl_index, crawl in enumerate(crawls):
            wb = load_workbook(filename=crawl)
            sheet_name = wb.sheetnames
            input_files.append([crawl, sheet_name])
            progress_bar.progress((crawl_index + 1) / len(crawls))
            time.sleep(0.01)

        # Lettura dei DataFrame con solo le colonne necessarie
        legacy_crawl = pd.read_excel(input_files[0][0], sheet_name=input_files[0][1][0])
        legacy_crawl = legacy_crawl[crawl_columns]
        new_crawl = pd.read_excel(input_files[1][0], sheet_name=input_files[1][1][0])
        new_crawl = new_crawl[crawl_columns]
        
        legacy_urls = legacy_crawl['Address'].tolist()
        new_urls = new_crawl['Address'].tolist()
        
    url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl)

def url_match(legacy_paths, new_paths, legacy_url_parse, new_url_parse):
    """Match basato sui percorsi URL completi"""
    with st.spinner('Analisi dei percorsi degli URL in corso...'):
        # Creazione DataFrame con tutti gli URL legacy
        all_urls_df = legacy_url_parse[['url', 'path']].copy()
        all_urls_df.rename(columns={'url': 'URL Legacy', 'path': 'Percorso Legacy'}, inplace=True)
        
        # Matching con PolyFuzz
        model.match(legacy_paths, new_paths)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .800]
        
        # Join per mantenere tutti gli URL legacy
        join_df = pd.merge(pfuzz_df, legacy_url_parse, left_on='From', right_on='path', how='right')
        join_df_2 = pd.merge(join_df, new_url_parse, left_on='To', right_on='path', how='left')
        
        # Pulizia e formattazione del DataFrame risultante
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
            
        url_df = join_df_2[['From', 'To', 'Similarity', 'Percorso Legacy', 'Percorso Nuovo', 'URL Legacy', 'URL Nuovo']]
        url_df = url_df.drop_duplicates()
        
        # Indicatore di match trovato
        url_df['Match Trovato'] = url_df['URL Nuovo'].notna()
        
    return url_df

def slug_match(legacy_slugs, new_slugs, legacy_url_parse, new_url_parse):
    """Match basato sugli slug degli URL"""
    with st.spinner('Analisi degli slug degli URL in corso...'):
        # Matching con PolyFuzz
        model.match(legacy_slugs, new_slugs)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .800]
        
        # Join per mantenere tutti gli URL legacy
        join_df = pd.merge(pfuzz_df, legacy_url_parse, left_on='From', right_on='last_dir', how='right')
        join_df_2 = pd.merge(join_df, new_url_parse, left_on='To', right_on='last_dir', how='left')
        
        # Pulizia e formattazione
        join_df_2.rename(
            columns={'url_x': 'URL Legacy', 'url_y': 'URL Nuovo', 'path_x': 'Percorso Legacy', 'path_y': 'Percorso Nuovo'},
            inplace=True)
            
        slug_df = join_df_2[['From', 'To', 'Similarity', 'Percorso Legacy', 'Percorso Nuovo', 'URL Legacy', 'URL Nuovo']]
        slug_df = slug_df.drop_duplicates()
        
        # Indicatore di match trovato
        slug_df['Match Trovato'] = slug_df['URL Nuovo'].notna()
        
    return slug_df

def title_match(legacy_titles, new_titles, legacy_crawl, new_crawl):
    """Match basato sui titoli delle pagine"""
    with st.spinner('Analisi dei titoli in corso...'):
        # Matching con PolyFuzz
        model.match(legacy_titles, new_titles)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .700]
        
        # Join per mantenere tutti gli URL legacy
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='Title 1', how='right')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='Title 1', how='left')
        
        # Pulizia e formattazione
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        title_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        title_df = title_df.drop_duplicates()
        
        # Indicatore di match trovato
        title_df['Match Trovato'] = title_df['URL Nuovo'].notna()
        
    return title_df

def h1_match(legacy_h1, new_h1, legacy_crawl, new_crawl):
    """Match basato sui tag H1"""
    with st.spinner('Analisi degli H1 in corso...'):
        # Matching con PolyFuzz
        model.match(legacy_h1, new_h1)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .900]
        
        # Join per mantenere tutti gli URL legacy
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='H1-1', how='right')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='H1-1', how='left')
        
        # Pulizia e formattazione
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        h1_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        h1_df = h1_df.drop_duplicates()
        
        # Indicatore di match trovato
        h1_df['Match Trovato'] = h1_df['URL Nuovo'].notna()
        
    return h1_df

def h2_match(legacy_h2, new_h2, legacy_crawl, new_crawl):
    """Match basato sui tag H2"""
    with st.spinner('Analisi degli H2 in corso...'):
        # Matching con PolyFuzz
        model.match(legacy_h2, new_h2)
        pfuzz_df = model.get_matches()
        pfuzz_df["Similarity"] = pfuzz_df["Similarity"].round(3)
        pfuzz_df = pfuzz_df.sort_values('Similarity', ascending=False)
        pfuzz_df = pfuzz_df[pfuzz_df['Similarity'] >= .900]
        
        # Join per mantenere tutti gli URL legacy
        join_df = pd.merge(pfuzz_df, legacy_crawl, left_on='From', right_on='H2-1', how='right')
        join_df_2 = pd.merge(join_df, new_crawl, left_on='To', right_on='H2-1', how='left')
        
        # Pulizia e formattazione
        join_df_2.rename(columns={'Address_x': 'URL Legacy', 'Address_y': 'URL Nuovo'}, inplace=True)
        h2_df = join_df_2[['From', 'To', 'Similarity', 'URL Legacy', 'URL Nuovo']]
        h2_df = h2_df.drop_duplicates()
        
        # Indicatore di match trovato
        h2_df['Match Trovato'] = h2_df['URL Nuovo'].notna()
        
    return h2_df

def url_parse(legacy_urls, legacy_crawl, new_urls, new_crawl):
    """Analisi e decomposizione degli URL"""
    with st.spinner('Decomposizione degli URL in corso...'):
        # Estrazione componenti URL
        url_parse_cols = ['url', 'path', 'last_dir']
        legacy_url_parse = adv.url_to_df(legacy_urls)
        legacy_url_parse = legacy_url_parse[url_parse_cols]
        new_url_parse = adv.url_to_df(new_urls)
        new_url_parse = new_url_parse[url_parse_cols]

        # Preparazione liste per il matching
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

    # Esecuzione di tutti i match
    match_dfs = [
        url_match(legacy_paths, new_paths, legacy_url_parse, new_url_parse),
        slug_match(legacy_slug, new_slug, legacy_url_parse, new_url_parse),
        title_match(legacy_titles, new_titles, legacy_crawl, new_crawl),
        h1_match(legacy_h1, new_h1, legacy_crawl, new_crawl),
        h2_match(legacy_h2, new_h2, legacy_crawl, new_crawl)
    ]
    
    export_dfs(match_dfs)

def export_dfs(match_dfs):
    """Esportazione e visualizzazione dei risultati"""
    sheet_names = ['URL Match', 'Slug Match', 'Title Match', 'H1 Match', 'H2 Match']
    
    # Selettore a schede per la visualizzazione
    selected_sheet = st.selectbox("Seleziona il match da visualizzare", sheet_names)
    sheet_index = sheet_names.index(selected_sheet)
    
    # Mostra statistiche dei match
    total_urls = len(match_dfs[sheet_index])
    matched_urls = match_dfs[sheet_index]['Match Trovato'].sum()
    st.write(f"URLs totali: {total_urls}")
    st.write(f"URLs matchati: {matched_urls}")
    st.write(f"Percentuale di match: {(matched_urls/total_urls*100):.2f}%")
    
    # Visualizzazione DataFrame
    st.dataframe(match_dfs[sheet_index])

    # Esportazione Excel
    with pd.ExcelWriter('mappatura_url.xlsx') as writer:
        for df, sheet_name in zip(match_dfs, sheet_names):
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Pulsante download
    with open("mappatura_url.xlsx", "rb") as file:
        st.download_button(
            label='Scarica l\'analisi del match',
            data=file,
            file_name='mappatura_url.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# Caricamento file e avvio analisi
legacy_file = st.file_uploader('Carica il file degli ***URLs attualmente live***', type='xlsx', key='legacy')
if legacy_file is not None:
    new_file = st.file_uploader('Carica il file degli ***URLs staging***', type='xlsx', key='new')
    if new_file is not None:
        crawl_files = [legacy_file, new_file]
        analyze_crawls(crawl_files)

# Footer
st.markdown("---")
st.markdown("© 2024 [NUR® Digital Marketing](https://www.nur.it/). Tutti i diritti riservati.")
