Build an MCP server that:
* Connects to my locally hosted Redis container that can be found in the docker-compose file.
* Exposes the keys from Redis as resources.
* Provides a tools that:
  1. lets the user ask enter a category, after which the MCP server finds a quote from the web that matches that category from https://www.api-ninjas.com/api/quotes. The quote that is retrieved is then saved in the Redis database.
  2. returns a list of quotes from the Redis instance.
* Expose the MCP server through a REST API endpoint hosted on an express server.