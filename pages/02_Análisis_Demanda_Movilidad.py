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
        st.session_state.total_employees = 100
    
    # Inicializar conexión Supabase
    if 'supabase' not in st.session_state:
        st.session_state.supabase = database.init_supabase()
        
    # Inicializar informe generado
    if 'mobility_report' not in st.session_state:
        st.session_state.mobility_report = None

# Procesar archivo CSV y convertir a JSON
def process_survey_data(uploaded_file, company_name, total_employees, status_container):
    try:
        with status_container.status("Procesando solicitud...") as status:
            supabase = st.session_state.supabase
            
            # Obtener o crear compañía
            company_id = database.get_company_id(supabase, company_name)
            
            # Verificar si ya existen datos para esta compañía
            data_exists = database.check_company_data_exists(supabase, company_id)

            if data_exists:
                # Eliminar datos existentes
                success, message = database.delete_company_data(supabase, company_name)
                if not success:
                    status.update(label=f"Error al eliminar datos existentes: {message}", state="error")
                    return False, None, None
                
                status.update(label=f"Datos existentes eliminados para '{company_name}'. Procesando archivo CSV...", state="running")
            
            json_data = None
            
            # Guardar temporalmente el archivo cargado
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            status.update(label="Convirtiendo datos de CSV a formato estructurado...", state="running")
            
            # Convertir CSV a JSON
            converter = SurveyMonkeyConverter()
            survey_df = converter.load_surveymonkey_one_hot(temp_path)
            json_data = converter.one_hot_df_to_json(survey_df)
            
            status.update(label=f"Conversión completada: {len(json_data)} respuestas, {len(json_data[0]) if json_data else 0} preguntas", state="running")
            
            # Limpiar archivos temporales
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            status.update(label="Guardando datos en la base de datos...", state="running")
            
            # Guardar datos de encuestas
            success, message = database.save_survey_data_batch(supabase, json_data, company_id)
            
            if not success:
                status.update(label=f"Error al guardar datos: {message}", state="error")
                return False, None, None
            
            # Realizar análisis con las fórmulas implementadas
            status.update(label="Calculando análisis de demanda de movilidad...", state="running")
            
            # Iniciar el análisis
            analytics = SurveyAnalytics(supabase, company_id)
            
            # Calcular tasa de participación
            participation_rate = analytics.calculate_participation_rate(total_employees)
            
            # Calcular distribución por género
            gender_distribution = analytics.calculate_gender_distribution()
            
            # Calcular distribución por código postal
            postal_code_distribution = analytics.calculate_postal_code_distribution()
            
            # Calcular distribución por edad
            age_distribution = analytics.calculate_age_distribution()
            
            # Calcular distribución por tipo de jornada
            workday_distribution = analytics.calculate_workday_type_distribution()
            
            # Calcular distribución por días de teletrabajo
            telework_distribution = analytics.calculate_telework_distribution()
            
            # Calcular distribución por modo de transporte
            transport_mode_distribution = analytics.calculate_transport_mode_distribution()
            
            # Calcular porcentaje de trabajadores multimodales
            multimodal_workers_percentage = analytics.calculate_multimodal_workers_percentage()
            
            # Calcular distribución por rangos de distancia
            distance_range_distribution = analytics.calculate_distance_range_distribution()
            
            # Calcular distribución por rangos de tiempo
            travel_time_distribution = analytics.calculate_travel_time_distribution()
            
            # Calcular porcentaje de trabajadores que realizan desplazamientos en misión
            business_trips_percentage = analytics.calculate_business_trips_percentage()
            
            # Calcular porcentaje de viajeros en misión que usan coche propio
            business_trips_own_car_percentage = analytics.calculate_business_trips_own_car_percentage()
            
            # Calcular porcentaje por tipo de motor del vehículo
            engine_type_percentage = analytics.calculate_engine_type_percentage()
            
            # Calcular porcentaje de intención de compra de vehículo eléctrico
            ev_purchase_intention_percentage = analytics.calculate_ev_purchase_intention_percentage()
            
            # Calcular porcentaje con aparcamiento gratuito en la empresa
            free_parking_percentage = analytics.calculate_free_parking_percentage()
            
            # Calcular porcentaje que no percibe problemas de aparcamiento
            no_parking_problems_percentage = analytics.calculate_no_parking_problems_percentage()
            
            # Calcular porcentaje por barrera al uso de transporte público
            public_transport_barriers_percentage = analytics.calculate_public_transport_barriers_percentage()
            
            # Calcular porcentaje de motivaciones para usar transporte público
            public_transport_motivations_percentage = analytics.calculate_public_transport_motivations_percentage()
            
            # Calcular porcentaje de disposición a compartir coche
            car_sharing_willingness_percentage = analytics.calculate_car_sharing_willingness_percentage()
            
            # Calcular porcentaje que conoce líneas de transporte público cercanas
            public_transport_lines_awareness_percentage = analytics.calculate_public_transport_lines_awareness_percentage()
            
            # Calcular porcentaje por factor de mejora del transporte público
            public_transport_improvement_factors_percentage = analytics.calculate_public_transport_improvement_factors_percentage()
            
            # Calcular porcentaje que conoce vías ciclistas
            cycling_routes_awareness_percentage = analytics.calculate_cycling_routes_awareness_percentage()

            # Calcular porcentaje por factor de mejora al uso de bicicleta
            cycling_improvement_factors_percentage = analytics.calculate_cycling_improvement_factors_percentage()
            
            # Recopilar resultados
            analysis_results = [
                participation_rate, 
                gender_distribution,
                postal_code_distribution,
                age_distribution,
                workday_distribution,
                telework_distribution,
                transport_mode_distribution,
                multimodal_workers_percentage,
                distance_range_distribution,
                travel_time_distribution,
                business_trips_percentage,
                business_trips_own_car_percentage,
                engine_type_percentage,
                ev_purchase_intention_percentage,
                free_parking_percentage,
                no_parking_problems_percentage,
                public_transport_barriers_percentage,
                public_transport_motivations_percentage,
                car_sharing_willingness_percentage,
                current_car_sharing_percentage,
                public_transport_lines_awareness_percentage,
                public_transport_improvement_factors_percentage,
                cycling_routes_awareness_percentage,
                cycling_improvement_factors_percentage
            ]
            
            # Finalizar con éxito
            status.update(label=f"¡Análisis completado para la compañía '{company_name}'!", state="complete")
            
            return True, json_data, analysis_results
                
    except Exception as e:
        if status_container:
            status_container.error(f"Error en el proceso: {e}")
        return False, None, None

# Mostrar resultados del análisis
def display_analysis_results(analysis_results):
    """Mostrar resultados del análisis en la página"""
    if analysis_results:
        st.subheader("Resultados del Análisis")
        st.json(analysis_results)
    else:
        st.info("No hay resultados de análisis disponibles.")

# Nueva función para mostrar resultados en pestañas
def display_results_in_tabs(analysis_results):
    """Muestra los resultados del análisis en pestañas"""
    if not analysis_results or 'mobility_report' not in st.session_state:
        st.warning("No hay resultados disponibles para mostrar.")
        return
        
    # Crear pestañas
    tab1, tab2 = st.tabs(["Informe Generado", "Datos en JSON"])
    
    # Pestaña 1: Informe generado
    with tab1:
        st.markdown(st.session_state.mobility_report)
    
    # Pestaña 2: JSON de resultados
    with tab2:
        st.json(analysis_results)

# Generar informe con LLM
def generate_mobility_report(analysis_results, company_name):
    """
    Genera un informe narrativo basado en los resultados del análisis utilizando LLM
    """
    if not analysis_results:
        st.error("No hay resultados de análisis disponibles para generar el informe.")
        return None
        
    try:
        with st.status("Generando informe de movilidad...") as status:
            # Inicializar el generador de informes
            generator = ReportGenerator(model="openai/o4-mini")
            
            # Generar el informe (la API key se tomará automáticamente de st.secrets)
            report, cost = generator.generate_mobility_report(analysis_results, company_name)
            
            # Mostrar información sobre el costo
            status.update(label=f"Informe generado. Costo aproximado: ${cost:.4f}", state="complete")
            
            return report
            
    except Exception as e:
        st.error(f"Error al generar informe: {e}")
        return None

def main():
    """Función principal para la interfaz de usuario"""
    st.title("Análisis de Demanda de Movilidad")
    
    # Organización vertical de elementos (sin sidebar como prefiere el usuario)
    col1, col2 = st.columns(2)
    
    with col1:
        # Input para el nombre de la compañía
        company_name = st.text_input("Nombre de la compañía", 
                                     value=st.session_state.company_name or "ACME",
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
        process_button = st.button("Procesar y generar informe", disabled=not (uploaded_file and company_name))
    
    with col5:
        # Botón para analizar datos existentes
        analyze_button = st.button("Generar informe con datos existentes", disabled=not company_name)
    
    if process_button and uploaded_file and company_name:
        st.session_state.company_name = company_name
        st.session_state.total_employees = total_employees
        
        with st.status("Procesando datos y generando informe...", expanded=True) as status:
            st.write("Cargando datos de encuesta...")
            
            supabase = st.session_state.supabase
            
            # Obtener o crear compañía
            company_id = database.get_company_id(supabase, company_name)
            
            # Verificar si ya existen datos para esta compañía
            data_exists = database.check_company_data_exists(supabase, company_id)

            if data_exists:
                # Eliminar datos existentes
                st.write(f"Se encontraron datos anteriores para '{company_name}'. Eliminando...")
                success, message = database.delete_company_data(supabase, company_name)
                if not success:
                    status.update(label=f"Error al eliminar datos existentes: {message}", state="error")
                    return
                st.write("Datos anteriores eliminados correctamente.")
            
            # Guardar temporalmente el archivo cargado
            st.write("Convirtiendo datos de CSV a formato estructurado...")
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Convertir CSV a JSON
            converter = SurveyMonkeyConverter()
            survey_df = converter.load_surveymonkey_one_hot(temp_path)
            json_data = converter.one_hot_df_to_json(survey_df)
            
            st.write(f"Conversión completada: {len(json_data)} respuestas procesadas")
            
            # Limpiar archivos temporales
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            st.write("Guardando datos en la base de datos...")
            
            # Guardar datos de encuestas
            success, message = database.save_survey_data_batch(supabase, json_data, company_id)
            
            if not success:
                status.update(label=f"Error al guardar datos: {message}", state="error")
                return
            
            # Realizar análisis con las fórmulas implementadas
            st.write("Calculando análisis de demanda de movilidad...")
            
            # Iniciar el análisis
            analytics = SurveyAnalytics(supabase, company_id)
            
            # Lista para almacenar los resultados
            analysis_results = []
            
            # Realizar todos los cálculos
            st.write("Calculando tasas de participación...")
            participation_rate = analytics.calculate_participation_rate(total_employees)
            analysis_results.append(participation_rate)
            
            st.write("Analizando datos demográficos...")
            gender_distribution = analytics.calculate_gender_distribution()
            postal_code_distribution = analytics.calculate_postal_code_distribution()
            age_distribution = analytics.calculate_age_distribution()
            analysis_results.extend([gender_distribution, postal_code_distribution, age_distribution])
            
            st.write("Analizando patrones de trabajo...")
            workday_distribution = analytics.calculate_workday_type_distribution()
            telework_distribution = analytics.calculate_telework_distribution()
            analysis_results.extend([workday_distribution, telework_distribution])
            
            st.write("Analizando modos de transporte...")
            transport_mode_distribution = analytics.calculate_transport_mode_distribution()
            multimodal_workers_percentage = analytics.calculate_multimodal_workers_percentage()
            distance_range_distribution = analytics.calculate_distance_range_distribution()
            travel_time_distribution = analytics.calculate_travel_time_distribution()
            analysis_results.extend([
                transport_mode_distribution, 
                multimodal_workers_percentage,
                distance_range_distribution,
                travel_time_distribution
            ])
            
            st.write("Analizando desplazamientos y vehículos...")
            business_trips_percentage = analytics.calculate_business_trips_percentage()
            business_trips_own_car_percentage = analytics.calculate_business_trips_own_car_percentage()
            engine_type_percentage = analytics.calculate_engine_type_percentage()
            ev_purchase_intention_percentage = analytics.calculate_ev_purchase_intention_percentage()
            analysis_results.extend([
                business_trips_percentage,
                business_trips_own_car_percentage,
                engine_type_percentage,
                ev_purchase_intention_percentage
            ])
            
            st.write("Analizando aparcamiento...")
            free_parking_percentage = analytics.calculate_free_parking_percentage()
            no_parking_problems_percentage = analytics.calculate_no_parking_problems_percentage()
            analysis_results.extend([free_parking_percentage, no_parking_problems_percentage])
            
            st.write("Analizando transporte público...")
            public_transport_barriers_percentage = analytics.calculate_public_transport_barriers_percentage()
            public_transport_motivations_percentage = analytics.calculate_public_transport_motivations_percentage()
            public_transport_lines_awareness_percentage = analytics.calculate_public_transport_lines_awareness_percentage()
            public_transport_improvement_factors_percentage = analytics.calculate_public_transport_improvement_factors_percentage()
            analysis_results.extend([
                public_transport_barriers_percentage,
                public_transport_motivations_percentage,
                public_transport_lines_awareness_percentage,
                public_transport_improvement_factors_percentage
            ])
            
            st.write("Analizando compartir coche y ciclismo...")
            car_sharing_willingness_percentage = analytics.calculate_car_sharing_willingness_percentage()
            cycling_routes_awareness_percentage = analytics.calculate_cycling_routes_awareness_percentage()
            cycling_improvement_factors_percentage = analytics.calculate_cycling_improvement_factors_percentage()
            analysis_results.extend([
                car_sharing_willingness_percentage,
                cycling_routes_awareness_percentage,
                cycling_improvement_factors_percentage
            ])
            
            # Guardar resultados en el estado de la sesión
            st.session_state.json_data = json_data
            st.session_state.analysis_results = analysis_results
            
            # Generar informe automáticamente
            st.write("Generando informe de movilidad...")
            generator = ReportGenerator(model="openai/o4-mini")
            report, cost = generator.generate_mobility_report(analysis_results, company_name)
            
            if report:
                st.session_state.mobility_report = report
                status.update(label=f"¡Análisis completado para '{company_name}'!", state="complete", expanded=False)
            else:
                status.update(label="Error al generar informe", state="error")
                return
        
        # Mostrar resultados en pestañas FUERA del status
        display_results_in_tabs(analysis_results)
    
    elif analyze_button and company_name:
        st.session_state.company_name = company_name
        st.session_state.total_employees = total_employees
        
        with st.status("Analizando datos existentes...", expanded=True) as status:
            supabase = st.session_state.supabase
            
            # Obtener ID de la compañía
            st.write("Verificando datos de compañía...")
            company_id = database.get_company_id(supabase, company_name, create_if_not_exists=False)
            
            if not company_id:
                status.update(label=f"No se encontró la compañía '{company_name}'.", state="error")
                return
            
            # Verificar si existen datos
            data_exists = database.check_company_data_exists(supabase, company_id)
            
            if not data_exists:
                status.update(label=f"No hay datos para la compañía '{company_name}'.", state="error")
                return
            
            # Iniciar el análisis
            analytics = SurveyAnalytics(supabase, company_id)
            
            # Lista para almacenar los resultados
            analysis_results = []
            
            # Realizar todos los cálculos
            st.write("Calculando tasas de participación...")
            participation_rate = analytics.calculate_participation_rate(total_employees)
            analysis_results.append(participation_rate)
            
            st.write("Analizando datos demográficos...")
            gender_distribution = analytics.calculate_gender_distribution()
            postal_code_distribution = analytics.calculate_postal_code_distribution()
            age_distribution = analytics.calculate_age_distribution()
            analysis_results.extend([gender_distribution, postal_code_distribution, age_distribution])
            
            st.write("Analizando patrones de trabajo...")
            workday_distribution = analytics.calculate_workday_type_distribution()
            telework_distribution = analytics.calculate_telework_distribution()
            analysis_results.extend([workday_distribution, telework_distribution])
            
            st.write("Analizando modos de transporte...")
            transport_mode_distribution = analytics.calculate_transport_mode_distribution()
            multimodal_workers_percentage = analytics.calculate_multimodal_workers_percentage()
            distance_range_distribution = analytics.calculate_distance_range_distribution()
            travel_time_distribution = analytics.calculate_travel_time_distribution()
            analysis_results.extend([
                transport_mode_distribution, 
                multimodal_workers_percentage,
                distance_range_distribution,
                travel_time_distribution
            ])
            
            st.write("Analizando desplazamientos y vehículos...")
            business_trips_percentage = analytics.calculate_business_trips_percentage()
            business_trips_own_car_percentage = analytics.calculate_business_trips_own_car_percentage()
            engine_type_percentage = analytics.calculate_engine_type_percentage()
            ev_purchase_intention_percentage = analytics.calculate_ev_purchase_intention_percentage()
            analysis_results.extend([
                business_trips_percentage,
                business_trips_own_car_percentage,
                engine_type_percentage,
                ev_purchase_intention_percentage
            ])
            
            st.write("Analizando aparcamiento...")
            free_parking_percentage = analytics.calculate_free_parking_percentage()
            no_parking_problems_percentage = analytics.calculate_no_parking_problems_percentage()
            analysis_results.extend([free_parking_percentage, no_parking_problems_percentage])
            
            st.write("Analizando transporte público...")
            public_transport_barriers_percentage = analytics.calculate_public_transport_barriers_percentage()
            public_transport_motivations_percentage = analytics.calculate_public_transport_motivations_percentage()
            public_transport_lines_awareness_percentage = analytics.calculate_public_transport_lines_awareness_percentage()
            public_transport_improvement_factors_percentage = analytics.calculate_public_transport_improvement_factors_percentage()
            analysis_results.extend([
                public_transport_barriers_percentage,
                public_transport_motivations_percentage,
                public_transport_lines_awareness_percentage,
                public_transport_improvement_factors_percentage
            ])
            
            st.write("Analizando compartir coche y ciclismo...")
            car_sharing_willingness_percentage = analytics.calculate_car_sharing_willingness_percentage()
            cycling_routes_awareness_percentage = analytics.calculate_cycling_routes_awareness_percentage()
            cycling_improvement_factors_percentage = analytics.calculate_cycling_improvement_factors_percentage()
            analysis_results.extend([
                car_sharing_willingness_percentage,
                cycling_routes_awareness_percentage,
                cycling_improvement_factors_percentage
            ])
            
            # Guardar resultados en el estado de la sesión
            st.session_state.analysis_results = analysis_results
            
            # Generar informe automáticamente
            st.write("Generando informe de movilidad...")
            generator = ReportGenerator(model="openai/o4-mini")
            report, cost = generator.generate_mobility_report(analysis_results, company_name)
            
            if report:
                st.session_state.mobility_report = report
                status.update(label=f"¡Análisis completado para '{company_name}'!", state="complete", expanded=False)
            else:
                status.update(label="Error al generar informe", state="error")
                return
        
        # Mostrar resultados en pestañas FUERA del status
        display_results_in_tabs(analysis_results)
    
    # Mostrar resultados si existen en la sesión y no se está procesando nuevo análisis
    if 'analysis_results' in st.session_state and st.session_state.analysis_results and 'mobility_report' in st.session_state and st.session_state.mobility_report:
        if not process_button and not analyze_button:  # Solo mostrar si no estamos procesando nuevos datos
            display_results_in_tabs(st.session_state.analysis_results)

if __name__ == "__main__":
    init_session_state()
    main()