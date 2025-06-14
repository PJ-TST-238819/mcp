import 'dotenv/config';
import inquirer from 'inquirer';
import OpenAI from 'openai';
import { GoogleGenerativeAI, Content } from '@google/generative-ai';
import Anthropic from '@anthropic-ai/sdk';
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

// --- Type Definitions ---

/**
 * Defines the structure for a single message in the chat history.
 * The role can be 'user' for user messages or 'assistant' for model responses.
 */
interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

type Provider = 'ChatGPT' | 'Gemini' | 'Anthropic';

// --- Initialize API Clients ---

// Initialize OpenAI client using the API key from environment variables
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Initialize Google Gemini client using the API key from environment variables
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY as string);
const geminiModel = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' });

// Initialize Anthropic client using the API key from environment variables
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// --- Global Variables ---

let currentProvider: Provider = 'ChatGPT'; // Default provider
let chatHistory: ChatHistoryItem[] = [];
const tools = new Map<string, string>(); // To store named tool URLs

// --- Provider Functions ---

/**
 * Gets a response from OpenAI's ChatGPT.
 * @param message - The user's input message.
 * @returns A promise that resolves to the model's response string.
 */
async function getChatGPTResponse(message: string): Promise<string> {
  try {
    const completion = await openai.chat.completions.create({
      messages: [...chatHistory, { role: 'user', content: message }],
      model: 'gpt-3.5-turbo',
    });
    return completion.choices[0]?.message?.content ?? 'No response from ChatGPT.';
  } catch (error) {
    console.error('Error getting response from ChatGPT:', (error as Error).message);
    return 'An error occurred while contacting ChatGPT.';
  }
}

/**
 * Gets a response from Google's Gemini.
 * It maps the generic chat history to the format required by the Gemini API.
 * @param message - The user's input message.
 * @returns A promise that resolves to the model's response string.
 */
async function getGeminiResponse(message: string): Promise<string> {
  try {
    const geminiHistory: Content[] = chatHistory.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.content }],
    }));

    const chat = geminiModel.startChat({
      history: geminiHistory,
    });

    const result = await chat.sendMessage(message);
    const response = await result.response;
    return response.text();
  } catch (error) {
    console.error('Error getting response from Gemini:', (error as Error).message);
    return 'An error occurred while contacting Gemini.';
  }
}

/**
 * Gets a response from Anthropic's Claude.
 * @param message - The user's input message.
 * @returns A promise that resolves to the model's response string.
 */
async function getAnthropicResponse(message: string): Promise<string> {
  try {
    // Anthropic's API expects the history in a specific format.
    const messages = [
        ...chatHistory.map(item => ({
          role: item.role as 'user' | 'assistant',
          content: item.content
        })),
        { role: 'user' as const, content: message }
    ];

    const response = await anthropic.messages.create({
      model: 'claude-3-opus-20240229',
      max_tokens: 1024,
      messages: messages,
    });
    
    // Handle the response content properly
    const firstContent = response.content[0];
    if (firstContent && firstContent.type === 'text') {
      return firstContent.text;
    }
    return 'No response from Anthropic.';
  } catch (error) {
    console.error('Error getting response from Anthropic:', (error as Error).message);
    return 'An error occurred while contacting Anthropic.';
  }
}

/**
 * Invokes a tool on a remote MCP server using the @mcp/client SDK.
 * @param baseUrl The base URL of the MCP server.
 * @param message The user's prompt for the tool.
 * @param toolName The name of the tool to call.
 */
async function invokeMcpTool(baseUrl: string, message: string, toolName: string): Promise<void> {
    process.stdout.write(`\n@${toolName} (MCP): `);
    let fullResponse = '';

    try {
        const client = new Client({
          name: toolName,
          version: '1.0.0',
        });

        await client.connect(new SSEClientTransport(new URL(baseUrl)));

        // await client.connect(baseUrl, async (session) => {
        //     // The `session` object is now active and connected to the MCP server.
        //     console.log(`\nConnected to MCP server at ${baseUrl}. Calling tool @${toolName}...`);

        //     // Call the specified tool with the user's prompt as an argument.
        //     const result = await session.callTool(toolName, { prompt: message });

        //     // Process the response from the tool.
        //     if (result.content && result.content[0]?.type === 'text') {
        //         fullResponse = result.content[0].text;
        //         process.stdout.write(fullResponse);
        //     } else {
        //         fullResponse = 'Tool did not return a text response.';
        //         process.stdout.write(fullResponse);
        //     }
        // });

        process.stdout.write('\n\n');

        // Update chat history with the tool interaction
        chatHistory.push({ role: 'user', content: `@${toolName} ${message}` });
        chatHistory.push({ role: 'assistant', content: fullResponse });

    } catch (error) {
        console.error(`\n\nAn error occurred while invoking tool @${toolName}:`, (error as Error).message);
        process.stdout.write('\n');
    }
}

// --- Main Application ---

/**
 * The main chat loop that handles user input and displays responses.
 */
async function chat(): Promise<void> {
  while (true) {
    const { message }: { message: string } = await inquirer.prompt([
      {
        type: 'input',
        name: 'message',
        message: `You (${currentProvider}):`,
      },
    ]);

    const lowerCaseMessage = message.toLowerCase();

    if (lowerCaseMessage === '/switch') {
      await switchProvider();
      continue;
    }

    if (lowerCaseMessage === '/exit') {
      console.log('Goodbye!');
      break;
    }

    if (lowerCaseMessage.startsWith('/addtool')) {
        await addTool();
        continue;
    }

    if (message.startsWith('@')) {
        const [toolInvocation, ...promptParts] = message.split(' ');
        const toolName = toolInvocation.substring(1);
        const prompt = promptParts.join(' ');
        const toolUrl = tools.get(toolName);

        if (toolUrl) {
            await invokeMcpTool(toolUrl, prompt, toolName);
        } else {
            console.log(`\nError: Tool "@${toolName}" not found. Use /addtool to register it.\n`);
        }
        continue;
    }
    
    let response: string;
    switch (currentProvider) {
        case 'ChatGPT':
        response = await getChatGPTResponse(message);
        break;
        case 'Gemini':
        response = await getGeminiResponse(message);
        break;
        case 'Anthropic':
        response = await getAnthropicResponse(message);
        break;
    }
    console.log(`\n${currentProvider}: ${response}\n`);
    chatHistory.push({ role: 'user', content: message });
    chatHistory.push({ role: 'assistant', content: response });
  }
}

/**
 * Prompts the user to register a new tool by name and URL.
 */
async function addTool(): Promise<void> {
    console.log('\n--- Add a New Tool ---');
    const { name } = await inquirer.prompt([
        { type: 'input', name: 'name', message: 'Tool Name (e.g., "mytool"): ' }
    ]);
    const { url } = await inquirer.prompt([
        { type: 'input', name: 'url', message: `Base URL for @${name} (e.g., http://localhost:8100): ` }
    ]);

    if(name && url) {
        tools.set(name, url);
        console.log(`\nTool "@${name}" added successfully. You can now use it by starting a prompt with "@${name}".\n`);
    } else {
        console.log('\nTool name and URL cannot be empty. Tool not added.\n');
    }
}


/**
 * Prompts the user to switch the AI provider and resets the chat history.
 */
async function switchProvider(): Promise<void> {
  const { provider }: { provider: Provider } = await inquirer.prompt([
    {
      type: 'list',
      name: 'provider',
      message: 'Switch to which provider?',
      choices: ['ChatGPT', 'Gemini', 'Anthropic'],
    },
  ]);
  
  currentProvider = provider;

  console.log(`Switched to ${currentProvider}.`);
  chatHistory = []; // Reset chat history when switching providers
}

/**
 * Starts the application by displaying a welcome message and initializing the chat.
 */
async function start(): Promise<void> {
  console.log('Welcome to the Multi-Provider Chat Client!');
  console.log('Commands:');
  console.log('  /switch   - Change AI provider (ChatGPT, Gemini, Anthropic)');
  console.log('  /addtool  - Register a new SSE tool endpoint');
  console.log('  /exit     - Quit the application');
  console.log('To use a tool, start your prompt with @toolname <your prompt>\n');
  await chat();
}

start();