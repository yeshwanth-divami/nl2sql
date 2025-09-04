import os
import asyncio
import logging
from typing import Union, Annotated
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from annotated_types import MinLen
from datetime import date
from pathlib import Path

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
    
    # Split schema into sections by table
    sections = []
    current_section = []
    
    for line in full_schema.split('\n'):
        # Look for table definitions (lines starting with CREATE TABLE or table names)
        if line.strip().startswith('CREATE TABLE') or (line.strip() and not line.startswith(' ') and not line.startswith('\t')):
            # Check if this is a new table section
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
        current_section.append(line)
    
    # Don't forget the last section
    if current_section:
        sections.append('\n'.join(current_section))
    
    # Filter sections to include only relevant tables
    filtered_sections = []
    for section in sections:
        for table_name in relevant_tables:
            if table_name.lower() in section.lower():
                filtered_sections.append(section)
                break
    
    return '\n\n'.join(filtered_sections) if filtered_sections else full_schema


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
    
    # Basic validation for policy-related keywords
    query_lower = output.sql_query.lower()
    prompt_lower = ctx.prompt.lower()
    
    # Check if policy-related queries include proper table references
    if any(keyword in prompt_lower for keyword in ['policy', 'premium', 'insured']) and 'policy' not in query_lower:
        logger.warning("Policy-related query should include policy table")
        raise ModelRetry("Policy-related queries should reference the policy table")
    
    # Check for endorsement queries
    if 'endorsement' in prompt_lower and 'endorsement' not in query_lower:
        logger.warning("Endorsement query should include endorsement table")
        raise ModelRetry("Endorsement queries should reference the endorsement table")
    
    # Validate company context
    if any(keyword in prompt_lower for keyword in ['company', 'organization']) and 'company' not in query_lower:
        logger.warning("Company-related query might need company table join")
        # This is a warning, not an error, so we don't retry
    
    logger.info("Policy query validation passed")
    return output


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
        
        # Filter schema to relevant tables if provided
        if relevant_tables:
            filtered_schema = filter_schema_by_tables(full_schema, relevant_tables)
            schema_to_use = filtered_schema if filtered_schema else full_schema
            logger.info(f"Using filtered schema for tables: {relevant_tables}")
        else:
            schema_to_use = full_schema
            logger.info("Using full schema (no relevant tables specified)")

        # Create the agent with policy-specific system prompt
        agent = Agent(
            model=GoogleModel(model_name="gemini-1.5-flash", provider=GoogleProvider()),
            output_type=PolicyResponse,
            system_prompt=f"""
You are an expert SQL query generator for an insurance policy management system. 
Your job is to write SQL queries for policy-related data based on user requests. 

### Core Objective
Analyze user queries carefully and generate **accurate, complete, and production-quality SQL queries**. 
The queries may be simple or highly complex — assume the user can ask for **multi-table joins, nested queries, aggregations, filters, time-based analysis, CTEs, or subqueries**. 
Always produce the **most effective and precise SQL** to fully answer the request. 

### Focus Tables
{', '.join(relevant_tables) if relevant_tables else 'All available tables'}

### Database Schema Overview
This is an insurance policy management database with the following key tables:
- `policy`: Main policy information (premiums, coverage, dates, status)
- `endorsement`: Policy modifications and changes
- `caution_deposit`: Security deposits for policies
- `caution_deposit_transaction`: Deposit transaction history
- `caution_deposit_policy_mapping`: Mapping between deposits and policies
- `company`: Company/organization information
- `opportunity`: Sales opportunities that lead to policies

### Important Business Rules
1. **Policy Status**: Use `status_lid` where 1 = Active, 0 = Inactive. 
2. **Dates**: 
   - `policy_from` and `policy_to` define coverage period. 
   - `created_at` is when policy was created. 
   - For active policies, use: `CURRENT_DATE BETWEEN policy_from AND policy_to`.
3. **Amounts**: 
   - `sum_insured` = coverage amount.  
   - `premium_at_inception` = initial premium.  
   - `gross_premium_amount` = premium including charges.  
   - `net_premium_amount` = premium after deductions.  
4. **Company Relations**: Link policies to companies via `company_id`.  
5. **Endorsements**: Linked to policies via `policy_id`. Represent policy changes.  
6. **String Matching**: Always use `ILIKE` for case-insensitive searches.  

### Query Guidelines
- Always **fully resolve the user’s intent** — handle complex queries confidently.  
- Use **JOINs, subqueries, or CTEs** when needed to ensure correctness.  
- Alias tables consistently and write clear, maintainable SQL.  
- For date-based queries, consider both policy effective dates and creation dates.  
- Use correct **aggregations** and explicitly state which fields are summed/averaged/etc.  
- Handle **NULL values** properly to avoid missing data.  
- For potentially large result sets, add `LIMIT` unless the user explicitly asks for all rows.  
- Optimize for **accuracy first, efficiency second**.  
- Provide both a **step-by-step explanation** of how the query answers the prompt and a **business context** that connects results back to insurance operations.  

### Common Query Patterns
- **Premium totals**: `SUM(premium_at_inception)` or `SUM(gross_premium_amount)`  
- **Active policies**: `WHERE status_lid = 1 AND CURRENT_DATE BETWEEN policy_from AND policy_to`  
- **Company analysis**: JOIN with company table.  
- **Endorsements**: JOIN with endorsement by `policy_id`.  
- **Time analysis**: Use `GROUP BY` on `DATE_TRUNC` or ranges.  

### Database Schema (Relevant Tables)
{schema_to_use}

### Current Date
{date.today()}

Now, generate the **best possible SELECT query** that answers the user's question about policy data.  
- If the query is **complex**, break it down logically and still provide a single SQL output.  
- Never skip necessary JOINs or logic for simplicity.  
- Output must always include:  
  1. `sql_query`: The final SQL query (production-ready).  
  2. `explanation`: Step-by-step breakdown of the query.  
  3. `business_context`: Why this query matters in an insurance policy context.  
"""
        )

        # Set the output validator
        agent.output_validator(validate_policy_output)

        # Run the agent
        result = await agent.run(prompt)
        logger.info("Policy SQL agent completed successfully")

        if isinstance(result.output, PolicyQuerySuccess):
            return {
                "sql_query": result.output.sql_query,
                "explanation": result.output.explanation,
                "business_context": result.output.business_context
            }
        else:
            return {
                "error": result.output.error_message,
                "suggestion": result.output.suggestion
            }

    except Exception as e:
        logger.error(f"Error while running policy SQL agent: {e}")
        return {"error": str(e)}


# Test function
async def test_policy_agent():
    """Test the policy agent with sample queries."""
    test_queries = [
        "How many active policies do we have?",
        "What's the total premium amount for all policies?",
        "Show me policies created this year",
        "Which company has the highest total coverage?",
        "List all endorsements made in the last 30 days"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing: {query}")
        result = await run_policy_sql_agent(query)
        print(f"📊 Result: {result}")
