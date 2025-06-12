import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import re
import io
import csv
import tempfile
from pathlib import Path
import json
import yaml
from report_generator import ReportGenerator

# Importar la nueva clase SurveyMonkeyConverter
from survey_converter import SurveyMonkeyConverter

# Cargar prompts del archivo YAML
def load_prompts():
    try:
        with open('prompts.yaml', 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
        return prompts
    except Exception as e:
        st.error(f"Error al cargar archivo de prompts: {e}")
        return {"analysis_prompt": "", "summary_prompt": ""}

# Inicializar variables de estado de sesión
def init_session_state():
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'df_one_hot' not in st.session_state:
        st.session_state.df_one_hot = None
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'summary_result' not in st.session_state:
        st.session_state.summary_result = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'api_key' not in st.session_state:
        st.session_state.api_key = st.secrets["openai"]["api_key"]
    if 'company_name' not in st.session_state:
        st.session_state.company_name = "ACME"
    if 'execution_costs' not in st.session_state:
        st.session_state.execution_costs = []
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0.0
    if 'report_generator' not in st.session_state:
        st.session_state.report_generator = ReportGenerator(api_key=st.session_state.api_key)

# Funciones de procesamiento de datos
def slugify(text: str, maxlen: int = 1000) -> str:
    """
    Reemplaza caracteres no alfanuméricos por guiones bajos, colapsa repeticiones,
    recorta al tamaño `maxlen`, y asegura que no haya guiones bajos al principio/final.
    """
    # Utilizar el método estático de la clase SurveyMonkeyConverter
    return SurveyMonkeyConverter.slugify(text, maxlen)

def load_surveymonkey_one_hot(csv_path: str) -> pd.DataFrame:
    """
    Lee el CSV crudo de SurveyMonkey y devuelve un DataFrame codificado one-hot.
    Fila 0: texto completo de la pregunta
    Fila 1:   • 'Open-Ended Response'  → pregunta abierta
             • 'Other (please specify)' o similar → one-hot + texto preservado
             • cualquier otra cosa     → etiqueta de opción
    La función preserva las respuestas abiertas como texto y convierte cada
    opción cerrada (elección única o múltiple) en una columna binaria.
    Para opciones "Other (please specify)", crea tanto una columna binaria
    como preserva el texto especificado en una columna separada.
    """
    return SurveyMonkeyConverter.load_surveymonkey_one_hot(csv_path)

def one_hot_df_to_json(df: pd.DataFrame) -> list[list[dict]]:
    """Wrapper: DataFrame completo → lista anidada lista para `json.dump`."""
    return SurveyMonkeyConverter.one_hot_df_to_json(df)

def dataframe_to_csv_string(df: pd.DataFrame) -> str:
    """Convertir un dataframe a string CSV"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def read_csv_as_text() -> str:
    """Leer el archivo CSV subido como texto"""
    if not Path(st.session_state.temp_file_path).exists():
        return ""
    
    with open(st.session_state.temp_file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        lines = ['\t'.join(row) for row in reader]
    return '\n'.join(lines)

def get_total_execution_cost():
    """
    Obtener el costo total de todas las llamadas a la API LLM
    
    Returns:
    - Un DataFrame con información de costos
    - El costo total como float
    """
    # Obtener los costos del report_generator
    if 'report_generator' in st.session_state:
        df_costs, total_cost = st.session_state.report_generator.get_cost_report()
        
        if not df_costs.empty:
            # Formatear columnas
            if 'cost' in df_costs.columns:
                df_costs["cost"] = df_costs["cost"].apply(lambda x: f"${x:.10f}")
            
            # Renombrar columnas para mostrar en la interfaz
            df_costs.columns = ["Fecha/Hora", "Operación", "ID Compañía", "Costo"]
            
            return df_costs, total_cost
    
    # Si no hay datos de costos, devolver un DataFrame vacío
    return pd.DataFrame(columns=["Modelo", "Costo", "Duración (s)", "Fecha/Hora"]), 0.0


# Interfaz de chat
def display_chat_interface():
    """Mostrar la interfaz de chat para interactuar con el LLM"""
    st.subheader("Charla con Analista de Movilidad")
    
    # Crear un contenedor con altura fija y scroll para los mensajes
    chat_container = st.container(height=500)
    
    # Mostrar mensajes existentes dentro del contenedor con scroll
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Hack para hacer scroll automático al final - añadir un div invisible al final
        if st.session_state.messages:
            st.markdown('<div id="end-of-chat"></div>', unsafe_allow_html=True)
            # Script para hacer scroll al final
            st.markdown("""
            <script>
                function scrollToBottom() {
                    var endOfChat = document.getElementById('end-of-chat');
                    if (endOfChat) {
                        endOfChat.scrollIntoView();
                    }
                }
                window.addEventListener('load', scrollToBottom);
            </script>
            """, unsafe_allow_html=True)
    
    # Input del chat - fuera del contenedor con scroll para que permanezca fijo
    if prompt := st.chat_input("Pregunta algo sobre el análisis de movilidad..."):
        # Añadir mensaje del usuario al estado y mostrarlo
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Mostrar respuesta del asistente con spinner
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        # Usar el ReportGenerator para manejar la llamada LLM
                        response, _ = st.session_state.report_generator._call_llm_api(prompt)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Error en la interfaz de chat: {e}")
                        # Botón para reiniciar la conversación
                        if st.button("Reiniciar conversación"):
                            st.session_state.messages = []
                            st.rerun()

# Aplicación principal
def main():
    # Inicializar estado de sesión
    init_session_state()
    
    # Configuración de la app
    st.set_page_config(
        page_title="Categorización de Centro",
        page_icon="🏢",
        layout="wide"
    )
    
    # Título de la app
    st.title("🏢 Categorización de Centro")
    
    # Sección de carga de archivo (organización vertical sin sidebar)
    company_name = st.text_input("Nombre de la Compañía", value=st.session_state.company_name)
    uploaded_file = st.file_uploader("Cargar archivo CSV", type="csv")
    st.session_state.company_name = company_name
    
    if uploaded_file is not None:
        # Botón para procesar con LLM
        if st.button("🧠 Analizar Datos"):
            # Guardar el archivo subido a un archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                tmp.write(uploaded_file.getvalue())
                st.session_state.temp_file_path = tmp.name
            
            # Usar st.status para mostrar el progreso del procesamiento
            with st.status("⏳ Procesando datos y generando análisis...", expanded=True) as status:
                # Procesar con codificación one-hot usando la clase SurveyMonkeyConverter
                st.write("📊 Procesando archivo CSV...")
                st.session_state.df_one_hot = SurveyMonkeyConverter.load_surveymonkey_one_hot(st.session_state.temp_file_path)
                
                st.write("🔄 Convirtiendo datos a formato JSON...")
                json_data = SurveyMonkeyConverter.one_hot_df_to_json(st.session_state.df_one_hot)
                st.session_state.json_data = json_data
                
                # Contar preguntas y respuestas para mensaje de éxito
                if json_data and len(json_data) > 0:
                    total_questions = len(json_data[0]) 
                    total_respondents = len(json_data)
                    st.write(f"✅ Identificadas {total_questions} preguntas de {total_respondents} respuestas de encuesta.")
                else:
                    total_questions = 0
                    total_respondents = 0
                    st.write("❌ No se han encontrado datos en el archivo.")
                
                # Usar el ReportGenerator para generar el análisis
                report_generator = st.session_state.report_generator
                
                st.write("📝 Generando resumen del análisis...")
                # Generar resumen
                summary_content, summary_cost = report_generator.generate_summary(
                    st.session_state.json_data, 
                    st.session_state.company_name
                )
                st.session_state.summary_result = summary_content
                
                st.write("🔍 Verificando la calidad del resumen...")
                # Verificar el resumen
                verification_result, verification_cost = report_generator.verify_summary(
                    st.session_state.json_data,
                    summary_content
                )
                st.session_state.verification_result = verification_result
                
                # Actualizar el estado al completar
                total_cost = summary_cost + verification_cost
                status.update(
                    label=f"✅ Análisis completado. Costo total: ${total_cost:.5f}", 
                    state="complete", 
                    expanded=False
                )
    
    # Mostrar resultados en pestañas
    if hasattr(st.session_state, 'summary_result') and st.session_state.summary_result:
        tab1, tab2, tab3 = st.tabs(["📊 Resultados de Análisis", "📋 Datos JSON", "💬 Interfaz de Chat"])
        
        with tab1:
            # # Resultado del primer prompt (colapsado)
            # with st.expander("📈 Análisis Detallado"):
            #     # Mostrar el análisis
            #     if hasattr(st.session_state, 'analysis_result') and st.session_state.analysis_result:
            #         st.markdown(st.session_state.analysis_result)
                
            #     # Agregar tabla de costos
            #     st.markdown("### 💰 Costos de Llamadas API")
            #     df_costs, total_cost = get_total_execution_cost()
            #     st.dataframe(df_costs)
            
            # Resultado del segundo prompt (visible)
            st.markdown("## 📝 Informe")
            st.markdown(st.session_state.summary_result)
            
            # Mostrar resultado de verificación si está disponible
            st.markdown("## ✅ Verificación")
            if 'verification_result' in st.session_state and st.session_state.verification_result:
                st.markdown(st.session_state.verification_result)
            
        with tab2:
            # Nueva pestaña para visualización de datos JSON
            st.subheader("📋 Respuestas en formato JSON")
            if hasattr(st.session_state, 'json_data') and st.session_state.json_data:
                st.json(st.session_state.json_data)
            else:
                st.info("ℹ️ No hay datos JSON disponibles.")
    
        
        with tab3:
            # Interfaz de chat
            display_chat_interface()
            
if __name__ == "__main__":
    main()