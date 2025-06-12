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

Estas herramientas permiten procesar y analizar datos de encuestas para plannes de 
transporte y movilidad al trabajo.

### Funcionalidades disponibles:

**Navegue por el menú lateral para acceder a las herramientas:**

* **Categorización de Centro** - Procesa encuestas de movilidad de gestores
* **Análisis de Demanda de Movilidad** - Procesa encuestas de movilidad de empleados

""")


# Pie de página
st.markdown("---")
st.markdown("© Ciclogreen - Herramientas de Análisis PTT")
