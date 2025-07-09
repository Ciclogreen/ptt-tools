import pandas as pd
import re
import numpy as np

class SurveyMonkeyConverter:
    """
    A class to handle the conversion of SurveyMonkey CSV exports into structured JSON data.
    This class encapsulates the complete workflow of transforming raw survey data
    into a structured format suitable for analysis and visualization.
    """

    @staticmethod
    def slugify(text: str, maxlen: int = 1000) -> str:
        """
        Replace non-alphanumeric chars by underscores, collapse repeats,
        trim to `maxlen`, and ensure no leading/trailing underscores.
        """
        text = re.sub(r"\W+", "_", text.lower()).strip("_")
        return text[:maxlen]

    @classmethod
    def load_surveymonkey_one_hot(cls, csv_path: str) -> pd.DataFrame:
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
        # Load the CSV - Importante usar header=None para que las columnas sean números
        raw = pd.read_csv(csv_path, header=None, dtype=object)
        
        # Get question and option rows
        questions = raw.iloc[0]      # first row
        option_row = raw.iloc[1]     # second row
        
        # Drop header rows and reset index
        df = raw.iloc[2:].reset_index(drop=True)

        # Create a new DataFrame with only the columns we need
        ordered_columns = []
        current_question = None
        original_question_order = []  # Para mantener el orden de las preguntas

        # Process each column
        for idx in range(len(questions)):
            if pd.notna(questions[idx]):
                current_question = cls.slugify(str(questions[idx]))
                
                # Mantener el orden de las preguntas
                if current_question not in original_question_order:
                    original_question_order.append(current_question)
                
                # Check if it's an open-ended question
                if str(option_row[idx]).lower() == "open-ended response":
                    df[current_question] = df[idx]
                    ordered_columns.append(current_question)
                # If it's a regular option, create a binary column
                else:
                    option_label = cls.slugify(str(option_row[idx]))
                    binary_name = f"{current_question}__{option_label}"
                    # Create binary column - 1 if the cell has a value, 0 otherwise
                    df[binary_name] = df[idx].notna().astype("int8")
                    ordered_columns.append(binary_name)
            # For options without a question header (continuation of previous question)
            elif current_question:
                # Check if it's an "other" option
                if any(keyword in str(option_row[idx]).lower() for keyword in ["otro (especifique)", "especifique", "añade información", "other (please specify)"]):
                    option_label = cls.slugify(str(option_row[idx]))
                    binary_name = f"{current_question}__{option_label}"
                    df[binary_name] = df[idx].notna().astype("int8")
                    text_name = f"{current_question}__{option_label}_text"
                    df[text_name] = df[idx]
                    ordered_columns.extend([binary_name, text_name])
                # For regular options
                else:
                    option_label = cls.slugify(str(option_row[idx]))
                    binary_name = f"{current_question}__{option_label}"
                    df[binary_name] = df[idx].notna().astype("int8")
                    ordered_columns.append(binary_name)

        # Drop original columns
        df = df.drop(columns=[i for i in range(len(questions)) if i in df.columns])
        
        # Reordenar columnas según el orden original de las preguntas
        reordered_columns = []
        for question in original_question_order:
            for col in ordered_columns:
                if col == question or col.startswith(f"{question}__"):
                    reordered_columns.append(col)
        
        # Asegurar que no perdemos ninguna columna
        remaining_cols = [col for col in ordered_columns if col not in reordered_columns]
        reordered_columns.extend(remaining_cols)
        
        # Filtrar columnas que terminan en __nan
        reordered_columns = [col for col in reordered_columns if not col.endswith("__nan")]
        
        # Return dataframe with columns in original question order
        return df[reordered_columns]

    @staticmethod
    def group_columns(columns):
        """
        Return a dict: base_question -> list of related columns
        (sub-options and *_text). Stand-alone questions get an empty list.
        """
        grouped = {}
        for col in columns:
            if "__" in col:
                base = col.split("__", 1)[0]
                grouped.setdefault(base, []).append(col)
            else:
                grouped.setdefault(col, [])
        return grouped

    @staticmethod
    def row_to_qa(row: pd.Series, groups: dict) -> list[dict]:
        """
        Convert one respondent (row) to
        [{index, question, answer}, …] keeping 1-based order.
        """
        qa_list = []
        q_idx = 1

        for base, cols in groups.items():
            if cols:  # one-hot question
                selected = []
                other_text = None
                other_option = None
                
                # First pass to identify "other" option and its text
                for col in cols:
                    if col.endswith("_text"):
                        val = row[col]
                        if pd.notna(val) and str(val).strip():
                            other_text = str(val).strip()
                    else:
                        option = col.split("__", 1)[1].replace("_", " ")
                        if row[col] == 1 or str(row[col]).strip() == "1":
                            if "otro" in option.lower() or "other" in option.lower() or "especif" in option.lower() or "añade información" in option.lower():
                                other_option = option
                            else:
                                selected.append(option)
                
                # Combine "other" with its text if both exist
                if other_option and other_text:
                    selected.append(f"{other_option}: {other_text}")
                elif other_option:
                    selected.append(other_option)
                elif other_text:
                    selected.append(other_text)

                if not selected:
                    q_idx += 1
                    continue

                # Siempre guardar como lista para preguntas con opciones (tipo "multi")
                answer = selected
            else:  # open question
                answer = row[base]

            # Capitalize first letter of the question
            question = base.replace("_", " ")
            if question:
                question = question[0].upper() + question[1:]

            qa_list.append(
                {
                    "index": q_idx,
                    "question": question,
                    "answer": answer,
                }
            )
            q_idx += 1

        return qa_list

    @classmethod
    def one_hot_df_to_json(cls, df: pd.DataFrame) -> list[list[dict]]:
        """Wrapper: whole DataFrame → nested list ready for `json.dump`."""
        groups = cls.group_columns(df.columns)
        result = [cls.row_to_qa(row, groups) for _, row in df.iterrows()]
        
        # Save the result to a JSON file for reference
        # import json
        # with open("result.json", "w", encoding="utf-8") as f:
        #     json.dump(result, f, indent=4, ensure_ascii=False)  
        
        return result
