import axios from "axios";

export const tools = [
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
    },
    {
        name: "list_folder_books",
        description: "Retrieve a list of available books in a specific nested folder path",
        inputSchema: {
            type: "object",
            properties: {
                folder_name: { type: "string", description: "Slash-delimited folder path relative to the configured Google Drive root" }
            },
            required: ["folder_name"],
        },
    },
    {
        name: "get_book_excerpts",
        description: "Get all excerpts (with summaries) for a specific book",
        inputSchema: {
            type: "object",
            properties: {
                book_id: { type: "string", description: "The Google Drive file ID of the book" }
            },
            required: ["book_id"],
        },
    }
];

export async function handleToolCall(name, args, API_BASE) {
    let res;
    switch (name) {
        case "list_folder_books":
            res = await axios.get(`${API_BASE}/books/folder/${args.folder_name}`);
            return res.data;
        case "list_books":
            res = await axios.get(`${API_BASE}/books`);
            return res.data;
        case "get_book_content":
            res = await axios.get(`${API_BASE}/books/${args.file_id}/content`);
            return res.data;
        case "request_excerpt":
            res = await axios.post(`${API_BASE}/books/${args.file_id}/excerpt`, {
                start: args.start,
                end: args.end
            });
            return res.data;
        case "check_job_status":
            res = await axios.get(`${API_BASE}/jobs/${args.job_id}/status`);
            return res.data;
        case "check_job_download":
            res = await axios.get(`${API_BASE}/jobs/${args.job_id}/download`);
            return res.data;
        case "get_book_excerpts":
            res = await axios.get(`${API_BASE}/excerpts/${args.book_id}`);
            return res.data;
        default:
            return null;
    }
}
