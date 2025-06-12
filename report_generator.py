import os
import json
import yaml
import logging
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
from litellm import completion, completion_cost

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Una clase profesional para generar informes a partir de datos de análisis de encuestas usando LLM.
    
    Esta clase gestiona:
    - Carga de plantillas de prompt
    - Procesamiento de resultados de análisis
    - Llamadas a la API de LLM con parámetros apropiados
    - Cálculo de costos de uso de API
    - Validación de la calidad del informe
    
    La clase sigue mejores prácticas para manejo de errores, logging y gestión de estado.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-4o-mini"):
        """
        Inicializa el ReportGenerator con configuración de API y plantillas de prompt.
        
        Args:
            api_key: Clave API para el servicio LLM (opcional si ya está en el estado de sesión)
            model: Identificador del modelo a usar para la generación de informes
        """
        # Almacenar configuración
        self.model = model
        self._api_key = api_key or self._get_api_key_from_session()
        
        # Cargar prompts en la inicialización
        self.prompts = self._load_prompts()
        
        # Inicializar estado
        self.total_cost = 0.0
        self.cost_history = []
    
    def _load_prompts(self) -> Dict[str, str]:
        """
        Carga plantillas de prompt desde el archivo YAML.
        
        Returns:
            Diccionario con las plantillas de prompt
        """
        try:
            # Buscar el archivo prompts.yaml en el directorio actual y en el directorio raíz
            prompt_paths = [
                'prompts.yaml',
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts.yaml')
            ]
            
            for path in prompt_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as file:
                        prompts = yaml.safe_load(file)
                        logger.info(f"Prompts cargados correctamente desde {path}")
                        return prompts
                        
            logger.warning("No se encontró el archivo de prompts")
            return {}
            
        except Exception as e:
            logger.error(f"Error al cargar prompts: {e}")
            return {}
    
    def _get_api_key_from_session(self) -> Optional[str]:
        """
        Recupera la clave API desde el estado de sesión de Streamlit o desde secrets si está disponible.
        
        Returns:
            Cadena de clave API o None si no se encuentra
        """
        import streamlit as st
        
        # Intentar obtener la clave API primero del estado de sesión
        if 'api_key' in st.session_state:
            return st.session_state.api_key
            
        # Caer en secrets si está disponible
        try:
            if 'openai' in st.secrets:
                return st.secrets["openai"]["api_key"]
        except:
            pass
            
        # Retornar None si no se encuentra ninguna clave API
        logger.warning("No se encontró ninguna clave API en el estado de sesión o en secrets")
        return None
    
    def generate_mobility_report(self, 
                              analysis_results: List[Dict[str, Any]], 
                              company_name: str,
                              company_id: Optional[int] = None) -> Tuple[str, float]:
        """
        Genera un informe de movilidad completo basado en resultados de análisis de fórmulas.
        
        Args:
            analysis_results: Lista de diccionarios que contienen resultados de análisis de fórmulas
            company_name: Nombre de la empresa para la que se genera el informe
            company_id: ID de empresa opcional para referencia
            
        Returns:
            Tupla que contiene (texto_del_informe_generado, costo_de_generación)
        """
        try:
            # Formatear los resultados del análisis para el prompt
            formatted_results = json.dumps(analysis_results, ensure_ascii=False, indent=2)
            
            # Obtener plantilla de prompt y completarla
            template = self.prompts.get("mobility_report_prompt", "")
            if not template:
                logger.error("No hay mobility_report_prompt disponible en el archivo de prompts")
                return "Error: No hay plantilla disponible para el informe de movilidad.", 0.0
                
            # Completar la plantilla de prompt
            filled_prompt = template.format(
                company_name=company_name,
                analysis_results=formatted_results
            )
            
            # Llamar a la API de LLM
            report_content, call_cost = self._call_llm_api(filled_prompt)
            
            # Actualizar seguimiento de costos
            self._track_cost(call_cost, "mobility_report_generation", company_id)
            
            # Verificar la calidad del informe (opcional)
            # quality_check = self.verify_report_quality(report_content, analysis_results)
            # if quality_check and quality_check.get('score', 0) < 0.7:
            #     logger.warning(f"Baja calidad de informe detectada: {quality_check}")
            
            return report_content, call_cost
            
        except Exception as e:
            logger.error(f"Error al generar informe de movilidad: {e}")
            return f"Error al generar informe: {e}", 0.0
    
    def _call_llm_api(self, message_content: str) -> Tuple[str, float]:
        """
        Llamar a la API de LLM con manejo de errores adecuado y seguimiento de costos.
        
        Args:
            message_content: El prompt para enviar al LLM
            
        Returns:
            Tupla que contiene (contenido_de_respuesta_del_modelo, costo_de_llamada)
        """
        try:
            # Verificar si tenemos una clave API válida - refrescar desde sesión/secrets
            self._api_key = self._get_api_key_from_session()
            
            if not self._api_key:
                logger.error("No hay clave API disponible")
                return "Error: No se ha configurado una clave API para LLM.", 0.0
            
            # Crear formato de mensaje para la API
            messages = [{"role": "user", "content": message_content}]
            
            # Medir tiempo de inicio
            start_time = pd.Timestamp.now()
            
            # Llamar a la API
            response = completion(
                model=self.model,
                messages=messages,
                # temperature=0.7,
                api_key=self._api_key
            )
            
            # Medir tiempo final y calcular duración
            end_time = pd.Timestamp.now()
            duration_seconds = (end_time - start_time).total_seconds()
            
            # Calcular costo
            cost = self._calculate_cost(response, duration_seconds)
            
            # Extraer contenido de la respuesta
            content = response.choices[0].message.content
            
            return content, cost
            
        except Exception as e:
            logger.error(f"Error al llamar a la API de LLM: {e}")
            return f"Error: {e}", 0.0
    
    def _calculate_cost(self, response: Any, duration_seconds: float = None) -> float:
        """
        Calcula el costo de una llamada a la API.
        
        Args:
            response: Objeto de respuesta de la API de LLM
            duration_seconds: Tiempo empleado para la llamada a la API
            
        Returns:
            Costo estimado de la llamada a la API
        """
        try:
            # Calcular costo usando litellm
            cost = completion_cost(completion_response=response)
            
            # Registrar información de costo y duración
            if duration_seconds:
                logger.info(f"Llamada a LLM completada en {duration_seconds:.2f}s, costo: ${cost:.4f}")
                
            # Advertir si el costo es demasiado alto
            if cost > 0.10:  # Umbral configurable
                logger.warning(f"Costo de LLM alto: ${cost:.4f}")
                
            return cost
            
        except Exception as e:
            logger.error(f"Error al calcular costo: {e}")
            # Estimación aproximada si falla el cálculo
            return 0.01  # Valor conservador
    
    def _track_cost(self, cost: float, operation_type: str, company_id: Optional[int] = None) -> None:
        """
        Mantener historial de costos para informes y presupuestos.
        
        Args:
            cost: Costo de la operación
            operation_type: Tipo de operación realizada
            company_id: ID de la empresa asociada con la operación
        """
        # Actualizar costo total
        self.total_cost += cost
        
        # Registrar en historial
        timestamp = pd.Timestamp.now()
        self.cost_history.append({
            'timestamp': timestamp,
            'operation_type': operation_type,
            'company_id': company_id,
            'cost': cost
        })
        
        # Limitar longitud del historial para evitar uso excesivo de memoria
        if len(self.cost_history) > 1000:
            self.cost_history = self.cost_history[-1000:]
    
    def get_cost_report(self) -> Tuple[pd.DataFrame, float]:
        """
        Obtiene un informe detallado de los costos de uso de API.
        
        Returns:
            Tupla de (dataframe_historial_costos, costo_total)
        """
        if not self.cost_history:
            return pd.DataFrame(), 0.0
            
        df = pd.DataFrame(self.cost_history)
        return df, self.total_cost
    
    def verify_report_quality(self, report_content: str, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verifica que el informe generado representa con precisión los datos de análisis.
        
        Args:
            report_content: Texto del informe generado
            analysis_results: Resultados del análisis original
            
        Returns:
            Diccionario con resultados de verificación y puntuación de calidad
        """
        # Aquí implementaríamos una verificación real de calidad
        # Por ahora, es un placeholder que devuelve una puntuación fija
        
        # TODO: Implementar verificación real usando otro LLM o reglas programáticas
        
        return {
            'score': 0.9,  # Puntuación de 0-1
            'verified': True,
            'missing_data': [],
            'inconsistencies': []
        }
        
    def generate_analysis(self, data: Any, clear_messages: bool = True) -> str:
        """
        Genera un análisis de los datos proporcionados usando el modelo LLM.
        
        Args:
            data: Datos para analizar, puede ser un DataFrame o datos JSON
            clear_messages: Si debe limpiar el historial de mensajes antes de la nueva solicitud
            
        Returns:
            El contenido del análisis generado
        """
        try:
            # Cargar plantillas de prompts
            prompts = self.prompts
            
            # Preparar los datos según su formato
            if hasattr(data, 'to_csv'):  # Si es un DataFrame
                import io
                csv_buffer = io.StringIO()
                data.to_csv(csv_buffer, index=False)
                data_str = csv_buffer.getvalue()
                filled_prompt = prompts.get("analysis_prompt", "").format(data=data_str)
            elif isinstance(data, (list, dict)):  # Si son datos JSON
                import json
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                filled_prompt = prompts.get("analysis_prompt", "").format(data=json_str)
            else:
                filled_prompt = prompts.get("analysis_prompt", "").format(data=str(data))
            
            # Llamar a la API de LLM
            analysis_content, call_cost = self._call_llm_api(filled_prompt)
            
            # Actualizar seguimiento de costos
            self._track_cost(call_cost, "analysis_generation")
            
            return analysis_content
            
        except Exception as e:
            logger.error(f"Error al generar análisis: {e}")
            return f"Error al generar análisis: {e}"
            
    def generate_summary(self, json_data: Any = None, company_name: str = "") -> Tuple[str, float]:
        """
        Genera un resumen a partir de datos JSON y el nombre de la empresa.
        
        Args:
            json_data: Datos en formato JSON para generar el resumen
            company_name: Nombre de la empresa
            
        Returns:
            Tupla con (texto_del_resumen, costo_de_generación)
        """
        try:
            # Cargar plantillas de prompts
            prompts = self.prompts
            
            # Preparar el prompt
            if json_data:
                import json
                json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                filled_prompt = prompts.get("summary_prompt", "").format(
                    company_name=company_name, 
                    json_data=json_str
                )
            else:
                # Fallback si no hay datos disponibles
                filled_prompt = prompts.get("summary_prompt", "").format(
                    company_name=company_name,
                    json_data="{}"
                )
            
            # Llamar a la API de LLM
            summary_content, call_cost = self._call_llm_api(filled_prompt)
            
            # Actualizar seguimiento de costos
            self._track_cost(call_cost, "summary_generation")
            
            return summary_content, call_cost
            
        except Exception as e:
            logger.error(f"Error al generar resumen: {e}")
            return f"Error al generar resumen: {e}", 0.0
            
    def generate_redaction(self) -> Tuple[str, float]:
        """
        Genera una redacción a partir del análisis previo.
        
        Returns:
            Tupla con (texto_de_redacción, costo_de_generación)
        """
        try:
            # Cargar plantillas de prompts
            prompts = self.prompts
            
            # Preparar el prompt
            filled_prompt = prompts.get("redaction_prompt", "")
            
            # Llamar a la API de LLM
            redaction_content, call_cost = self._call_llm_api(filled_prompt)
            
            # Actualizar seguimiento de costos
            self._track_cost(call_cost, "redaction_generation")
            
            return redaction_content, call_cost
            
        except Exception as e:
            logger.error(f"Error al generar redacción: {e}")
            return f"Error al generar redacción: {e}", 0.0
            
    def verify_summary(self, questions_data: Any, summary_text: str) -> Tuple[str, float]:
        """
        Verifica la calidad del resumen comparándolo con los datos originales.
        
        Args:
            questions_data: Datos originales de las preguntas
            summary_text: Texto del resumen a verificar
            
        Returns:
            Tupla con (resultado_de_verificación, costo_de_verificación)
        """
        try:
            # Cargar plantillas de prompts
            prompts = self.prompts
            
            # Preparar el prompt
            filled_prompt = prompts.get("verification_prompt", "").format(
                questions_data=questions_data,
                summary_text=summary_text
            )
            
            # Llamar a la API de LLM con un modelo más pequeño para economizar
            verification_result, call_cost = self._call_llm_api(filled_prompt)
            
            # Actualizar seguimiento de costos
            self._track_cost(call_cost, "summary_verification")
            
            return verification_result, call_cost
            
        except Exception as e:
            logger.error(f"Error al verificar resumen: {e}")
            return f"Error al verificar resumen: {e}", 0.0
