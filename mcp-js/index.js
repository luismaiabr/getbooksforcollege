import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as books from "./books.js";
import * as tasks from "./tasks.js";
import * as roadmap from "./roadmap.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DEBUG_LOG = "/tmp/mcp-debug.log";
function log(msg) {
    const timestamp = new Date().toISOString();
    const formattedMsg = `[${timestamp}] ${msg}\n`;
    console.error(msg);
    try {
        fs.appendFileSync(DEBUG_LOG, formattedMsg);
    } catch (e) {
        // ignore
    }
}

// Try to load .env from the parent directory
try {
    const envPath = path.resolve(__dirname, "..", ".env");
    if (fs.existsSync(envPath)) {
        const envContent = fs.readFileSync(envPath, "utf-8");
        envContent.split("\n").forEach(line => {
            const match = line.match(/^\s*([^#\s=]+)\s*=\s*(.*)$/);
            if (match) {
                const key = match[1].trim();
                let value = match[2].trim();
                // Remove quotes if present
                if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.substring(1, value.length - 1);
                }
                process.env[key] = value;
            }
        });
        log("Loaded environment from .env");
    } else {
        log(`.env not found at ${envPath}`);
    }
} catch (e) {
    log(`Warning: Could not load .env file: ${e.message}`);
}

// Create MCP Server instance
const server = new Server(
    {
        name: "book-gateway",
        version: "1.0.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// Proxy to FastAPI - prioritizes explicit FASTAPI_URL, then BASE_URL from .env
const API_BASE = process.env.FASTAPI_URL || process.env.BASE_URL || "http://localhost:8000";
log(`Using API_BASE: ${API_BASE}`);

const allTools = [
    ...books.tools,
    ...tasks.tools,
    ...roadmap.tools
];

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
    log("Handling ListToolsRequest");
    return {
        tools: allTools,
    };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    log(`Executing tool: ${name} with args: ${JSON.stringify(args)}`);

    try {
        let result = await books.handleToolCall(name, args, API_BASE);
        if (result === null) {
            result = await tasks.handleToolCall(name, args, API_BASE);
        }
        if (result === null) {
            result = await roadmap.handleToolCall(name, args, API_BASE);
        }

        if (result === null) {
            log(`Tool not found: ${name}`);
            throw new Error(`Tool not found: ${name}`);
        }

        log(`Tool ${name} executed successfully`);
        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result, null, 2),
                },
            ],
        };
    } catch (error) {
        const errorMessage = error.response ? 
            (typeof error.response.data === 'object' ? JSON.stringify(error.response.data) : String(error.response.data)) : 
            (error.message || String(error));
        
        log(`Error executing tool ${name}: ${errorMessage}`);
        
        return {
            content: [
                {
                    type: "text",
                    text: `Error executing tool: ${errorMessage}`,
                },
            ],
            isError: true,
        };
    }
});

// Start the server using stdio transport
async function startServer() {
    log("Connecting to Stdio transport...");
    const transport = new StdioServerTransport();
    await server.connect(transport);
    log("Book Gateway MCP Server running on stdio");
}

startServer().catch((error) => {
    log(`Fatal error running server: ${error.message}`);
    process.exit(1);
});


