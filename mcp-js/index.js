import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as books from "./books.js";
import * as tasks from "./tasks.js";
import * as roadmap from "./roadmap.js";

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

// We proxy to FastAPI running on 8000
const API_BASE = process.env.FASTAPI_URL || "http://localhost:8000";

const allTools = [
    ...books.tools,
    ...tasks.tools,
    ...roadmap.tools
];

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: allTools,
    };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
        const { name, arguments: args } = request.params;

        let result = await books.handleToolCall(name, args, API_BASE);
        if (result === null) {
            result = await tasks.handleToolCall(name, args, API_BASE);
        }
        if (result === null) {
            result = await roadmap.handleToolCall(name, args, API_BASE);
        }

        if (result === null) {
            throw new Error(`Tool not found: ${name}`);
        }

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result, null, 2),
                },
            ],
        };
    } catch (error) {
        return {
            content: [
                {
                    type: "text",
                    text: `Error executing tool: ${error.response ? JSON.stringify(error.response.data) : error.message}`,
                },
            ],
            isError: true,
        };
    }
});

// Start the server using stdio transport
async function startServer() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Book Gateway MCP Server running on stdio");
}

startServer().catch((error) => {
    console.error("Fatal error running server:", error);
    process.exit(1);
});
