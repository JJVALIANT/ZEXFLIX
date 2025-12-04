import streamlit as st
import pandas as pd
import gspread 
import numpy as np
import re
import datetime 

# Constante para la paginación
ITEMS_PER_PAGE = 24

# 1. Configuración de la página
st.set_page_config(
    layout="wide",
    page_title="ZEXFLIX", 
    initial_sidebar_state="collapsed"
)

# --- CSS para OCULTAR Toolbar y ajustar padding ---
st.markdown("""
<style>
/* 1. OCULTAR LA BARRA DE HERRAMIENTAS SUPERIOR (TOOLBAR/HEADER) */
header {
    visibility: hidden;
    height: 0px !important;
    padding: 0 !important;
}

/* 2. OCULTAR EL MENÚ DE TRES PUNTOS POR SEPARADO */
#MainMenu {
    visibility: hidden;
}

/* 3. Ajustes de padding y margen del contenido principal */
.block-container {
    padding-top: 1.6rem; 
    padding-bottom: 0rem; 
}

/* 4. AJUSTE DE LA IMAGEN DEL LOGO PARA SER RESPONSIVA Y CENTRADA */
.custom-logo-container {
    margin-bottom: 15px; 
    text-align: center; 
}

.custom-logo-container img {
    max-width: 100%; 
    height: auto;    
    max-height: 80px; 
    width: auto;     
    display: block;  
    margin-left: auto;
    margin-right: auto;
}

@media (max-width: 600px) {
    .custom-logo-container img {
        max-height: 60px; 
    }
}
</style>
""", unsafe_allow_html=True)
# --- FIN CSS ---

# 🟢 Renderizar el Logo (Estático)
LOGO_URL = "https://i.imgur.com/4WKV5rd.png"
LOGO_HTML = f"""
<div class="custom-logo-container">
    <img src="{LOGO_URL}" alt="ZEXFLIX Logo">
</div>
"""
st.markdown(LOGO_HTML, unsafe_allow_html=True) 

# --- LÓGICA DE NAVIGACIÓN POR URL ---

# 1. Leer los parámetros de la URL
query_params = st.query_params

# 2. Revisar si hay un deep link que fuerce la vista de detalle
if "item_index" in query_params:
    try:
        target_index = int(query_params["item_index"])
        st.session_state['current_view'] = 'detail'
        st.session_state['selected_item_index'] = target_index
    except ValueError:
        # Si el deep link es malformado, forzamos el catálogo.
        st.session_state['current_view'] = 'catalog'
# 3. Inicializar el estado si es la primera vez que se ejecuta y no hay deep link válido
elif 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'catalog'
    st.session_state['selected_item_index'] = None
    st.session_state['current_page'] = 1 # Inicialización de la página

def go_to_catalog():
    st.session_state['current_view'] = 'catalog'
    st.session_state['selected_item_index'] = None
    st.session_state['current_page'] = 1 # Resetear a la página 1 al volver al catálogo
    # Usamos query_params.clear() para resetear la URL y forzar el recálculo sin usar st.rerun()
    st.query_params.clear() 

# 2. CONEXIÓN SEGURA A GOOGLE SHEETS
@st.cache_data(ttl=3600)
def load_data():
    try:
        # 🟢 MODIFICACIÓN CLAVE: Conexión segura usando Streamlit Secrets
        creds_json = st.secrets["gcp_service_account"]
        
        # 🟢 CORRECCIÓN DE FUNCIÓN: Usamos la función correcta de gspread
        gc = gspread.service_account_from_dict(creds_json)
        
        # ID CORRECTO (Tu ID real)
        spreadsheet_id = "1d4OatU_u7Obj_BKW4vGov6gIZzivl4N3KsIqUua19Jc" 
        sh = gc.open_by_key(spreadsheet_id)
        
        # Seleccionamos la primera hoja (índice 0) para mayor seguridad
        worksheet = sh.get_worksheet(0)
        
        # 🟢 USO DE GET_ALL_VALUES: Más robusto que get_all_records
        data = worksheet.get_all_values()
        
        if not data:
             return pd.DataFrame()

        # Usamos la primera fila como encabezados
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        
        # Lógica original de limpieza de tu código v0.08
        df_clean = df.dropna(how="all").astype(str)
        
        # Verificamos si existe la columna Portada antes de filtrar
        if 'Portada' in df_clean.columns:
            df_with_cover = df_clean[df_clean['Portada'].str.strip() != ""] 
            st.sidebar.caption(f"Películas con Cover: {len(df_with_cover)}")
            return df_with_cover
        else:
            st.error("Error: La columna 'Portada' no se encuentra en la hoja de cálculo.")
            return df_clean

    except Exception as e:
        # [RESTAURADO A SU VERSIÓN ORIGINAL]: Mensaje de error más conciso pero útil
        st.error(f"Error al cargar datos. Error: {e}")
        return pd.DataFrame() 

df = load_data()

# ----------------------------------------------------
# 🟢 FUNCIONES DE VISTAS
# ----------------------------------------------------

def get_youtube_id(url):
    if not url: return None
    m = re.search(r'(?<=v=)[\w-]+|(?<=youtu\.be\/)[\w-]+', url)
    return m.group(0) if m else None

def show_detail_page(df, selected_index):
    try:
        row = df.loc[selected_index]
    except KeyError:
        st.error("Error: Ítem no encontrado.")
        go_to_catalog()
        st.rerun() 
        return

    st.button("⬅️ Volver al Catálogo", on_click=go_to_catalog)
    st.markdown("---")
    
    title_es = row.get('Título en español', 'Sin Título')
    year = row.get('Año', 'N/A')
    maker = row.get('Realizador', 'N/A')
    genre = row.get('Género', 'N/A')
    duration = row.get('Duración', 'N/A') 
    synopsis = row.get('Sinopsis', 'Sin sinopsis disponible.')
    icon_value = row.get('ÍconoMetraje', '')
    country_flag = row.get('Bandera', '')
    scale_value = row.get('Escala', '')
    cover_url = row.get('Portada', '')
    stream_url = row.get('Stream', '#')
    trailer_url = row.get('Trailer', '')
    
    st.title(title_es)
    
    col_img, col_info = st.columns([1, 3])
    
    with col_img:
        MAX_DETAIL_IMAGE_HEIGHT = 450
        with st.container(height=MAX_DETAIL_IMAGE_HEIGHT):
            if cover_url and cover_url != 'nan':
                st.image(cover_url, use_container_width=True)
    
    with col_info:
        st.markdown(f"<p style='color: #FF4B4B; font-size: 1.0em; margin-top: 0; margin-bottom: 0;'>{icon_value} {genre} {country_flag}</p>", unsafe_allow_html=True) 
        st.markdown(f"<h3 style='color: white; margin-top: 0.1em; margin-bottom: 0.1em; font-size: 1.8em; line-height: 1.2;'>{title_es}</h3>", unsafe_allow_html=True) 
        st.markdown(f"<p style='color: #AAA; font-size: 1.0em; margin-top: 0.1em; margin-bottom: 0.5em;'>{year} | {maker}</p>", unsafe_allow_html=True) 
        
        hands_emoji = row.get('Escala', 'N/A')
        try:
            num_hands = int(float(hands_emoji)) 
            hands_emoji = "✋" * num_hands
        except ValueError:
            pass
        st.markdown(f"<p style='color: white; font-size: 1.1em; margin-top: 0.5em; margin-bottom: 1.5em;'>**Escala:** {hands_emoji} | **Duración:** {duration}</p>", unsafe_allow_html=True) 

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Sinopsis")
    st.markdown(synopsis)
    
    if stream_url and stream_url != '#':
        st.markdown(
            f"""
            <a href="{stream_url}" target="_blank" style="text-decoration: none;">
                <button style="
                    background-color: #FF4B4B; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-size: 1.1em; cursor: pointer; margin-top: 20px; margin-bottom: 20px; width: 100%; text-align: center; 
                ">
                    ▶️ VER EN STREAMING
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )
    
    if trailer_url:
        st.subheader("Tráiler")
        youtube_id = get_youtube_id(trailer_url)
        if youtube_id:
            st.video(trailer_url)
        else:
            st.warning(f"El enlace de tráiler ('{trailer_url}') no es un URL de YouTube válido.")
    st.markdown("---")

# Función de sanitización de texto para la búsqueda
def clean_text_for_search(text):
    if pd.isna(text):
        return ""
    # Esta expresión regular permite letras, números y espacios. Elimina la mayoría de los caracteres problemáticos.
    return re.sub(r'[^\w\s]', ' ', str(text)).lower()


def show_catalog(df):
    if df.empty:
        st.warning("No se encontraron películas.")
        return

    # 1. Barajamos los índices del DataFrame (solo una vez por día/usuario)
    if 'shuffled_indices' not in st.session_state:
        # Calculamos la semilla diaria basada en el día ordinal.
        today = datetime.date.today()
        daily_seed = today.toordinal() 
        
        # Usamos la semilla diaria para el barajado.
        st.session_state['shuffled_indices'] = df.sample(frac=1, random_state=daily_seed).index.tolist()
    
    # 2. Creamos el DataFrame base para mostrar (barajado)
    df_display = df.loc[st.session_state['shuffled_indices']] 
    
    # --- Definición de columnas de búsqueda (18 en total) ---
    SEARCH_COLUMNS = [
        'Título original', 'Título en español', 'País', 'Año', 'Metraje', 
        'Sinopsis', 'Grupo', 'Género', 'Orientación', 'Perversiones', 
        'Realizador', 'Libro', 'Estudio', 'Reparto', 'Fotografía', 
        'Música', 'Comentarios', 'Especial'
    ]

    # --- 3. Barra de búsqueda ---
    search_query = st.text_input(
        "🎬 Buscar en el Catálogo (AND Multi-Palabra)",
        placeholder="Escribe palabras clave (ej: Darín AND comedia AND argentina)...",
        key="catalog_search"
    )

    # --- 4. Lógica de Filtrado (solo si hay una consulta) ---
    if search_query:
        # Reinicia la página a 1 si la búsqueda cambia
        if 'last_search_query' not in st.session_state or st.session_state['last_search_query'] != search_query:
            st.session_state['current_page'] = 1
            st.session_state['last_search_query'] = search_query

        # Creamos una copia del DataFrame para el proceso de búsqueda y aplicamos la limpieza
        df_searchable = df_display.copy()
        for col in SEARCH_COLUMNS:
            if col in df_searchable.columns:
                # Aplicamos la función de limpieza a cada columna que se utilizará en la búsqueda
                df_searchable[col] = df_searchable[col].apply(clean_text_for_search)
                
        # Normalizamos la consulta y la dividimos en palabras clave
        keywords = clean_text_for_search(search_query).split()
        
        # Máscara final: Inicialmente True para todas las filas. 
        final_mask = pd.Series([True] * len(df_searchable), index=df_searchable.index)

        # Iteramos sobre cada palabra clave
        for keyword in keywords:
            # Si la palabra clave está vacía después de la limpieza (ej: solo se ingresó puntuación), la ignoramos
            if not keyword:
                continue
                
            # Máscara para la palabra clave actual (OR entre las 18 columnas)
            keyword_mask = pd.Series([False] * len(df_searchable), index=df_searchable.index)
            
            # Combinamos condiciones OR a través de las 18 columnas para la palabra clave actual
            for col in SEARCH_COLUMNS:
                if col in df_searchable.columns:
                    col_contains_keyword = df_searchable[col].str.contains(keyword, regex=False, na=False)
                    keyword_mask = keyword_mask | col_contains_keyword
            
            # Combinamos la máscara de la palabra clave con la máscara final (AND booleano)
            final_mask = final_mask & keyword_mask 
            
        # Aplicamos el filtro combinado al DataFrame ORIGINAL (df_display)
        df_display = df_display[final_mask]
    else:
        # Reinicia la página a 1 si se borra la búsqueda
        if 'last_search_query' in st.session_state and st.session_state['last_search_query']:
             st.session_state['current_page'] = 1
             st.session_state['last_search_query'] = ''


    # --- 5. Lógica de Paginación ---
    
    total_items = len(df_display)
    total_pages = int(np.ceil(total_items / ITEMS_PER_PAGE))
    
    # Aseguramos que la página actual no exceda el límite
    if st.session_state['current_page'] > total_pages and total_pages > 0:
        st.session_state['current_page'] = total_pages
    elif total_pages == 0:
          st.session_state['current_page'] = 1

    current_page = st.session_state['current_page']
    
    # Calcular índices de corte
    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    # Aplicar paginación al DataFrame
    df_paginated = df_display.iloc[start_idx:end_idx]

    # --- 6. Título con recuento ---
    st.subheader(f"Catálogo: {total_items} películas encontradas")
            
    # --- 7. Navegación Superior (Centrada en una línea) ---
    if total_pages > 1:
        # Usamos 3 columnas para alinear los botones a los lados y el texto en el centro
        nav_cols_top = st.columns([1, 1, 1])

        with nav_cols_top[0]:
            if st.button("<< Anterior", key="nav_prev_top", disabled=(current_page == 1), use_container_width=True):
                st.session_state['current_page'] -= 1
                st.rerun()
        
        with nav_cols_top[1]:
            # Centrarmos la información de la página usando HTML
            st.markdown(f"<p style='text-align: center; margin: 0; padding-top: 10px; font-weight: bold;'>Página {current_page} de {total_pages}</p>", unsafe_allow_html=True)

        with nav_cols_top[2]:
            if st.button("Siguiente >>", key="nav_next_top", disabled=(current_page == total_pages), use_container_width=True):
                st.session_state['current_page'] += 1
                st.rerun()

    # --- CSS GLOBAL Y GRID RESPONSIVO (se mantiene el CSS de las tarjetas) ---
    st.markdown("""
    <style>
        .catalog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 20px;
            margin-top: 20px;
            margin-bottom: 30px; 
        }
        
        .catalog-card {
            background-color: transparent;
            border-radius: 8px;
            transition: transform 0.2s;
            display: flex;
            flex-direction: column;
            text-decoration: none !important;
            color: inherit !important;
            height: 100%; 
        }
        
        .catalog-card:hover {
            transform: scale(1.03);
        }
        
        .catalog-img-container {
            width: 100%;
            height: 350px; 
            background-color: #0e1117;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 8px;
            position: relative;
        }
        
        .catalog-img-container img {
            width: 100%;
            height: 100%;
            object-fit: cover; 
        }
        
        .catalog-text h3 {
            color: white !important;
            margin: 0 0 2px 0 !important;
            font-size: 1.1em !important; 
            font-weight: 800 !important; 
            line-height: 1.1 !important;
            
            /* Limitar líneas del título */
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .catalog-text p {
            margin: 0px 0 1px 0 !important;
            line-height: 1.2 !important;
            white-space: nowrap; 
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        a.catalog-link {
            text-decoration: none;
            color: inherit;
            display: block; 
        }
        a.catalog-link:hover {
            text-decoration: none;
            color: inherit;
            color: #FF4B4B; 
        }

        /* AJUSTE PARA MÓVILES: Forzar 2 columnas simétricas */
        @media (max-width: 600px) {
            .catalog-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                gap: 10px !important; 
            }
            .catalog-img-container {
                height: auto !important; 
                aspect-ratio: 2/3 !important; 
            }
            .catalog-text h3 {
                font-size: 0.9em !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- GENERACIÓN DEL HTML DEL CATÁLOGO (usa df_paginated) ---
    cards_html = ""
    
    for index, row in df_paginated.iterrows(): # Usamos df_paginated
        cover_url = row.get('Portada', '')
        
        if cover_url and cover_url != 'nan':
            genre = row.get('Género', 'N/A')
            country_flag = row.get('Bandera', '')
            icon_value = row.get('ÍconoMetraje', '')
            title = row.get('Título en español', 'Sin Título')
            year = row.get('Año', 'N/A')
            maker = row.get('Realizador', 'N/A')
            
            scale_value = row.get('Escala', '')
            duration = row.get('Duración', 'N/A')
            hands_emoji = ""
            if scale_value:
                try:
                    num_hands = int(float(scale_value)) 
                    hands_emoji = "✋" * num_hands
                except ValueError:
                    hands_emoji = scale_value

            link_url = f"?item_index={index}"

            # Construimos la tarjeta HTML en una sola línea para evitar problemas de parsing
            card = f'<a href="{link_url}" target="_self" class="catalog-link"><div class="catalog-card"><div class="catalog-img-container"><img src="{cover_url}" loading="lazy"></div><div class="catalog-text"><p style="color: #FF4B4B; font-size: 0.8em; text-transform: uppercase;">{icon_value} {genre} {country_flag}</p><h3>{title}</h3><p style="color: #AAAAAA; font-size: 0.9em;">{year} | {maker}</p><p style="font-size: 1.0em; color: white;">{hands_emoji} <span style="font-size: 0.8em; color: #888;">| {duration}</span></p></div></div></a>'
            
            cards_html += card

    # Renderizamos todo el grid
    st.markdown(f'<div class="catalog-grid">{cards_html}</div>', unsafe_allow_html=True)


    # --- 8. Navegación Inferior (Centrada en una línea) ---
    if total_pages > 1:
        st.markdown("---")
        # Usamos 3 columnas para alinear los botones a los lados y el texto en el centro
        nav_cols_bottom = st.columns([1, 1, 1])
        
        with nav_cols_bottom[0]:
            if st.button("<< Anterior", key="nav_prev_bottom", disabled=(current_page == 1), use_container_width=True):
                st.session_state['current_page'] -= 1
                st.rerun()

        with nav_cols_bottom[1]:
            # Centrarmos la información de la página usando HTML
            st.markdown(f"<p style='text-align: center; margin: 0; padding-top: 10px; font-weight: bold;'>Página {current_page} de {total_pages}</p>", unsafe_allow_html=True)


        with nav_cols_bottom[2]:
            if st.button("Siguiente >>", key="nav_next_bottom", disabled=(current_page == total_pages), use_container_width=True):
                st.session_state['current_page'] += 1
                st.rerun()
                
# ----------------------------------------------------
# 🟢 FLUJO PRINCIPAL
# ----------------------------------------------------

st.sidebar.markdown("# Opciones de Filtrado")
st.sidebar.markdown("Puedes añadir filtros aquí, como por género o año.")
st.sidebar.markdown("---")
st.sidebar.caption("Aplicación Zexflix v0.10")


if not df.empty:
    if st.session_state['current_view'] == 'catalog':
        show_catalog(df)
    elif st.session_state['current_view'] == 'detail':
        show_detail_page(df, st.session_state['selected_item_index'])
