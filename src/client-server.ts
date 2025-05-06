import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

let client: Client|undefined = undefined
const baseUrl = new URL('http://localhost:3000/mcp');
try {
  client = new Client({
    name: 'streamable-http-client',
    version: '1.0.0'
  });
  const transport = new StreamableHTTPClientTransport(
    baseUrl
  );
  await client.connect(transport);
  console.log("Connected using Streamable HTTP transport");
} catch (error) {
  console.error("Error connecting to the server:", error);
  process.exit(1);
}

// List prompts
const prompts = await client.listPrompts();

console.log("Available prompts:", prompts);

// Get a prompt
const prompt = await client.getPrompt({
  name: "give-secret",
  arguments: {
    code: "123-456"
  }
});

console.log("Prompt response:", JSON.stringify(prompt, null, 2)); 

// List resources
// const resources = await client.listResources();

// Read a resource
// const resource = await client.readResource({
//   uri: "file:///example.txt"
// });

// Call a tool
// const result = await client.callTool({
//   name: "example-tool",
//   arguments: {
//     arg1: "value"
//   }
// });