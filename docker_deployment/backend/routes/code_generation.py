import os
import json
import pandas as pd
import subprocess
import tempfile
import sys
import google.generativeai as genai
from google.cloud import storage
from google.auth import default
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Literal

router = APIRouter()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# GCS Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "ai-analysis-v1")
DEFAULT_BUCKET = os.getenv("DEFAULT_BUCKET", "ai-analysis-default-bucket")

def get_gcs_client():
    """Get GCS client using Application Default Credentials"""
    try:
        credentials, project = default()
        client = storage.Client(credentials=credentials, project=project)
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize GCS client: {str(e)}")

def download_file_from_gcs(bucket_name: str, file_name: str, local_path: str):
    """Download a file from GCS to local path"""
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        if not blob.exists():
            raise Exception(f"File {file_name} not found in bucket {bucket_name}")
        
        blob.download_to_filename(local_path)
        return True
    except Exception as e:
        raise Exception(f"Failed to download {file_name} from {bucket_name}: {str(e)}")


class CodeGenerationRequest(BaseModel):
    question: str
    language: Literal["python", "sql"]
    selected_files: List[Dict[str, Any]]

class CodeExecutionRequest(BaseModel):
    code: str
    language: Literal["python", "sql"]
    selected_files: List[Dict[str, Any]] = []

class CodeGenerationResponse(BaseModel):
    code: str
    success: bool
    error: str = None

class CodeExecutionResponse(BaseModel):
    success: bool
    table_html: str = None
    error: str = None

def _generate_response(prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Internal function to call Gemini API."""
    try:
        if not GOOGLE_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Try different model names in order of preference
        
        
        print(f"Trying model: {model}")
        gemini_model = genai.GenerativeModel(model)
        response = gemini_model.generate_content(prompt)
        print(f"Successfully generated response with {model}")
        return response.text
        
        # If all models fail, raise the last error
        raise Exception("All Gemini models failed")
        
    except Exception as e:
        print(f"An error occurred with Gemini API: {e}")
        error_message = str(e).replace("'", "\\'")
        return f"print('Error generating code: {error_message}')"

def _clean_response(text: str, language: str) -> str:
    """Cleans markdown and other formatting from the LLM response."""
    # Remove code block markers
    text = text.strip()
    text = text.replace(f"```{language}", "").replace("```python", "").replace("```sql", "").replace("```", "")
    return text.strip()

def generate_aggregation_code(question: str, tables_context: List[Dict[str, Any]], language: str) -> str:
    """Generates the code to produce the final data table, named ans_df."""
    context_str = ""
    for table in tables_context:
        name_to_use = table.get('variable_name', table.get('filename', 'data'))
        columns_info = ""
        
        # Try to get columns info if available
        if 'columns' in table:
            columns_info = ", ".join([f"{col}" for col in table['columns']])
        elif 'columns_with_types' in table:
            columns_info = ", ".join([f"{name} ({dtype})" for name, dtype in table['columns_with_types'].items()])
        
        context_str += f"- Name: `{name_to_use}`\n"
        context_str += f"  Description: {table.get('description', 'Data file')}\n"
        if columns_info:
            context_str += f"  Columns: {columns_info}\n"
        context_str += "\n"
        
    prompt = f"""
    You are an expert {language} data analyst. A user wants to answer the question: "{question}".
    
    You have access to ONLY the following dataframes which are ALREADY LOADED into memory:
    {context_str}
    
    IMPORTANT: You can ONLY use the dataframes listed above. Do NOT create or reference any other data sources.
    
    Your task is to write a short, clean {language} script to produce the final data table that answers the question.

    --- VERY STRICT RESPONSE RULES ---
    1. Pay close attention to the data types. If a column is a string (object), you may need to convert it to a number before performing calculations.
    2. Provide ONLY the raw {language} code.
    3. You are strictly forbidden from writing `pd.read_csv` or creating your own DataFrames (e.g., NO `pd.DataFrame({{...}})`). You MUST use ONLY the provided dataframes.
    4. Structure your code in logical steps. For each step (e.g., filtering, merging, grouping), assign the result to a new DataFrame with a descriptive name (e.g., `filtered_races_df`, `merged_results_df`).
    5. The final variable containing the answer MUST be named `ans_df`.
    6. DO NOT include comments, explanations, or function definitions (no `def my_function():`).
    7. DO NOT visualize the data. Just produce the final `ans_df`.
    8. Use as few variables as possible and minimize empty lines.
    9. ONLY use the dataframes that were explicitly provided in the context above.
    10. WRITE CONCISE CODE: NO empty lines between related operations. Only use ONE empty line between major logical steps.
    11. FORMAT: Keep code compact - no unnecessary spacing or blank lines within logical blocks.
    """
    
    response_text = _generate_response(prompt)
    return _clean_response(response_text, language)

@router.post("/generate-code", response_model=CodeGenerationResponse)
async def generate_code(request: CodeGenerationRequest):
    """Generate code for data analysis based on user question and selected files."""
    try:
        if not GOOGLE_API_KEY:
            raise HTTPException(
                status_code=500, 
                detail="GEMINI_API_KEY not configured. Please set the environment variable."
            )
        
        if not request.selected_files:
            raise HTTPException(
                status_code=400, 
                detail="No files selected for analysis"
            )
        
        # Step 1: Create variable names and preserve mapping
        file_mapping = {}
        import re
        
        for file_info in request.selected_files:
            filename = file_info['filename']
            # Create clean variable name from filename
            variable_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0]).lower()
            if variable_name[0].isdigit():
                variable_name = 'df_' + variable_name
            
            # Determine bucket based on source
            source = file_info.get('source', 'uploaded')
            if source == 'uploaded':
                bucket_name = DEFAULT_BUCKET
            else:  # public/external GCS
                bucket_name = file_info.get('bucket', DEFAULT_BUCKET)
            
            file_mapping[variable_name] = {
                'filename': filename,
                'bucket': bucket_name,
                'source': source
            }
        
        # Step 2: Generate data loading code for kernel (load ALL files from both buckets)
        data_loading_code = [
            "import pandas as pd", 
            "import numpy as np",
            "# Load all files from both buckets"
        ]
        
        # Load all files from default bucket
        data_loading_code.append("# Loading files from default bucket (ai-analysis-default-bucket)")
        data_loading_code.append("try:")
        data_loading_code.append("    olist_orders_dataset = pd.read_csv('gs://ai-analysis-default-bucket/olist_orders_dataset.csv', storage_options={'token': None})")
        data_loading_code.append("    print('Loaded olist_orders_dataset from default bucket with shape:', olist_orders_dataset.shape)")
        data_loading_code.append("except Exception as e:")
        data_loading_code.append("    print('Could not load olist_orders_dataset from default bucket:', str(e))")
        data_loading_code.append("    olist_orders_dataset = None")
        data_loading_code.append("")
        
        # Load all files from sample bucket
        data_loading_code.append("# Loading files from sample bucket (sample-bucket-v2901)")
        sample_files = [
            ("circuits", "circuits.csv"),
            ("constructor_results", "constructor_results.csv"),
            ("constructor_standings", "constructor_standings.csv"),
            ("constructors", "constructors.csv"),
            ("driver_standings", "driver_standings.csv"),
            ("drivers", "drivers.csv"),
            ("pit_stops", "pit_stops.csv"),
            ("qualifying", "qualifying.csv"),
            ("races", "races.csv"),
            ("results", "results.csv"),
            ("seasons", "seasons.csv"),
            ("sprint_results", "sprint_results.csv"),
            ("status", "status.csv")
        ]
        
        for var_name, filename in sample_files:
            data_loading_code.append(f"try:")
            data_loading_code.append(f"    {var_name} = pd.read_csv('gs://sample-bucket-v2901/{filename}', storage_options={{'token': None}})")
            data_loading_code.append(f"    print('Loaded {var_name} from sample bucket with shape:', {var_name}.shape)")
            data_loading_code.append(f"except Exception as e:")
            data_loading_code.append(f"    print('Could not load {var_name} from sample bucket:', str(e))")
            data_loading_code.append(f"    {var_name} = None")
            data_loading_code.append("")
        
        # Step 3: Build context for LLM (dataframes/tables are loaded in kernel)
        context_str = ""
        for var_name, file_info in file_mapping.items():
            if request.language == "sql":
                context_str += f"- Table: `{var_name}`\n"
            else:
                context_str += f"- Name: `{var_name}`\n"
            context_str += f"  Description: Data file: {file_info['filename']}\n"
            context_str += f"  Source: {file_info['source']} from bucket {file_info['bucket']}\n"
            context_str += f"  Columns: Auto-detected from loaded data\n\n"
        
        # Step 4: Generate analysis code using LLM
        if request.language == "python":
            prompt = f"""
            You are an expert {request.language} data analyst. A user wants to answer the question: "{request.question}".
            
            You have access to ONLY the following dataframes which are ALREADY LOADED into memory:
            {context_str}
            
            IMPORTANT: You can ONLY use the dataframes listed above. Do NOT create or reference any other data sources.
            
            Your task is to write a short, clean {request.language} script to produce the final data table that answers the question.

            --- VERY STRICT RESPONSE RULES ---
            1. Pay close attention to the data types. If a column is a string (object), you may need to convert it to a number before performing calculations.
            2. Provide ONLY the raw {request.language} code.
            3. You are strictly forbidden from writing `pd.read_csv` or creating your own DataFrames. You MUST use ONLY the provided dataframes.
            4. Structure your code in logical steps. For each step, assign the result to a new DataFrame with a descriptive name.
            5. The final variable containing the answer MUST be named `ans_df`.
            6. DO NOT include comments, explanations, or function definitions.
            7. DO NOT visualize the data. Just produce the final `ans_df`.
            8. Use as few variables as possible and minimize empty lines.
            9. ONLY use the dataframes that were explicitly provided in the context above.
            10. WRITE CONCISE CODE: NO empty lines between related operations. Only use ONE empty line between major logical steps.
        """
        elif request.language == "sql":
            prompt = f"""
            You are an expert SQL data analyst. A user wants to answer the question: "{request.question}".
            
            You have access to the following tables which are ALREADY LOADED into a SQLite database:
            {context_str}
            
            IMPORTANT: You can ONLY use the tables listed above. All tables are available in the SQLite database.
            
            Your task is to write a clean SQL query to produce the final result that answers the question.

            --- VERY STRICT RESPONSE RULES ---
            1. Provide ONLY the raw SQL query.
            2. Use standard SQL syntax compatible with SQLite.
            3. You are strictly forbidden from creating new tables or using external data sources.
            4. Structure your query logically with proper JOINs, WHERE clauses, and GROUP BY as needed.
            5. Use descriptive column aliases when needed.
            6. DO NOT include comments, explanations, or multiple queries.
            7. DO NOT use CREATE TABLE, INSERT, UPDATE, or DELETE statements.
            8. Use as few subqueries as possible and write efficient queries.
            9. ONLY use the tables that were explicitly provided in the context above.
            10. WRITE CONCISE SQL: Use proper indentation and formatting.
        11. FORMAT: Keep code compact - no unnecessary spacing or blank lines within logical blocks.
        """
        
        generated_code = _generate_response(prompt)
        cleaned_code = _clean_response(generated_code, request.language)
        
        # Step 5: Return only the clean aggregation code (data loading happens in kernel)
        return CodeGenerationResponse(
            code=cleaned_code,
            success=True
        )
        
    except Exception as e:
        print(f"Error generating code: {e}")
        return CodeGenerationResponse(
            code="",
            success=False,
            error=str(e)
        )

@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute generated code in kernel and return results table."""
    try:
        if request.language == "python":
            # Step 1: Create file mapping (same as in generate_code)
            file_mapping = {}
            import re
            
            for file_info in request.selected_files:
                filename = file_info['filename']
                # Create clean variable name from filename
                variable_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0]).lower()
                if variable_name[0].isdigit():
                    variable_name = 'df_' + variable_name
                
                # Determine bucket based on source
                source = file_info.get('source', 'uploaded')
                if source == 'uploaded':
                    bucket_name = DEFAULT_BUCKET
                else:  # public/external GCS
                    bucket_name = file_info.get('bucket', DEFAULT_BUCKET)
                
                file_mapping[variable_name] = {
                    'filename': filename,
                    'bucket': bucket_name,
                    'source': source
                }
            
            # Step 2: Load ALL files from both buckets into kernel
            data_loading_code = [
                "import pandas as pd", 
                "import numpy as np",
                "# Load all files from both buckets"
            ]
            
            # Load all files from default bucket
            data_loading_code.append("# Loading files from default bucket (ai-analysis-default-bucket)")
            data_loading_code.append("try:")
            data_loading_code.append("    olist_orders_dataset = pd.read_csv('gs://ai-analysis-default-bucket/olist_orders_dataset.csv', storage_options={'token': None})")
            data_loading_code.append("    print('Loaded olist_orders_dataset from default bucket with shape:', olist_orders_dataset.shape)")
            data_loading_code.append("except Exception as e:")
            data_loading_code.append("    print('Could not load olist_orders_dataset from default bucket:', str(e))")
            data_loading_code.append("    olist_orders_dataset = None")
            data_loading_code.append("")
            
            # Load all files from sample bucket
            data_loading_code.append("# Loading files from sample bucket (sample-bucket-v2901)")
            sample_files = [
                ("circuits", "circuits.csv"),
                ("constructor_results", "constructor_results.csv"),
                ("constructor_standings", "constructor_standings.csv"),
                ("constructors", "constructors.csv"),
                ("driver_standings", "driver_standings.csv"),
                ("drivers", "drivers.csv"),
                ("pit_stops", "pit_stops.csv"),
                ("qualifying", "qualifying.csv"),
                ("races", "races.csv"),
                ("results", "results.csv"),
                ("seasons", "seasons.csv"),
                ("sprint_results", "sprint_results.csv"),
                ("status", "status.csv")
            ]
            
            for var_name, filename in sample_files:
                data_loading_code.append(f"try:")
                data_loading_code.append(f"    {var_name} = pd.read_csv('gs://sample-bucket-v2901/{filename}', storage_options={{'token': None}})")
                data_loading_code.append(f"    print('Loaded {var_name} from sample bucket with shape:', {var_name}.shape)")
                data_loading_code.append(f"except Exception as e:")
                data_loading_code.append(f"    print('Could not load {var_name} from sample bucket:', str(e))")
                data_loading_code.append(f"    {var_name} = None")
                data_loading_code.append("")
            
            # Combine data loading + user's analysis code
            full_code = "\n".join(data_loading_code) + f"""

# User's analysis code:
{request.code}
"""
            
            # Step 4: Execute in kernel
            result = execute_python_code_in_kernel(full_code)
            
            if result["success"]:
                # Convert JSON data to HTML table
                table_html = json_to_html_table(result["data"])
                return CodeExecutionResponse(
                    success=True,
                    table_html=table_html
                )
            else:
                return CodeExecutionResponse(
                    success=False,
                    error=result["error"]
                )
        
        elif request.language == "sql":
            # Step 2: Load ALL files from both buckets into kernel (same as Python)
            data_loading_code = [
                "import pandas as pd", 
                "import numpy as np",
                "import sqlite3",
                "import io",
                "# Load all files from both buckets"
            ]
            
            # Load all files from default bucket
            data_loading_code.append("# Loading files from default bucket (ai-analysis-default-bucket)")
            data_loading_code.append("try:")
            data_loading_code.append("    olist_orders_dataset = pd.read_csv('gs://ai-analysis-default-bucket/olist_orders_dataset.csv', storage_options={'token': None})")
            data_loading_code.append("    print('Loaded olist_orders_dataset from default bucket with shape:', olist_orders_dataset.shape)")
            data_loading_code.append("except Exception as e:")
            data_loading_code.append("    print('Could not load olist_orders_dataset from default bucket:', str(e))")
            data_loading_code.append("    olist_orders_dataset = None")
            data_loading_code.append("")
            
            # Load all files from sample bucket
            data_loading_code.append("# Loading files from sample bucket (sample-bucket-v2901)")
            sample_files = [
                ("circuits", "circuits.csv"),
                ("constructor_results", "constructor_results.csv"),
                ("constructor_standings", "constructor_standings.csv"),
                ("constructors", "constructors.csv"),
                ("driver_standings", "driver_standings.csv"),
                ("drivers", "drivers.csv"),
                ("pit_stops", "pit_stops.csv"),
                ("qualifying", "qualifying.csv"),
                ("races", "races.csv"),
                ("results", "results.csv"),
                ("seasons", "seasons.csv"),
                ("sprint_results", "sprint_results.csv"),
                ("status", "status.csv")
            ]
            
            for var_name, filename in sample_files:
                data_loading_code.append(f"try:")
                data_loading_code.append(f"    {var_name} = pd.read_csv('gs://sample-bucket-v2901/{filename}', storage_options={{'token': None}})")
                data_loading_code.append(f"    print('Loaded {var_name} from sample bucket with shape:', {var_name}.shape)")
                data_loading_code.append(f"except Exception as e:")
                data_loading_code.append(f"    print('Could not load {var_name} from sample bucket:', str(e))")
                data_loading_code.append(f"    {var_name} = None")
                data_loading_code.append("")
            
            # Create SQLite database and load dataframes as tables
            data_loading_code.append("# Create SQLite database and load dataframes as tables")
            data_loading_code.append("conn = sqlite3.connect(':memory:')")
            data_loading_code.append("")
            
            # Load all dataframes into SQLite
            all_dataframes = ["olist_orders_dataset"] + [var_name for var_name, _ in sample_files]
            for var_name in all_dataframes:
                data_loading_code.append(f"try:")
                data_loading_code.append(f"    if {var_name} is not None:")
                data_loading_code.append(f"        {var_name}.to_sql('{var_name}', conn, if_exists='replace', index=False)")
                data_loading_code.append(f"        print(f'Loaded {var_name} into SQLite database')")
                data_loading_code.append(f"except Exception as e:")
                data_loading_code.append(f"    print(f'Could not load {var_name} into SQLite: {{str(e)}}')")
                data_loading_code.append("")
            
            # Combine data loading + user's SQL code
            full_code = "\n".join(data_loading_code) + f"""

# User's SQL code:
print("Executing SQL query:")
print("```sql")
print('''{request.code}''')
print("```")

try:
    result_df = pd.read_sql_query('''{request.code}''', conn)
    print(f"Query executed successfully. Result shape: {{result_df.shape}}")
    print("\\nFirst few rows:")
    print(result_df.head())
    
    # Store result for JSON conversion
    ans_df = result_df
    print("\\nResult stored as 'ans_df'")
    
except Exception as e:
    print(f"SQL execution error: {{str(e)}}")
    ans_df = None

# Close database connection
conn.close()
"""
            
            # Step 3: Execute in kernel
            result = execute_python_code_in_kernel(full_code)
            
            if result["success"]:
                # Convert JSON data to HTML table
                table_html = json_to_html_table(result["data"])
                return CodeExecutionResponse(
                    success=True,
                    table_html=table_html
                )
            else:
                return CodeExecutionResponse(
                    success=False,
                    error=result["error"]
                )
        
        else:
            raise ValueError(f"Unsupported language: {request.language}")
            
    except Exception as e:
        print(f"Error executing code: {e}")
        return CodeExecutionResponse(
            success=False,
            error=str(e)
        )

def execute_python_code_in_kernel(code: str) -> Dict[str, Any]:
    """Execute Python code safely and return results."""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Add code to ensure ans_df is converted to JSON
            full_code = f"""
{code}

# Ensure ans_df exists and convert to JSON
import json
_candidate_names = [name for name, val in list(globals().items()) if isinstance(val, pd.DataFrame)]
if 'ans_df' not in globals() and _candidate_names:
    ans_df = globals()[_candidate_names[-1]]

if 'ans_df' in globals():
    result = ans_df.to_json(orient='records')
    print("SUCCESS_JSON_START")
    print(result)
    print("SUCCESS_JSON_END")
else:
    print("ERROR: No ans_df found")
"""
            f.write(full_code)
            f.flush()
            
            # Execute the code
            result = subprocess.run(
                [sys.executable, f.name],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Clean up the temporary file
            os.unlink(f.name)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Code execution failed: {result.stderr}"
                }
            
            # Extract JSON from output
            output = result.stdout
            if "SUCCESS_JSON_START" in output and "SUCCESS_JSON_END" in output:
                json_start = output.find("SUCCESS_JSON_START") + len("SUCCESS_JSON_START") + 1
                json_end = output.find("SUCCESS_JSON_END")
                json_str = output[json_start:json_end].strip()
                
                try:
                    data = json.loads(json_str)
                    return {
                        "success": True,
                        "data": data
                    }
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse JSON result: {e}"
                    }
            else:
                return {
                    "success": False,
                    "error": "No valid result found in code output"
                }
                
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Code execution timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution error: {str(e)}"
        }

def json_to_html_table(data: List[Dict[str, Any]]) -> str:
    """Convert JSON data to HTML table."""
    if not data:
        return "<p>No data to display</p>"
    
    # Get column names from the first row
    columns = list(data[0].keys()) if data else []
    
    # Build HTML table
    html = """
    <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
            <tr>
    """
    
    # Add header row
    for col in columns:
        html += f'<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{col}</th>\n'
    
    html += """
            </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
    """
    
    # Add data rows
    for row in data:
        html += "<tr>\n"
        for col in columns:
            value = row.get(col, "")
            # Format numbers nicely
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    value = f"{value:,.2f}" if value != int(value) else f"{int(value):,}"
                else:
                    value = f"{value:,}"
            
            html += f'<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{value}</td>\n'
        html += "</tr>\n"
    
    html += """
        </tbody>
    </table>
    """
    
    return html
