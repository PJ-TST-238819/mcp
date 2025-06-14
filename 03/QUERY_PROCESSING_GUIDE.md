# Query Processing Guide: How to Use the MCP Server for Database Interactions

This guide explains in detail how queries are processed through the MCP (Model Context Protocol) server to interact with the PostgreSQL database.

## ⚠️ IMPORTANT: Direct Database Execution

**The MCP server executes database commands IMMEDIATELY and DIRECTLY without asking for user confirmation or permissions.** When you request a database operation through the chat interface, the system will:

- ✅ **Immediately execute** CREATE, DROP, INSERT, UPDATE, DELETE operations
- ✅ **Directly modify** your database structure and data
- ✅ **Permanently change** your database without confirmation prompts
- ❌ **No "Are you sure?" prompts** - operations execute instantly
- ❌ **No undo functionality** - changes are committed immediately

**This means:**
- "Drop the users table" → **Table is deleted immediately**
- "Delete all records from orders" → **All data is permanently removed**
- "Update all prices to 0" → **All prices are changed to 0 instantly**

**Use with caution in production environments!**

## Overview of Query Processing Flow

```
User Input → Intent Detection → Tool Selection → MCP Server → DIRECT DATABASE EXECUTION → Response
```

## Detailed Processing Steps

### 1. User Input Analysis

When you send a message, the system first analyzes it to determine the intent:

```python
# Example user inputs and their detection
"Show me all tables"           → Database operation detected
"Create a users table"         → Database operation detected  
"Hello, how are you?"          → General conversation detected
"What's the weather like?"     → General conversation detected
```

**Intent Detection Keywords:**
- **Query operations**: select, find, search, get, show, list, display, view, retrieve
- **Table operations**: table, tables, create table, drop table, alter table, describe table
- **Data operations**: insert, add, update, modify, delete, remove, change
- **Database specific**: database, db, sql, query, column, columns, row, rows, record, records
- **Schema operations**: schema, structure, add column, drop column, rename column

### 2. Tool Selection Process

When a database operation is detected, the system:

1. **Connects to MCP Server** at `http://localhost:8100/sse`
2. **Retrieves available tools** from the server
3. **Analyzes the user request** against available tools
4. **Selects the most appropriate tool** using LLM reasoning

**Available MCP Tools:**

| Tool Name | Purpose | Example Usage |
|-----------|---------|---------------|
| `execute_sql_query` | Run any SQL query | "Execute: SELECT * FROM users" |
| `list_tables` | Show all tables | "What tables exist?" |
| `describe_table` | Show table structure | "Describe the users table" |
| `create_table` | Create new table | "Create a products table" |
| `drop_table` | Delete table | "Drop the old_data table" |
| `insert_data` | Add new records | "Add a user named John" |
| `update_data` | Modify existing records | "Update user with id 1" |
| `delete_data` | Remove records | "Delete inactive users" |
| `alter_table_add_column` | Add column to table | "Add phone column to users" |
| `alter_table_drop_column` | Remove column | "Remove old_field column" |
| `alter_table_rename_column` | Rename column | "Rename email to email_address" |
| `get_database_info` | Get DB information | "Show database details" |
| `TimeTool` | Get current time | "What time is it in Tokyo?" |
| `weather_tool` | Get weather info | "Weather in London?" |

### 3. Tool Selection Examples

Here's how different user requests map to specific tools:

#### Example 1: Table Listing
```
User: "What tables are in the database?"
↓
Intent: Database operation detected (keywords: "tables", "database")
↓
Tool Selection Prompt to LLM:
"User wants to see tables. Available tools include list_tables which 
lists all tables in the database. Choose appropriate tool."
↓
LLM Response: {"tool": "list_tables", "arguments": {}}
↓
MCP Server executes list_tables()
```

#### Example 2: Table Creation
```
User: "Create a users table with id, name, and email"
↓
Intent: Database operation detected (keywords: "create", "table")
↓
Tool Selection Prompt to LLM:
"User wants to create a table. Available tools include create_table 
which creates new tables with column definitions."
↓
LLM Response: {
  "tool": "create_table",
  "arguments": {
    "table_name": "users",
    "columns_definition": "id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(255)"
  }
}
↓
MCP Server executes create_table()
```

#### Example 3: Data Insertion
```
User: "Add a user named John Doe with email john@example.com"
↓
Intent: Database operation detected (keywords: "add", "user")
↓
Tool Selection Prompt to LLM:
"User wants to insert data. Available tools include insert_data 
which adds new records to tables."
↓
LLM Response: {
  "tool": "insert_data",
  "arguments": {
    "table_name": "users",
    "data": "{\"name\": \"John Doe\", \"email\": \"john@example.com\"}"
  }
}
↓
MCP Server executes insert_data()
```

### 4. MCP Server Processing

When the MCP server receives a tool call:

1. **Validates the tool name** and arguments
2. **Establishes database connection** using environment variables
3. **Executes the appropriate function** with provided arguments
4. **Returns structured response** with success/error status

**Database Connection Process:**
```python
# Server uses these environment variables from .env
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'app_db'),
    'user': os.getenv('POSTGRES_USER', 'app_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'app_pass')
}
```

### 5. Response Processing

The MCP server returns responses in this format:

```json
{
  "success": true/false,
  "data": [...],           // For SELECT queries
  "message": "...",        // For other operations
  "affected_rows": 5,      // For INSERT/UPDATE/DELETE
  "error": "..."           // If success is false
}
```

The client then processes this technical response into user-friendly language:

```
Technical Response: {"success": true, "tables": ["users", "products"], "count": 2}
↓
User-Friendly Response: "I found 2 tables in your database: 'users' and 'products'."
```

## How to Use the MCP Server Directly

### Method 1: Through the Enhanced Chat Client (Recommended)

```bash
python client_sse_chat_enhanced.py
```

Then use natural language:
- "Show me all tables"
- "Create a products table with id, name, price"
- "Add a product: name 'Laptop', price 999.99"
- "Update products set price = 899.99 where name = 'Laptop'"

### Method 2: Direct MCP Client Usage

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def direct_mcp_usage():
    async with sse_client("http://localhost:8100/sse") as (in_stream, out_stream):
        async with ClientSession(in_stream, out_stream) as session:
            # Initialize
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])
            
            # Call a specific tool
            result = await session.call_tool("list_tables", arguments={})
            print("Result:", result.content[0].text)

asyncio.run(direct_mcp_usage())
```

### Method 3: HTTP API Usage

The MCP server also exposes an HTTP endpoint:

```bash
# Check server health
curl http://localhost:8100/health

# For SSE connections (used by MCP clients)
curl http://localhost:8100/sse
```

## Advanced Query Processing Patterns

### 1. Complex Multi-Step Operations

```
User: "Create a users table, add some sample data, then show me the results"
↓
System processes this as multiple operations:
1. create_table for users
2. insert_data for sample records  
3. execute_sql_query to SELECT all users
```

### 2. Conditional Logic

```
User: "If the users table doesn't exist, create it, otherwise show me all users"
↓
System:
1. Uses list_tables to check existing tables
2. Based on result, either calls create_table or execute_sql_query
```

### 3. Error Handling and Recovery

```
User: "Add a user to the customers table"
↓
If customers table doesn't exist:
- MCP server returns error
- Client suggests: "The customers table doesn't exist. Would you like me to create it first?"
```

## Tool-Specific Processing Details

### execute_sql_query
- **Input**: Any valid SQL query string
- **Processing**: Executes query directly on database
- **Output**: For SELECT: data rows; For others: affected row count
- **Use case**: Complex queries, custom operations

```python
# Example call
await session.call_tool("execute_sql_query", {
    "query": "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name"
})
```

### insert_data
- **Input**: table_name (string), data (JSON string)
- **Processing**: Parses JSON, builds INSERT query with parameterized values
- **Output**: Success message with inserted data
- **Security**: Uses parameterized queries to prevent SQL injection

```python
# Example call
await session.call_tool("insert_data", {
    "table_name": "users",
    "data": '{"name": "Alice", "email": "alice@example.com", "age": 30}'
})
```

### update_data
- **Input**: table_name, set_data (JSON), where_condition (string)
- **Processing**: Builds UPDATE query with SET clause from JSON
- **Output**: Number of affected rows
- **Safety**: Requires explicit WHERE condition

```python
# Example call
await session.call_tool("update_data", {
    "table_name": "users",
    "set_data": '{"email": "newemail@example.com", "updated_at": "2024-01-01"}',
    "where_condition": "id = 5"
})
```

## Error Handling in Query Processing

### Common Error Scenarios

1. **Database Connection Errors**
   ```
   Error: "Failed to connect to database"
   Cause: PostgreSQL not running or wrong credentials
   Solution: Check docker-compose and .env file
   ```

2. **Table Not Found**
   ```
   Error: "Table 'xyz' not found"
   Cause: Referencing non-existent table
   Solution: Use list_tables to see available tables
   ```

3. **Invalid SQL Syntax**
   ```
   Error: "Syntax error in SQL query"
   Cause: Malformed SQL in execute_sql_query
   Solution: Check SQL syntax or use specific tools
   ```

4. **Data Type Mismatches**
   ```
   Error: "Invalid input syntax for type integer"
   Cause: Trying to insert string into integer column
   Solution: Check table schema with describe_table
   ```

### Error Recovery Patterns

The system handles errors gracefully:

```python
try:
    result = await session.call_tool("insert_data", arguments)
    return process_success_response(result)
except Exception as e:
    if "table does not exist" in str(e):
        return "The table doesn't exist. Would you like me to create it first?"
    elif "duplicate key" in str(e):
        return "This record already exists. Would you like to update it instead?"
    else:
        return f"I encountered an error: {str(e)}"
```

## Performance Considerations

### Connection Management
- Each MCP operation opens a new database connection
- Connections are properly closed after each operation
- For high-frequency operations, consider connection pooling

### Query Optimization
- Use specific tools (list_tables, describe_table) instead of complex SQL when possible
- For large datasets, consider pagination in custom SQL queries
- Use indexes for frequently queried columns

### Memory Usage
- Large result sets are streamed rather than loaded entirely into memory
- Conversation history is limited to prevent memory bloat
- Tool responses are processed incrementally

## Security Best Practices

### SQL Injection Prevention
- All tools use parameterized queries
- User input is properly escaped
- Direct SQL execution is logged and monitored

### Access Control
- Database credentials are environment-based
- No hardcoded passwords in code
- Consider role-based database access

### Data Validation
- Input validation on all tool parameters
- Type checking for JSON data
- Sanitization of table and column names

This comprehensive guide should help you understand exactly how queries flow through the MCP server and how to effectively use it for database interactions.
