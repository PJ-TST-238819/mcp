"""
Anthropic service module for processing queries with Claude models.
"""

from typing import Any, List, Dict, Tuple

class AnthropicService:
    def __init__(self, anthropic_client, model: str):
        self.anthropic = anthropic_client
        self.model = model

    async def process_query(self, query: str, available_tools: List[Dict], previous_messages: List = None) -> Tuple[str, List]:
        """
        Process a query using Anthropic's Claude models.
        """
        messages = []
        if previous_messages:
            messages.extend(previous_messages)

        messages.append({
            "role": "user",
            "content": query
        })

        # Call Anthropic API (assume synchronous for now, adapt as needed)
        response = self.anthropic.messages.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            max_tokens=1000
        )

        final_text = []
        assistant_message_content = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
                # Tool execution should be handled by the caller
                final_text.append(f"[Tool call: {tool_name} with args {tool_args}]")
                assistant_message_content.append(content)

        return "\n".join(final_text), messages
