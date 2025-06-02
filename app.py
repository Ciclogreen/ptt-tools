import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import yaml
import tempfile
import csv
import io
from pathlib import Path
from litellm import completion, completion_cost
import re

# Load prompts from YAML file
def load_prompts():
    try:
        with open('prompts.yaml', 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
        return prompts
    except Exception as e:
        st.error(f"Error loading prompts file: {e}")
        return {"analysis_prompt": "", "summary_prompt": ""}

# Initialize session state variables
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
        st.session_state.company_name = "ACME S.A."
    if 'execution_costs' not in st.session_state:
        st.session_state.execution_costs = []
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0.0

# Data processing functions
def slugify(text: str, maxlen: int = 1000) -> str:
    """
    Replace non-alphanumeric chars by underscores, collapse repeats,
    trim to `maxlen`, and ensure no leading/trailing underscores.
    """
    text = re.sub(r"\W+", "_", text.lower()).strip("_")
    return text[:maxlen]

def load_surveymonkey_one_hot(csv_path: str) -> pd.DataFrame:
    """
    Read the raw SurveyMonkey CSV and return a one-hot encoded DataFrame.
    Row 0: full question wording
    Row 1:   • 'Open-Ended Response'  → open question
             • 'Other (please specify)' or similar → one-hot + text preserved
             • anything else          → option label
    The function preserves open-ended answers as text and converts every
    closed option (single-choice o multi-choice) into a binary column.
    For "Other (please specify)" options, it creates both a binary column
    and preserves the specified text in a separate column.
    """
    raw = pd.read_csv(csv_path, header=None, dtype=object)
    questions = raw.iloc[0]      # first row
    option_row = raw.iloc[1]     # second row
    df = raw.iloc[2:].reset_index(drop=True)  # actual responses

    current_question = None
    columns_to_drop = []
    original_question_order = []  # To keep track of question order
    column_mapping = {}  # To map original columns to new column names
    original_to_new = {}  # To map original question slugs to new columns
    
    # First pass: Create all the one-hot columns
    for idx in range(len(questions)):
        # When a new question starts we get its full wording
        if pd.notna(questions[idx]):
            current_question = slugify(str(questions[idx]))
            if current_question not in original_question_order:
                original_question_order.append(current_question)
            if current_question not in original_to_new:
                original_to_new[current_question] = []

        # "Open-Ended Response" → keep as plain text, just rename
        if str(option_row[idx]).strip() == "Open-Ended Response":
            new_name = current_question
            df.rename(columns={idx: new_name}, inplace=True)
            original_to_new[current_question].append(new_name)
            column_mapping[idx] = new_name

        # Check for "Other (please specify)" or similar options
        elif any(keyword in str(option_row[idx]).lower() for keyword in ["otro (especifique)", "especifique", "añade información"]):
            # Create the binary indicator column
            option_label = slugify(str(option_row[idx]))
            binary_name = f"{current_question}__{option_label}"
            df[binary_name] = df[idx].notna().astype("int8")
            original_to_new[current_question].append(binary_name)
            
            # Create a text column to preserve the specified text
            text_name = f"{current_question}__{option_label}_text"
            df[text_name] = df[idx]
            original_to_new[current_question].append(text_name)
            
            # Original column not needed anymore
            columns_to_drop.append(idx)

        # Otherwise the cell contains a standard option label → one-hot
        else:
            option_label = slugify(str(option_row[idx]))
            new_name = f"{current_question}__{option_label}"
            df[new_name] = df[idx].notna().astype("int8")
            original_to_new[current_question].append(new_name)
            columns_to_drop.append(idx)  # original text not needed

    # Remove original option columns
    df.drop(columns=columns_to_drop, inplace=True)
    
    # Reorder columns according to original question order
    ordered_columns = []
    for question in original_question_order:
        if question in original_to_new:
            ordered_columns.extend(original_to_new[question])
    
    # Make sure we include any columns that weren't captured in our ordering process
    remaining_cols = [col for col in df.columns if col not in ordered_columns]
    ordered_columns.extend(remaining_cols)
    
    # Filter out columns ending with "__nan"
    ordered_columns = [col for col in ordered_columns if not col.endswith("__nan")]
    
    # Return dataframe with columns in original question order
    return df[ordered_columns]

def dataframe_to_csv_string(df: pd.DataFrame) -> str:
    """Convert a dataframe to a CSV string"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def read_csv_as_text() -> str:
    """Read the uploaded CSV file as text"""
    if not Path(st.session_state.temp_file_path).exists():
        return ""
    
    with open(st.session_state.temp_file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        lines = ['\t'.join(row) for row in reader]
    return '\n'.join(lines)

# LLM processing functions
def call_llm_api(message_content, clear=False):
    """
    Central function to call LLM API and handle message management
    
    Parameters:
    - message_content: String content of the user message
    - clear: Whether to clear the message history before adding this message
    
    Returns:
    - The content of the LLM response
    """
    try:
        # Initialize messages list if it doesn't exist
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # Clear messages if requested
        if clear:
            st.session_state.messages = []
        
        # Add the new user message only if it's not empty
        if message_content:
            user_message = {"role": "user", "content": message_content}
            st.session_state.messages.append(user_message)

        model = "openai/o4-mini"
        # model = "openai/o3"
        # model = "openai/gpt-4o-mini"
        # model = "openai/gpt-4.1"
        
        # Asegurarse de que todos los mensajes tienen formato válido antes de enviarlos
        valid_messages = []
        for msg in st.session_state.messages:
            # Verificar que el mensaje contiene 'role' y 'content' y que 'content' no es nulo
            if 'role' in msg and 'content' in msg and msg['content'] is not None and msg['content'] != '':
                # Asegurarse de que el contenido es texto plano
                if isinstance(msg['content'], str):
                    valid_messages.append(msg)
        
        # Medir el tiempo de inicio
        start_time = pd.Timestamp.now()
        
        # Llamar al modelo con los mensajes validados
        response = completion(
            model=model, 
            messages=valid_messages,
            temperature=1,
            api_key=st.session_state.api_key
        )
        
        # Medir el tiempo de finalización y calcular duración
        end_time = pd.Timestamp.now()
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Calculate and store cost
        cost = calculate_cost(response, duration_seconds)
        
        # Get content from response
        content = response.choices[0].message.content
        
        # Add assistant's response to the conversation
        st.session_state.messages.append({"role": "assistant", "content": content})
        
        return content
    
    except Exception as e:
        st.error(f"Error calling LLM API: {e}")
        return f"Error: {e}"

def calculate_cost(response, duration_seconds=None):
    """
    Calculate the cost of an LLM API call
    
    Parameters:
    - response: The response from the LLM API call
    - duration_seconds: The duration of the call in seconds
    
    Returns:
    - The cost of the API call as a float
    """
    try:
        # Calculate the cost using litellm's completion_cost function
        cost = completion_cost(completion_response=response)
        
        # Store the cost information
        model_name = response.model
        call_info = {
            "model": model_name,
            "cost": float(cost),
            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
            "duration": duration_seconds if duration_seconds is not None else 0.0
        }
        
        # Add to session state
        if 'execution_costs' not in st.session_state:
            st.session_state.execution_costs = []
        st.session_state.execution_costs.append(call_info)
        
        # Update total cost
        if 'total_cost' not in st.session_state:
            st.session_state.total_cost = 0.0
        st.session_state.total_cost += float(cost)
        
        return float(cost)
    except Exception as e:
        st.warning(f"Could not calculate cost: {e}")
        return 0.0

def get_total_execution_cost():
    """
    Get the total cost of all LLM API calls
    
    Returns:
    - A DataFrame with cost information
    - The total cost as a float
    """
    if 'execution_costs' not in st.session_state or not st.session_state.execution_costs:
        return pd.DataFrame(columns=["Model", "Cost", "Duration (s)", "Timestamp"]), 0.0
    
    # Create DataFrame
    df_costs = pd.DataFrame(st.session_state.execution_costs)
    df_costs.columns = ["Model", "Cost", "Timestamp", "Duration"]
    
    # Format costs to display with scientific notation for very small values
    df_costs["Cost"] = df_costs["Cost"].apply(lambda x: f"${x:.10f}")
    
    # Format duration to show with 2 decimal places
    df_costs["Duration"] = df_costs["Duration"].apply(lambda x: f"{x:.2f}s")
    
    # Reorder columns to show duration before timestamp
    df_costs = df_costs[["Model", "Cost", "Duration", "Timestamp"]]
    
    total = st.session_state.total_cost
    
    # Add a total row to the dataframe
    total_row = pd.DataFrame({
        "Model": ["TOTAL"],
        "Cost": [f"${total:.10f}"],
        "Timestamp": ["-"],
        "Duration": ["-"]
    })
    
    # Concatenate the original dataframe with the total row
    df_costs = pd.concat([df_costs, total_row], ignore_index=True)
    
    return df_costs, total

def process_with_llm(df=None):
    """Process the data with LLM using CSV format
    
    Parameters:
    - df: If provided, creates a new conversation with the CSV data
    
    Returns the latest response from the LLM
    """
    # Load prompts
    prompts = load_prompts()
    
    # If df is None, use the stored DataFrame
    if df is None and st.session_state.df_one_hot is not None:
        df = st.session_state.df_one_hot
    
    # If df is provided, start a new conversation with CSV data
    if df is not None:
        # Convert dataframe to CSV string
        csv_text = dataframe_to_csv_string(df)
        
        # Fill the prompt template with our CSV data
        filled_prompt = prompts["analysis_prompt"].format(data=csv_text)
        
        # Call the LLM API with a cleared message history
        return call_llm_api(filled_prompt, clear=True)
    
    # Exit if no data
    return "No data provided for analysis."

def generate_summary():
    """Generate a summary from the analysis"""
    # Load prompts
    prompts = load_prompts()
    
    # Get company name from session state
    company_name = st.session_state.company_name if 'company_name' in st.session_state else ""
    
    # Fill the prompt template with company name
    filled_prompt = prompts["summary_prompt"].format(company_name=company_name)
    
    # Call LLM API with the summary prompt
    summary_content = call_llm_api(filled_prompt)
    
    # Store summary result
    st.session_state.summary_result = summary_content
    
    # Automatically verify the summary after generation
    verify_summary()
    
    return summary_content

def generate_redaction():
    """Generate a redaction from the analysis"""
    # Load prompts
    prompts = load_prompts()
    
    # Get company name from session state
    # company_name = st.session_state.company_name if 'company_name' in st.session_state else ""
    
    # Fill the prompt template with company name
    filled_prompt = prompts["redaction_prompt"]
    
    # Call LLM API with the redaction prompt
    redaction_content = call_llm_api(filled_prompt)
    
    # Store redaction result
    st.session_state.redaction_result = redaction_content
    
    return redaction_content

def verify_summary():
    """Verify the quality of the summary against the analysis result"""
    # Load prompts
    prompts = load_prompts()
    
    # Check if we have both analysis_result and summary_result
    if not st.session_state.analysis_result or not st.session_state.summary_result:
        return "No hay datos disponibles para la verificación."
    
    # Get the data from session state
    questions_data = st.session_state.analysis_result
    summary_text = st.session_state.summary_result
    
    # Fill the prompt template with the data
    filled_prompt = prompts["verification_prompt"].format(
        questions_data=questions_data,
        summary_text=summary_text
    )
    
    # Call the LLM API (reusing the existing function)
    verification_result = call_llm_api(filled_prompt)
    
    # Store the result in session state
    st.session_state.verification_result = verification_result
    
    return verification_result

# Visualization functions
def create_visualizations(df):
    """Create simple visualizations from the data"""
    st.subheader("Data Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Problem visualization
        try:
            problem_cols = [col for col in df.columns if 'problema_principal' in col]
            if problem_cols:
                # Ensure columns are numeric
                numeric_df = df[problem_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
                problem_counts = numeric_df.sum().sort_values(ascending=False)
                problem_labels = [col.split('__')[-1] for col in problem_counts.index]
                
                fig = px.bar(
                    x=problem_counts.values,
                    y=problem_labels,
                    orientation='h',
                    title="Main Problems Reported",
                    labels={'x': 'Count', 'y': 'Problem Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not create problem visualization: {e}")
    
    with col2:
        # Transport visualization
        try:
            transport_cols = [col for col in df.columns if 'medios_de_transporte' in col or 
                            'herramientas_actuales_de_la_empresa' in col]
            
            if transport_cols:
                # Ensure columns are numeric
                numeric_df = df[transport_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
                transport_counts = numeric_df.sum().sort_values(ascending=False)
                transport_labels = [col.split('__')[-1] for col in transport_counts.index]
                
                if len(transport_counts) > 0:
                    fig = px.pie(
                        values=transport_counts.values, 
                        names=transport_labels,
                        title="Transportation Options Available"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No transportation data available for visualization")
        except Exception as e:
            st.warning(f"Could not create transport visualization: {e}")

# Chat interface
def display_chat_interface():
    """Display the chat interface for interacting with the LLM"""
    st.subheader("Chat with Mobility Analyst")
    
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
                        response = call_llm_api("")  # Pasamos string vacío porque ya añadimos el mensaje a st.session_state.messages
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Error en la interfaz de chat: {e}")
                        # Botón para reiniciar la conversación
                        if st.button("Reiniciar conversación"):
                            st.session_state.messages = []
                            st.rerun()

# Main application
def main():
    # Initialize session state
    init_session_state()
    
    # App configuration
    st.set_page_config(
        page_title="Mobility Analysis Tool",
        page_icon="🚲",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # App title
    st.title("Mobility Analysis Tool")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    company_name = st.text_input("Company Name", value=st.session_state.company_name)
    st.session_state.company_name = company_name
    
    if uploaded_file is not None:
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            tmp.write(uploaded_file.getvalue())
            st.session_state.temp_file_path = tmp.name
        
        # Process with one-hot encoding using the original function
        with st.spinner("Processing CSV data..."):
            st.session_state.df_one_hot = load_surveymonkey_one_hot(st.session_state.temp_file_path)
            st.success(f"Processed {st.session_state.df_one_hot.shape[0]} rows with {st.session_state.df_one_hot.shape[1]} features")
        
        # Show a preview of the data
        with st.expander("Preview of One-Hot Encoded Data"):
            st.dataframe(st.session_state.df_one_hot)
        
        # Process with LLM button
        if st.button("Analyze Data"):
            with st.spinner("Analyzing data..."):
                # Process data with first prompt
                st.session_state.analysis_result = process_with_llm(df=st.session_state.df_one_hot)
                
                # Process with second prompt (redaction)
                # st.session_state.redaction_result = generate_redaction()

                # Process with second prompt (summary)
                st.session_state.summary_result = generate_summary()
    
    # Display results in tabs
    if hasattr(st.session_state, 'analysis_result') and st.session_state.analysis_result:
        tab1, tab2 = st.tabs(["Analysis Results", "Chat Interface"])
        
        with tab1:
            # First prompt result (collapsed)
            with st.expander("Detailed Analysis"):
                st.markdown(st.session_state.analysis_result)
                
                # Add cost table
                st.markdown("### API Call Costs")
                df_costs, total_cost = get_total_execution_cost()
                st.dataframe(df_costs)
                # Ya no es necesario mostrar el total aquí ya que está en la tabla
                # st.markdown(f"**Total Cost:** ${total_cost:.10f}")
            
            # Second prompt result (visible)
            st.markdown("## Summary")
            st.markdown(st.session_state.summary_result)
            
            # Display verification result if available
            st.markdown("## Verification")
            if 'verification_result' in st.session_state and st.session_state.verification_result:
                st.markdown(st.session_state.verification_result)
            
            # Create visualizations
            # create_visualizations(st.session_state.df_one_hot)

        with tab2:
            # Chat interface
            display_chat_interface()

if __name__ == "__main__":
    main()