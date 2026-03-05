import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";

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

const tools = [
    {
        name: "list_books",
        description: "Retrieve a list of available books",
        inputSchema: {
            type: "object",
            properties: {},
        },
    },
    {
        name: "get_book_content",
        description: "Get content of a specific book",
        inputSchema: {
            type: "object",
            properties: {
                file_id: { type: "string" },
            },
            required: ["file_id"],
        },
    },
    {
        name: "request_excerpt",
        description: "Request an excerpt for a book",
        inputSchema: {
            type: "object",
            properties: {
                file_id: { type: "string" },
                start: { type: "integer" },
                end: { type: "integer" }
            },
            required: ["file_id", "start", "end"],
        },
    },
    {
        name: "check_job_status",
        description: "Check the status of an export job",
        inputSchema: {
            type: "object",
            properties: {
                job_id: { type: "string" },
            },
            required: ["job_id"],
        },
    },
    {
        name: "check_job_download",
        description: "Check download details of an export job",
        inputSchema: {
            type: "object",
            properties: {
                job_id: { type: "string" },
            },
            required: ["job_id"],
        },
    }
];

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: tools,
    };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
        const { name, arguments: args } = request.params;

        let res;
        if (name === "list_books") {
            res = await axios.get(`${API_BASE}/books`);
        } else if (name === "get_book_content") {
            res = await axios.get(`${API_BASE}/books/${args.file_id}/content`);
        } else if (name === "request_excerpt") {
            res = await axios.post(`${API_BASE}/books/${args.file_id}/excerpt`, {
                start: args.start,
                end: args.end
            });
        } else if (name === "check_job_status") {
            res = await axios.get(`${API_BASE}/jobs/${args.job_id}/status`);
        } else if (name === "check_job_download") {
            res = await axios.get(`${API_BASE}/jobs/${args.job_id}/download`);
        } else {
            throw new Error(`Tool not found: ${name}`);
        }

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(res.data, null, 2),
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
