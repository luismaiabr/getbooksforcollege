import axios from "axios";

export const tools = [
    {
        name: "get_teaching_roadmaps",
        description: "Retrieve study tracking info for lessons in the Teaching Roadmap",
        inputSchema: {
            type: "object",
            properties: {
                course_name: { type: "string", description: "Optional. Filter by a specific course name" }
            },
            required: [],
        },
    },
    {
        name: "mark_lesson_studied",
        description: "Mark a specific lesson as studied or not studied in the teaching roadmap",
        inputSchema: {
            type: "object",
            properties: {
                lesson_id: { type: "string", description: "The UUID of the lesson" },
                has_been_studied: { type: "boolean", description: "Set to true if studied, false otherwise" }
            },
            required: ["lesson_id", "has_been_studied"],
        },
    }
];

export async function handleToolCall(name, args, API_BASE) {
    let res;
    switch (name) {
        case "get_teaching_roadmaps":
            let url = `${API_BASE}/roadmap`;
            if (args.course_name) {
                url += `?course_name=${encodeURIComponent(args.course_name)}`;
            }
            res = await axios.get(url);
            return res.data;
        case "mark_lesson_studied":
            res = await axios.post(`${API_BASE}/roadmap/${args.lesson_id}/studied`, {
                has_been_studied: args.has_been_studied
            });
            return res.data;
        default:
            return null;
    }
}
