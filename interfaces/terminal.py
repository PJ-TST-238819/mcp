"""
Terminal interface for interactive chat loop.
"""

import logging

logger = logging.getLogger(__name__)

async def chat_loop(client, process_query_fn):
    """
    Run an interactive chat loop with the server using the provided process_query function.
    """
    previous_messages = []
    print("Type your queries or 'quit' to exit.")
    print("Type 'refresh' to clear conversation history.")
    print(f"Using {client.llm_provider.upper()} as the LLM provider.")

    while True:
        try:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break

            if query.lower() == "refresh":
                previous_messages = []
                print("Conversation history cleared.")
                continue

            response, previous_messages = await process_query_fn(query, previous_messages=previous_messages)
            print("\nResponse:", response)
        except Exception as e:
            logger.exception("Error in chat loop")
            print("Error:", str(e))
