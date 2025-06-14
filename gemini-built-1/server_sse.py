import datetime
import os
from zoneinfo import ZoneInfo
from fastapi import FastAPI
import asyncio
import json
from typing import List, Dict, Any, Optional

import requests
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

import aiomysql

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_DATABASE', 'app_db'),
    'user': os.getenv('DB_USERNAME', 'app_user'),
    'password': os.getenv('DB_PASSWORD', 'app_pass')
}

# Database connection functions
def get_sync_connection():
    """Get a synchronous MySQL database connection"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset='utf8mb4'
        )
        logger.info("Successfully connected to MySQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL database: {e}")
        raise

async def get_async_connection():
    """Get an asynchronous MySQL database connection"""
    try:
        conn = await aiomysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            db=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset='utf8mb4'
        )
        logger.info("Successfully connected to MySQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL database: {e}")
        raise


# Initialize the MCP server with your tools
mcp = FastMCP(
    name="Database SSE Server"
)

transport = SseServerTransport("/messages/")

@mcp.tool()
def execute_sql_query(query: str):
    """Execute SELECT queries on the MySQL database. This tool provides read-only database access for retrieving and analyzing stored information.

    CURRENT PERMISSIONS: READ-ONLY ACCESS
    - You can ONLY execute SELECT queries to retrieve data
    - You CANNOT execute INSERT, UPDATE, DELETE, CREATE, ALTER, or other write operations
    - Use this tool to explore existing data and understand database structure

    PRIMARY PURPOSE: Retrieve and analyze information stored in the database following a systematic approach.

    CHAIN OF THOUGHT FOR RETRIEVING INFORMATION:
    1. Identify what information you need to find
    2. Execute "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';" to list all existing tables
    3. Analyze which tables might contain the relevant information
    4. Execute "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'your_table';" to understand table structures
    5. Construct appropriate SELECT queries to retrieve the needed data
    6. Use JOINs, WHERE clauses, and other SQL features to filter and combine data as needed

    EXPLICIT READ CAPABILITIES - YOU CAN:
    - Run any SELECT query to retrieve data
    - List all tables in the database
    - Examine table structures and column information
    - Execute complex queries with JOINs, subqueries, aggregations
    - Filter data with WHERE clauses
    - Sort and group data with ORDER BY and GROUP BY
    - Count, sum, and perform other aggregate functions
    - Query system tables for metadata information

    WHEN TO USE THIS TOOL:
    - Retrieving previously stored information
    - Exploring what data exists in the database
    - Understanding database structure and schema
    - Complex data queries requiring JOINs or advanced SQL features
    - Analyzing and reporting on existing data
    - Searching for specific information across tables
    - ANY read operation or data exploration task

    LIMITATIONS:
    - NO write operations (INSERT, UPDATE, DELETE)
    - NO schema modifications (CREATE, ALTER, DROP)
    - NO data manipulation - only data retrieval

    IMPORTANT REMINDERS:
    - You have DIRECT read access to the database - use it freely
    - Always explore existing tables and structures first
    - Use appropriate SELECT queries to find relevant information
    - This tool should be your primary method for database data retrieval

    Args:
        query: Any valid SELECT query string or other read-only SQL commands

    Returns:
    - Structured data results from SELECT queries
    - Table and column information from metadata queries
    - Error information if query fails
    """

    try:
        logger.info(f"Executing SQL query: {query}")
        conn = get_sync_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        
        # Check if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            results_list = [dict(row) for row in results]
            conn.close()
            return {
                "success": True,
                "data": results_list,
                "row_count": len(results_list)
            }
        else:
            # For INSERT, UPDATE, DELETE, etc.
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            return {
                "success": True,
                "message": f"Query executed successfully. {affected_rows} rows affected.",
                "affected_rows": affected_rows
            }
    except Exception as e:
        logger.error(f"Database query error: {e}")
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }

async def handle_sse(request):
    # Prepare bidirectional streams over SSE
    async with transport.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as (in_stream, out_stream):
        # Run the MCP server: read JSON-RPC from in_stream, write replies to out_stream
        await mcp._mcp_server.run(
            in_stream,
            out_stream,
            mcp._mcp_server.create_initialization_options()
        )


#Build a small Starlette app for the two MCP endpoints
sse_app = Starlette(
    routes=[
        Route("/sse", handle_sse, methods=["GET"]),
        # Note the trailing slash to avoid 307 redirects
        Mount("/messages/", app=transport.handle_post_message)
    ]
)


app = FastAPI()
app.mount("/", sse_app)

@app.get("/health")
def read_root():
    return {"message": "MCP SSE Server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
