import asyncio
import json
import re
from typing import Dict, List, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

import httpx
_orig_request = httpx.AsyncClient.request

async def _patched_request(self, method, url, *args, **kwargs):
    kwargs.setdefault("follow_redirects", True)
    return await _orig_request(self, method, url, *args, **kwargs)

httpx.AsyncClient.request = _patched_request

class DatabaseChatAgent:
    def __init__(self):
        self.client = OpenAI()
        self.conversation_history = []
        self.sse_url = "http://localhost:8100/sse"
        
    def detect_database_intent(self, message: str) -> bool:
        """Detect if the user's message requires database operations"""
        database_keywords = [
            # Query operations
            'select', 'find', 'search', 'get', 'show', 'list', 'display', 'view', 'retrieve',
            # Table operations
            'table', 'tables', 'create table', 'drop table', 'alter table', 'describe table',
            # Data operations
            'insert', 'add', 'update', 'modify', 'delete', 'remove', 'change',
            # Database specific
            'database', 'db', 'sql', 'query', 'column', 'columns', 'row', 'rows', 'record', 'records',
            # Schema operations
            'schema', 'structure', 'add column', 'drop column', 'rename column'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in database_keywords)
    
    def llm_chat(self, message: str, system_prompt: str = None) -> str:
        """Send message to LLM for regular chat or processing"""
        if system_prompt is None:
            system_prompt = (
                "You are a helpful database assistant with read-only access. You can help with both general conversation "
                "and database operations. Be friendly and conversational while being informative. "
                "IMPORTANT: You have READ-ONLY database access. When the user asks about information or wants to explore data, you must directly run SELECT queries on the database as follows: "
                "First, list existing tables to understand what data is available. "
                "Then, examine table structures to understand the schema. "
                "Finally, execute appropriate SELECT queries to retrieve and analyze the requested information. "
                "You CANNOT store new information, create tables, or modify existing data - only retrieve and analyze existing data. "
                "If users ask you to store or remember information, explain that you currently have read-only access and can only help them explore existing data."
            )

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history for context
        for entry in self.conversation_history[-6:]:  # Keep last 6 exchanges for context
            messages.append(entry)
        
        messages.append({"role": "user", "content": message})
        
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        return completion.choices[0].message.content
    
    def get_tool_selection_prompt(self, query: str, tools: any) -> str:
        """Generate prompt for tool selection"""
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in tools.tools
        ])
        
        return (
            "You are a database assistant with access to these tools:\n\n"
            f"{tools_description}\n\n"
            f"User's request: {query}\n\n"
            "Analyze the user's request and choose the most appropriate tool. "
            "If multiple operations are needed, start with the first logical step.\n\n"
            "IMPORTANT: Respond ONLY with a JSON object in this exact format:\n"
            "{\n"
            '    "tool": "tool_name",\n'
            '    "arguments": {\n'
            '        "parameter_name": "value"\n'
            "    }\n"
            "}\n\n"
            "Do not include any other text or explanation."
        )
    
    def process_tool_response(self, original_query: str, tool_response: str) -> str:
        """Process tool response and generate user-friendly response"""
        system_prompt = (
            "You are a helpful database assistant. Take the technical tool response and "
            "convert it into a clear, user-friendly answer that directly addresses the user's question. "
            "Be conversational and explain what was done or found. If there are errors, explain them clearly."
        )
        
        prompt = (
            f"User asked: {original_query}\n\n"
            f"Tool response: {tool_response}\n\n"
            "Please provide a clear, friendly response to the user based on this information."
        )
        
        return self.llm_chat(prompt, system_prompt)
    
    async def handle_database_operation(self, query: str) -> str:
        """Handle database operations using MCP tools"""
        try:
            async with sse_client(url=self.sse_url) as (in_stream, out_stream):
                async with ClientSession(in_stream, out_stream) as session:
                    # Initialize connection
                    info = await session.initialize()
                    logger.info(f"Connected to {info.serverInfo.name}")
                    
                    # Get available tools
                    tools = await session.list_tools()
                    
                    # Get tool selection from LLM
                    tool_prompt = self.get_tool_selection_prompt(query, tools)
                    tool_selection = self.llm_chat(tool_prompt)
                    
                    try:
                        tool_call = json.loads(tool_selection)
                        
                        # Execute the tool
                        result = await session.call_tool(
                            tool_call["tool"], 
                            arguments=tool_call["arguments"]
                        )
                        
                        tool_response = result.content[0].text
                        
                        # Process the response for the user
                        return self.process_tool_response(query, tool_response)
                        
                    except json.JSONDecodeError:
                        return "I had trouble understanding how to process your database request. Could you please rephrase it?"
                    except Exception as e:
                        return f"I encountered an error while processing your database request: {str(e)}"
                        
        except Exception as e:
            logger.error(f"Database operation error: {e}")
            return "I'm having trouble connecting to the database. Please check if the database server is running."
    
    async def chat(self, message: str) -> str:
        """Main chat method that routes to appropriate handler"""
        # Check if this is a database-related request
        if self.detect_database_intent(message):
            response = await self.handle_database_operation(message)
        else:
            # Handle as regular conversation
            response = self.llm_chat(message)
        
        # Store in conversation history
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response

async def main():
    """Main chat loop"""
    agent = DatabaseChatAgent()
    
    print("🤖 Database Chat Assistant")
    print("=" * 50)
    print("I can help you with database operations and general questions!")
    print("Try asking me to:")
    print("- List tables in the database")
    print("- Create or modify tables")
    print("- Insert, update, or query data")
    print("- Get database information")
    print("- Or just have a normal conversation!")
    print("\nType 'done' when you want to exit.")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
                
            # Check for exit conditions
            if user_input.lower() in ['done', 'exit', 'quit', 'bye']:
                print("\n🤖 Assistant: Goodbye! Have a great day! 👋")
                break
            
            # Get response from agent
            print("\n🤖 Assistant: ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n🤖 Assistant: Goodbye! Have a great day! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Let's try again...")

if __name__ == "__main__":
    asyncio.run(main())
