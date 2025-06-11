from supabase import create_client
import streamlit as st

def init_supabase():
    """Inicializa la conexión con Supabase"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        return None

def get_company_id(supabase, company_name, create_if_not_exists=True):
    """Obtiene el ID de una compañía o la crea si no existe"""
    company_query = supabase.table('companies').select('id').eq('company_name', company_name).execute()
    
    if company_query.data:
        return company_query.data[0]['id']
    elif create_if_not_exists:
        company_result = supabase.table('companies').insert({
            'company_name': company_name
        }).execute()
        return company_result.data[0]['id']
    else:
        return None

def check_company_data_exists(supabase, company_id):
    """Verifica si ya existen datos para una compañía"""
    questions_query = supabase.table('questions').select('id', count='exact').eq('company_id', company_id).execute()
    return questions_query.count > 0

def delete_company_data(supabase, company_name):
    """Elimina todos los datos de una compañía específica"""
    try:
        # Buscar la compañía por nombre
        company_query = supabase.table('companies').select('id').eq('company_name', company_name).execute()
        
        if not company_query.data:
            return False, f"No se encontró ninguna compañía con el nombre '{company_name}'"
        
        company_id = company_query.data[0]['id']
        
        # Eliminar en orden correcto para evitar problemas de clave foránea
        # 1. Primero las respuestas (answers) - dependen de options, questions y respondents
        try:
            answers_result = supabase.table('answers').delete().eq('company_id', company_id).execute()
            answers_count = len(answers_result.data)
        except Exception as e:
            return False, f"Error al eliminar respuestas: {e}"
        
        # 2. Luego las opciones (options) - dependen de questions
        try:
            options_result = supabase.table('options').delete().eq('company_id', company_id).execute()
            options_count = len(options_result.data)
        except Exception as e:
            return False, f"Error al eliminar opciones: {e}"
        
        # 3. Respondentes (respondents)
        try:
            respondents_result = supabase.table('respondents').delete().eq('company_id', company_id).execute()
            respondents_count = len(respondents_result.data)
        except Exception as e:
            return False, f"Error al eliminar respondentes: {e}"
        
        # 4. Finalmente las preguntas (questions)
        try:
            questions_result = supabase.table('questions').delete().eq('company_id', company_id).execute()
            questions_count = len(questions_result.data)
        except Exception as e:
            return False, f"Error al eliminar preguntas: {e}"
        
        # Nota: No eliminamos la compañía en sí, solo sus datos asociados
        
        return True, f"Datos eliminados: {answers_count} respuestas, {options_count} opciones, {respondents_count} respondentes, {questions_count} preguntas"
    except Exception as e:
        return False, f"Error general al eliminar datos: {e}"

def save_survey_data(supabase, json_data, company_id):
    """Guarda datos de encuestas en la base de datos"""
    try:
        # Para cada respondente (persona que completó la encuesta)
        for respondent_data in json_data:
            # Crear un nuevo respondente asociado a la compañía
            respondent_result = supabase.table('respondents').insert({
                'company_id': company_id
            }).execute()
            respondent_id = respondent_result.data[0]['id']
            
            # Procesar cada pregunta y respuesta
            for qa in respondent_data:
                question_text = qa['question']
                question_index = qa['index']
                answer = qa['answer']
                
                # Determinar el tipo de pregunta basado en el formato de la respuesta
                question_type = 'open'
                if isinstance(answer, list):
                    question_type = 'multi'
                elif isinstance(answer, str) and answer.strip():
                    question_type = 'single'
                
                # Verificar si la pregunta ya existe para esta compañía, si no, crearla
                question_query = supabase.table('questions').select('id').eq('question_text', question_text).eq('company_id', company_id).execute()
                
                if question_query.data:
                    question_id = question_query.data[0]['id']
                else:
                    question_result = supabase.table('questions').insert({
                        'company_id': company_id,
                        'question_text': question_text,
                        'question_type': question_type,
                        'question_index': question_index
                    }).execute()
                    question_id = question_result.data[0]['id']
                
                # Procesar respuestas según el tipo
                if question_type == 'open':
                    # Respuesta abierta
                    supabase.table('answers').insert({
                        'company_id': company_id,
                        'respondent_id': respondent_id,
                        'question_id': question_id,
                        'open_value': str(answer) if answer is not None else ''
                    }).execute()
                else:
                    # Respuesta de opción única o múltiple
                    answers_list = [answer] if question_type == 'single' else answer
                    
                    for ans in answers_list:
                        # Verificar si la opción ya existe, si no, crearla
                        option_query = supabase.table('options').select('id').eq('question_id', question_id).eq('option_text', ans).execute()
                        
                        if option_query.data:
                            option_id = option_query.data[0]['id']
                        else:
                            option_result = supabase.table('options').insert({
                                'company_id': company_id,
                                'question_id': question_id,
                                'option_text': ans
                            }).execute()
                            option_id = option_result.data[0]['id']
                        
                        # Guardar la respuesta
                        supabase.table('answers').insert({
                            'company_id': company_id,
                            'respondent_id': respondent_id,
                            'question_id': question_id,
                            'option_id': option_id
                        }).execute()
        
        return True, f"Datos guardados exitosamente"
    except Exception as e:
        return False, f"Error al guardar datos: {e}"

def get_stats_for_company(supabase, company_id):
    """Obtiene estadísticas básicas para una compañía"""
    stats = {}
    
    # Contar respondentes
    respondent_query = supabase.table('respondents').select('*', count='exact').eq('company_id', company_id).execute()
    stats['respondents_count'] = respondent_query.count
    
    # Contar preguntas
    question_query = supabase.table('questions').select('*', count='exact').eq('company_id', company_id).execute()
    stats['questions_count'] = question_query.count
    
    return stats

def save_survey_data_batch(supabase, json_data, company_id):
    """Saves survey data to the database using batch operations"""
    try:
        # Step 1: Extract all unique questions and options
        all_questions = {}  # question_text -> {index, type}
        all_options = {}    # (question_text, option_text) -> None
        
        # First pass: collect all unique questions and options
        for respondent_data in json_data:
            for qa in respondent_data:
                question_text = qa['question']
                question_index = qa['index']
                answer = qa['answer']
                
                # Determine question type
                question_type = 'open'
                if isinstance(answer, list):
                    question_type = 'multi'
                elif isinstance(answer, str) and answer.strip():
                    question_type = 'single'
                
                # Store question info
                if question_text not in all_questions:
                    all_questions[question_text] = {
                        'index': question_index,
                        'type': question_type
                    }
                
                # Store option info for non-open questions
                if question_type != 'open':
                    answers_list = [answer] if question_type == 'single' else answer
                    for ans in answers_list:
                        # Convertir la respuesta a string para asegurar que sea hashable
                        option_text = str(ans) if ans is not None else ""
                        all_options[(question_text, option_text)] = None
        
        # Step 2: Batch upsert all questions
        questions_batch = []
        for question_text, info in all_questions.items():
            questions_batch.append({
                'company_id': company_id,
                'question_text': question_text,
                'question_type': info['type'],
                'question_index': info['index']
            })
        
        # Batch insert questions (will upsert based on unique constraint)
        if questions_batch:
            questions_result = supabase.table('questions').upsert(
                questions_batch,
                on_conflict='company_id,question_text'
            ).execute()
            
            # Create mapping from question_text to question_id
            question_id_map = {}
            for question in questions_result.data:
                question_id_map[question['question_text']] = question['id']
        
        # Step 3: Batch upsert all options
        options_batch = []
        for (question_text, option_text) in all_options.keys():
            if question_text in question_id_map:
                options_batch.append({
                    'company_id': company_id,
                    'question_id': question_id_map[question_text],
                    'option_text': option_text
                })
        
        # Batch insert options
        option_id_map = {}  # (question_id, option_text) -> option_id
        if options_batch:
            options_result = supabase.table('options').upsert(
                options_batch,
                on_conflict='question_id,option_text'
            ).execute()
            
            # Create mapping from (question_id, option_text) to option_id
            for option in options_result.data:
                option_id_map[(option['question_id'], option['option_text'])] = option['id']
        
        # Step 4: Process respondents and answers in batches
        # Process in chunks to avoid very large payloads
        batch_size = 50
        for i in range(0, len(json_data), batch_size):
            current_batch = json_data[i:i+batch_size]
            
            # Create respondents in batch
            respondents_batch = []
            for _ in current_batch:
                respondents_batch.append({'company_id': company_id})
            
            respondents_result = supabase.table('respondents').insert(
                respondents_batch
            ).execute()
            
            # Now process answers
            all_answers = []
            for idx, respondent_data in enumerate(current_batch):
                respondent_id = respondents_result.data[idx]['id']
                
                for qa in respondent_data:
                    question_text = qa['question']
                    answer = qa['answer']
                    
                    # Skip if question wasn't successfully inserted
                    if question_text not in question_id_map:
                        continue
                        
                    question_id = question_id_map[question_text]
                    question_type = all_questions[question_text]['type']
                    
                    # Process answers according to type
                    if question_type == 'open':
                        all_answers.append({
                            'company_id': company_id,
                            'respondent_id': respondent_id,
                            'question_id': question_id,
                            'open_value': str(answer) if answer is not None else ''
                        })
                    else:
                        answers_list = [answer] if question_type == 'single' else answer
                        
                        for ans in answers_list:
                            # Convertir la respuesta a string para compatibilidad con las claves del mapa de opciones
                            ans_str = str(ans) if ans is not None else ""
                            option_id = option_id_map.get((question_id, ans_str))
                            if option_id:
                                all_answers.append({
                                    'company_id': company_id,
                                    'respondent_id': respondent_id,
                                    'question_id': question_id,
                                    'option_id': option_id
                                })
            
            # Insert all answers in batch
            if all_answers:
                # Split into manageable chunks if needed
                answers_chunk_size = 100
                for j in range(0, len(all_answers), answers_chunk_size):
                    answers_chunk = all_answers[j:j+answers_chunk_size]
                    supabase.table('answers').insert(answers_chunk).execute()
        
        return True, f"Data saved successfully using batch operations"
    except Exception as e:
        return False, f"Error saving data: {e}"