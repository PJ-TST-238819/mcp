"""
Gemini service module for processing queries with Google's Gemini models.
"""

from typing import Any, List, Dict, Tuple

class GeminiService:
    def __init__(self, gemini_client, model: str, genai_types):
        self.gemini = gemini_client
        self.model = model
        self.genai_types = genai_types

    async def process_query(self, query: str, available_tools: List[Dict], previous_messages: List = None) -> Tuple[str, List]:
        """
        Process a query using Google's Gemini models.
        """
        gemini_tools = self._convert_tools_to_gemini_format(available_tools)
        tools = self.genai_types.Tool(function_declarations=gemini_tools)
        config = self.genai_types.GenerateContentConfig(tools=[tools])

        chat_history = self._prepare_gemini_chat_history(previous_messages)
        chat = self.gemini.chats.create(
            model=self.model,
            config=config,
            history=chat_history
        )

        final_text = []
        messages = previous_messages.copy() if previous_messages else []
        messages.append({"role": "user", "content": query})

        response = chat.send_message(query)
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text.append(part.text)
                    if hasattr(part, "function_call") and part.function_call:
                        function_call = part.function_call
                        tool_name = function_call.name
                        tool_args = self._parse_gemini_function_args(function_call)
                        final_text.append(f"[Tool call: {tool_name} with args {tool_args}]")
                        # Tool execution should be handled by the caller

        return "\n".join(final_text), messages

    def _convert_tools_to_gemini_format(self, available_tools: list) -> list:
        type_mapping = {
            "number": "NUMBER",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT",
        }
        gemini_tools = []
        for tool in available_tools:
            function_declaration = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": {"type": "OBJECT", "properties": {}, "required": []}
            }
            if "input_schema" in tool and tool["input_schema"]:
                schema = tool["input_schema"]
                if "properties" in schema:
                    for prop_name, prop_details in schema["properties"].items():
                        prop_type = prop_details.get("type", "STRING").upper()
                        prop_type = type_mapping.get(prop_type.lower(), "STRING")
                        property_schema = {"type": prop_type}
                        if "description" in prop_details:
                            property_schema["description"] = prop_details["description"]
                        function_declaration["parameters"]["properties"][prop_name] = property_schema
                if "required" in schema:
                    function_declaration["parameters"]["required"] = schema["required"]
            gemini_tools.append(function_declaration)
        return gemini_tools

    def _prepare_gemini_chat_history(self, previous_messages: list) -> list:
        chat_history = []
        if not previous_messages:
            return chat_history
        for message in previous_messages:
            if message["role"] == "user" and isinstance(message["content"], str):
                chat_history.append({
                    "role": "user",
                    "parts": [{"text": message["content"]}]
                })
            elif message["role"] == "assistant" and isinstance(message["content"], str):
                chat_history.append({
                    "role": "model",
                    "parts": [{"text": message["content"]}]
                })
        return chat_history

    def _parse_gemini_function_args(self, function_call):
        tool_args = {}
        try:
            if hasattr(function_call.args, "items"):
                for k, v in function_call.args.items():
                    tool_args[k] = v
            else:
                args_str = str(function_call.args)
                if args_str.strip():
                    import json
                    tool_args = json.loads(args_str)
        except Exception:
            pass
        return tool_args
