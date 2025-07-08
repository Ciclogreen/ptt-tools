import streamlit as st
import pandas as pd
import os
import tempfile
from survey_converter import SurveyMonkeyConverter
import database
from survey_analytics import SurveyAnalytics
import json
from report_generator import ReportGenerator

def init_session_state():
    """Inicializar variables de estado de la sesión"""
    if 'json_data' not in st.session_state:
        st.session_state.json_data = None
    
    if 'company_name' not in st.session_state:
        st.session_state.company_name = ""
    
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
        
    if 'total_employees' not in st.session_state:
        st.session_state.total_employees = 600
    
    # Inicializar conexión Supabase
    if 'supabase' not in st.session_state:
        st.session_state.supabase = database.init_supabase()
        
    # Inicializar informe generado
    if 'mobility_report' not in st.session_state:
        st.session_state.mobility_report = None
        
    # Inicializar resultado de verificación
    if 'mobility_verification_result' not in st.session_state:
        st.session_state.mobility_verification_result = None

# Función para realizar análisis (código común entre ambos botones)
def perform_analysis(company_name, total_employees, company_id, supabase, status, json_data=None):
    """
    Función común para realizar el análisis de datos.
    
    Args:
        company_name: Nombre de la compañía
        total_employees: Número total de empleados
        company_id: ID de la compañía en la base de datos
        supabase: Cliente Supabase
        status: Objeto de estado de streamlit
        json_data: Datos JSON (opcional, solo cuando se cargan desde CSV)
        
    Returns:
        Tupla (éxito, resultados de análisis, costo)
    """
    # Lista para almacenar los resultados
    analysis_results = []
    
    try:
        # Iniciar el análisis
        analytics = SurveyAnalytics(supabase, company_id)
        
        # Realizar todos los cálculos
        st.write("📊 Calculando tasas de participación...")
        participation_rate = analytics.calculate_participation_rate(total_employees)
        analysis_results.append(participation_rate)
        
        st.write("👥 Analizando datos demográficos...")
        gender_distribution = analytics.calculate_gender_distribution()
        postal_code_distribution = analytics.calculate_postal_code_distribution()
        age_distribution = analytics.calculate_age_distribution()
        department_distribution = analytics.calculate_department_distribution()
        analysis_results.extend([gender_distribution, postal_code_distribution, age_distribution, department_distribution])
        
        st.write("🕰️ Analizando patrones de trabajo...")
        workday_distribution = analytics.calculate_workday_type_distribution()
        workdays_distribution = analytics.calculate_workdays_distribution()
        telework_distribution = analytics.calculate_telework_distribution()
        analysis_results.extend([workday_distribution, workdays_distribution, telework_distribution])
        
        st.write("🚗 Analizando modos de transporte...")
        transport_mode_distribution = analytics.calculate_transport_mode_distribution()
        multimodal_workers_percentage = analytics.calculate_multimodal_workers_percentage()
        transport_combinations = analytics.calculate_transport_combination_distribution()
        distance_range_distribution = analytics.calculate_distance_range_distribution()
        travel_time_distribution = analytics.calculate_travel_time_distribution()
        analysis_results.extend([
            transport_mode_distribution, 
            multimodal_workers_percentage,
            transport_combinations,
            distance_range_distribution,
            travel_time_distribution
        ])
        
        st.write("🚙 Analizando desplazamientos y vehículos...")
        business_trips_percentage = analytics.calculate_business_trips_percentage()
        business_trips_own_car_percentage = analytics.calculate_business_trips_own_car_percentage()
        engine_type_percentage = analytics.calculate_engine_type_percentage()
        car_occupancy_distribution = analytics.calculate_car_occupancy_distribution()
        ev_purchase_intention_percentage = analytics.calculate_ev_purchase_intention_percentage()
        work_trip_frequency_distribution = analytics.calculate_work_trip_frequency_distribution()
        main_transport_mode_during_work_distribution = analytics.calculate_main_transport_mode_during_work_distribution()
        average_trip_distance_during_work = analytics.calculate_average_trip_distance()
        work_trip_reason_distribution = analytics.calculate_work_trip_reason_distribution()
        replaceable_trip_distribution = analytics.calculate_replaceable_trips_distribution()
        cycling_barriers_percentage = analytics.calculate_cycling_barriers_percentage()
        analysis_results.extend([
            business_trips_percentage,
            business_trips_own_car_percentage,
            engine_type_percentage,
            car_occupancy_distribution,
            ev_purchase_intention_percentage,    
            work_trip_frequency_distribution,
            main_transport_mode_during_work_distribution,
            average_trip_distance_during_work,
            work_trip_reason_distribution,
            replaceable_trip_distribution,      
            cycling_barriers_percentage
        ])
        
        st.write("🅿️ Analizando aparcamiento...")
        free_parking_percentage = analytics.calculate_free_parking_percentage()
        no_parking_problems_percentage = analytics.calculate_no_parking_problems_percentage()
        analysis_results.extend([free_parking_percentage, no_parking_problems_percentage])
        
        st.write("🚌 Analizando transporte público...")
        public_transport_barriers_percentage = analytics.calculate_public_transport_barriers_percentage()
        public_transport_time_distribution = analytics.calculate_public_transport_estimated_time_distribution()
        public_transport_motivations_percentage = analytics.calculate_public_transport_motivations_percentage()
        public_transport_lines_awareness_percentage = analytics.calculate_public_transport_lines_awareness_percentage()
        public_transport_improvement_factors_percentage = analytics.calculate_public_transport_improvement_factors_percentage()
        public_transport_satisfaction = analytics.calculate_public_transport_satisfaction_distribution()
        analysis_results.extend([
            public_transport_barriers_percentage,
            public_transport_time_distribution,
            public_transport_motivations_percentage,
            public_transport_lines_awareness_percentage,
            public_transport_improvement_factors_percentage,
            public_transport_satisfaction
        ])


        st.write("🚲 Analizando compartir coche y ciclismo...")
        car_sharing_willingness_percentage = analytics.calculate_car_sharing_willingness_percentage()
        cycling_routes_awareness_percentage = analytics.calculate_cycling_routes_awareness_percentage()
        cycling_improvement_factors_percentage = analytics.calculate_cycling_improvement_factors_percentage()
        pedestrian_environment_rating = analytics.calculate_pedestrian_environment_rating()
        open_proposals_for_mobility = analytics.analyze_open_proposals_for_mobility(ReportGenerator(model="openai/gpt-4o-mini"))
        analysis_results.extend([
            car_sharing_willingness_percentage,
            cycling_routes_awareness_percentage,
            cycling_improvement_factors_percentage,
            pedestrian_environment_rating,
            open_proposals_for_mobility
        ])
        
        # Generar informe automáticamente
        st.write("📝 Generando informe de movilidad...")
        generator = ReportGenerator()
        report, cost = generator.generate_mobility_report(analysis_results, company_name)
        
        if report:
            st.session_state.mobility_report = report
            
            # Verificar la calidad del informe
            st.write("🔍 Verificando la calidad del informe...")
            verification_result, verification_cost = generator.verify_mobility_report(
                analysis_results,
                report
            )
            st.session_state.mobility_verification_result = verification_result
            
            # Actualizar costo total
            total_cost = cost + verification_cost
            status.update(label=f"✅ Análisis completado. Costo total: ${total_cost:.5f}", state="complete", expanded=False)
            return True, analysis_results, total_cost
        else:
            status.update(label="❌ Error al generar informe", state="error")
            return False, None, 0
            
    except Exception as e:
        status.update(label=f"❌ Error en el análisis: {str(e)}", state="error")
        return False, None, 0


def main():
    
    st.set_page_config(
        page_title="Demanda de Movilidad",
        page_icon="🚗",
        layout="wide"
    )

    st.title("🚗 Demanda de Movilidad")
    
    # Organización vertical de elementos (sin sidebar como prefiere el usuario)
    col1, col2 = st.columns(2)
    
    with col1:
        # Input para el nombre de la compañía
        company_name = st.text_input("Nombre de la compañía", 
                                     value=st.session_state.company_name or "imm",
                                     key="company_input")
        
    with col2:
        # Input para el número total de empleados
        total_employees = st.number_input("Total de empleados", 
                                         value=st.session_state.total_employees,
                                         min_value=1,
                                         key="employees_input")
        
    # Selector de archivo CSV (mantenerlo en la columna principal)
    uploaded_file = st.file_uploader("Cargar archivo CSV de encuesta", type=['csv'])
    
    col4, col5 = st.columns(2)
    with col4:
        # Botón para procesar CSV
        process_button = st.button("🧠 Procesar y generar informe", disabled=not (uploaded_file and company_name))
    
    with col5:
        # Botón para analizar datos existentes
        analyze_button = st.button("📊 Generar informe con datos existentes", disabled=not company_name)
    
    # Actualizar variables de sesión
    st.session_state.company_name = company_name
    st.session_state.total_employees = total_employees
    
    supabase = st.session_state.supabase
    status_container = st.container()
    
    if process_button and uploaded_file and company_name:
        # Ruta 1: Procesar nuevo CSV y generar informe
        success = False
        with status_container.status("⏳ Procesando datos y generando informe...", expanded=True) as status:
            st.write("📊 Cargando datos de encuesta...")
            
            # Obtener o crear compañía
            company_id = database.get_company_id(supabase, company_name)
            
            # Verificar si ya existen datos para esta compañía
            data_exists = database.check_company_data_exists(supabase, company_id)

            if data_exists:
                # Eliminar datos existentes
                st.write(f"🗑️ Se encontraron datos anteriores para '{company_name}'. Eliminando...")
                success, message = database.delete_company_data(supabase, company_name)
                if not success:
                    status.update(label=f"❌ Error al eliminar datos existentes: {message}", state="error")
                    st.stop()
                st.write("✅ Datos anteriores eliminados correctamente.")
            
            # Guardar temporalmente el archivo cargado
            st.write("🔄 Convirtiendo datos de CSV a formato estructurado...")
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Convertir CSV a JSON
            converter = SurveyMonkeyConverter()
            survey_df = converter.load_surveymonkey_one_hot(temp_path)
            json_data = converter.one_hot_df_to_json(survey_df)
            
            st.write(f"✅ Conversión completada: {len(json_data)} respuestas procesadas")
            
            # Limpiar archivos temporales
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            st.write("💾 Guardando datos en la base de datos...")
            
            # Guardar datos de encuestas
            success, message = database.save_survey_data_batch(supabase, json_data, company_id)
            
            if not success:
                status.update(label=f"❌ Error al guardar datos: {message}", state="error")
                st.stop()
            
            # Realizar análisis con las fórmulas implementadas
            st.write("📈 Calculando análisis de demanda de movilidad...")
            
            # Llamar a la función común de análisis
            success, analysis_results, cost = perform_analysis(company_name, total_employees, company_id, supabase, status, json_data)
            
            if success:
                st.session_state.json_data = json_data
                st.session_state.analysis_results = analysis_results
        
        # Mostrar resultados FUERA del bloque status
        if success:
            display_results_in_tabs(analysis_results)
    
    elif analyze_button and company_name:
        # Ruta 2: Analizar datos existentes
        success = False
        with status_container.status("⏳ Analizando datos existentes...", expanded=True) as status:
            # Obtener ID de la compañía
            st.write("🔍 Verificando datos de compañía...")
            company_id = database.get_company_id(supabase, company_name, create_if_not_exists=False)
            
            if not company_id:
                status.update(label=f"❌ No se encontró la compañía '{company_name}'.", state="error")
                st.stop()
            
            # Verificar si existen datos
            data_exists = database.check_company_data_exists(supabase, company_id)
            
            if not data_exists:
                status.update(label=f"❌ No hay datos para la compañía '{company_name}'.", state="error")
                st.stop()
            
            # Llamar a la función común de análisis
            success, analysis_results, cost = perform_analysis(company_name, total_employees, company_id, supabase, status)
            
            if success:
                st.session_state.analysis_results = analysis_results
        
        # Mostrar resultados FUERA del bloque status
        if success:
            display_results_in_tabs(analysis_results)
    
    # Mostrar resultados si existen en la sesión y no se está procesando nuevo análisis
    elif 'analysis_results' in st.session_state and st.session_state.analysis_results and 'mobility_report' in st.session_state:
        display_results_in_tabs(st.session_state.analysis_results)


def display_results_in_tabs(analysis_results):
    """Muestra los resultados del análisis en pestañas"""
    if not analysis_results or 'mobility_report' not in st.session_state:
        st.warning("⚠️ No hay resultados disponibles para mostrar.")
        return
        
    # Crear pestañas
    tab1, tab2 = st.tabs(["📝 Informe Generado", "📊 Datos en JSON"])
    
    # Pestaña 1: Informe generado
    with tab1:
        st.markdown(st.session_state.mobility_report)
        
        # Mostrar resultado de verificación si está disponible
        st.markdown("## ✅ Verificación")
        if 'mobility_verification_result' in st.session_state and st.session_state.mobility_verification_result:
            st.markdown(st.session_state.mobility_verification_result)
    
    # Pestaña 2: JSON de resultados
    with tab2:
        st.json(analysis_results)


def generate_mobility_report(analysis_results, company_name):
    """
    Genera un informe narrativo basado en los resultados del análisis utilizando LLM
    """
    if not analysis_results:
        st.error("❌ No hay resultados de análisis disponibles para generar el informe.")
        return None
        
    try:
        with st.status("⏳ Generando informe de movilidad...") as status:
            # Inicializar el generador de informes
            generator = ReportGenerator()
            
            # Generar el informe (la API key se tomará automáticamente de st.secrets)
            report, cost = generator.generate_mobility_report(analysis_results, company_name)
            
            # Mostrar información sobre el costo
            status.update(
                label=f"✅ Informe generado. Costo total: ${cost:.5f}", 
                state="complete", 
                expanded=False
            )
            
            return report
            
    except Exception as e:
        st.error(f"❌ Error al generar informe: {e}")
        return None


if __name__ == "__main__":
    init_session_state()
    main()