import streamlit as st
from supabase import create_client

# Inicializar conexión a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

st.set_page_config(
    page_title="Estructura de Encuesta",
    page_icon="📝",
    layout="wide"
)
st.title("📝 Estructura de la Encuesta por Compañía")

# Input para el nombre de la compañía
with st.container():
    company_name = st.text_input("🏢 Nombre de la compañía", value="")
    submit = st.button("🔍 Ver estructura", use_container_width=True)

# Variables para mostrar resultados fuera del status
show_results = False
results = {}

if submit and company_name:
    with st.status("Buscando datos en la base de datos...", expanded=True) as status:
        supabase = init_supabase()
        status.update(label="🔎 Buscando compañía...", state="running")
        company_query = supabase.table('companies').select('id').eq('company_name', company_name).execute()
        if not company_query.data:
            status.update(label=f"⚠️ No se encontró la compañía '{company_name}' en la base de datos.", state="error")
            st.warning(f"No se encontró la compañía '{company_name}' en la base de datos.")
        else:
            company_id = company_query.data[0]['id']
            status.update(label="📋 Obteniendo preguntas y respondentes...", state="running")
            questions_query = supabase.table('questions').select('id,question_text,question_type,question_index').eq('company_id', company_id).order('question_index').execute()
            questions = questions_query.data or []
            total_questions = len(questions)
            respondents_query = supabase.table('respondents').select('id').eq('company_id', company_id).execute()
            total_respondents = len(respondents_query.data or [])
            status.update(label="📊 Calculando respondentes por pregunta...", state="running")
            question_respondents = {}
            for q in questions:
                qid = q['id']
                answers_query = supabase.table('answers').select('respondent_id').eq('company_id', company_id).eq('question_id', qid).execute()
                respondent_ids = set(a['respondent_id'] for a in (answers_query.data or []))
                question_respondents[qid] = len(respondent_ids)
            status.update(label="✅ Datos obtenidos", state="complete", expanded=False)
            # Guardar resultados para mostrar fuera del status
            results = {
                'company_name': company_name,
                'total_questions': total_questions,
                'total_respondents': total_respondents,
                'questions': questions,
                'question_respondents': question_respondents,
                'supabase': supabase,
            }
            show_results = True

# Mostrar resultados fuera del status
if show_results and results:
    st.subheader(f"📊 Resumen para '{results['company_name']}'")
    col1, col2 = st.columns(2)
    col1.metric("❓ Total de preguntas", results['total_questions'])
    col2.metric("👤 Total de respondentes", results['total_respondents'])
    st.divider()
    if results['total_questions'] == 0:
        st.info("ℹ️ No hay preguntas registradas para esta compañía.")
    else:
        st.subheader("🗂️ Preguntas y opciones")
        for q in results['questions']:
            qid = q['id']
            qtext = q['question_text']
            qtype = q.get('question_type', '')
            n_resp = results['question_respondents'].get(qid, 0)
            options_query = results['supabase'].table('options').select('option_text').eq('question_id', qid).order('option_text').execute()
            options = [o['option_text'] for o in (options_query.data or [])]
            with st.expander(f"{q['question_index']+1 if q.get('question_index') is not None else ''}. {qtext}", expanded=True):
                st.write(f"Tipo: `{qtype}` | 👥 Respondieron: **{n_resp}**")
                if options:
                    st.write("Opciones:")
                    st.markdown("\n".join([f"- {opt}" for opt in options]))
                else:
                    st.info("Pregunta abierta, sin opciones")
            # st.divider() 