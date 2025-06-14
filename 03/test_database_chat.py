#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced database chat client.
This script shows how to use the chat interface for both regular conversation
and database operations.
"""

import asyncio
import subprocess
import time
import sys
from client_sse_chat_enhanced import DatabaseChatAgent

async def test_database_operations():
    """Test various database operations through the chat interface"""
    agent = DatabaseChatAgent()
    
    print("🧪 Testing Database Chat Agent")
    print("=" * 50)
    
    # Test cases covering different types of operations
    test_queries = [
        # General conversation
        "Hello! How are you today?",
        
        # Database exploration
        "What tables are in the database?",
        "Show me the database information",
        
        # Table creation
        "Create a table called users with columns: id as serial primary key, name as varchar(100), email as varchar(255), created_at as timestamp default now()",
        
        # Data insertion
        "Insert a user with name 'John Doe' and email 'john@example.com' into the users table",
        "Add another user: name 'Jane Smith', email 'jane@example.com'",
        
        # Data querying
        "Show me all users in the users table",
        "Describe the structure of the users table",
        
        # Table modification
        "Add a column called 'phone' with type varchar(20) to the users table",
        
        # Data updates
        "Update the user with name 'John Doe' to set phone to '123-456-7890'",
        
        # Final query
        "Show me all users again to see the changes",
        
        # General conversation to test mixed mode
        "Thanks for helping me with the database! What else can you do?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 40)
        
        try:
            response = await agent.chat(query)
            print(f"🤖 Response: {response}")
            
            # Small delay between operations
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    print("✅ Test completed!")

def check_server_running():
    """Check if the MCP server is running"""
    try:
        import requests
        response = requests.get("http://localhost:8100/health", timeout=5)
        return response.status_code == 200
    except:
        return False

async def main():
    """Main function to run tests or start interactive chat"""
    print("🚀 Database Chat System")
    print("=" * 50)
    
    # Check if server is running
    if not check_server_running():
        print("❌ MCP Server is not running!")
        print("Please start the server first:")
        print("   python server_sse.py")
        print("\nThen run this script again.")
        return
    
    print("✅ MCP Server is running!")
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Run automated tests")
    print("2. Start interactive chat")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        await test_database_operations()
    elif choice == "2":
        print("\nStarting interactive chat...")
        print("(This will import and run the main chat function)")
        from client_sse_chat_enhanced import main as chat_main
        await chat_main()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
