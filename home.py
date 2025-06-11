import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Encuestas PTT",
    page_icon="📊",
    layout="wide"
)

# Contenido de la página principal
st.title("Herramientas de Análisis de Encuestas PTT")

st.markdown("""
## Bienvenido a la plataforma de análisis de encuestas de movilidad

Esta herramienta permite procesar y analizar datos de encuestas relacionadas con movilidad 
y transporte para generar información valiosa para la planificación urbana.

### Funcionalidades disponibles:

**Navegue por el menú lateral para acceder a las herramientas:**

* **Categorización de Centro** - Analiza respuestas para clasificar centros según sus características
* **Análisis de Demanda de Movilidad** - Procesa encuestas de movilidad

""")


# Pie de página
st.markdown("---")
st.markdown("© Ciclogreen - Herramientas de Análisis PTT")
