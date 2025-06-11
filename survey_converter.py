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
                current_question = cls.slugify(str(questions[idx]))
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
            elif any(keyword in str(option_row[idx]).lower() for keyword in ["otro (especifique)", "especifique", "añade información", "other (please specify)"]):
                # Create the binary indicator column
                option_label = cls.slugify(str(option_row[idx]))
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
                option_label = cls.slugify(str(option_row[idx]))
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

                answer = selected[0] if len(selected) == 1 else selected
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
        return [cls.row_to_qa(row, groups) for _, row in df.iterrows()]
