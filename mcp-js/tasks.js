import axios from "axios";

export const tools = [
    {
        name: "create_task",
        description: "Create a new task",
        inputSchema: {
            type: "object",
            properties: {
                title: { type: "string" },
                category: { type: "string" },
                priority: { type: "string", enum: ["HIGH", "MEDIUM", "LOW"] },
                status: { type: "string", enum: ["PENDING", "DONE", "NOT_FINISHED", "CANCELLED", "POSTPONED"] },
                repeat: { type: "string", enum: ["never", "daily", "weekly", "bimonthly", "monthly"] },
                strategy: { type: "string" },
                target_date: { type: "string", description: "ISO format date YYYY-MM-DD" },
                time_estimate_minutes: { type: "integer" },
                external_link: { type: "string" },
                metadata: { type: "object" }
            },
            required: ["title", "category"],
        },
    },
    {
        name: "list_tasks",
        description: "List tasks with optional filters",
        inputSchema: {
            type: "object",
            properties: {
                category: { type: "string" },
                status: { type: "string", enum: ["PENDING", "DONE", "NOT_FINISHED", "CANCELLED", "POSTPONED"] },
                target_date: { type: "string", description: "ISO format date YYYY-MM-DD" }
            },
        },
    },
    {
        name: "get_task",
        description: "Get details of a specific task",
        inputSchema: {
            type: "object",
            properties: {
                task_id: { type: "string", description: "UUID of the task" },
            },
            required: ["task_id"],
        },
    },
    {
        name: "update_task",
        description: "Update an existing task",
        inputSchema: {
            type: "object",
            properties: {
                task_id: { type: "string", description: "UUID of the task" },
                updates: {
                    type: "object",
                    properties: {
                        title: { type: "string" },
                        category: { type: "string" },
                        priority: { type: "string", enum: ["HIGH", "MEDIUM", "LOW"] },
                        status: { type: "string", enum: ["PENDING", "DONE", "NOT_FINISHED", "CANCELLED", "POSTPONED"] },
                        repeat: { type: "string", enum: ["never", "daily", "weekly", "bimonthly", "monthly"] },
                        strategy: { type: "string" },
                        target_date: { type: "string", description: "ISO format date YYYY-MM-DD" },
                        time_estimate_minutes: { type: "integer" },
                        external_link: { type: "string" },
                        metadata: { type: "object" }
                    }
                }
            },
            required: ["task_id", "updates"],
        },
    },
    {
        name: "delete_task",
        description: "Delete a task",
        inputSchema: {
            type: "object",
            properties: {
                task_id: { type: "string", description: "UUID of the task" },
            },
            required: ["task_id"],
        },
    }
];

export async function handleToolCall(name, args, API_BASE) {
    let res;
    switch (name) {
        case "create_task":
            res = await axios.post(`${API_BASE}/tasks/`, args);
            return res.data;
        case "list_tasks":
            res = await axios.get(`${API_BASE}/tasks/`, { params: args });
            return res.data;
        case "get_task":
            res = await axios.get(`${API_BASE}/tasks/${args.task_id}`);
            return res.data;
        case "update_task":
            res = await axios.patch(`${API_BASE}/tasks/${args.task_id}`, args.updates);
            return res.data;
        case "delete_task":
            res = await axios.delete(`${API_BASE}/tasks/${args.task_id}`);
            return { status: "deleted", task_id: args.task_id };
        default:
            return null;
    }
}
