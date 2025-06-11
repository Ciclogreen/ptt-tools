import pandas as pd
import numpy as np
from supabase import Client

class SurveyAnalytics:
    """
    Class to perform analytics on mobility survey data from Supabase database.
    Each method calculates a specific formula from the mobility survey analysis.
    """
    
    def __init__(self, supabase_client: Client, company_id: int):
        """
        Initialize the analytics with a Supabase client and company ID.
        
        Args:
            supabase_client: The Supabase client instance
            company_id: ID of the company to analyze
        """
        self.supabase = supabase_client
        self.company_id = company_id
        
    def get_total_responses(self):
        """
        Get the total number of survey responses for the company.
        
        Returns:
            int: Total number of responses
        """
        try:
            result = self.supabase.table('respondents').select('id', count='exact').eq('company_id', self.company_id).execute()
            return result.count
        except Exception as e:
            print(f"Error getting total responses: {e}")
            return 0
    
    def calculate_participation_rate(self, total_employees: int):
        """
        Formula 1: Calculate participation rate
        Participation (%) = N_responses / N_total_employees × 100
        
        Args:
            total_employees: Total number of employees
            
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        if total_employees <= 0:
            return {
                "name": "Tasa de participación de la encuesta",
                "result": 0,
                "error": "El número total de empleados debe ser mayor que cero"
            }
        
        responses = self.get_total_responses()
        participation_rate = (responses / total_employees) * 100
        
        return {
            "name": "Tasa de participación de la encuesta",
            "result": round(participation_rate, 2),
            "variables": {
                "N_respuestas": responses,
                "N_empleados_totales": total_employees
            }
        }
    
    def calculate_gender_distribution(self):
        """
        Formula 2: Calculate gender distribution
        Percentage_gender (%) = N_gender / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. First, find the gender question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            gender_question_id = None
            gender_question_text = ""
            
            # Search for gender question using keywords
            gender_keywords = ["género", "genero", "sexo", "gender", "sex"]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in gender_keywords):
                    gender_question_id = question['id']
                    gender_question_text = question['question_text']
                    break
            
            if not gender_question_id:
                return {
                    "name": "Distribución por género",
                    "error": "No se encontró pregunta relacionada con género en la encuesta"
                }
            
            # 2. Get all options for the gender question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', gender_question_id).eq('company_id', self.company_id).execute()
            
            option_ids = {}
            for option in options.data:
                option_ids[option['id']] = option['option_text']
            
            # 3. Count answers for each gender option
            gender_counts = {}
            
            for option_id, option_text in option_ids.items():
                count_result = self.supabase.table('answers').select('id', count='exact').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                gender_counts[option_text] = count_result.count
            
            # Calculate total valid responses
            total_valid_responses = sum(gender_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por género",
                    "error": "No hay respuestas válidas para la pregunta de género"
                }
            
            # Calculate percentages
            gender_percentages = {}
            for gender, count in gender_counts.items():
                gender_percentages[gender] = round((count / total_valid_responses) * 100, 2)
            
            return {
                "name": "Distribución por género",
                "question": gender_question_text,
                "result": gender_percentages,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": gender_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por género",
                "error": f"Error al calcular la distribución por género: {e}"
            }
    
    def calculate_postal_code_distribution(self):
        """
        Formula 3: Calculate postal code distribution
        Percentage_CP (%) = N_residentes_CP / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. First, find the postal code question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            postal_question_id = None
            postal_question_text = ""
            
            # Search for postal code question using keywords
            postal_keywords = ["código postal", "codigo postal", "postal code", "cp", "zip", "c.p."]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in postal_keywords):
                    postal_question_id = question['id']
                    postal_question_text = question['question_text']
                    break
            
            if not postal_question_id:
                return {
                    "name": "Distribución por código postal",
                    "error": "No se encontró pregunta relacionada con código postal en la encuesta"
                }
            
            # 2. Usar la API de Supabase en lugar de SQL directo
            # Primero, obtenemos todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', postal_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Distribución por código postal",
                    "error": "No se encontraron opciones para la pregunta de código postal"
                }
            
            # Creamos un mapa de option_id a option_text (código postal)
            option_map = {opt['id']: opt['option_text'] for opt in options.data}
            
            # Obtenemos todas las respuestas para esta compañía
            answers = self.supabase.table('answers').select('option_id').eq('company_id', self.company_id).execute()
            
            if not answers.data:
                return {
                    "name": "Distribución por código postal",
                    "error": "No hay respuestas para la pregunta de código postal"
                }
            
            # Contamos manualmente las respuestas por código postal
            postal_counts = {}
            for answer in answers.data:
                option_id = answer['option_id']
                # Solo procesamos si el option_id pertenece a la pregunta de código postal
                if option_id in option_map:
                    postal_code = option_map[option_id]
                    if postal_code in postal_counts:
                        postal_counts[postal_code] += 1
                    else:
                        postal_counts[postal_code] = 1
            
            # Calcular total de respuestas válidas
            total_valid_responses = sum(postal_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por código postal",
                    "error": "No hay respuestas válidas para la pregunta de código postal"
                }
            
            # Calcular porcentajes
            postal_percentages = {}
            for postal_code, count in postal_counts.items():
                postal_percentages[postal_code] = round((count / total_valid_responses) * 100, 2)
            
            # Si hay muchos códigos postales, limitamos a los 10 más frecuentes para la respuesta
            if len(postal_percentages) > 10:
                sorted_items = sorted(postal_percentages.items(), key=lambda x: x[1], reverse=True)
                top_10_items = dict(sorted_items[:10])
                other_percentage = sum(dict(sorted_items[10:]).values())
                
                postal_percentages = top_10_items
                if other_percentage > 0:
                    postal_percentages["Otros"] = round(other_percentage, 2)
            
            # Obtener los nombres de municipios para cada código postal y crear un nuevo diccionario con formato "CP - Municipio"
            enriched_postal_percentages = {}
            for postal_code, percentage in postal_percentages.items():
                # No hacer llamada a la API para la categoría "Otros"
                if postal_code == "Otros":
                    enriched_postal_percentages[postal_code] = percentage
                    continue
                
                # Obtener el nombre del municipio
                municipality_name = self.get_municipality_name_by_postal_code(postal_code)
                
                # Crear una nueva clave con el formato "CP - Municipio" si hay nombre de municipio
                if municipality_name:
                    new_key = f"{postal_code} - {municipality_name}"
                else:
                    new_key = postal_code
                
                # Agregar al diccionario enriquecido
                enriched_postal_percentages[new_key] = percentage
            
            return {
                "name": "Distribución por código postal",
                "question": postal_question_text,
                "result": enriched_postal_percentages,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": postal_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por código postal",
                "error": f"Error al calcular la distribución por código postal: {e}"
            }

    def calculate_age_distribution(self):
        """
        Formula 4: Calculate employee distribution by age range
        Percentage_age (%) = N_age_range / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. First, find the age question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            age_question_id = None
            age_question_text = ""
            
            # Search for age question using keywords
            age_keywords = ["edad", "age", "rango de edad", "age range", "años", "years"]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in age_keywords):
                    age_question_id = question['id']
                    age_question_text = question['question_text']
                    break
            
            if not age_question_id:
                return {
                    "name": "Distribución por edad",
                    "error": "No se encontró pregunta relacionada con la edad en la encuesta"
                }
            
            # 2. Get all options for the age question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', age_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Distribución por edad",
                    "error": "No se encontraron opciones para la pregunta de edad"
                }
            
            # Create map of option_id to option_text (age range)
            option_map = {opt['id']: opt['option_text'] for opt in options.data}
            
            # 3. Get all answers filtered by company_id
            answers = self.supabase.table('answers').select('option_id').eq('company_id', self.company_id).execute()
            
            if not answers.data:
                return {
                    "name": "Distribución por edad",
                    "error": "No hay respuestas para la pregunta de edad"
                }
            
            # Count responses by age range
            age_counts = {}
            for answer in answers.data:
                option_id = answer['option_id']
                # Only process if the option_id belongs to the age question
                if option_id in option_map:
                    age_range = option_map[option_id]
                    if age_range in age_counts:
                        age_counts[age_range] += 1
                    else:
                        age_counts[age_range] = 1
            
            # Calculate total valid responses
            total_valid_responses = sum(age_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por edad",
                    "error": "No hay respuestas válidas para la pregunta de edad"
                }
            
            # Calculate percentages
            age_percentages = {}
            for age_range, count in age_counts.items():
                age_percentages[age_range] = round((count / total_valid_responses) * 100, 2)
            
            # Sort age ranges if possible (try to extract numeric values from the ranges)
            try:
                # This attempts to sort age ranges like "18-25", "26-35", "36-45", etc.
                sorted_items = sorted(age_percentages.items(), key=lambda x: int(x[0].split('-')[0].strip("<").strip(">").strip()))
                age_percentages = dict(sorted_items)
            except:
                # If sorting fails, leave as is (might be non-standard age ranges)
                pass
            
            return {
                "name": "Distribución por edad",
                "question": age_question_text,
                "result": age_percentages,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": age_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por edad",
                "error": f"Error al calcular la distribución por edad: {e}"
            }

    def calculate_workday_type_distribution(self):
        """
        Formula 5: Calculate distribution by workday type
        Percentage_workday (%) = N_workday_type / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. Find the workday type question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            workday_question_id = None
            workday_question_text = ""
            
            # Search for workday type question using keywords
            workday_keywords = ["jornada", "horario", "schedule", "workday", "work day", "horario laboral", "work schedule"]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in workday_keywords):
                    workday_question_id = question['id']
                    workday_question_text = question['question_text']
                    break
            
            if not workday_question_id:
                return {
                    "name": "Distribución por tipo de jornada",
                    "error": "No se encontró pregunta relacionada con tipo de jornada en la encuesta"
                }
            
            # 2. Get all options for the workday type question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', workday_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Distribución por tipo de jornada",
                    "error": "No se encontraron opciones para la pregunta de tipo de jornada"
                }
            
            # Create map of option_id to option_text
            option_map = {opt['id']: opt['option_text'] for opt in options.data}
            
            # 3. Get all answers filtered by company_id
            answers = self.supabase.table('answers').select('option_id').eq('company_id', self.company_id).execute()
            
            if not answers.data:
                return {
                    "name": "Distribución por tipo de jornada",
                    "error": "No hay respuestas para la pregunta de tipo de jornada"
                }
            
            # Count responses by workday type
            workday_counts = {}
            for answer in answers.data:
                option_id = answer['option_id']
                # Only process if the option_id belongs to the workday question
                if option_id in option_map:
                    workday_type = option_map[option_id]
                    if workday_type in workday_counts:
                        workday_counts[workday_type] += 1
                    else:
                        workday_counts[workday_type] = 1
            
            # Calculate total valid responses
            total_valid_responses = sum(workday_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por tipo de jornada",
                    "error": "No hay respuestas válidas para la pregunta de tipo de jornada"
                }
            
            # Calculate percentages
            workday_percentages = {}
            for workday_type, count in workday_counts.items():
                workday_percentages[workday_type] = round((count / total_valid_responses) * 100, 2)
            
            return {
                "name": "Distribución por tipo de jornada",
                "question": workday_question_text,
                "result": workday_percentages,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": workday_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por tipo de jornada",
                "error": f"Error al calcular la distribución por tipo de jornada: {e}"
            }
    
    def calculate_telework_distribution(self):
        """
        Formula 6: Calculate distribution by telework days per month
        Percentage_telework (%) = N_days_range / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. Find the telework question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            telework_question_id = None
            telework_question_text = ""
            
            # Search for telework question using keywords
            telework_keywords = [
                "teletrabajo", "remoto", "remote", "telework", "trabajo remoto", "trabajo desde casa", "work from home", "wfh", "teletrabajas"
            ]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in telework_keywords):
                    telework_question_id = question['id']
                    telework_question_text = question['question_text']
                    break
            
            if not telework_question_id:
                return {
                    "name": "Distribución por días de teletrabajo",
                    "error": "No se encontró pregunta relacionada con teletrabajo en la encuesta"
                }
            
            # 2. Get all options for the telework question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', telework_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Distribución por días de teletrabajo",
                    "error": "No se encontraron opciones para la pregunta de teletrabajo"
                }
            
            # Create map of option_id to option_text
            option_map = {opt['id']: opt['option_text'] for opt in options.data}
            
            # 3. Get all answers filtered by company_id
            answers = self.supabase.table('answers').select('option_id').eq('company_id', self.company_id).execute()
            
            if not answers.data:
                return {
                    "name": "Distribución por días de teletrabajo",
                    "error": "No hay respuestas para la pregunta de teletrabajo"
                }
            
            # Count responses by telework days range
            telework_counts = {}
            for answer in answers.data:
                option_id = answer['option_id']
                # Only process if the option_id belongs to the telework question
                if option_id in option_map:
                    telework_range = option_map[option_id]
                    if telework_range in telework_counts:
                        telework_counts[telework_range] += 1
                    else:
                        telework_counts[telework_range] = 1
            
            # Calculate total valid responses
            total_valid_responses = sum(telework_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por días de teletrabajo",
                    "error": "No hay respuestas válidas para la pregunta de teletrabajo"
                }
            
            # Calculate percentages
            telework_percentages = {}
            for telework_range, count in telework_counts.items():
                telework_percentages[telework_range] = round((count / total_valid_responses) * 100, 2)
            
            # Try to sort ranges if they contain numbers (e.g., "1-2 días", "3-4 días")
            try:
                # Extract first number from each range for sorting
                def extract_first_number(range_text):
                    import re
                    numbers = re.findall(r'\d+', range_text)
                    if numbers:
                        return int(numbers[0])
                    # Special cases like "Ninguno" or "Todos los días"
                    if "ning" in range_text.lower():
                        return -1  # "Ninguno" should be first
                    if "tod" in range_text.lower():
                        return 999  # "Todos los días" should be last
                    return 0
                
                sorted_items = sorted(telework_percentages.items(), key=lambda x: extract_first_number(x[0]))
                telework_percentages = dict(sorted_items)
            except:
                # If sorting fails, leave as is
                pass
            
            return {
                "name": "Distribución por días de teletrabajo",
                "question": telework_question_text,
                "result": telework_percentages,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": telework_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por días de teletrabajo",
                "error": f"Error al calcular la distribución por días de teletrabajo: {e}"
            }

    def calculate_transport_mode_distribution(self):
        """
        Formula 7: Calculate main transport mode distribution
        Percentage_modal (%) = N_modal_modo / N_valid_responses × 100
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. Find the transport mode question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            transport_question_id = None
            transport_question_text = ""
            
            # Search for transport mode question using keywords
            transport_keywords = [
                "principal medio de transporte",
                "modo de transporte", "transport mode", "medio de transporte", 
                "desplazamiento", "commute", "viaje al trabajo", "trip to work",
                "movilidad", "mobility", "cómo llegas", "how do you get"
            ]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in transport_keywords):
                    transport_question_id = question['id']
                    transport_question_text = question['question_text']
                    break
            
            if not transport_question_id:
                return {
                    "name": "Distribución por modo de transporte",
                    "error": "No se encontró pregunta relacionada con el modo de transporte en la encuesta"
                }
            
            # 2. Get all options for the transport mode question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', transport_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Distribución por modo de transporte",
                    "error": "No se encontraron opciones para la pregunta de modo de transporte"
                }
            
            # Create map of option_id to option_text
            option_map = {opt['id']: opt['option_text'] for opt in options.data}
            
            # 3. Get all answers filtered by company_id
            answers = self.supabase.table('answers').select('option_id').eq('company_id', self.company_id).execute()
            
            if not answers.data:
                return {
                    "name": "Distribución por modo de transporte",
                    "error": "No hay respuestas para la pregunta de modo de transporte"
                }
            
            # Count responses by transport mode
            transport_counts = {}
            for answer in answers.data:
                option_id = answer['option_id']
                # Only process if the option_id belongs to the transport mode question
                if option_id in option_map:
                    transport_mode = option_map[option_id]
                    if transport_mode in transport_counts:
                        transport_counts[transport_mode] += 1
                    else:
                        transport_counts[transport_mode] = 1
            
            # Calculate total valid responses
            total_valid_responses = sum(transport_counts.values())
            
            if total_valid_responses == 0:
                return {
                    "name": "Distribución por modo de transporte",
                    "error": "No hay respuestas válidas para la pregunta de modo de transporte"
                }
            
            # Calculate percentages
            transport_percentages = {}
            for transport_mode, count in transport_counts.items():
                transport_percentages[transport_mode] = round((count / total_valid_responses) * 100, 2)
            
            # Group similar transport modes for better analysis
            grouped_modes = self._group_similar_transport_modes(transport_percentages)
            
            return {
                "name": "Distribución por modo de transporte",
                "question": transport_question_text,
                "result": transport_percentages,
                "result_grouped": grouped_modes if grouped_modes else None,
                "variables": {
                    "N_respuestas_válidas": total_valid_responses,
                    "counts": transport_counts
                }
            }
            
        except Exception as e:
            return {
                "name": "Distribución por modo de transporte",
                "error": f"Error al calcular la distribución por modo de transporte: {e}"
            }
    
    def _group_similar_transport_modes(self, transport_percentages):
        """
        Helper method to group similar transport modes into categories.
        This helps when the survey has many specific transport modes.
        
        Args:
            transport_percentages: Dictionary of transport modes and their percentages
            
        Returns:
            Dictionary of grouped transport modes and their combined percentages
        """
        try:
            # Define common transport mode categories and keywords to identify them
            categories = {
                "Coche (solo)": ["coche solo", "coche individual", "auto solo", "car alone", "solo driver"],
                "Coche compartido": ["coche compartido", "auto compartido", "carpooling", "shared car", "shared ride"],
                "Transporte público": ["bus", "autobús", "metro", "tren", "tranvía", "subway", "train", "public transport", "transporte público"],
                "Bicicleta": ["bici", "bicicleta", "bike", "bicycle", "cycling"],
                "A pie": ["pie", "caminando", "walk", "walking", "a pie", "on foot"],
                "Moto/Scooter": ["moto", "motocicleta", "motorcycle", "scooter", "motorbike"],
                "Otros": []  # Catch-all category for other modes
            }
            
            # Group the percentages
            grouped_percentages = {category: 0 for category in categories.keys()}
            
            # Categorize each mode
            for mode, percentage in transport_percentages.items():
                mode_lower = mode.lower()
                categorized = False
                
                # Check each category
                for category, keywords in categories.items():
                    if any(keyword in mode_lower for keyword in keywords):
                        grouped_percentages[category] += percentage
                        categorized = True
                        break
                
                # If not categorized, add to "Otros"
                if not categorized:
                    grouped_percentages["Otros"] += percentage
            
            # Remove categories with zero percentage
            grouped_percentages = {k: v for k, v in grouped_percentages.items() if v > 0}
            
            # Round percentages to two decimal places
            for mode in grouped_percentages:
                grouped_percentages[mode] = round(grouped_percentages[mode], 2)
            
            return grouped_percentages
        
        except Exception:
            # If grouping fails, return None and just use the original percentages
            return None

    def get_total_questions(self):
        """
        Return the total number of questions for the current company.
        
        Returns:
            dict: Dictionary with the total number of questions and additional metadata
        """
        try:
            # Query questions table to get total count, filtered by company_id
            result = self.supabase.table('questions').select('id', count='exact').eq('company_id', self.company_id).execute()
            
            total_questions = result.count
            
            return {
                "name": "Total de preguntas",
                "result": total_questions
            }
            
        except Exception as e:
            return {
                "name": "Total de preguntas",
                "error": f"Error al obtener el total de preguntas: {e}"
            }

    def calculate_multimodal_workers_percentage(self):
        """
        Formula 8: Calculate percentage of multimodal workers
        Percentage_multimodal (%) = N_multimodales / N_valid_responses × 100
        
        Multimodal workers are those who combine multiple transport modes.
        If the user doesn't answer to the multimodal question, they are considered non-multimodal.
        
        Returns:
            dict: Dictionary containing the calculation name and results
        """
        try:
            # 1. Find all respondents (to get total valid responses)
            all_respondents_query = self.supabase.table('respondents').select('id', count='exact').eq('company_id', self.company_id).execute()
            total_valid_responses = all_respondents_query.count
            
            if total_valid_responses == 0:
                return {
                    "name": "Porcentaje de trabajadores multimodales",
                    "error": "No hay encuestados para esta compañía"
                }
            
            # 2. Find the multimodal question by searching for keywords
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            
            multimodal_question_id = None
            multimodal_question_text = ""
            
            # Search for multimodal question using keywords
            multimodal_keywords = [
                "Si combinas varios medios de transporte",
                "combinas", "combine", "combinación", "combination", 
                "varios medios", "multiple modes", "multimodal",
                "más de un medio", "more than one mode", "varios transportes"
            ]
            for question in questions.data:
                question_text = question['question_text'].lower()
                if any(keyword in question_text for keyword in multimodal_keywords):
                    multimodal_question_id = question['id']
                    multimodal_question_text = question['question_text']
                    break
            
            if not multimodal_question_id:
                return {
                    "name": "Porcentaje de trabajadores multimodales",
                    "error": "No se encontró pregunta relacionada con combinación de transportes en la encuesta"
                }
            
            # 3. Get respondents who answered the multimodal question
            # First get options for this question
            options = self.supabase.table('options').select('id').eq('question_id', multimodal_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                return {
                    "name": "Porcentaje de trabajadores multimodales",
                    "error": "No se encontraron opciones para la pregunta de combinación de transportes"
                }
            
            # Get the option IDs for this question
            option_ids = [option['id'] for option in options.data]
            
            # Get distinct respondents who answered this question
            multimodal_respondents = set()
            for option_id in option_ids:
                answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                
                for answer in answers.data:
                    multimodal_respondents.add(answer['respondent_id'])
            
            # Calculate number of multimodal workers
            multimodal_count = len(multimodal_respondents)
            
            # Calculate percentage
            multimodal_percentage = round((multimodal_count / total_valid_responses) * 100, 2)
            non_multimodal_percentage = round(100 - multimodal_percentage, 2)
            
            return {
                "name": "Porcentaje de trabajadores multimodales",
                "question": multimodal_question_text,
                "result": {
                    "Multimodal": multimodal_percentage,
                    "No multimodal": non_multimodal_percentage
                },
                "variables": {
                    "N_multimodales": multimodal_count,
                    "N_respuestas_válidas": total_valid_responses
                }
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de trabajadores multimodales",
                "error": f"Error al calcular el porcentaje de trabajadores multimodales: {e}"
            }

    def calculate_distance_range_distribution(self):
        """
        Calcula la distribución de desplazamientos por rango de distancias.
        
        Los rangos son:
        - Menos de 5 km
        - Entre 6 y 15 km
        - Entre 16 y 25 km
        - Entre 26 y 35 km
        - Más de 35 km
        
        Returns:
            dict: Resultados del análisis con porcentajes y conteos para cada rango
        """
        try:
            # Buscar la pregunta relacionada con distancia al trabajo
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            distance_question_id = None
            distance_keywords = ["cuántos kilómetros recorres"]
            
            for question in questions.data:
                if any(keyword in question['question_text'].lower() for keyword in distance_keywords):
                    distance_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not distance_question_id:
                return {
                    "name": "Porcentaje de desplazamientos por tramo de distancia",
                    "error": "No se encontró ninguna pregunta relacionada con la distancia al trabajo"
                }
            
            # Definir los rangos de distancia
            distance_ranges = [
                {"name": "Menos de 5 km", "min": 0, "max": 5, "count": 0},
                {"name": "Entre 6 y 15 km", "min": 6, "max": 15, "count": 0},
                {"name": "Entre 16 y 25 km", "min": 16, "max": 25, "count": 0},
                {"name": "Entre 26 y 35 km", "min": 26, "max": 35, "count": 0},
                {"name": "Más de 35 km", "min": 36, "max": float('inf'), "count": 0}
            ]
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', distance_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                # Si no hay opciones preestablecidas, esta puede ser una pregunta de texto libre
                # Buscar respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', distance_question_id).eq('company_id', self.company_id).execute()
                unique_respondents = set()
                
                for answer in answers.data:
                    if answer['respondent_id'] in unique_respondents:
                        continue
                        
                    unique_respondents.add(answer['respondent_id'])
                    distance_value = self._extract_distance_value(answer['response_value'])
                    
                    if distance_value is not None:
                        # Clasificar en el rango correspondiente
                        for range_info in distance_ranges:
                            if range_info["min"] <= distance_value <= range_info["max"]:
                                range_info["count"] += 1
                                break
            else:
                # Si hay opciones predefinidas, buscar respuestas por opción
                for option in options.data:
                    distance_value = self._extract_distance_value(option['option_text'])
                    if distance_value is None:
                        continue
                        
                    # Determinar a qué rango corresponde esta opción
                    matching_range = None
                    for range_info in distance_ranges:
                        if range_info["min"] <= distance_value <= range_info["max"]:
                            matching_range = range_info
                            break
                    
                    if matching_range:
                        # Contar respuestas para esta opción
                        answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                        matching_range["count"] += len(answers.data)
            
            # Calcular total de respondentes únicos para esta pregunta
            total_respondents = self._count_unique_respondents_for_question(distance_question_id)
            
            # Calcular porcentajes
            percentages = {}
            variables = {
                "N_respuestas_válidas": total_respondents
            }
            
            for range_info in distance_ranges:
                percentage = (range_info["count"] / total_respondents) * 100 if total_respondents > 0 else 0
                percentages[range_info["name"]] = round(percentage, 2)
                variables[f"N_distancia_tramo_{range_info['min']}-{range_info['max'] if range_info['max'] != float('inf') else '+'} km"] = range_info["count"]
            
            return {
                "name": "Porcentaje de desplazamientos por tramo de distancia",
                "question": question_text if 'question_text' in locals() else "Distancia al trabajo",
                "result": percentages,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de desplazamientos por tramo de distancia",
                "error": f"Error al calcular la distribución por rangos de distancia: {e}"
            }

    def _extract_distance_value(self, text_value):
        """
        Extrae un valor numérico de distancia de un texto.
        
        Args:
            text_value: Texto del que extraer el valor de distancia
            
        Returns:
            float: Valor numérico de distancia en km, o None si no se puede extraer
        """
        if not text_value or not isinstance(text_value, str):
            return None
            
        text_value = text_value.lower()
        
        try:
            # Intentar diferentes patrones de extracción
            
            # Patrón 1: Buscar números seguidos por "km" o "kilómetros"
            import re
            km_patterns = [
                r'(\d+[.,]?\d*)\s*km',
                r'(\d+[.,]?\d*)\s*kilómetros',
                r'(\d+[.,]?\d*)\s*kilometros',
                r'(\d+[.,]?\d*)\s*kilómetro',
                r'(\d+[.,]?\d*)\s*kilometro'
            ]
            
            for pattern in km_patterns:
                match = re.search(pattern, text_value)
                if match:
                    # Reemplazar coma por punto para parsear correctamente
                    value_str = match.group(1).replace(',', '.')
                    return float(value_str)
            
            # Patrón 2: Si solo hay un número en el texto, asumimos que es km
            numbers = re.findall(r'(\d+[.,]?\d*)', text_value)
            if len(numbers) == 1:
                return float(numbers[0].replace(',', '.'))
            
            # Patrón 3: Rangos específicos ya definidos
            range_patterns = {
                r'menos\s*de\s*5': 3,  # Valor medio para "menos de 5 km"
                r'entre\s*6\s*y\s*15': 10.5,  # Valor medio para "entre 6 y 15 km"
                r'entre\s*16\s*y\s*25': 20.5,  # Valor medio para "entre 16 y 25 km"
                r'entre\s*26\s*y\s*35': 30.5,  # Valor medio para "entre 26 y 35 km"
                r'más\s*de\s*35': 40  # Valor aproximado para "más de 35 km"
            }
            
            for pattern, value in range_patterns.items():
                if re.search(pattern, text_value):
                    return value
                    
            return None
            
        except Exception as e:
            print(f"Error al extraer valor de distancia de '{text_value}': {e}")
            return None
    
    def _count_unique_respondents_for_question(self, question_id):
        """
        Cuenta el número de respondentes únicos para una pregunta específica.
        
        Args:
            question_id: ID de la pregunta
            
        Returns:
            int: Número de respondentes únicos
        """
        try:
            # Primero, obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id').eq('question_id', question_id).eq('company_id', self.company_id).execute()
            option_ids = [option['id'] for option in options.data]
            
            if not option_ids:
                # Si no hay opciones, pueden ser respuestas directas
                # Buscar respuestas directamente
                answers = self.supabase.table('answers').select('respondent_id').eq('question_id', question_id).eq('company_id', self.company_id).execute()
                unique_respondents = {answer['respondent_id'] for answer in answers.data}
                return len(unique_respondents)
            
            # Si hay opciones, contar respondentes únicos que contestaron a alguna opción
            unique_respondents = set()
            for option_id in option_ids:
                answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                for answer in answers.data:
                    unique_respondents.add(answer['respondent_id'])
                    
            return len(unique_respondents)
            
        except Exception as e:
            print(f"Error al contar respondentes únicos para pregunta {question_id}: {e}")
            return 0

    def calculate_travel_time_distribution(self):
        """
        Calcula la distribución de desplazamientos por tramo de tiempo.
        
        Los rangos de tiempo son:
        - Menos de 15 minutos
        - Entre 16 y 30 minutos
        - Entre 31 y 45 minutos
        - Entre 46 y 60 minutos
        - Más de 60 minutos
        
        Returns:
            dict: Resultados del análisis con porcentajes para cada tramo de tiempo
        """
        try:
            # Buscar la pregunta relacionada con tiempo de viaje al trabajo
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            time_question_id = None
            question_text = "Tiempo de desplazamiento al trabajo"
            
            # Palabras clave para identificar la pregunta sobre tiempo de viaje al trabajo
            time_keywords = [
                "cuántos minutos dedicas"
            ]
            
            for question in questions.data:
                if any(keyword in question['question_text'].lower() for keyword in time_keywords):
                    time_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not time_question_id:
                return {
                    "name": "Porcentaje de desplazamientos por tramo de tiempo",
                    "error": "No se encontró ninguna pregunta relacionada con el tiempo de desplazamiento al trabajo"
                }
            
            # Definir los rangos de tiempo
            time_ranges = [
                {"name": "Menos de 15 minutos", "min": 0, "max": 15, "count": 0},
                {"name": "Entre 16 y 30 minutos", "min": 16, "max": 30, "count": 0},
                {"name": "Entre 31 y 45 minutos", "min": 31, "max": 45, "count": 0},
                {"name": "Entre 46 y 60 minutos", "min": 46, "max": 60, "count": 0},
                {"name": "Más de 60 minutos", "min": 61, "max": float('inf'), "count": 0}
            ]
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', time_question_id).eq('company_id', self.company_id).execute()
            
            if not options.data:
                # Si no hay opciones preestablecidas, esta puede ser una pregunta de texto libre
                # Buscar respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', time_question_id).eq('company_id', self.company_id).execute()
                unique_respondents = set()
                
                for answer in answers.data:
                    if answer['respondent_id'] in unique_respondents:
                        continue
                        
                    unique_respondents.add(answer['respondent_id'])
                    time_value = self._extract_time_value(answer['response_value'])
                    
                    if time_value is not None:
                        # Clasificar en el rango correspondiente
                        for range_info in time_ranges:
                            if range_info["min"] <= time_value <= range_info["max"]:
                                range_info["count"] += 1
                                break
            else:
                # Si hay opciones predefinidas, buscar respuestas por opción
                for option in options.data:
                    time_value = self._extract_time_value(option['option_text'])
                    if time_value is None:
                        continue
                        
                    # Determinar a qué rango corresponde esta opción
                    matching_range = None
                    for range_info in time_ranges:
                        if range_info["min"] <= time_value <= range_info["max"]:
                            matching_range = range_info
                            break
                    
                    if matching_range:
                        # Contar respuestas para esta opción
                        answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                        matching_range["count"] += len(answers.data)
            
            # Calcular total de respondentes únicos para esta pregunta
            total_respondents = self._count_unique_respondents_for_question(time_question_id)
            
            # Calcular porcentajes
            percentages = {}
            variables = {
                "N_respuestas_válidas": total_respondents
            }
            
            for range_info in time_ranges:
                percentage = (range_info["count"] / total_respondents) * 100 if total_respondents > 0 else 0
                percentages[range_info["name"]] = round(percentage, 2)
                variables[f"N_tiempo_tramo_{range_info['min']}-{range_info['max'] if range_info['max'] != float('inf') else '+'} min"] = range_info["count"]
            
            return {
                "name": "Porcentaje de desplazamientos por tramo de tiempo",
                "question": question_text,
                "result": percentages,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de desplazamientos por tramo de tiempo",
                "error": f"Error al calcular la distribución por tramos de tiempo: {e}"
            }
    
    def _extract_time_value(self, text_value):
        """
        Extrae un valor numérico de tiempo (en minutos) de un texto.
        
        Args:
            text_value: Texto del que extraer el valor de tiempo
            
        Returns:
            float: Valor numérico de tiempo en minutos, o None si no se puede extraer
        """
        if not text_value or not isinstance(text_value, str):
            return None
            
        text_value = text_value.lower()
        
        try:
            # Intentar diferentes patrones de extracción
            
            # Patrón 1: Buscar números seguidos por "min", "minutos", etc.
            import re
            
            # Patrón 1: Buscar números seguidos por "km" o "kilómetros"
            min_patterns = [
                r'(\d+[.,]?\d*)\s*min',
                r'(\d+[.,]?\d*)\s*minutos',
                r'(\d+[.,]?\d*)\s*minuto'
            ]
            
            for pattern in min_patterns:
                match = re.search(pattern, text_value)
                if match:
                    # Reemplazar coma por punto para parsear correctamente
                    value_str = match.group(1).replace(',', '.')
                    return float(value_str)
            
            # Patrón 2: Buscar horas y convertir a minutos
            hour_patterns = [
                r'(\d+[.,]?\d*)\s*h',
                r'(\d+[.,]?\d*)\s*hora',
                r'(\d+[.,]?\d*)\s*horas'
            ]
            
            for pattern in hour_patterns:
                match = re.search(pattern, text_value)
                if match:
                    # Convertir horas a minutos
                    value_str = match.group(1).replace(',', '.')
                    return float(value_str) * 60
            
            # Patrón 3: Formato "X horas Y minutos"
            combined_pattern = r'(\d+)[^\d]*hora[^\d]*(\d+)[^\d]*minuto'
            match = re.search(combined_pattern, text_value)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                return hours * 60 + minutes
            
            # Patrón 4: Si solo hay un número en el texto, asumimos que son minutos
            numbers = re.findall(r'(\d+[.,]?\d*)', text_value)
            if len(numbers) == 1:
                return float(numbers[0].replace(',', '.'))
            
            # Patrón 5: Rangos específicos ya definidos
            range_patterns = {
                r'menos\s*de\s*15': 10,  # Valor medio para "menos de 15 minutos"
                r'entre\s*16\s*y\s*30': 23,  # Valor medio para "entre 16 y 30 minutos"
                r'entre\s*31\s*y\s*45': 38,  # Valor medio para "entre 31 y 45 minutos"
                r'entre\s*46\s*y\s*60': 53,  # Valor medio para "entre 46 y 60 minutos"
                r'más\s*de\s*60': 75  # Valor aproximado para "más de 60 minutos"
            }
            
            for pattern, value in range_patterns.items():
                if re.search(pattern, text_value):
                    return value
                    
            return None
            
        except Exception as e:
            print(f"Error al extraer valor de tiempo de '{text_value}': {e}")
            return None
            
    def get_municipality_name_by_postal_code(self, postal_code):
        """
        Gets the municipality name for a given postal code using GeoAPI.
        
        Args:
            postal_code: Postal code to get the municipality for
            
        Returns:
            str: Municipality name or None if not found
        """
        import requests
        import streamlit as st
        
        try:
            # Get the API key from secrets
            api_key = st.secrets["geoapi"]["api_key"]
            
            if not api_key:
                raise ValueError("GeoAPI key not found in secrets")

            if not postal_code.startswith("0"):
                postal_code = "0" + postal_code
            
            # Build the API URL
            url = f"https://apiv1.geoapi.es/vias?CPOS={postal_code}&type=JSON&version=2025.01&key={api_key}"
            
            # Make the request
            response = requests.get(url)
            
            # Check if request was successful
            if response.status_code != 200:
                return None
            
            # Parse the response
            data = response.json()
            
            # Check if there's data in the response
            if not data.get('data') or len(data['data']) == 0:
                return None
            
            # Get the first item and extract the municipality name
            municipality_name = data['data'][0].get('DMUN50')
            
            return municipality_name
            
        except Exception as e:
            print(f"Error getting municipality for postal code {postal_code}: {e}")
            return None

    def calculate_business_trips_percentage(self):
        """
        Calcula el porcentaje de trabajadores que realizan desplazamientos en misión 
        (desplazamientos adicionales durante la jornada laboral).
        
        Esta métrica se basa en la pregunta: "¿Realizas más desplazamientos durante tu jornada laboral?"
        con respuestas de tipo sí/no.
        
        Returns:
            dict: Resultados del análisis con el porcentaje de trabajadores que realizan desplazamientos en misión
        """
        try:
            # Buscar la pregunta relacionada con desplazamientos en misión
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            mission_question_id = None
            question_text = "Desplazamientos durante jornada laboral"
            
            # Palabras clave para identificar la pregunta sobre desplazamientos en misión
            mission_keywords = [
                "desplazamientos durante", "más desplazamientos", "otros desplazamientos", 
                "desplazamientos adicionales", "desplazamiento en misión"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                if any(keyword in question['question_text'].lower() for keyword in mission_keywords):
                    mission_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not mission_question_id:
                return {
                    "name": "Porcentaje de trabajadores que realizan desplazamientos en misión",
                    "error": "No se encontró ninguna pregunta relacionada con desplazamientos en misión"
                }
            
            # Obtener todas las opciones para esta pregunta (Sí/No)
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', mission_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            yes_count = 0
            no_count = 0
            
            # Almacenar IDs de respondentes que realizan desplazamientos en misión
            mission_respondents = set()
            
            # Si hay opciones predefinidas (típico para preguntas sí/no)
            if options.data:
                for option in options.data:
                    # Normalizar el texto de la opción
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar si es una respuesta afirmativa o negativa
                    is_affirmative = any(word in option_text for word in ['sí', 'si', 'yes', 'true', '1'])
                    
                    # Contar las respuestas para esta opción
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                    
                    # Procesar respuestas
                    for answer in answers.data:
                        if is_affirmative:
                            yes_count += 1
                            # Guardar el ID del respondente para uso en otras fórmulas
                            mission_respondents.add(answer['respondent_id'])
                        else:
                            no_count += 1
            else:
                # Si es una pregunta de texto libre, intentar analizar las respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', mission_question_id).eq('company_id', self.company_id).execute()
                unique_respondents = set()
                
                for answer in answers.data:
                    if answer['respondent_id'] in unique_respondents:
                        continue
                    
                    unique_respondents.add(answer['respondent_id'])
                    response_text = answer['response_value'].lower().strip()
                    
                    # Analizar si la respuesta es afirmativa o negativa
                    if any(word in response_text for word in ['sí', 'si', 'yes', 'true', '1', 'verdadero', 'afirmativo']):
                        yes_count += 1
                        # Guardar el ID del respondente para uso en otras fórmulas
                        mission_respondents.add(answer['respondent_id'])
                    elif any(word in response_text for word in ['no', 'false', '0', 'falso', 'negativo']):
                        no_count += 1
            
            # Guardar los IDs de respondentes con misiones para uso en otras fórmulas
            self.mission_respondents = mission_respondents
            
            # Total de respuestas válidas
            total_valid_responses = yes_count + no_count
            
            # Calcular porcentajes
            yes_percentage = (yes_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            no_percentage = (no_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            
            # Preparar resultado
            result = {
                "Sí": round(yes_percentage, 2),
                "No": round(no_percentage, 2)
            }
            
            variables = {
                "N_respuestas_válidas": total_valid_responses,
                "N_misión": yes_count,
                "N_no_misión": no_count
            }
            
            return {
                "name": "Porcentaje de trabajadores que realizan desplazamientos en misión",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de trabajadores que realizan desplazamientos en misión",
                "error": f"Error al calcular el porcentaje de trabajadores con desplazamientos en misión: {e}"
            }
            
    def calculate_business_trips_own_car_percentage(self):
        """
        Calcula el porcentaje de viajeros en misión (trabajadores que realizan desplazamientos
        durante su jornada laboral) que utilizan coche propio.
        
        Esta métrica se basa en la pregunta: "¿El vehículo que utilizas para ir al trabajo 
        es propiedad de la compañía?" y se calcula solo sobre el subconjunto de trabajadores
        que indicaron que realizan desplazamientos en misión.
        
        La fórmula es: Porcentaje_misión_coche (%) = N_misión_coche_prop / N_misión × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de viajeros en misión que usan coche propio
        """
        try:
            # Verificar que tenemos la lista de respondentes que realizan desplazamientos en misión
            if not hasattr(self, 'mission_respondents') or not self.mission_respondents:
                # Si no tenemos los datos, ejecutamos primero el cálculo de misiones
                business_trips = self.calculate_business_trips_percentage()
                # Verificar si hubo error
                if "error" in business_trips:
                    return {
                        "name": "Porcentaje de viajeros en misión que usan coche propio",
                        "error": "No se pudieron identificar los trabajadores que realizan desplazamientos en misión"
                    }
            
            # Si no hay trabajadores con desplazamientos en misión, retornar resultado vacío
            if not hasattr(self, 'mission_respondents') or len(self.mission_respondents) == 0:
                return {
                    "name": "Porcentaje de viajeros en misión que usan coche propio",
                    "error": "No hay trabajadores identificados que realicen desplazamientos en misión"
                }
            
            # Buscar la pregunta relacionada con la propiedad del vehículo
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            car_ownership_question_id = None
            question_text = "Propiedad del vehículo usado para desplazamientos"
            
            # Palabras clave para identificar la pregunta sobre la propiedad del vehículo
            car_keywords = [
                "vehículo que utilizas", "coche que utilizas", "vehículo propiedad", 
                "coche propio", "coche de empresa", "vehículo de empresa", "propiedad de la compañía"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                if any(keyword in question_lower for keyword in car_keywords):
                    car_ownership_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not car_ownership_question_id:
                return {
                    "name": "Porcentaje de viajeros en misión que usan coche propio",
                    "error": "No se encontró ninguna pregunta relacionada con la propiedad del vehículo"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', car_ownership_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            company_car_count = 0
            own_car_count = 0
            
            # Si hay opciones predefinidas
            if options.data:
                for option in options.data:
                    # Normalizar el texto de la opción
                    option_text = option['option_text'].lower().strip()
                    
                    # Para la pregunta "¿El vehículo que utilizas para ir al trabajo es propiedad de la compañía?"
                    # Si = coche de empresa, No = coche propio
                    is_company_car = any(word in option_text for word in ['sí', 'si', 'yes', 'true', '1'])
                    
                    # Contar solo las respuestas de los trabajadores que hacen desplazamientos en misión
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                    
                    for answer in answers.data:
                        # Solo contar si el respondente está en nuestra lista de desplazamientos en misión
                        if answer['respondent_id'] in self.mission_respondents:
                            if is_company_car:
                                company_car_count += 1
                            else:
                                own_car_count += 1
            else:
                # Si es una pregunta de texto libre, intentar analizar las respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', car_ownership_question_id).eq('company_id', self.company_id).execute()
                
                for answer in answers.data:
                    # Solo procesar si el respondente está en nuestra lista de desplazamientos en misión
                    if answer['respondent_id'] in self.mission_respondents:
                        response_text = answer['response_value'].lower().strip()
                        
                        # Para la pregunta "¿El vehículo que utilizas para ir al trabajo es propiedad de la compañía?"
                        # Si = coche de empresa, No = coche propio
                        if any(word in response_text for word in ['sí', 'si', 'yes', 'true', '1', 'verdadero', 'afirmativo']):
                            company_car_count += 1
                        else:
                            own_car_count += 1
            
            # Total de respuestas válidas (solo entre los que hacen desplazamientos en misión)
            total_mission_car_respondents = company_car_count + own_car_count
            
            # Calcular porcentajes
            company_car_percentage = (company_car_count / total_mission_car_respondents) * 100 if total_mission_car_respondents > 0 else 0
            own_car_percentage = (own_car_count / total_mission_car_respondents) * 100 if total_mission_car_respondents > 0 else 0
            
            # Preparar resultado
            result = {
                "Coche propio": round(own_car_percentage, 2),
                "Coche de empresa": round(company_car_percentage, 2)
            }
            
            variables = {
                "N_misión": len(self.mission_respondents),
                "N_misión_coche_respuestas": total_mission_car_respondents,
                "N_misión_coche_prop": own_car_count,
                "N_misión_coche_empresa": company_car_count
            }
            
            return {
                "name": "Porcentaje de viajeros en misión que usan coche propio",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de viajeros en misión que usan coche propio",
                "error": f"Error al calcular el porcentaje de viajeros en misión con coche propio: {e}"
            }
            
    def calculate_engine_type_percentage(self):
        """
        Calcula el porcentaje de vehículos por tipo de motor.
        
        Esta métrica analiza qué tipo de motor tienen los vehículos utilizados por los trabajadores
        (gasolina, diésel, eléctrico, híbrido, etc.).
        
        La fórmula es: Porcentaje_motor (%) = N_motor_tipo / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con los porcentajes por tipo de motor
        """
        try:
            # Buscar la pregunta relacionada con el tipo de motor del vehículo
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            engine_question_id = None
            question_text = "Tipo de motor del vehículo"
            
            # Palabras clave para identificar la pregunta sobre el tipo de motor
            engine_keywords = [
                "tipo de motor", "tipo de vehículo", "combustible", "propulsión", 
                "tipo de combustible", "motor del vehículo", "motor de tu vehículo",
                "motor de tu coche", "tipo de coche"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                if any(keyword in question_lower for keyword in engine_keywords):
                    engine_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not engine_question_id:
                return {
                    "name": "Porcentaje por tipo de motor del vehículo",
                    "error": "No se encontró ninguna pregunta relacionada con el tipo de motor del vehículo"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', engine_question_id).eq('company_id', self.company_id).execute()
            
            # Categorías de tipos de motor y contadores
            engine_types = {
                "Gasolina": 0,
                "Diésel": 0,
                "Híbrido": 0,
                "Eléctrico": 0,
                "Gas (GLP/GNC)": 0,
                "Otro": 0
            }
            
            # Mapeo de términos comunes a categorías estandarizadas
            engine_mapping = {
                # Gasolina
                "gasolina": "Gasolina",
                "gasoil": "Gasolina",
                "gasolin": "Gasolina",
                # Diésel
                "diesel": "Diésel",
                "diésel": "Diésel",
                "gasóleo": "Diésel",
                # Híbrido
                "hybrid": "Híbrido",
                "híbrido": "Híbrido",
                "hibrido": "Híbrido",
                "mild hybrid": "Híbrido",
                "híbrido enchufable": "Híbrido",
                "híbrido plug-in": "Híbrido",
                "phev": "Híbrido",
                # Eléctrico
                "eléctrico": "Eléctrico",
                "electrico": "Eléctrico",
                "electric": "Eléctrico",
                "ev": "Eléctrico",
                "bev": "Eléctrico",
                # Gas
                "glp": "Gas (GLP/GNC)",
                "gnc": "Gas (GLP/GNC)",
                "gas": "Gas (GLP/GNC)",
                "autogas": "Gas (GLP/GNC)",
                "lpg": "Gas (GLP/GNC)",
                "cng": "Gas (GLP/GNC)"
            }
            
            # Respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                for option in options.data:
                    # Normalizar el texto de la opción
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar la categoría del motor
                    engine_category = "Otro"  # Por defecto
                    
                    # Buscar coincidencia en el mapeo
                    for keyword, category in engine_mapping.items():
                        if keyword in option_text:
                            engine_category = category
                            break
                    
                    # Contar respuestas para esta opción
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                    
                    # Actualizar el contador de esta categoría
                    count = len(answers.data)
                    engine_types[engine_category] += count
                    
                    # Añadir los respondentes
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        
            else:
                # Si es una pregunta de texto libre, intentar analizar las respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', engine_question_id).eq('company_id', self.company_id).execute()
                
                # Procesamos respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Identificar la categoría del motor
                    engine_category = "Otro"  # Por defecto
                    
                    # Buscar coincidencia en el mapeo
                    for keyword, category in engine_mapping.items():
                        if keyword in response_text:
                            engine_category = category
                            break
                    
                    # Actualizar el contador de esta categoría
                    engine_types[engine_category] += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            # Eliminar categorías con cero respuestas
            engine_types = {k: v for k, v in engine_types.items() if v > 0}
            
            # Calcular porcentajes
            percentages = {}
            for engine_type, count in engine_types.items():
                percentage = (count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
                percentages[engine_type] = round(percentage, 2)
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_valid_responses
            }
            
            # Añadir contadores específicos por tipo de motor
            for engine_type, count in engine_types.items():
                safe_engine_type = engine_type.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                variables[f"N_motor_{safe_engine_type}"] = count
            
            return {
                "name": "Porcentaje por tipo de motor del vehículo",
                "question": question_text,
                "result": percentages,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje por tipo de motor del vehículo",
                "error": f"Error al calcular el porcentaje por tipo de motor del vehículo: {e}"
            }

    def calculate_ev_purchase_intention_percentage(self):
        """
        Calcula el porcentaje de intención de compra de vehículo eléctrico.
        
        Esta métrica analiza cuántos trabajadores tienen previsto adquirir un vehículo
        eléctrico en el futuro. 
        
        La fórmula es: Porcentaje_intención_VE (%) = N_intención_compra_VE / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de intención de compra
        """
        try:
            # Buscar la pregunta relacionada con la intención de compra de vehículo eléctrico
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            ev_intention_question_id = None
            question_text = "Intención de compra de vehículo eléctrico"
            
            # Palabras clave para identificar la pregunta sobre intención de compra de vehículo eléctrico
            ev_intention_keywords = [
                "previsto adquirir", "piensas comprar", "intención de compra", 
                "comprarías un vehículo eléctrico", "comprarás un vehículo eléctrico",
                "prevé adquirir", "previsión de compra", "planeas adquirir"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con intención de compra y vehículo eléctrico
                if "eléctrico" in question_lower and any(keyword in question_lower for keyword in ev_intention_keywords):
                    ev_intention_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not ev_intention_question_id:
                return {
                    "name": "Porcentaje de intención de compra de vehículo eléctrico",
                    "error": "No se encontró ninguna pregunta relacionada con la intención de compra de vehículo eléctrico"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', ev_intention_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            car_count = 0    # Sí, coche eléctrico
            moto_count = 0   # Sí, moto eléctrica
            no_count = 0     # No
            unsure_count = 0  # Respuestas no clasificadas
            
            # Respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                for option in options.data:
                    # Normalizar el texto de la opción
                    option_text = option['option_text'].lower().strip()
                    
                    # Clasificar la respuesta según los valores específicos
                    is_car = "coche eléctrico" in option_text
                    is_moto = "moto eléctrica" in option_text
                    is_no = option_text == "no" or option_text.startswith("no,")
                    
                    # Contar respuestas para esta opción
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                    
                    count = len(answers.data)
                    
                    # Clasificar y contar
                    if is_car:
                        car_count += count
                    elif is_moto:
                        moto_count += count
                    elif is_no:
                        no_count += count
                    else:
                        unsure_count += count
                
                    # Añadir los respondentes
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        
            else:
                # Si es una pregunta de texto libre, intentar analizar las respuestas directamente
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', ev_intention_question_id).eq('company_id', self.company_id).execute()
                
                # Procesamos respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Clasificar la respuesta según los valores específicos
                    is_car = "coche eléctrico" in response_text
                    is_moto = "moto eléctrica" in response_text
                    is_no = response_text == "no" or response_text.startswith("no,")
                    
                    # Contar por categoría
                    if is_car:
                        car_count += 1
                    elif is_moto:
                        moto_count += 1
                    elif is_no:
                        no_count += 1
                    else:
                        unsure_count += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            # Calcular porcentajes
            car_percentage = (car_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            moto_percentage = (moto_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            no_percentage = (no_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            unsure_percentage = (unsure_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            
            # Preparar resultado
            result = {
                "Sí, coche eléctrico": round(car_percentage, 2),
                "Sí, moto eléctrica": round(moto_percentage, 2),
                "No": round(no_percentage, 2)
            }
            
            # Añadir "No sabe/No contesta" solo si hay respuestas en esta categoría
            if unsure_count > 0:
                result["No sabe/No contesta"] = round(unsure_percentage, 2)
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_valid_responses,
                "N_intención_compra_coche": car_count,
                "N_intención_compra_moto": moto_count,
                "N_no_intención_compra": no_count,
                "N_no_sabe": unsure_count
            }
            
            return {
                "name": "Porcentaje de intención de compra de vehículo eléctrico",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de intención de compra de vehículo eléctrico",
                "error": f"Error al calcular el porcentaje de intención de compra de vehículo eléctrico: {e}"
            }

    def calculate_free_parking_percentage(self):
        """
        Calcula el porcentaje de trabajadores con aparcamiento gratuito en la empresa.
        
        Esta métrica analiza cuántos trabajadores tienen acceso a aparcamiento gratuito
        en su centro de trabajo.
        
        La fórmula es: Porcentaje_parking_gratuito (%) = N_aparcamiento_gratuito / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de trabajadores con aparcamiento gratuito
        """
        try:
            # Buscar la pregunta relacionada con el lugar de aparcamiento
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            parking_question_id = None
            question_text = "Lugar de aparcamiento habitual"
            
            # Palabras clave para identificar la pregunta sobre lugar de aparcamiento
            parking_keywords = [
                "lugar de aparcamiento",
                "aparcamiento", "aparcar", "parking", "estacionamiento", "estacionar",
                "lugar donde aparcas", "lugar donde estacionas", "donde aparcar"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con aparcamiento
                if "aparcamiento" in question_lower or "parking" in question_lower or any(keyword in question_lower for keyword in parking_keywords):
                    parking_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not parking_question_id:
                return {
                    "name": "Porcentaje con aparcamiento gratuito en la empresa",
                    "error": "No se encontró ninguna pregunta relacionada con el lugar de aparcamiento"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', parking_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            workplace_parking_count = 0  # Aparcamiento del centro de trabajo
            total_responses = 0
            
            # Respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Identificar la opción de "Aparcamiento del centro de trabajo"
                workplace_parking_option_ids = []
                
                for option in options.data:
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar si la opción es "Aparcamiento del centro de trabajo"
                    if "centro de trabajo" in option_text and ("aparcamiento" in option_text or "parking" in option_text):
                        workplace_parking_option_ids.append(option['id'])
                
                # Si encontramos la opción, contamos las respuestas
                if workplace_parking_option_ids:
                    for option_id in workplace_parking_option_ids:
                        answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                        for answer in answers.data:
                            respondents.add(answer['respondent_id'])
                            workplace_parking_count += 1
                
                # Obtener el total de respuestas a esta pregunta
                for option in options.data:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option['id']).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                
                total_responses = len(respondents)
            
            else:
                # Si es una pregunta de texto libre, intentar analizar las respuestas
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', parking_question_id).eq('company_id', self.company_id).execute()
                
                # Procesamos respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                workplace_keywords = ["centro de trabajo", "empresa", "trabajo", "oficina", "centro laboral"]
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Identificar si es aparcamiento en el centro de trabajo
                    if any(keyword in response_text for keyword in workplace_keywords):
                        workplace_parking_count += 1
                
                total_responses = len(respondents)
            
            # Si no hay respuestas, devolver error
            if total_responses == 0:
                return {
                    "name": "Porcentaje con aparcamiento gratuito en la empresa",
                    "error": "No se encontraron respuestas a la pregunta sobre lugar de aparcamiento"
                }
            
            # Calcular porcentaje
            workplace_parking_percentage = (workplace_parking_count / total_responses) * 100
            
            # Preparar resultado
            result = {
                "Aparcamiento gratuito en empresa": round(workplace_parking_percentage, 2),
                "Otro tipo de aparcamiento": round(100 - workplace_parking_percentage, 2)
            }
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_responses,
                "N_aparcamiento_gratuito": workplace_parking_count,
            }
            
            return {
                "name": "Porcentaje con aparcamiento gratuito en la empresa",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje con aparcamiento gratuito en la empresa",
                "error": f"Error al calcular el porcentaje con aparcamiento gratuito: {e}"
            }

    def calculate_no_parking_problems_percentage(self):
        """
        Calcula el porcentaje de trabajadores que no perciben problemas de aparcamiento.
        
        Esta métrica analiza cuántos trabajadores consideran que no hay problemas
        de estacionamiento en su lugar de trabajo.
        
        La fórmula es: Porcentaje_sin_problemas_parking (%) = N_sin_problemas_parking / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de trabajadores sin problemas de aparcamiento
        """
        try:
            # Buscar la pregunta relacionada con los problemas de aparcamiento
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            parking_problems_question_id = None
            question_text = "Problemas de estacionamiento"
            
            # Palabras clave para identificar la pregunta sobre problemas de aparcamiento
            parking_problems_keywords = [
                "problemas de estacionamiento", "problemas de aparcamiento", 
                "dificultades para aparcar", "dificultad para estacionar",
                "problema de parking", "estacionar con dificultad"
            ]
           
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con problemas de aparcamiento
                if "problema" in question_lower and ("aparcamiento" in question_lower or "estacionamiento" in question_lower or "parking" in question_lower):
                    parking_problems_question_id = question['id']
                    question_text = question['question_text']
                    break
                elif any(keyword in question_lower for keyword in parking_problems_keywords):
                    parking_problems_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not parking_problems_question_id:
                return {
                    "name": "Porcentaje que no percibe problemas de aparcamiento",
                    "error": "No se encontró ninguna pregunta relacionada con problemas de aparcamiento"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', parking_problems_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            no_problems_count = 0  # Conteo de "No" (no hay problemas)
            yes_problems_count = 0  # Conteo de "Sí" (sí hay problemas)
            
            # Respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Identificar opciones que representan "No" (no hay problemas)
                no_option_ids = []
                yes_option_ids = []
                
                for option in options.data:
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar si la opción es "no" (no hay problemas)
                    if option_text == "no" or option_text.startswith("no "):
                        no_option_ids.append(option['id'])
                    
                    # Identificar si la opción es "sí" (sí hay problemas)
                    elif option_text == "sí" or option_text == "si" or option_text.startswith("sí ") or option_text.startswith("si "):
                        yes_option_ids.append(option['id'])
                
                # Contar respuestas para cada tipo de opción
                for option_id in no_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        no_problems_count += 1
                
                for option_id in yes_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        yes_problems_count += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', parking_problems_question_id).eq('company_id', self.company_id).execute()
                
                # Procesar respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Detectar respuestas negativas (no hay problemas)
                    if response_text == "no" or response_text.startswith("no "):
                        no_problems_count += 1
                    
                    # Detectar respuestas afirmativas (sí hay problemas)
                    elif response_text == "sí" or response_text == "si" or response_text.startswith("sí ") or response_text.startswith("si "):
                        yes_problems_count += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            if total_valid_responses == 0:
                return {
                    "name": "Porcentaje que no percibe problemas de aparcamiento",
                    "error": "No se encontraron respuestas a la pregunta sobre problemas de aparcamiento"
                }
            
            # Calcular porcentajes
            no_problems_percentage = (no_problems_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            yes_problems_percentage = (yes_problems_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            
            # Preparar resultado
            result = {
                "No percibe problemas": round(no_problems_percentage, 2),
                "Sí percibe problemas": round(yes_problems_percentage, 2)
            }
            
            # Otras respuestas (si las hay)
            other_responses = total_valid_responses - (no_problems_count + yes_problems_count)
            if other_responses > 0:
                other_percentage = (other_responses / total_valid_responses) * 100
                result["Sin clasificar"] = round(other_percentage, 2)
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_valid_responses,
                "N_sin_problemas_parking": no_problems_count,
                "N_con_problemas_parking": yes_problems_count
            }
            
            return {
                "name": "Porcentaje que no percibe problemas de aparcamiento",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje que no percibe problemas de aparcamiento",
                "error": f"Error al calcular el porcentaje que no percibe problemas de aparcamiento: {e}"
            }

    def calculate_public_transport_barriers_percentage(self):
        """
        Calcula el porcentaje por barrera al uso del transporte público.
        
        Esta métrica analiza las razones principales por las que los trabajadores
        no utilizan el transporte público y calcula el porcentaje para cada barrera.
        
        La fórmula es: Porcentaje_barrera (%) = N_mención_barrera / N_respuestas_pregunta × 100
        
        Returns:
            dict: Resultados del análisis con los porcentajes de cada barrera al transporte público
        """
        try:
            # Buscar la pregunta relacionada con barreras al transporte público
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            barriers_question_id = None
            question_text = "Barreras al uso del transporte público"
            
            # Palabras clave para identificar la pregunta sobre barreras al transporte público
            barriers_keywords = [
                "razones", "motivos", "barreras", "limitaciones", "dificultades", 
                "no utilizas", "no usas", "no usar", "no utilizar", "impiden utilizar",
                "impiden usar", "por qué no", "razón por la que no"
            ]
           
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con barreras y transporte público
                if any(keyword in question_lower for keyword in barriers_keywords):
                    barriers_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not barriers_question_id:
                return {
                    "name": "Porcentaje por barrera al uso de transporte público",
                    "error": "No se encontró ninguna pregunta relacionada con barreras al uso de transporte público"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', barriers_question_id).eq('company_id', self.company_id).execute()
            
            # Recopilar información de las opciones
            option_counts = {}  # Conteo de menciones por opción
            option_texts = {}   # Texto de cada opción para el resultado
            
            # Lista de respondentes únicos
            respondents = set()
            
            # Si hay opciones predefinidas (pregunta de opción múltiple)
            if options.data:
                # Mapeo de IDs de opciones a textos de opciones
                for option in options.data:
                    option_id = option['id']
                    option_text = option['option_text'].strip()
                    option_texts[option_id] = option_text
                    option_counts[option_id] = 0
                
                # Contar menciones para cada opción
                all_answers = self.supabase.table('answers').select('respondent_id', 'option_id').eq('question_id', barriers_question_id).eq('company_id', self.company_id).execute()
                
                for answer in all_answers.data:
                    respondents.add(answer['respondent_id'])
                    option_id = answer['option_id']
                    if option_id in option_counts:
                        option_counts[option_id] += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', barriers_question_id).eq('company_id', self.company_id).execute()
                
                # Conjunto de palabras clave para clasificar respuestas textuales
                common_barriers = {
                    "economico": ["económico", "ahorro", "barato", "precio", "costo", "dinero", "tarifa"],
                    "ecologico": ["ecológico", "medio ambiente", "contaminación", "sostenible", "verde"],
                    "comodidad": ["cómodo", "comodidad", "confort", "leer", "descansar", "relajarse"],
                    "rapidez": ["rápido", "rapidez", "tiempo", "duración", "corto"],
                    "no_aparcar": ["aparcar", "aparcamiento", "parking", "estacionar"],
                    "stress": ["estrés", "tranquilidad", "relax", "no conducir", "tráfico"],
                    "unico_disponible": ["única opción", "única alternativa", "no hay más", "obligado"]
                }
                
                # Inicializar contadores para cada barrera común
                for barrier_key in common_barriers:
                    option_counts[barrier_key] = 0
                    option_texts[barrier_key] = barrier_key.replace("_", " ").title()
                
                # Contar menciones para cada barrera identificada en el texto libre
                for answer in answers.data:
                    respondent_id = answer['respondent_id']
                    respondents.add(respondent_id)
                    
                    response_text = answer['response_value'].lower()
                    
                    # Verificar qué barreras se mencionan en la respuesta
                    for barrier_key, keywords in common_barriers.items():
                        if any(keyword in response_text for keyword in keywords):
                            option_counts[barrier_key] += 1
            
            # Total de respondentes que contestaron la pregunta
            total_respondents = len(respondents)
            
            if total_respondents == 0:
                return {
                    "name": "Porcentaje por barrera al uso de transporte público",
                    "error": "No se encontraron respuestas a la pregunta sobre barreras al transporte público"
                }
            
            # Calcular porcentajes y preparar resultado
            result = {}
            detailed_result = {}
            variables = {"N_respuestas_pregunta": total_respondents}
            
            # Ordenar las opciones por frecuencia de mención (mayor a menor)
            sorted_options = sorted(option_counts.items(), key=lambda x: x[1], reverse=True)
            
            for option_id, count in sorted_options:
                if count > 0:  # Solo incluir barreras que fueron mencionadas
                    option_name = option_texts[option_id]
                    percentage = (count / total_respondents) * 100
                    
                    # Para el resultado principal, mostrar solo las barreras más frecuentes
                    if len(result) < 5:  # Limitar a las 5 barreras más mencionadas para el resultado principal
                        result[option_name] = round(percentage, 2)
                    
                    # Incluir todas las barreras en el resultado detallado
                    detailed_result[option_name] = round(percentage, 2)
                    
                    # Guardar el conteo en las variables
                    variables[f"N_{option_id}"] = count
            
            return {
                "name": "Porcentaje por barrera al uso de transporte público",
                "question": question_text,
                "result": result,
                "detailed_result": detailed_result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje por barrera al uso de transporte público",
                "error": f"Error al calcular el porcentaje por barrera al uso de transporte público: {e}"
            }
            
    def calculate_public_transport_motivations_percentage(self):
        """
        Calcula el porcentaje de motivaciones para usar el transporte público.
        
        Esta métrica analiza las razones principales por las que los trabajadores
        utilizan el transporte público y calcula el porcentaje para cada motivación.
        
        La fórmula es: Porcentaje_motivo_TP (%) = N_mención_motivo_TP / N_usuarios_TP_respuestas × 100
        
        Returns:
            dict: Resultados del análisis con los porcentajes de cada motivación para usar transporte público
        """
        try:
            # Buscar la pregunta relacionada con motivaciones para usar transporte público
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            motivations_question_id = None
            question_text = "Motivaciones para usar transporte público"
            
            # Palabras clave para identificar la pregunta sobre motivaciones
            motivations_keywords = [
                "principales motivos",
                "por qué utilizas", "por qué usas", "motivo", "razón", "motivación", 
                "incentivo", "ventaja", "beneficio", "factor", "favorable",
                "preferencia", "elección", "decisión de usar"
            ]
            
            transport_keywords = [
                "transporte público", "autobús", "bus", "metro", "tren", "tranvía", "cercanías"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con motivaciones y transporte público
                transport_mentioned = any(keyword in question_lower for keyword in transport_keywords)
                motivation_mentioned = any(keyword in question_lower for keyword in motivations_keywords)
                
                if transport_mentioned and motivation_mentioned:
                    motivations_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not motivations_question_id:
                return {
                    "name": "Porcentaje de motivaciones para usar transporte público",
                    "error": "No se encontró ninguna pregunta relacionada con motivaciones para usar transporte público"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', motivations_question_id).eq('company_id', self.company_id).execute()
            
            # Recopilar información de las opciones
            option_counts = {}  # Conteo de menciones por opción
            option_texts = {}   # Texto de cada opción para el resultado
            
            # Lista de respondentes únicos (usuarios de transporte público que respondieron)
            respondents = set()
            
            # Si hay opciones predefinidas (pregunta de opción múltiple)
            if options.data:
                # Mapeo de IDs de opciones a textos de opciones
                for option in options.data:
                    option_id = option['id']
                    option_text = option['option_text'].strip()
                    option_texts[option_id] = option_text
                    option_counts[option_id] = 0
                
                # Contar menciones para cada opción
                all_answers = self.supabase.table('answers').select('respondent_id', 'option_id').eq('question_id', motivations_question_id).eq('company_id', self.company_id).execute()
                
                for answer in all_answers.data:
                    respondents.add(answer['respondent_id'])
                    option_id = answer['option_id']
                    if option_id in option_counts:
                        option_counts[option_id] += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', motivations_question_id).eq('company_id', self.company_id).execute()
                
                # Conjunto de palabras clave para clasificar respuestas textuales
                common_motivations = {
                    "economico": ["económico", "ahorro", "barato", "precio", "costo", "dinero", "tarifa"],
                    "ecologico": ["ecológico", "medio ambiente", "contaminación", "sostenible", "verde"],
                    "comodidad": ["cómodo", "comodidad", "confort", "leer", "descansar", "relajarse"],
                    "rapidez": ["rápido", "rapidez", "tiempo", "duración", "corto"],
                    "no_aparcar": ["aparcar", "aparcamiento", "parking", "estacionar"],
                    "stress": ["estrés", "tranquilidad", "relax", "no conducir", "tráfico"],
                    "unico_disponible": ["única opción", "única alternativa", "no hay más", "obligado"]
                }
                
                # Inicializar contadores para cada motivación común
                for motivation_key in common_motivations:
                    option_counts[motivation_key] = 0
                    option_texts[motivation_key] = motivation_key.replace("_", " ").title()
                
                # Contar menciones para cada motivación identificada en el texto libre
                for answer in answers.data:
                    respondent_id = answer['respondent_id']
                    respondents.add(respondent_id)
                    
                    response_text = answer['response_value'].lower()
                    
                    # Verificar qué motivaciones se mencionan en la respuesta
                    for motivation_key, keywords in common_motivations.items():
                        if any(keyword in response_text for keyword in keywords):
                            option_counts[motivation_key] += 1
            
            # Total de usuarios de transporte público que respondieron
            total_respondents = len(respondents)
            
            if total_respondents == 0:
                return {
                    "name": "Porcentaje de motivaciones para usar transporte público",
                    "error": "No se encontraron respuestas a la pregunta sobre motivaciones para usar transporte público"
                }
            
            # Calcular porcentajes y preparar resultado
            result = {}
            detailed_result = {}
            variables = {"N_usuarios_TP_respuestas": total_respondents}
            
            # Ordenar las opciones por frecuencia de mención (mayor a menor)
            sorted_options = sorted(option_counts.items(), key=lambda x: x[1], reverse=True)
            
            for option_id, count in sorted_options:
                if count > 0:  # Solo incluir motivaciones que fueron mencionadas
                    option_name = option_texts[option_id]
                    percentage = (count / total_respondents) * 100
                    
                    # Para el resultado principal, mostrar solo las motivaciones más frecuentes
                    if len(result) < 5:  # Limitar a las 5 motivaciones más mencionadas para el resultado principal
                        result[option_name] = round(percentage, 2)
                    
                    # Incluir todas las motivaciones en el resultado detallado
                    detailed_result[option_name] = round(percentage, 2)
                    
                    # Guardar el conteo en las variables
                    variables[f"N_mención_{option_id}"] = count
            
            return {
                "name": "Porcentaje de motivaciones para usar transporte público",
                "question": question_text,
                "result": result,
                "detailed_result": detailed_result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de motivaciones para usar transporte público",
                "error": f"Error al calcular el porcentaje de motivaciones para usar transporte público: {e}"
            }
            
    def calculate_car_sharing_willingness_percentage(self):
        """
        Calcula el porcentaje de trabajadores dispuestos a compartir coche.
        
        Esta métrica analiza la disposición de los trabajadores a participar en
        iniciativas de coche compartido (carpooling) con otros empleados.
        
        La fórmula es: Porcentaje_dispuestos_compartir (%) = N_dispuestos_compartir / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de disposición a compartir coche
        """
        try:
            # Buscar la pregunta relacionada con la disposición a compartir coche
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            car_sharing_question_id = None
            question_text = "Disposición a compartir coche"
            
            # Palabras clave para identificar la pregunta sobre compartir coche
            car_sharing_keywords = [
                "compartir coche", "compartir vehículo", "coche compartido", 
                "carpooling", "car sharing", "car-sharing", "carpool",
                "dispuesto a compartir", "compartirías", "compartirías tu coche", 
                "compartir trayecto"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                if any(keyword in question_lower for keyword in car_sharing_keywords):
                    car_sharing_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not car_sharing_question_id:
                return {
                    "name": "Porcentaje de disposición a compartir coche",
                    "error": "No se encontró ninguna pregunta relacionada con compartir coche"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', car_sharing_question_id).eq('company_id', self.company_id).execute()
            
            # Diccionario para almacenar el conteo por cada opción
            option_counts = {}
            
            # Lista de respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Crear mapeo de ID de opción a texto de opción
                option_id_to_text = {}
                for option in options.data:
                    option_id_to_text[option['id']] = option['option_text']
                    option_counts[option['option_text']] = 0
                
                # Contar respuestas para cada opción
                for option_id, option_text in option_id_to_text.items():
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        option_counts[option_text] += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', car_sharing_question_id).eq('company_id', self.company_id).execute()
                
                # Procesar respuestas
                for answer in answers.data:
                    response_text = answer['response_value'].strip()
                    respondents.add(answer['respondent_id'])
                    
                    # Incrementar contador para esta respuesta
                    if response_text not in option_counts:
                        option_counts[response_text] = 0
                    option_counts[response_text] += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            if total_valid_responses == 0:
                return {
                    "name": "Porcentaje de disposición a compartir coche",
                    "error": "No se encontraron respuestas a la pregunta sobre compartir coche"
                }
            
            # Calcular porcentajes
            result = {}
            variables = {
                "N_respuestas_válidas": total_valid_responses
            }
            
            # Ordenar las opciones por número de respuestas (de mayor a menor)
            sorted_options = sorted(option_counts.items(), key=lambda x: x[1], reverse=True)
            
            for option_text, count in sorted_options:
                if count == 0:
                    continue
                percentage = (count / total_valid_responses) * 100
                result[option_text] = round(percentage, 2)
                variables[f"N_{option_text.replace(' ', '_')}"] = count
            
            return {
                "name": "Porcentaje de disposición a compartir coche",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje de disposición a compartir coche",
                "error": f"Error al calcular el porcentaje de disposición a compartir coche: {e}"
            }
            
    def calculate_public_transport_lines_awareness_percentage(self):
        """
        Calcula el porcentaje de trabajadores que conocen las líneas de transporte público cercanas a su lugar de trabajo.
        
        Esta métrica analiza el conocimiento que tienen los trabajadores sobre las opciones
        de transporte público disponibles cerca de su centro de trabajo.
        
        La fórmula es: Porcentaje_conoce_líneas_TP (%) = N_conoce_líneas_TP / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de conocimiento de líneas de transporte público
        """
        try:
            # Buscar la pregunta relacionada con el conocimiento de líneas de transporte público
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            awareness_question_id = None
            question_text = "Conocimiento de líneas de transporte público"
            
            # Palabras clave para identificar la pregunta sobre conocimiento de líneas de transporte público
            awareness_keywords = [
                "conoces las líneas", "conoces líneas", "conoce las líneas", "conoce líneas",
                "conoces el transporte público", "conoces las rutas", "conoces rutas",
                "sabes qué líneas", "sabes que líneas", "sabes qué rutas", "sabes que rutas",
                "conocimiento de líneas", "conocimiento de rutas", "conocimiento del transporte público",
                "líneas de autobús", "líneas de metro", "líneas de tren", "líneas cercanas",
                "transporte público cercano", "transporte público próximo"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con conocimiento de líneas de transporte público
                if any(keyword in question_lower for keyword in awareness_keywords):
                    awareness_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not awareness_question_id:
                return {
                    "name": "Porcentaje que conoce líneas de transporte público cercanas",
                    "error": "No se encontró ninguna pregunta relacionada con el conocimiento de líneas de transporte público"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', awareness_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            aware_count = 0      # Conocen las líneas (Sí)
            unaware_count = 0    # No conocen las líneas (No)
            
            # Lista de respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Identificar opciones que representan conocimiento (Sí) o desconocimiento (No)
                yes_option_ids = []
                no_option_ids = []
                
                for option in options.data:
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar si la opción es "sí"
                    if option_text == "sí" or option_text == "si" or option_text.startswith("sí ") or option_text.startswith("si "):
                        yes_option_ids.append(option['id'])
                    
                    # Identificar si la opción es "no"
                    elif option_text == "no" or option_text.startswith("no "):
                        no_option_ids.append(option['id'])
                
                # Contar respuestas para cada tipo de opción
                for option_id in yes_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        aware_count += 1
                
                for option_id in no_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        unaware_count += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', awareness_question_id).eq('company_id', self.company_id).execute()
                
                # Procesar respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Detectar respuestas afirmativas (sí conocen)
                    if response_text == "sí" or response_text == "si" or response_text.startswith("sí ") or response_text.startswith("si "):
                        aware_count += 1
                    
                    # Detectar respuestas negativas (no conocen)
                    elif response_text == "no" or response_text.startswith("no "):
                        unaware_count += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            if total_valid_responses == 0:
                return {
                    "name": "Porcentaje que conoce líneas de transporte público cercanas",
                    "error": "No se encontraron respuestas a la pregunta sobre conocimiento de líneas de transporte público"
                }
            
            # Calcular porcentajes
            aware_percentage = (aware_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            unaware_percentage = (unaware_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            
            # Preparar resultado
            result = {
                "Conocen las líneas": round(aware_percentage, 2),
                "No conocen las líneas": round(unaware_percentage, 2)
            }
            
            # Calcular porcentaje de respuestas no clasificadas (si las hay)
            other_responses = total_valid_responses - (aware_count + unaware_count)
            if other_responses > 0:
                other_percentage = (other_responses / total_valid_responses) * 100
                result["Sin clasificar"] = round(other_percentage, 2)
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_valid_responses,
                "N_conoce_líneas_TP": aware_count,
                "N_no_conoce_líneas_TP": unaware_count
            }
            
            return {
                "name": "Porcentaje que conoce líneas de transporte público cercanas",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje que conoce líneas de transporte público cercanas",
                "error": f"Error al calcular el porcentaje que conoce líneas de transporte público cercanas: {e}"
            }
            
    def calculate_public_transport_improvement_factors_percentage(self):
        """
        Calcula el porcentaje por factor de mejora del transporte público.
        
        Esta métrica analiza qué factores harían que el transporte público fuera más atractivo
        para los trabajadores, basándose en sus respuestas a preguntas como 
        '¿Qué haría que el uso del transporte público fuera una opción de transporte más atractiva?'
        donde pueden seleccionar múltiples opciones.
        
        La fórmula es: Porcentaje_factor_mejora_TP (%) = N_mención_factor_TP / N_respuestas_pregunta_mejora_TP × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de cada factor de mejora
        """
        try:
            # Buscar la pregunta relacionada con factores de mejora del transporte público
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            improvement_question_id = None
            question_text = "Factores para mejorar el transporte público"
            
            # Palabras clave para identificar la pregunta sobre factores de mejora
            improvement_keywords = [
                "haría que el uso del transporte público", "haría más atractivo",
                "mejoraría el transporte público", "mejorar el transporte público",
                "mejorar la oferta de transporte público", "haría que usaras",
                "motivaría a usar el transporte público", "para usar más el transporte público",
                "factor de mejora", "factores de mejora", "mejora del transporte",
                "más atractivo", "más útil", "más eficiente", "más conveniente"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                if any(keyword in question_lower for keyword in improvement_keywords):
                    improvement_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not improvement_question_id:
                return {
                    "name": "Porcentaje por factor de mejora del transporte público",
                    "error": "No se encontró ninguna pregunta relacionada con factores de mejora del transporte público"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', improvement_question_id).eq('company_id', self.company_id).execute()
            
            # Diccionario para almacenar el recuento de cada factor
            factor_counts = {}
            
            # Lista de todos los respondentes únicos
            all_respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Mapear las opciones a sus textos
                option_texts = {option['id']: option['option_text'] for option in options.data}
                
                # Contar respuestas para cada opción
                for option_id, option_text in option_texts.items():
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    
                    count = len(answers.data)
                    if count > 0:
                        factor_counts[option_text] = count
                        
                        # Registrar respondentes únicos
                        for answer in answers.data:
                            all_respondents.add(answer['respondent_id'])
            
            else:
                # Si es una pregunta de texto libre, intentamos agrupar respuestas similares
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', improvement_question_id).eq('company_id', self.company_id).execute()
                
                # Agrupar respuestas por respondente (pueden dar múltiples respuestas)
                respondent_answers = {}
                for answer in answers.data:
                    respondent_id = answer['respondent_id']
                    response = answer['response_value'].strip()
                    
                    if respondent_id not in respondent_answers:
                        respondent_answers[respondent_id] = []
                    
                    # Añadir la respuesta si no está vacía
                    if response:
                        respondent_answers[respondent_id].append(response)
                
                # Añadir cada respuesta única al recuento
                for respondent_id, responses in respondent_answers.items():
                    all_respondents.add(respondent_id)
                    
                    for response in responses:
                        if response not in factor_counts:
                            factor_counts[response] = 0
                        factor_counts[response] += 1
            
            # Si no hay respuestas válidas, devolver error
            if not factor_counts:
                return {
                    "name": "Porcentaje por factor de mejora del transporte público",
                    "error": "No se encontraron respuestas válidas a la pregunta sobre factores de mejora"
                }
            
            # Total de respuestas (no de respondentes, ya que cada persona puede dar varias respuestas)
            total_mentions = sum(factor_counts.values())
            
            # Calcular porcentajes para cada factor
            percentages = {}
            for factor, count in factor_counts.items():
                percentage = (count / total_mentions) * 100
                percentages[factor] = round(percentage, 2)
            
            # Ordenar factores por porcentaje (de mayor a menor)
            sorted_percentages = {k: v for k, v in sorted(percentages.items(), key=lambda item: item[1], reverse=True)}
            
            # Variables para la fórmula
            variables = {
                "N_respondentes": len(all_respondents),
                "N_respuestas_total": total_mentions
            }
            
            # Añadir conteo de cada factor a las variables
            for factor, count in factor_counts.items():
                safe_factor_name = factor.replace(" ", "_").lower()
                variables[f"N_factor_{safe_factor_name}"] = count
            
            return {
                "name": "Porcentaje por factor de mejora del transporte público",
                "question": question_text,
                "result": sorted_percentages,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje por factor de mejora del transporte público",
                "error": f"Error al calcular el porcentaje por factor de mejora del transporte público: {e}"
            }
            
    def calculate_cycling_routes_awareness_percentage(self):
        """
        Calcula el porcentaje de trabajadores que conocen las vías ciclistas cercanas a su lugar de trabajo.
        
        Formula: Porcentaje_conoce_vías (%) = N_conoce_vías_ciclistas / N_respuestas_válidas × 100
        
        Returns:
            dict: Resultados del análisis con el porcentaje de conocimiento de vías ciclistas
        """
        try:
            # Buscar la pregunta relacionada con el conocimiento de vías ciclistas
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            cycling_question_id = None
            question_text = "Conocimiento de vías ciclistas"
            
            # Palabras clave para identificar la pregunta sobre conocimiento de vías ciclistas
            cycling_keywords = [
                "vías ciclistas", "carriles bici", "carril bici", "rutas ciclistas", 
                "carril-bici", "infraestructura ciclista", "camino ciclista"
            ]
            
            # Buscar la pregunta adecuada
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Verificar si la pregunta contiene palabras clave relacionadas con vías ciclistas
                if any(keyword in question_lower for keyword in cycling_keywords):
                    cycling_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not cycling_question_id:
                return {
                    "name": "Porcentaje que conoce vías ciclistas",
                    "error": "No se encontró ninguna pregunta relacionada con el conocimiento de vías ciclistas"
                }
            
            # Obtener todas las opciones para esta pregunta
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', cycling_question_id).eq('company_id', self.company_id).execute()
            
            # Contadores
            aware_count = 0      # Conocen las vías ciclistas (Sí)
            unaware_count = 0    # No conocen las vías ciclistas (No)
            
            # Lista de respondentes que han contestado a esta pregunta
            respondents = set()
            
            # Si hay opciones predefinidas
            if options.data:
                # Identificar opciones que representan conocimiento (Sí) o desconocimiento (No)
                yes_option_ids = []
                no_option_ids = []
                
                for option in options.data:
                    option_text = option['option_text'].lower().strip()
                    
                    # Identificar si la opción es "sí"
                    if option_text == "sí" or option_text == "si" or option_text.startswith("sí ") or option_text.startswith("si "):
                        yes_option_ids.append(option['id'])
                    
                    # Identificar si la opción es "no"
                    elif option_text == "no" or option_text.startswith("no "):
                        no_option_ids.append(option['id'])
                
                # Contar respuestas para cada tipo de opción
                for option_id in yes_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        aware_count += 1
                
                for option_id in no_option_ids:
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        unaware_count += 1
            
            else:
                # Si es una pregunta de texto libre
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', cycling_question_id).eq('company_id', self.company_id).execute()
                
                # Procesar respuestas únicas por respondente
                unique_respondent_answers = {}
                for answer in answers.data:
                    unique_respondent_answers[answer['respondent_id']] = answer['response_value'].lower().strip()
                
                for respondent_id, response_text in unique_respondent_answers.items():
                    respondents.add(respondent_id)
                    
                    # Detectar respuestas afirmativas (sí conocen)
                    if response_text == "sí" or response_text == "si" or response_text.startswith("sí ") or response_text.startswith("si "):
                        aware_count += 1
                    
                    # Detectar respuestas negativas (no conocen)
                    elif response_text == "no" or response_text.startswith("no "):
                        unaware_count += 1
            
            # Total de respuestas válidas
            total_valid_responses = len(respondents)
            
            if total_valid_responses == 0:
                return {
                    "name": "Porcentaje que conoce vías ciclistas",
                    "error": "No se encontraron respuestas a la pregunta sobre conocimiento de vías ciclistas"
                }
            
            # Calcular porcentajes
            aware_percentage = (aware_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            unaware_percentage = (unaware_count / total_valid_responses) * 100 if total_valid_responses > 0 else 0
            
            # Preparar resultado
            result = {
                "Conocen las vías ciclistas": round(aware_percentage, 2),
                "No conocen las vías ciclistas": round(unaware_percentage, 2)
            }
            
            # Calcular porcentaje de respuestas no clasificadas (si las hay)
            other_responses = total_valid_responses - (aware_count + unaware_count)
            if other_responses > 0:
                other_percentage = (other_responses / total_valid_responses) * 100
                result["Sin clasificar"] = round(other_percentage, 2)
            
            # Variables para la fórmula
            variables = {
                "N_respuestas_válidas": total_valid_responses,
                "N_conoce_vías_ciclistas": aware_count,
                "N_no_conoce_vías_ciclistas": unaware_count
            }
            
            return {
                "name": "Porcentaje que conoce vías ciclistas",
                "question": question_text,
                "result": result,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje que conoce vías ciclistas",
                "error": f"Error al calcular el porcentaje que conoce vías ciclistas: {e}"
            }

    def calculate_cycling_improvement_factors_percentage(self):
        """
        Calculates the percentage of improvement factors that would encourage bicycle usage among workers.
        
        Formula: Percentage_bicycle_improvement_factor (%) = N_mention_bicycle_factor / N_responses_bicycle_question × 100
        
        Returns:
            dict: Results of analysis with percentages for each bicycle improvement factor
        """
        try:
            # Find the question related to improvement factors for bicycle usage
            questions = self.supabase.table('questions').select('id', 'question_text').eq('company_id', self.company_id).execute()
            cycling_factors_question_id = None
            question_text = "Factores que mejorarían el uso de la bicicleta"
            
            # Keywords to identify the question about factors that would improve bicycle usage
            cycling_factors_keywords = [
                "bicicleta fuera una opción más atractiva",
                "mejoraría el uso de la bicicleta", "mejorarían el uso de la bicicleta", 
                "factores para usar la bicicleta", "que te animaría a usar la bicicleta",
                "qué te animaría a usar la bicicleta", "facilitar el uso de la bicicleta",
                "mejorar uso bicicleta", "motivaría a usar bicicleta"
            ]
            
            # Find the appropriate question
            for question in questions.data:
                question_lower = question['question_text'].lower()
                
                # Check if the question contains keywords related to bicycle improvement factors
                if any(keyword in question_lower for keyword in cycling_factors_keywords):
                    cycling_factors_question_id = question['id']
                    question_text = question['question_text']
                    break
            
            if not cycling_factors_question_id:
                return {
                    "name": "Porcentaje por factor de mejora al uso de bicicleta",
                    "error": "No se encontró ninguna pregunta relacionada con factores de mejora para el uso de la bicicleta"
                }
            
            # Get all options for this question
            options = self.supabase.table('options').select('id', 'option_text').eq('question_id', cycling_factors_question_id).eq('company_id', self.company_id).execute()
            
            # Initialize counters and respondents
            factors_count = {}  # Dictionary to count each factor
            respondents = set()  # Set to count unique respondents
            
            if options.data:
                # Case 1: It's a question with predefined options
                for option in options.data:
                    option_id = option['id']
                    factor_text = option['option_text'].strip()
                    
                    # Skip options that are not relevant
                    if factor_text.lower() in ["ninguno", "nada", "no aplica", "no sabe", "no responde"]:
                        continue
                    
                    # Initialize counter for this factor
                    if factor_text not in factors_count:
                        factors_count[factor_text] = 0
                    
                    # Count answers for this option
                    answers = self.supabase.table('answers').select('respondent_id').eq('option_id', option_id).eq('company_id', self.company_id).execute()
                    for answer in answers.data:
                        respondents.add(answer['respondent_id'])
                        factors_count[factor_text] += 1
            
            else:
                # Case 2: It's a free-text question
                answers = self.supabase.table('answers').select('response_value', 'respondent_id').eq('question_id', cycling_factors_question_id).eq('company_id', self.company_id).execute()
                
                # Manual processing of free text responses
                import re
                for answer in answers.data:
                    respondent_id = answer['respondent_id']
                    respondents.add(respondent_id)
                    
                    response_text = answer['response_value'].strip()
                    if not response_text or response_text.lower() in ["ninguno", "nada", "no aplica", "no sabe", "no responde"]:
                        continue
                    
                    # Split the response into separate elements by commas (or semicolons)
                    factors = [f.strip() for f in re.split(r'[,;]', response_text) if f.strip()]
                    
                    for factor in factors:
                        if factor not in factors_count:
                            factors_count[factor] = 0
                        factors_count[factor] += 1
            
            # Total number of respondents to this question
            total_respondents = len(respondents)
            
            if total_respondents == 0:
                return {
                    "name": "Porcentaje por factor de mejora al uso de bicicleta",
                    "error": "No se encontraron respuestas a la pregunta sobre factores de mejora para el uso de la bicicleta"
                }
            
            # Calculate percentages for each factor
            percentages = {}
            for factor, count in factors_count.items():
                percentages[factor] = round((count / total_respondents) * 100, 2)
            
            # Sort factors by percentage (from highest to lowest)
            sorted_percentages = {k: v for k, v in sorted(percentages.items(), key=lambda item: item[1], reverse=True)}
            
            # Variables for the formula
            variables = {
                "N_respuestas_pregunta_bici": total_respondents
            }
            
            # Add count for each factor to the variables
            for factor, count in factors_count.items():
                var_name = f"N_mención_{factor.lower().replace(' ', '_')}"
                variables[var_name] = count
            
            return {
                "name": "Porcentaje por factor de mejora al uso de bicicleta",
                "question": question_text,
                "result": sorted_percentages,
                "variables": variables
            }
            
        except Exception as e:
            return {
                "name": "Porcentaje por factor de mejora al uso de bicicleta",
                "error": f"Error al calcular el porcentaje por factor de mejora al uso de bicicleta: {e}"
            }