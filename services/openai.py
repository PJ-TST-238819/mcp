"""
OpenAI service module for processing queries with GPT models.
"""

from typing import Any, List, Dict, Tuple
import json

class OpenAIService:
    def __init__(self, openai_client, model: str):
        self.openai = openai_client
        self.model = model

    async def process_query(self, query: str, available_tools: List[Dict], previous_messages: List = None) -> Tuple[str, List]:
        """
        Process a query using OpenAI's GPT models.
        """
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            } for tool in available_tools
        ]

        messages = []
        if previous_messages:
            messages.extend(previous_messages)

        messages.append({
            "role": "user",
            "content": query
        })

        response = await self.openai.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        final_text = []

        if response_message.tool_calls:
            final_text.append(response_message.content or "")
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": response_message.tool_calls
            })
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                final_text.append(f"[Tool call: {function_name} with args {function_args}]")
                # Tool execution should be handled by the caller

        else:
            final_text.append(response_message.content)

        return "\n".join(final_text), messages
