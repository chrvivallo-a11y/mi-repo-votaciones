import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Monitor de Votaciones - Cámara de Diputados", layout="wide")
st.title("🏛️ Monitor de Votaciones - Cámara de Diputadas y Diputados")
st.markdown("Este panel lee los datos automáticamente desde el motor de extracción en GitHub.")

# 2. Carga de datos (con caché para que sea ultra rápido)
@st.cache_data
def cargar_datos():
    # Aquí debes poner el enlace "Raw" de tu archivo en GitHub
    # Ejemplo: url = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/resultados_votaciones.txt"
    # Por ahora, leerá el archivo local si lo estás probando en tu computador:
    url = "resultados_votaciones.txt" 
    
    try:
        df = pd.read_csv(url, sep='\t')
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # 3. Barra lateral para filtros interactivos
    st.sidebar.header("Filtros de Búsqueda")
    
    # Filtro por Proyecto de Ley
    lista_proyectos = df['Proyecto De Ley'].unique()
    proyecto_seleccionado = st.sidebar.selectbox("Selecciona un Proyecto de Ley:", ["Todos"] + list(lista_proyectos))
    
    # Filtro por Diputado
    lista_diputados = sorted(df['Votante'].unique())
    diputado_seleccionado = st.sidebar.selectbox("Busca un Diputado/a:", ["Todos"] + lista_diputados)

    # Aplicar los filtros al DataFrame
    df_filtrado = df.copy()
    if proyecto_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Proyecto De Ley'] == proyecto_seleccionado]
    if diputado_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Votante'] == diputado_seleccionado]

    # 4. Métricas Rápidas (Tarjetas superiores)
    st.markdown("### Resumen de Votos")
    col1, col2, col3, col4 = st.columns(4)
    
    votos_a_favor = len(df_filtrado[df_filtrado['Voto_Emitido'] == 'A Favor'])
    votos_en_contra = len(df_filtrado[df_filtrado['Voto_Emitido'] == 'En Contra'])
    abstenciones = len(df_filtrado[df_filtrado['Voto_Emitido'] == 'Abstención'])
    pareos = len(df_filtrado[df_filtrado['Voto_Emitido'] == 'Pareo'])
    
    col1.metric("🟢 A Favor", votos_a_favor)
    col2.metric("🔴 En Contra", votos_en_contra)
    col3.metric("⚪ Abstenciones", abstenciones)
    col4.metric("🟡 Pareos", pareos)

    st.markdown("---")

    # 5. Gráficos y Tablas
    col_grafico, col_tabla = st.columns([1, 1])

    with col_grafico:
        st.markdown("### Distribución de Votos")
        # Agrupamos los datos para el gráfico
        conteo_votos = df_filtrado['Voto_Emitido'].value_counts().reset_index()
        conteo_votos.columns = ['Tipo de Voto', 'Cantidad']
        
        # Gráfico de torta interactivo con Plotly
        fig = px.pie(
            conteo_votos, 
            values='Cantidad', 
            names='Tipo de Voto', 
            color='Tipo de Voto',
            color_discrete_map={
                'A Favor': '#2ecc71',
                'En Contra': '#e74c3c',
                'Abstención': '#bdc3c7',
                'Pareo': '#f1c40f'
            },
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_tabla:
        st.markdown("### Detalle Individual")
        # Mostramos una tabla limpia con los votantes
        tabla_limpia = df_filtrado[['Votante', 'Voto_Emitido', 'Materia', 'Resultado']]
        st.dataframe(tabla_limpia, use_container_width=True, hide_index=True)

else:
    st.warning("No se encontraron datos. Verifica que el motor de GitHub haya guardado el archivo 'resultados_votaciones.txt'.")
