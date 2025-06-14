const express = require('express');
const Redis = require('ioredis');
const axios = require('axios');
const debug = require('debug')('mcp-server');

const app = express();
const redis = new Redis({
  host: '127.0.0.1',
  port: 6379,
  password: '', // No password as per docker-compose
});

// MCP Configuration
const MCP_VERSION = '1.0.0';
let supervisor = null;

app.use(express.json());

// Debug middleware
app.use((req, res, next) => {
  debug(`Incoming request: ${req.method} ${req.url}`);
  next();
});

// MCP Supervisor Registration
app.post('/supervisor', (req, res) => {
  const { url } = req.body;
  if (!url) {
    return res.status(400).json({ error: 'Supervisor URL required' });
  }
  supervisor = url;
  res.json({ registered: true, supervisor });
});

// MCP Manifest endpoint
app.get('/mcp/manifest', (req, res) => {
  res.json({
    mcp_version: MCP_VERSION,
    service: 'MCP Redis Quotes Server',
    endpoints: [
      { path: '/mcp/manifest', method: 'GET', description: 'MCP manifest' },
      { path: '/mcp/ping', method: 'GET', description: 'MCP ping/health' },
      { path: '/mcp/resources', method: 'GET', description: 'List MCP resources' },
      { path: '/supervisor', method: 'POST', description: 'Register MCP supervisor' },
      { path: '/resources', method: 'GET', description: 'List Redis keys' },
      { path: '/quote', method: 'POST', description: 'Add a quote' },
      { path: '/quotes', method: 'GET', description: 'List all quotes' },
      { path: '/mcp/events', method: 'GET', description: 'MCP SSE events stream' }
    ]
  });
});

// MCP Ping endpoint
app.get('/mcp/ping', (req, res) => {
  res.json({
    status: 'ok',
    mcp_version: MCP_VERSION,
    service: 'MCP Redis Quotes Server'
  });
});

// Expose Redis keys as resources
app.get('/resources', async (req, res) => {
  try {
    const keys = await redis.keys('*');
    res.json({ keys });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch keys', details: err.message });
  }
});

// MCP Resources endpoint
app.get('/mcp/resources', async (req, res) => {
  try {
    const keys = await redis.keys('*');
    res.json({
      resources: keys.map(k => ({
        key: k,
        type: k.startsWith('quotes:') ? 'quote' : 'unknown'
      }))
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch resources', details: err.message });
  }
});

// Tool 1: Add a quote by category
app.post('/quote', async (req, res) => {
  const { apiKey } = req.body;
  if (!apiKey) {
    return res.status(400).json({ error: 'apiKey is required' });
  }
  try {
    const response = await axios.get('https://api.api-ninjas.com/v1/quotes', {
      headers: { 'X-Api-Key': apiKey },
    });
    const quoteObj = response.data[0];
    if (!quoteObj) {
      return res.status(404).json({ error: 'No quote found for this category' });
    }
    const timestamp = Date.now();
    const key = `quotes:${timestamp}`;
    const enrichedQuote = {
      ...quoteObj,
      timestamp,
      version: MCP_VERSION
    };
    await redis.set(key, JSON.stringify(enrichedQuote));
    
    // Notify supervisor if registered
    if (supervisor) {
      try {
        await axios.post(supervisor, {
          type: 'QUOTE_ADDED',
          data: { key, quote: enrichedQuote }
        });
      } catch (error) {
        debug('Failed to notify supervisor:', error.message);
      }
    }
    
    res.json({ saved: true, key, quote: enrichedQuote });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch or save quote', details: err.message });
  }
});

// Tool 2: List all quotes
app.get('/quotes', async (req, res) => {
  try {
    const keys = await redis.keys('quotes:*');
    const values = await redis.mget(keys);
    const quotes = values.map((v, i) => ({
      key: keys[i],
      ...JSON.parse(v),
    }));
    res.json({ quotes });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch quotes', details: err.message });
  }
});

// Health check with MCP version
app.get('/', (req, res) => {
  res.json({
    status: 'running',
    service: 'MCP Redis Quotes Server',
    version: MCP_VERSION,
    supervisor: supervisor || 'not registered'
  });
});

// MCP SSE Events endpoint (only this uses text/event-stream)
app.get('/mcp/events', (req, res) => {
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive'
  });
  res.flushHeaders();

  // Send a comment as keep-alive every 15 seconds
  const keepAlive = setInterval(() => {
    res.write(': keep-alive\n\n');
  }, 15000);

  // Optionally, store res in a list to broadcast events (not shown here)

  req.on('close', () => {
    clearInterval(keepAlive);
    res.end();
  });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  debug(`MCP Redis Quotes Server listening on port ${PORT}`);
});
