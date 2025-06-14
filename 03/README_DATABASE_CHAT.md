# Enhanced Database Chat System

This system provides an intelligent chat interface that can handle both regular conversations and database operations using PostgreSQL through MCP (Model Context Protocol) tools.

## Features

### 🤖 Intelligent Chat Agent
- **Dual Mode Operation**: Automatically detects when database operations are needed vs. regular conversation
- **Natural Language Processing**: Converts natural language requests into appropriate database operations
- **Conversation Memory**: Maintains context throughout the chat session
- **User-Friendly Responses**: Converts technical database responses into clear, conversational language

### 🗄️ Comprehensive Database Tools
- **Table Management**: Create, drop, alter tables
- **Data Operations**: Insert, update, delete, query data
- **Schema Operations**: Add/drop/rename columns
- **Database Exploration**: List tables, describe structures, get database info
- **Complex Queries**: Execute custom SQL queries

### 🔄 Continuous Chat Loop
- Runs until user says "done", "exit", "quit", or "bye"
- Handles errors gracefully and continues the conversation
- Supports both database operations and general chat

## Setup

### 1. Prerequisites
```bash
# Install required packages
pip install -r requirements.txt

# Ensure PostgreSQL is running (using Docker Compose)
docker-compose up -d
```

### 2. Environment Configuration
Make sure your `.env` file contains:
```env
OPENAI_API_KEY="your-openai-api-key"
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. Start the MCP Server
```bash
python server_sse.py
```
The server will start on `http://localhost:8100`

## Usage

### Option 1: Interactive Chat
```bash
python client_sse_chat_enhanced.py
```

### Option 2: Test Script (Recommended for first time)
```bash
python test_database_chat.py
```
This provides options to:
1. Run automated tests to see all features
2. Start interactive chat
3. Exit

## Example Conversations

### Database Operations
```
You: What tables are in the database?
Assistant: I can see that there are currently no tables in your database. The database is empty and ready for you to create some tables!

You: Create a table called users with id, name, and email columns
Assistant: I've successfully created the 'users' table for you! The table includes:
- id: Serial primary key (auto-incrementing)
- name: VARCHAR(100) for storing user names
- email: VARCHAR(255) for email addresses

You: Add a user named John Doe with email john@example.com
Assistant: Great! I've successfully added John Doe to the users table with the email john@example.com.

You: Show me all users
Assistant: Here are all the users in your database:
1. John Doe (john@example.com)
```

### Mixed Conversation
```
You: Hello! How are you today?
Assistant: Hello! I'm doing great, thank you for asking! I'm here and ready to help you with any questions you have or database operations you need to perform. How can I assist you today?

You: What's the weather like?
Assistant: I don't have access to current weather information, but I'd be happy to help you with database operations or other questions! Is there anything specific you'd like to know or any database tasks you'd like to perform?

You: Actually, can you show me what tables exist in my database?
Assistant: Of course! Let me check what tables are currently in your database...
[Proceeds with database operation]
```

## Available Database Operations

### Table Management
- "Create a table called [name] with columns [definition]"
- "Drop the [table_name] table"
- "Show me all tables"
- "Describe the [table_name] table"

### Data Operations
- "Insert [data] into [table_name]"
- "Update [table_name] set [column] = [value] where [condition]"
- "Delete from [table_name] where [condition]"
- "Show me all data from [table_name]"
- "Find [criteria] in [table_name]"

### Schema Modifications
- "Add a column [name] with type [type] to [table_name]"
- "Drop column [name] from [table_name]"
- "Rename column [old_name] to [new_name] in [table_name]"

### Advanced Operations
- "Execute this SQL query: [your SQL]"
- "Get database information"
- "Show me the structure of [table_name]"

## Architecture

### Components

1. **server_sse.py**: MCP server with database tools
   - Connects to PostgreSQL using environment variables
   - Provides 13 different database operation tools
   - Handles both sync and async database connections

2. **client_sse_chat_enhanced.py**: Enhanced chat client
   - `DatabaseChatAgent` class for intelligent routing
   - Natural language intent detection
   - Conversation history management
   - User-friendly response processing

3. **test_database_chat.py**: Test and demo script
   - Automated testing of all features
   - Interactive chat launcher
   - Server health checking

### Key Features of the Enhanced Client

#### Intent Detection
The system automatically detects database-related requests using keyword analysis:
- Query operations: select, find, search, get, show, list, etc.
- Table operations: table, create table, drop table, alter table, etc.
- Data operations: insert, add, update, modify, delete, remove, etc.
- Database specific: database, db, sql, query, column, row, record, etc.

#### Smart Tool Selection
When a database operation is detected:
1. Connects to the MCP server
2. Gets available tools
3. Uses LLM to select the most appropriate tool
4. Executes the operation
5. Processes the response into user-friendly language

#### Error Handling
- Graceful handling of connection errors
- Clear error messages for users
- Automatic retry suggestions
- Maintains conversation flow even after errors

## Troubleshooting

### Common Issues

1. **Server not running**
   ```
   Error: I'm having trouble connecting to the database
   Solution: Start the MCP server with `python server_sse.py`
   ```

2. **Database connection failed**
   ```
   Check: PostgreSQL is running (docker-compose up -d)
   Check: Environment variables in .env file are correct
   ```

3. **OpenAI API errors**
   ```
   Check: OPENAI_API_KEY is set correctly in .env
   Check: You have sufficient API credits
   ```

### Testing the Setup

1. Start PostgreSQL: `docker-compose up -d`
2. Start MCP server: `python server_sse.py`
3. Run test script: `python test_database_chat.py`
4. Choose option 1 to run automated tests

## Advanced Usage

### Custom SQL Queries
You can execute any SQL query by saying:
```
"Execute this SQL query: SELECT * FROM users WHERE name LIKE 'John%'"
```

### Complex Operations
The system can handle multi-step operations:
```
"Create a products table with id, name, price, and category, then add a few sample products"
```

### Conversation Context
The system remembers previous operations:
```
You: Create a users table
Assistant: [Creates table]
You: Add some sample data to it
Assistant: [Knows to add data to the users table created earlier]
```

## Security Notes

- The system uses parameterized queries to prevent SQL injection
- Database credentials are stored in environment variables
- All operations are logged for debugging
- Consider running in a development environment first

## Contributing

To extend the system:
1. Add new tools to `server_sse.py`
2. Update intent detection keywords in `client_sse_chat_enhanced.py`
3. Add test cases to `test_database_chat.py`
4. Update this README with new features

## License

This project is part of the MCP database integration system.
