from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
from .chat_service import ChatService
from .policy_sql_agent import run_policy_sql_agent

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

class CombinedNL2SQLResponse(BaseModel):
    user_query: str
    onyx_response: str
    relevant_tables: list = None
    sql_query: str = None
    explanation: str = None
    business_context: str = None
    error: str = None

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
        # Pattern 1: Look for "Relevant tables:" followed by numbered lists
        # Example: "1. policy (description)" or "- policy (description)"
        table_pattern = r'(?:^|\n)\s*(?:\d+\.|\-|\*)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(table_pattern, onyx_response, re.MULTILINE | re.IGNORECASE)
        
        for match in matches:
            table_name = match.strip().lower()
            if table_name and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from numbered list: {table_name}")
        
        # Pattern 2: Look for table names in backticks or code format
        # Example: "`policy`" or "table `policy`"
        backtick_pattern = r'`([a-zA-Z_][a-zA-Z0-9_]*)`'
        backtick_matches = re.findall(backtick_pattern, onyx_response)
        
        for match in backtick_matches:
            table_name = match.strip().lower()
            if table_name and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from backticks: {table_name}")
        
        # Pattern 3: Look for explicit table mentions
        # Example: "The policy table", "from the company table"
        explicit_pattern = r'\b(?:the\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+table\b'
        explicit_matches = re.findall(explicit_pattern, onyx_response, re.IGNORECASE)
        
        for match in explicit_matches:
            table_name = match.strip().lower()
            if table_name and table_name not in mentioned_tables:
                mentioned_tables.append(table_name)
                logger.info(f"Found table from explicit mention: {table_name}")
        
        # Remove duplicates and filter out common words that aren't table names
        common_words = {'table', 'tables', 'data', 'information', 'details', 'records', 'database', 'schema'}
        mentioned_tables = [t for t in mentioned_tables if t not in common_words and len(t) > 2]
        
        # Remove duplicates while preserving order
        unique_tables = []
        for table in mentioned_tables:
            if table not in unique_tables:
                unique_tables.append(table)
        
        if unique_tables:
            logger.info(f"Successfully extracted tables from Onyx: {unique_tables}")
            return unique_tables
        else:
            logger.warning("No tables extracted from Onyx response using pattern matching")
            return []
            
    except Exception as e:
        logger.error(f"Error parsing Onyx response: {e}")
        return []

@app.post("/nl2sql", response_model=CombinedNL2SQLResponse)
async def combined_nl2sql(request: CombinedNL2SQLRequest):
    """
    Combined NL2SQL: Get context from Onyx + Generate SQL using Pydantic AI.
    
    - **prompt**: Natural language query about policy data
    - **assistant_id**: The ID of the assistant to use (default: 16)
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
        
        # Step 1: Get context from Onyx
        onyx_response = await chat_service.create_chat_session(
            prompt=request.prompt,
            assistant_id=request.assistant_id
        )
        
        # Step 1.5: Extract relevant table names from Onyx response
        relevant_tables = extract_table_names_from_onyx_response(onyx_response)
        logger.info(f"Extracted relevant tables from Onyx: {relevant_tables}")
        
        # Step 2: Generate SQL using Pydantic AI agent with relevant tables
        sql_result = await run_policy_sql_agent(request.prompt, relevant_tables)
        
        response = CombinedNL2SQLResponse(
            user_query=request.prompt,
            onyx_response=onyx_response,
            relevant_tables=relevant_tables
        )
        
        if "error" in sql_result:
            response.error = sql_result["error"]
        else:
            response.sql_query = sql_result.get("sql_query", "")
            response.explanation = sql_result.get("explanation", "")
            response.business_context = sql_result.get("business_context", "")
        
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
