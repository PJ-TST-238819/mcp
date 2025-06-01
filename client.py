import asyncio
import sys
import logging
import json
import re
from typing import Optional, Literal

from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from anthropic import Anthropic
from openai import AsyncOpenAI
from google import genai
from google.genai import types as genai_types

from dotenv import load_dotenv

from services.anthropic import AnthropicService
from services.openai import OpenAIService
from services.gemini import GeminiService
from interfaces.terminal import chat_loop

load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/mcp_client.log"),
        logging.StreamHandler()
    ]
)

class MCPClient:
    def __init__(self, llm_provider: Literal["anthropic", "openai", "gemini"] = "anthropic"):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm_provider = llm_provider
        self.llm_service = None

        # Initialize the selected LLM client and service
        if llm_provider == "anthropic":
            self.llm_client = Anthropic()
            self.llm_service = AnthropicService(self.llm_client, model="claude-3-5-sonnet-20241022")
        elif llm_provider == "openai":
            self.llm_client = AsyncOpenAI()
            self.llm_service = OpenAIService(self.llm_client, model="gpt-4o")
        elif llm_provider == "gemini":
            self.llm_client = genai.Client()
            self.llm_service = GeminiService(self.llm_client, model="gemini-2.0-flash", genai_types=genai_types)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Use 'anthropic', 'openai', or 'gemini'.")

        logger.info(f"Initialized MCPClient with {llm_provider} as the LLM provider")

    async def connect_to_sse_server(self, server_url: str):
        logger.debug(f"Connecting to SSE MCP server at {server_url}")
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()
        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"\n\nConnected to SSE MCP Server at {server_url}. \nAvailable tools: {[tool.name for tool in tools]}")

    async def connect_to_stdio_server(self, server_script_path: str):
        is_python = False
        is_javascript = False
        command = None
        args = [server_script_path]
        if server_script_path.startswith("@") or "/" not in server_script_path:
            is_javascript = True
            command = "npx"
        else:
            is_python = server_script_path.endswith(".py")
            is_javascript = server_script_path.endswith(".js")
            if not (is_python or is_javascript):
                raise ValueError("Server script must be a .py, .js file or npm package.")
            command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )
        logger.debug(f"\n\nConnecting to stdio MCP server with command: {command} and args: {args}")
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.writer = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.writer))
        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"\n\nConnected to stdio MCP Server. Available tools: {[tool.name for tool in tools]}")

    async def connect_to_server(self, server_path_or_url: str):
        url_pattern = re.compile(r'^https?://')
        if url_pattern.match(server_path_or_url):
            await self.connect_to_sse_server(server_path_or_url)
        else:
            await self.connect_to_stdio_server(server_path_or_url)

    async def process_query(self, query: str, previous_messages: list = None):
        if not self.session:
            raise RuntimeError("Client session is not initialized.")

        # Get available tools
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": dict(tool.inputSchema) if tool.inputSchema else {}
        } for tool in response.tools]

        # Call the LLM service's process_query
        response_text, messages = await self.llm_service.process_query(query, available_tools, previous_messages)

        # Check for tool calls in the response and handle them
        # For simplicity, we look for "[Tool call: ...]" markers in the response_text
        # In a production system, this should be handled more robustly (e.g., via structured return values)
        tool_call_pattern = re.compile(r"\[Tool call: ([\w\-]+) with args (.+?)\]")
        matches = tool_call_pattern.findall(response_text)
        for tool_name, tool_args_str in matches:
            try:
                tool_args = json.loads(tool_args_str.replace("'", '"'))
            except Exception:
                tool_args = {}
            logger.info(f"Calling tool {tool_name} with args {tool_args}...")
            result = await self.session.call_tool(tool_name, tool_args)
            response_text += f"\n[tool results: {result}]"

        return response_text, messages

    async def cleanup(self):
        await self.exit_stack.aclose()
        if hasattr(self, '_session_context') and self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if hasattr(self, '_streams_context') and self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_script_path_or_url> [llm_provider]")
        print("Examples:")
        print("  - stdio server (npm): python client.py @playwright/mcp@latest")
        print("  - stdio server (python): python client.py ./weather.py")
        print("  - SSE server: python client.py http://localhost:3000/mcp")
        print("  - Specify LLM provider: python client.py ./weather.py openai")
        print("  - Use Gemini: python client.py ./weather.py gemini")
        sys.exit(1)

    llm_provider = "anthropic"
    if len(sys.argv) > 2 and sys.argv[2].lower() in ["anthropic", "openai", "gemini"]:
        llm_provider = sys.argv[2].lower()

    client = MCPClient(llm_provider=llm_provider)
    try:
        await client.connect_to_server(sys.argv[1])
        await chat_loop(client, client.process_query)
    finally:
        await client.cleanup()
        print("\nMCP Client Closed!")

if __name__ == "__main__":
    asyncio.run(main())
