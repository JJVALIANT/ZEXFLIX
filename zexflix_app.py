import streamlit as st
import pandas as pd
import gspread # Necesario para la conexión segura
import numpy as np
import re
import datetime # Importamos datetime para obtener la fecha actual

# Constante para la paginación
ITEMS_PER_PAGE = 24

# 1. Configuración de la página
st.set_page_config(
    layout="wide",
    page_title="ZEXFLIX",
    initial_sidebar_state="collapsed"
)

st.title("ZEXFLIX")

# --- LÓGICA DE NAVEGACIÓN POR URL (REESTRUCTURADA) ---

# 1. Leer los parámetros de la URL
query_params = st.query_params

# 2. Revisar si hay un deep link que fuerce la vista de detalle
if "item_index" in query_params:
    try:
        # Intenta convertir el índice a entero. Si falla, el valor es inválido.
        target_index = int(query_params.item_index)
    except ValueError:
        target_index = None # Índice inválido

    if target_index is not None:
        # Si el índice es válido, establecer el estado para mostrar el detalle
        st.session_state.current_page = 'detail'
        st.session_state.selected_index = target_index
    else:
        # Si el índice es inválido, forzar la vista de catálogo
        st.session_state.current_page = 'catalog'
else:
    # Si no hay parámetro item_index, forzar la vista de catálogo
    st.session_state.current_page = 'catalog'

# --- CARGA DE DATOS DESDE GOOGLE SHEETS ---

# Usamos st.cache_data para evitar cargar los datos en cada interacción
@st.cache_data(ttl=3600)
def load_data():
    try:
        # 🟢 MODIFICACIÓN CLAVE: Conexión segura usando Streamlit Secrets
        creds_json = st.secrets["gcp_service_account"]
        # 🐛 CORRECCIÓN DEL ERROR: Se elimina la palabra 'account' repetida.
        gc = gspread.service_account_from_dict(creds_json)
        
        # 🔄 RESTAURANDO LA LÓGICA ORIGINAL (v0.08)
        # ID CORRECTO copiado de tu código original:
        spreadsheet_id = "1d4OatU_u7Obj_BKW4vGov6gIZzivl4N3KsIqUua19Jc" 
        
        # Usamos open_by_key tal cual lo hacías en local
        sh = gc.open_by_key(spreadsheet_id)
        
        # Usamos la primera hoja (índice 0) tal cual lo hacías en local
        # Esto evita errores si la hoja se llama "MAIN " (con espacio) o de otra forma.
        worksheet = sh.get_worksheet(0)

        # 🟢 Extracción segura de datos
        data = worksheet.get_all_values()

        if not data:
            st.error("Error al cargar datos. La hoja parece estar vacía.")
            return pd.DataFrame()
        
        # 2. Separar encabezados y filas de datos
        headers = data[0]
        rows = data[1:]

        # 3. Crear el DataFrame
        df = pd.DataFrame(rows, columns=headers)

        # Configuración de los datos
        df.set_index('index', inplace=True)
        # Se añade un manejo de errores en caso de que la columna 'index' sea nula o no numérica
        try:
            df.index = df.index.astype(int)
        except ValueError:
            st.error("Error de datos: La columna 'index' debe contener solo números enteros válidos.")
            return pd.DataFrame()
            
        df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').fillna(0).astype(int)

        return df

    except Exception as e:
        # Muestra el error de configuración de secretos de forma amigable
        if "gcp_service_account" in str(e):
             st.error("Error de configuración de secretos: Asegúrate de haber copiado el JSON completo de credenciales en los Secrets de Streamlit Cloud bajo la clave 'gcp_service_account'.")
        # Muestra otros errores de carga de datos
        elif "service_account_from_dict" in str(e):
            st.error("Error al cargar datos. Error: Módulo 'gspread' obsoleto. Por favor, actualiza la librería en 'requirements.txt' a gspread>=5.0.0.")
        # ⚠️ Mensaje clave para el error 404/403: Se recuerda al usuario el permiso.
        elif "<Response [404]>" in str(e) or "<Response [403]>" in str(e):
            # 💡 MENSAJE MEJORADO PARA SER MÁS EXPLÍCITO SOBRE LA CUENTA DE SERVICIO
            st.error("Error de acceso (403/404). Confirma que has compartido la hoja de cálculo con la **cuenta de servicio** de Google (el email críptico que termina en **.iam.gserviceaccount.com**) como 'Editor'.")
        else:
            # Mensaje genérico
            st.error(f"Error desconocido al cargar datos. Asegúrate que la hoja de cálculo esté compartida con la cuenta de servicio. Detalles: {e}")
        return pd.DataFrame()


# --- FUNCIONES DE VISTA DE PÁGINA ---

# Función para volver al catálogo
def go_to_catalog():
    st.session_state.current_page = 'catalog'
    st.session_state.page = 1
    # Borrar el item_index de la URL para volver a la URL base
    st.query_params.clear()
    st.rerun()

# Función para cambiar de página
def change_page(page_num):
    st.session_state.page = page_num
    # Forzar la recarga para aplicar el estado de la página
    st.rerun()

# Función para mostrar los detalles de una película/serie
def show_detail_page(df, selected_index):
    # Botón para volver al catálogo
    if st.button("← Volver al Catálogo"):
        go_to_catalog()
        return

    try:
        row = df.loc[selected_index]
    except KeyError:
        st.error("Error: Ítem no encontrado.")
        go_to_catalog()
        st.rerun() # Usamos st.rerun() aquí para forzar la actualización después de un error (KeyError)
        return

    st.markdown(f"## {row['title']} ({row['release_year']})")
    
    # URL de la imagen de ejemplo (usando el índice para variar)
    placeholder_image_url = f"https://placehold.co/1200x600/222222/cccccc?text=ZEXFLIX+-+{row['title']}"

    # Contenedor para la imagen y los metadatos
    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(placeholder_image_url, caption=row['genre'], use_column_width=True)

    with col2:
        st.markdown(f"**Tipo:** {row['type']}")
        st.markdown(f"**Duración:** {row['duration']}")
        st.markdown(f"**Reparto:** {row['cast']}")
        st.markdown(f"**Dirección:** {row['director']}")
        st.markdown(f"**País:** {row['country']}")
        st.markdown(f"**Calificación:** {row['rating']}")
        st.markdown(f"**Fecha Añadida:** {row['date_added']}")
        st.markdown(f"**Descripción:** {row['description']}")
        
        # Muestra el link para compartir
        current_url = st.experimental_get_query_params()
        if "item_index" not in current_url or current_url["item_index"][0] != str(selected_index):
             share_link = f"{st.experimental_get_query_params(base_url=True)}?item_index={selected_index}"
             st.markdown(f"**Link para Compartir:** [Copiar Link]({share_link})")


# Función para mostrar el catálogo completo con paginación
def show_catalog(df):
    
    # 2. Búsqueda y Filtro (Columna 1)
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("Buscar por Título, Director o Reparto", key="search_term")
    with col2:
        # Obtener lista única y ordenada de años de lanzamiento para el filtro
        years = sorted(df['release_year'].unique(), reverse=True)
        # Se añade "Todos" como opción para deshabilitar el filtro
        years.insert(0, "Todos")
        selected_year = st.selectbox("Filtrar por Año", years, index=0)

    # Aplicar filtros
    filtered_df = df.copy()

    # Filtro de búsqueda por texto
    if search_term:
        search_mask = (
            filtered_df['title'].str.contains(search_term, case=False, na=False) |
            filtered_df['director'].str.contains(search_term, case=False, na=False) |
            filtered_df['cast'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    # Filtro por año
    if selected_year != "Todos":
        filtered_df = filtered_df[filtered_df['release_year'] == selected_year]

    # Mostrar mensaje si no hay resultados
    if filtered_df.empty:
        st.warning("No se encontraron resultados para los filtros seleccionados.")
        return

    # --- Lógica de Paginación ---
    
    total_items = len(filtered_df)
    total_pages = int(np.ceil(total_items / ITEMS_PER_PAGE))
    
    # Inicializar estado de página si no existe
    if 'page' not in st.session_state:
        st.session_state.page = 1
    
    # Asegurar que la página actual sea válida
    current_page = st.session_state.page
    if current_page > total_pages:
        current_page = total_pages
        st.session_state.page = total_pages

    # Calcular el rango de índices para la página actual
    start_index = (current_page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    
    # Obtener los datos para la página actual
    page_df = filtered_df.iloc[start_index:end_index]

    # --- Mostrar Elementos ---
    
    # Título y Recuento
    st.markdown(f"### Catálogo ({total_items} resultados)")
    
    # Renderizar el Grid
    cols = st.columns(6)
    for i, (_, row) in enumerate(page_df.iterrows()):
        col = cols[i % 6]
        with col:
            # URL de la imagen de ejemplo (usando el índice para variar)
            placeholder_image_url = f"https://placehold.co/200x300/222222/cccccc?text={row['index']}"
            
            # Usar el índice del DataFrame (la clave principal) para identificar el item
            item_index = row.name
            
            # Crear un botón con la imagen y el título
            st.image(placeholder_image_url, use_column_width=True)
            st.markdown(f"**{row['title']}**")
            
            # Botón de "Ver Detalle"
            if st.button("Ver Detalle", key=f"detail_{item_index}"):
                st.session_state.current_page = 'detail'
                st.session_state.selected_index = item_index
                # Actualizar la URL para el deep link
                st.query_params["item_index"] = str(item_index)
                st.rerun()

    # --- Controles de Paginación ---
    
    st.markdown("---")
    
    pag_col1, pag_col2, pag_col3 = st.columns([1, 3, 1])

    with pag_col1:
        if current_page > 1:
            if st.button("← Anterior"):
                change_page(current_page - 1)

    with pag_col2:
        # Crear un selectbox para ir directamente a la página
        page_options = [f"Página {i} de {total_pages}" for i in range(1, total_pages + 1)]
        selected_option = page_options[current_page - 1]
        
        # Mostrar el selectbox sin permitir cambios si solo hay una página
        if total_pages > 1:
            selected_page_text = st.selectbox(
                "Ir a la página", 
                page_options, 
                index=current_page - 1,
                label_visibility="collapsed"
            )
            # Extraer el número de página de la selección de texto
            # Usamos un regex simple para extraer el número
            match = re.search(r'Página (\d+)', selected_page_text)
            new_page_num = int(match.group(1)) if match else current_page
            
            # Cambiar la página si el usuario seleccionó una diferente
            if new_page_num != current_page:
                change_page(new_page_num)
        else:
            st.markdown(f"<p style='text-align: center;'>Página 1 de 1</p>", unsafe_allow_html=True)
            

    with pag_col3:
        if current_page < total_pages:
            if st.button("Siguiente →"):
                change_page(current_page + 1)
                
    st.markdown("---")
    st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.8em;'>Mostrando ítems {start_index + 1} a {min(end_index, total_items)} de {total_items} en total.</p>", unsafe_allow_html=True)


# --- LÓGICA DE LA APLICACIÓN PRINCIPAL ---

# Inicializar estado de página
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'catalog'
if 'page' not in st.session_state:
    st.session_state.page = 1

# Cargar los datos
df_main = load_data()

# Solo si el DataFrame no está vacío (la carga fue exitosa) se procede
if not df_main.empty:
    if st.session_state.current_page == 'catalog':
        show_catalog(df_main)
    elif st.session_state.current_page == 'detail':
        # Asegurarse de que selected_index exista en el estado de sesión
        if 'selected_index' in st.session_state:
            show_detail_page(df_main, st.session_state.selected_index)
        else:
            # Fallback si el estado es 'detail' pero falta el índice
            st.error("Error: Ítem de detalle no especificado. Volviendo al catálogo.")
            go_to_catalog()
