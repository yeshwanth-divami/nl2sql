from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
from .chat_service import ChatService
from .policy_sql_agent import run_policy_sql_agent, run_policy_sql_agent_with_execution

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="NL2SQL Chat API", version="0.1.0")

# Request/Response models
class ChatRequest(BaseModel):
    prompt: str
    assistant_id: str = "16"  # Default assistant ID

class ChatResponse(BaseModel):
    user_query: str
    response: str
    chat_session_id: str = None

class PolicySQLRequest(BaseModel):
    prompt: str
    
class PolicySQLResponse(BaseModel):
    user_query: str
    sql_query: str = None
    explanation: str = None
    business_context: str = None
    error: str = None
    suggestion: str = None

class CombinedNL2SQLRequest(BaseModel):
    prompt: str
    assistant_id: str = "16"
    execute_query: bool = False

class CombinedNL2SQLResponse(BaseModel):
    user_query: str
    onyx_response: str
    relevant_tables: list = None
    sql_query: str = None
    explanation: str = None
    business_context: str = None
    error: str = None
    # Execution results
    execution_success: bool = None
    execution_time_ms: float = None
    row_count: int = None
    column_count: int = None
    executed_at: str = None
    data: list = None
    columns: list = None
    execution_error: str = None

# Initialize the chat service
chat_service = ChatService()


def extract_table_names_from_onyx_response(onyx_response: str) -> list:
    """
    Extract table names mentioned in Onyx response.
    Parses the actual structure of Onyx response to find table names.
    """
    import re
    
    logger.info(f"Parsing Onyx response: {onyx_response}")
    
    mentioned_tables = []
    
    try:
        # Define valid table names from our schema for validation
        valid_table_names = {
            'policy', 'caution_deposit', 'caution_deposit_transaction', 'caution_deposit_policy_mapping',
            'endorsement', 'mstr_policy_constraints', 'opportunity', 'opportunity_broking_slip_version_cover_map_details',
            'opportunity_broking_slip_version_details', 'opportunity_claim_experience', 'opportunity_cover_map',
            'opportunity_final_negotiation', 'opportunity_placement_slip_generation', 'opportunity_policy_confirmation',
            'opportunity_policy_confirmation_document_map', 'opportunity_policy_docket', 'opportunity_policy_docket_document_map',
            'opportunity_policy_hard_copy', 'opportunity_policy_hard_copy_document_map', 'opportunity_premium_cover_detail',
            'opportunity_rfp_cover_detail', 'policy_cd_number_map', 'policy_configuration', 'policy_configuration_components_detail',
            'policy_configuration_template_doc_map', 'policy_cover_map', 'policy_employee_claim', 'policy_employee_claim_settlement',
            'policy_employee_endorsement', 'policy_employee_enrollment', 'policy_employee_enrollment_choice',
            'policy_endorsement_template_doc_map', 'policy_enrollment_dependent', 'policy_enrollment_employee',
            'policy_enrollment_employee_policy_map', 'policy_enrollment_template_doc_map', 'policy_enrollment_upload_summary',
            'policy_insurer_map', 'policy_premium_installment_schedules', 'policy_tpa_map', 'business_target',
            'mstr_stage_activity_template', 'company', 'lookup_data'
        }
        
        # Pattern 1: Look for table names in structured format like "Relevant tables:" sections
        # Look for numbered/bulleted lists with table names
        structured_pattern = r'(?:relevant tables?|tables?)[:\s]*\n(?:\d+\.\s*([a-zA-Z_][a-zA-Z0-9_]*)|[\-\*]\s*([a-zA-Z_][a-zA-Z0-9_]*))'
        structured_matches = re.findall(structured_pattern, onyx_response, re.IGNORECASE | re.MULTILINE)
        
        for match_group in structured_matches:
            for match in match_group:
                if match and match.lower() in valid_table_names:
                    table_name = match.lower()
                    if table_name not in mentioned_tables:
                        mentioned_tables.append(table_name)
                        logger.info(f"Found table from structured list: {table_name}")
        
        # Pattern 2: Look for table names in backticks
        backtick_pattern = r'`([a-zA-Z_][a-zA-Z0-9_]*)`'
        backtick_matches = re.findall(backtick_pattern, onyx_response)
        
        for match in backtick_matches:
            table_name = match.strip().lower()
            if table_name in valid_table_names and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from backticks: {table_name}")
        
        # Pattern 3: Look for explicit table mentions in sentences
        # Match patterns like "the opportunity_rfp_cover_detail table" or "opportunity table"
        sentence_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s+table\b'
        sentence_matches = re.findall(sentence_pattern, onyx_response, re.IGNORECASE)
        
        for match in sentence_matches:
            table_name = match.strip().lower()
            if table_name in valid_table_names and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from sentence: {table_name}")
        
        # Pattern 4: Look for standalone table names that are clearly mentioned as database objects
        # Only match complete valid table names surrounded by word boundaries
        for table_name in valid_table_names:
            pattern = r'\b' + re.escape(table_name) + r'\b'
            if re.search(pattern, onyx_response, re.IGNORECASE) and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from direct mention: {table_name}")
        
        if mentioned_tables:
            logger.info(f"Successfully extracted valid tables from Onyx: {mentioned_tables}")
            return mentioned_tables
        else:
            logger.warning("No valid tables extracted from Onyx response")
            return []
            
    except Exception as e:
        logger.error(f"Error parsing Onyx response: {e}")
        return []


async def onyx_chat_with_sql_generation(prompt: str, assistant_id: str = "16", execute_query: bool = False) -> dict:
    """
    Function 1: Onyx chat service with integrated SQL generation and optional execution.
    Gets context from Onyx and generates SQL using the query generation agent.
    
    Args:
        prompt: Natural language query
        assistant_id: Onyx assistant ID
        execute_query: Whether to execute the generated SQL query
        
    Returns:
        dict: Combined response with Onyx context, generated SQL, and optional results
    """
    try:
        logger.info(f"Starting Onyx chat with SQL generation (execute={execute_query}) for: {prompt}")
        
        # Step 1: Get context from Onyx
        try:
            onyx_response = await chat_service.create_chat_session(
                prompt=prompt,
                assistant_id=assistant_id
            )
            logger.info("Onyx response received")
            
            # Step 2: Extract relevant table names from Onyx response
            relevant_tables = extract_table_names_from_onyx_response(onyx_response)
            logger.info(f"Extracted relevant tables from Onyx: {relevant_tables}")
            
        except Exception as onyx_error:
            logger.warning(f"Onyx service error: {onyx_error}")
            logger.info("Falling back to SQL generation without Onyx context")
            onyx_response = f"Onyx service unavailable: {str(onyx_error)}"
            relevant_tables = []  # Use full schema as fallback
        
        # Step 3: Generate SQL and optionally execute using agent with execution
        sql_result = await run_policy_sql_agent_with_execution(prompt, relevant_tables, execute_query)
        logger.info("SQL generation and execution completed")
        
        # Combine results
        result = {
            "user_query": prompt,
            "onyx_response": onyx_response,
            "relevant_tables": relevant_tables,
            "sql_query": sql_result.get("sql_query", ""),
            "explanation": sql_result.get("explanation", ""),
            "business_context": sql_result.get("business_context", ""),
            "error": sql_result.get("error")
        }
        
        # Add execution results if query was executed
        if execute_query:
            result.update({
                "execution_success": sql_result.get("execution_success"),
                "execution_time_ms": sql_result.get("execution_time_ms"),
                "row_count": sql_result.get("row_count"),
                "column_count": sql_result.get("column_count"),
                "executed_at": sql_result.get("executed_at"),
                "data": sql_result.get("data"),
                "columns": sql_result.get("columns"),
                "execution_error": sql_result.get("execution_error")
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Onyx chat with SQL generation: {e}")
        return {
            "user_query": prompt,
            "error": f"Failed to process request: {str(e)}"
        }


async def standalone_sql_generation(prompt: str, relevant_tables: list = None, execute_query: bool = False) -> dict:
    """
    Function 2: Standalone SQL query generation and optional execution.
    Direct SQL generation without Onyx integration.
    
    Args:
        prompt: Natural language query
        relevant_tables: Optional list of relevant tables
        execute_query: Whether to execute the generated SQL query
        
    Returns:
        dict: SQL generation and execution result
    """
    try:
        logger.info(f"Starting standalone SQL generation (execute={execute_query}) for: {prompt}")
        
        # Generate SQL and optionally execute using agent with execution
        sql_result = await run_policy_sql_agent_with_execution(prompt, relevant_tables, execute_query)
        logger.info("Standalone SQL generation and execution completed")
        
        result = {
            "user_query": prompt,
            "sql_query": sql_result.get("sql_query", ""),
            "explanation": sql_result.get("explanation", ""),
            "business_context": sql_result.get("business_context", ""),
            "error": sql_result.get("error")
        }
        
        # Add execution results if query was executed
        if execute_query:
            result.update({
                "execution_success": sql_result.get("execution_success"),
                "execution_time_ms": sql_result.get("execution_time_ms"),
                "row_count": sql_result.get("row_count"),
                "column_count": sql_result.get("column_count"),
                "executed_at": sql_result.get("executed_at"),
                "data": sql_result.get("data"),
                "columns": sql_result.get("columns"),
                "execution_error": sql_result.get("execution_error")
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in standalone SQL generation: {e}")
        return {
            "user_query": prompt,
            "error": f"Failed to generate SQL: {str(e)}"
        }

@app.post("/nl2sql", response_model=CombinedNL2SQLResponse)
async def combined_nl2sql(request: CombinedNL2SQLRequest):
    """
    Combined NL2SQL: Uses Function 1 (Onyx chat with integrated SQL generation and optional execution).
    
    - **prompt**: Natural language query about policy data
    - **assistant_id**: The ID of the assistant to use (default: 16)
    - **execute_query**: Whether to execute the generated SQL query (default: False)
    """
    try:
        # Check environment variables
        if not os.getenv('AUTH_TOKEN'):
            raise HTTPException(
                status_code=500, 
                detail="AUTH_TOKEN environment variable is not set"
            )
        if not os.getenv('GOOGLE_API_KEY'):
            raise HTTPException(
                status_code=500, 
                detail="GOOGLE_API_KEY environment variable is not set"
            )
        
        # Use Function 1: Onyx chat with integrated SQL generation and optional execution
        result = await onyx_chat_with_sql_generation(
            prompt=request.prompt,
            assistant_id=request.assistant_id,
            execute_query=request.execute_query
        )
        
        # Create response from the separated function result
        response = CombinedNL2SQLResponse(
            user_query=result["user_query"],
            onyx_response=result.get("onyx_response", ""),
            relevant_tables=result.get("relevant_tables", [])
        )
        
        if result.get("error"):
            response.error = result["error"]
        else:
            response.sql_query = result.get("sql_query", "")
            response.explanation = result.get("explanation", "")
            response.business_context = result.get("business_context", "")
            
            # Add execution results if available
            if request.execute_query:
                response.execution_success = result.get("execution_success")
                response.execution_time_ms = result.get("execution_time_ms")
                response.row_count = result.get("row_count")
                response.column_count = result.get("column_count")
                response.executed_at = result.get("executed_at")
                response.data = result.get("data")
                response.columns = result.get("columns")
                response.execution_error = result.get("execution_error")
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    """Get current configuration (for debugging)"""
    return {
        "auth_token_set": bool(os.getenv('AUTH_TOKEN')),
        "google_api_key_set": bool(os.getenv('GOOGLE_API_KEY')),
        "llm_model_provider": os.getenv('LLM_MODEL_PROVIDER'),
        "llm_model_version": os.getenv('LLM_MODEL_VERSION'),
        "default_assistant_id": chat_service.default_persona_id,
        "endpoints": {
            "chat": "/chat - Onyx chat service",
            "policy_sql": "/policy-sql - Pydantic AI SQL generation",
            "combined": "/nl2sql-combined - Onyx + Pydantic AI"
        }
    }
