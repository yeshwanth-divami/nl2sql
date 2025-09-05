import os
import logging
from typing import Union, Annotated, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from annotated_types import MinLen
from pathlib import Path
from .dbinteraction import get_global_database_interactor, execute_sql_query_fast, QueryExecutionResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_policy_schema() -> str:
    """Load the policy schema from the data folder."""
    try:
        schema_path = Path(__file__).parent.parent.parent / "data" / "iirm" / "tables-policy-detailed.txt"
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = f.read()
        logger.info("Policy schema loaded successfully")
        return schema_content
    except FileNotFoundError:
        logger.error(f"Schema file not found at {schema_path}")
        return ""
    except Exception as e:
        logger.error(f"Error loading schema: {e}")
        return ""


def filter_schema_by_tables(full_schema: str, relevant_tables: list) -> str:
    """
    Filter the database schema to include only relevant tables.
    
    Args:
        full_schema: Complete database schema text
        relevant_tables: List of table names to include
        
    Returns:
        str: Filtered schema containing only relevant tables
    """
    if not relevant_tables or not full_schema:
        return full_schema
    
    lines = full_schema.split('\n')
    filtered_lines = []
    include_section = False
    
    for line in lines:
        # Check if this is a table definition line
        line_lower = line.lower().strip()
        if any(table.lower() in line_lower and not line.startswith(' ') for table in relevant_tables):
            include_section = True
        elif line.strip() == '' or line.startswith('---') or line.isupper():
            # Keep headers and separators
            pass
        elif not line.startswith(' ') and line.strip() != '':
            # New table section that's not in our list
            include_section = False
            
        if include_section or line.strip() == '' or line.startswith('---') or line.isupper():
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


# Response models
class PolicyQuerySuccess(BaseModel):
    sql_query: Annotated[str, MinLen(1)]
    explanation: str = Field("", description="Explanation of the SQL query for policy data")
    business_context: str = Field("", description="Business context and insights about the query")

class PolicyQueryError(BaseModel):
    error_message: str
    suggestion: str = Field("", description="Suggestion for correcting the query")

PolicyResponse = Union[PolicyQuerySuccess, PolicyQueryError]


# Output validator for policy queries
async def validate_policy_output(ctx: RunContext, output: PolicyResponse) -> PolicyResponse:
    if isinstance(output, PolicyQueryError):
        logger.info("Invalid policy request detected.")
        return output

    # Clean up the query
    output.sql_query = output.sql_query.replace('\\', '').strip()
    
    # Ensure it's a SELECT query
    if not output.sql_query.upper().startswith('SELECT'):
        logger.warning("Query is not a SELECT")
        raise ModelRetry("Please create a SELECT query for policy data")
    
    # Check for opportunity queries
    prompt_lower = ctx.prompt.lower()
    if any(keyword in prompt_lower for keyword in ['opportunity', 'brokerage', 'sales']) and 'opportunity' not in output.sql_query.lower():
        logger.warning("Opportunity-related query should include opportunity table")
        raise ModelRetry("Opportunity-related queries should reference the opportunity table")
    
    logger.info("Policy query validation passed")
    return output


def create_simple_system_prompt(relevant_tables: list, schema_content: str) -> str:
    """
    Create a simple, focused system prompt for lookup table integration.
    
    Args:
        relevant_tables: List of relevant table names
        schema_content: Database schema content
        
    Returns:
        str: System prompt focused on lookup table handling
    """
    
    focus_tables = ', '.join(relevant_tables) if relevant_tables else 'All available tables'
    
    return f"""
You are an expert SQL query generator for an insurance policy management system.

## CORE RULES:
**ONLY GENERATE SELECT STATEMENTS** - Never use DELETE, UPDATE, INSERT, ALTER, DROP, CREATE, TRUNCATE.

## CRITICAL LOOKUP TABLE RULE:
**ONLY USE LOOKUP_DATA FOR ACTUAL ENUM/STATUS VALUES**

When users mention:
1. **Enum/Status values** (Active, Inactive, Health Insurance, Motor Insurance) → Use lookup_data JOIN
2. **Entity names/projects** (Project Falcon, Company ABC, Person Names) → Search text fields directly
3. **Mixed queries** → Use LEFT JOIN for enum values + text field search

## LOOKUP VS TEXT FIELD STRATEGY:

**For ENUM/STATUS queries** (use lookup_data):
- Policy status: "Active", "Inactive", "Pending"
- Policy types: "Health Insurance", "Motor Insurance", "Fire Insurance" 
- Approval status: "Approved", "Rejected", "Under Review"

**For ENTITY/PROJECT queries** (search text fields directly):
- Project names: "Project Falcon", "Operation Alpha"
- Company names: "ABC Corp", "Tech Solutions"
- Person names: "John Smith", "Manager Name"

## CORRECT PATTERNS:

```sql
-- ENUM/STATUS: Use JOIN with lookup_data
SELECT p.*, ld.value as status 
FROM policy p 
JOIN lookup_data ld ON p.status_lid = ld.id 
WHERE ld.value ILIKE '%active%'

-- ENTITY/PROJECT: Search text fields directly
SELECT o.estimated_brokerage 
FROM opportunity o 
WHERE o.remarks ILIKE '%Project Falcon%' 
   OR o.sales_pitch ILIKE '%Project Falcon%' 
   OR o.source ILIKE '%Project Falcon%'

-- MIXED: Include both lookup and text search
SELECT o.estimated_brokerage, ld.value as opportunity_type
FROM opportunity o 
LEFT JOIN lookup_data ld ON o.opportunity_type_lid = ld.id
WHERE (o.remarks ILIKE '%Project Falcon%' 
    OR o.sales_pitch ILIKE '%Project Falcon%' 
    OR o.source ILIKE '%Project Falcon%')
  AND ld.value ILIKE '%renewal%'  -- if filtering by type too
```

## KEY FIELD PATTERNS:
- Fields ending with `_lid` → Always references `lookup_data.id`
- `policy_type_lid` → Policy types (Health, Motor, Fire, etc.)
- `status_lid` → Status values (Active, Inactive, Pending, etc.)
- `approval_status_lid` → Approval states
- Common pattern: `[table].[field]_lid = lookup_data.id`

## TEXT SEARCH STRATEGY:
**SMART ENTITY DETECTION:**

1. **Analyze the user input first**:
   - Is it a system status/type? → Use lookup_data JOIN
   - Is it a custom name/project? → Search text fields directly
   
2. **Common text fields for entity searches**:
   - `remarks` → General comments and descriptions
   - `sales_pitch` → Sales and marketing descriptions  
   - `source` → Source information and references
   - `policy_name` → Policy names and titles
   - `cover_name` → Coverage names and descriptions

3. **Always use ILIKE with % wildcards for flexibility**

## EXAMPLE QUERIES:
```sql
-- User asks: "Show active policies" (STATUS - use lookup)
SELECT p.*, ld.value as status 
FROM policy p 
JOIN lookup_data ld ON p.status_lid = ld.id 
WHERE ld.value ILIKE '%active%'

-- User asks: "Find opportunity called 'Project Falcon'" (ENTITY - text search)
SELECT o.estimated_brokerage, o.remarks, o.sales_pitch, o.source
FROM opportunity o 
WHERE o.remarks ILIKE '%Project Falcon%' 
   OR o.sales_pitch ILIKE '%Project Falcon%' 
   OR o.source ILIKE '%Project Falcon%'

-- User asks: "Health insurance opportunities" (TYPE + entity search)
SELECT o.*, ld.value as policy_type
FROM opportunity o 
LEFT JOIN lookup_data ld ON o.policy_type_lid = ld.id
WHERE ld.value ILIKE '%health%'
```

## FOCUS TABLES: {focus_tables}

## DATABASE SCHEMA:
{schema_content}

## OUTPUT REQUIREMENTS:
1. **sql_query**: Complete SELECT query with proper lookup joins
2. **explanation**: Explain the lookup strategy used  
3. **business_context**: Insurance domain relevance

**Remember: Distinguish between ENUM values (use lookup_data) and ENTITY names (search text fields)!**
"""


async def run_policy_sql_agent(prompt: str, relevant_tables: list = None) -> dict:
    """
    Run the Pydantic AI agent to generate SQL queries for policy data.
    
    Args:
        prompt: Natural language query about policy data
        relevant_tables: List of relevant table names from Onyx (optional)
        
    Returns:
        dict: Contains sql_query, explanation, and business_context or error
    """
    logger.info(f"Running policy SQL agent with prompt: {prompt}")
    logger.info(f"Relevant tables from Onyx: {relevant_tables}")
    
    if not prompt.strip():
        return {"error": "Prompt cannot be empty."}

    try:
        # Check Google API key
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_API_KEY environment variable is not set.")
            return {"error": "GOOGLE_API_KEY must be set in environment variables."}
        
        # Load the full policy schema
        full_schema = load_policy_schema()
        if not full_schema:
            return {"error": "Could not load policy schema"}
        
        # Filter schema to relevant tables if provided, but ALWAYS include lookup_data
        if relevant_tables:
            # Always include lookup_data table for text value lookups
            enhanced_tables = list(set(relevant_tables + ['lookup_data']))
            filtered_schema = filter_schema_by_tables(full_schema, enhanced_tables)
            schema_to_use = filtered_schema if filtered_schema else full_schema
            logger.info(f"Using filtered schema for tables: {enhanced_tables}")
        else:
            schema_to_use = full_schema
            logger.info("Using full schema (no relevant tables specified)")

        # Create simple focused system prompt
        system_prompt = create_simple_system_prompt(relevant_tables, schema_to_use)

        # Create the agent with simple system prompt
        agent = Agent(
            model=GoogleModel(model_name="gemini-1.5-flash", provider=GoogleProvider()),
            output_type=PolicyResponse,
            system_prompt=system_prompt
        )
        # Set the output validator
        agent.output_validator(validate_policy_output)

        # Run the agent
        result = await agent.run(prompt)
        logger.info("Policy SQL agent completed successfully")
        
        # Extract the actual output from the AgentRunResult
        if hasattr(result, 'output'):
            result_data = result.output
        else:
            result_data = result
            
        logger.info(f"Result data type: {type(result_data)}")
        logger.info(f"Result data: {result_data}")
        
        if isinstance(result_data, PolicyQuerySuccess):
            return {
                "sql_query": result_data.sql_query,
                "explanation": result_data.explanation,
                "business_context": result_data.business_context,
                "error": None
            }
        elif isinstance(result_data, PolicyQueryError):
            return {
                "sql_query": None,
                "explanation": None,
                "business_context": None,
                "error": result_data.error_message + " " + result_data.suggestion
            }
        else:
            # Fallback for unexpected result types
            logger.warning(f"Unexpected result type: {type(result_data)}")
            return {
                "sql_query": None,
                "explanation": None,
                "business_context": None,
                "error": f"Unexpected result type: {type(result_data)}"
            }
            
    except Exception as e:
        logger.error(f"Error while running policy SQL agent: {e}")
        return {
            "sql_query": None,
            "explanation": None, 
            "business_context": None,
            "error": f"SQL agent error: {str(e)}"
        }


async def run_policy_sql_agent_with_execution(prompt: str, relevant_tables: list = None, execute_query: bool = True) -> dict:
    """
    Run the policy SQL agent and execute the generated query.
    
    Args:
        prompt: Natural language query about policy data
        relevant_tables: List of relevant table names from Onyx
        execute_query: Whether to execute the generated SQL query
        
    Returns:
        dict: Contains SQL generation results plus execution results
    """
    # First generate the SQL query
    agent_result = await run_policy_sql_agent(prompt, relevant_tables)
    
    # If there's an error in generation, return early
    if agent_result.get("error"):
        return {
            **agent_result,
            "execution_success": None,
            "execution_time_ms": None,
            "row_count": None,
            "column_count": None,
            "executed_at": None,
            "data": None,
            "columns": None,
            "execution_error": None
        }
    
    # Execute the generated SQL
    sql_query = agent_result.get("sql_query")
    if sql_query and execute_query:
        try:
            execution_result = execute_sql_query_fast(sql_query)
            return {
                **agent_result,
                "execution_success": execution_result.success,
                "execution_time_ms": execution_result.execution_time_ms,
                "row_count": len(execution_result.data) if execution_result.success else 0,
                "column_count": len(execution_result.columns) if execution_result.success and execution_result.columns else 0,
                "executed_at": execution_result.executed_at,
                "data": execution_result.data if execution_result.success else None,
                "columns": execution_result.columns if execution_result.success else None,
                "execution_error": execution_result.error if not execution_result.success else None
            }
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            return {
                **agent_result,
                "execution_success": False,
                "execution_time_ms": None,
                "row_count": None,
                "column_count": None,
                "executed_at": None,
                "data": None,
                "columns": None,
                "execution_error": str(e)
            }
    elif sql_query and not execute_query:
        # Just return the query without execution
        return {
            **agent_result,
            "execution_success": None,
            "execution_time_ms": None,
            "row_count": None,
            "column_count": None,
            "executed_at": None,
            "data": None,
            "columns": None,
            "execution_error": None
        }
    
    return agent_result
