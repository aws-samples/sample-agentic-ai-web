import { BedrockRuntimeClient, ConverseCommand } from "@aws-sdk/client-bedrock-runtime";

import chalk from 'chalk';

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

// Define the initial prompt for the web automation task
const initialPrompt = "Search the price of AAA Amazon Basics batteries and write a summary of your findings in markdown format to a file named 'search-results.md'"

// Define the system prompt that instructs the model how to use the tools
const systemPrompt = `You are a web navigation assistant with vision capabilities.
When you don't know something DO NOT stop or make assumptions, ASK the user for feedback so we can continue.
When you see a screenshot, analyze it carefully to identify elements and their positions.
First click on elements like form fields, then use the type tool to enter text. You can submit forms by setting submit=true when typing.
You can scroll up or down to see more content on the page.
After completing your search, use the writeFile tool to save your findings in markdown format.
Think step by step and take screenshots between each step to ensure you are doing what you think you are doing.
`;

const modelId = "us.anthropic.claude-3-7-sonnet-20250219-v1:0";

function printUser(s) {
    console.log(chalk.blue(JSON.stringify(s, null, 2)));
}
function printAssistant(s) {
    console.log(chalk.red(JSON.stringify(s, null, 2)));
}
function printSystem(s) {
    console.log(chalk.green(JSON.stringify(s, null, 2)));
}

const artifactURIs = [];

function convertToBedrockTools(tools) {
    const bedrockTools = [];

    for (const tool of tools.tools) {
        const bedrockTool = {
            toolSpec: {
                name: tool.name,
                description: tool.description || `Use ths ${tool.name} tool`,
                inputSchema: {
                    json: tool.inputSchema || { type: "object", properties: {}, required: [] }
                }
            }
        };

        // if (bedrockTool.toolSpec.inputSchema.json.properties.ctx) {
        //     delete bedrockTool.toolSpec.inputSchema.json.properties.ctx;
        // }

        bedrockTools.push(bedrockTool);
    }

    return bedrockTools;
}

async function processToolRequest(toolName, toolId, toolInput) {
    printSystem(`Processing tool request: ${toolName} with ID ${toolId}`);

    try {
        const result = await client.callTool({
            name: toolName,
            arguments: toolInput
        });

        const bedrockContent = [];

        if (result.content && Array.isArray(result.content)) {
            for (const contentItem of result.content) {
                if (contentItem.type) {
                    if (contentItem.type === "image") {
                        const imageData = atob(contentItem.data);

                        bedrockContent.push({
                            json: { filename: "screenshot.jpeg" }
                        });

                        bedrockContent.push({
                            image: {
                                format: "jpeg",
                                source: {
                                    bytes: imageData
                                }
                            }
                        });
                    } else if (contentItem.type === "text" && contentItem.text) {
                        bedrockContent.push({
                            json: { text: contentItem.text }
                        });
                    } else if (contentItem.type === "resource" && contentItem.resource) {
                        const resource = contentItem.resource;
                        if (resource.uri) {
                            bedrockContent.push({
                                json: {
                                    resource: resource.uri.unicode
                                }
                            });
                            artifactURIs.push(resource.uri);
                            printSystem(`Tracked artifact URI: ${resource.uri}`);
                        }
                        if (resource.text) {
                            bedrockContent.push({
                                json: {
                                    resource: resource.text
                                }
                            });
                        }
                    }
                }
            }
        }

        return {
            toolResult: {
                toolUseId: toolId,
                content: bedrockContent
            }
        }
    } catch (error) {
        console.log(`Error executing tool ${toolName}: ${error.message}`);

        return {
            toolResult: {
                toolUseId: toolId,
                content: [{
                    json: { error: error.message }
                }]
            }
        }
    }
}
async function run() {
    const tools = await client.listTools();
    printSystem(`Available MCP tools: ${tools.tools.map(tool => tool.name)}`);

    const bedrockClient = new BedrockRuntimeClient({ region: "us-west-2" });

    const bedrockTools = convertToBedrockTools(tools);
    printSystem(`Converted ${bedrockTools.length} tools to Bedrock format`);

    const messages = [{
        role: "user",
        content: [{ text: initialPrompt }]
    }];

    printSystem("Starting conversation with model");
    printUser(`User: ${initialPrompt}`);

    let nbRequest = 1;

    printSystem(`Sending request ${nbRequest} to Bedrock with ${messages.length} messages...`);
    let response = await bedrockClient.send(
        new ConverseCommand({
            modelId,
            system: [{
                text: systemPrompt
            }],
            messages: messages,
            toolConfig: {
                tools: bedrockTools
            }
        })
    );

    let outputMessage = response.output.message;
    let stopReason = response.stopReason;

    printAssistant(outputMessage);
    messages.push(outputMessage);

    while (stopReason === "tool_use") {
        const toolContent = [];
        for (const content of outputMessage.content) {
            if (content.toolUse) {
                const tool = content.toolUse;
                const toolId = tool.toolUseId;
                const toolName = tool.name;

                const toolInput = tool.input || {};
                if (typeof toolInput === 'string') {
                    toolInput = JSON.parse(toolInput);
                }

                printAssistant(`Executing tool: ${toolName}`);
                printAssistant(toolInput);

                const resultContent = await processToolRequest(toolName, toolId, toolInput);
                toolContent.push(resultContent);
            }
        }

        const pageInfoResult = await processToolRequest("getPageInfo", "page_info", {})
        const pageInfoContent = pageInfoResult.toolResult.content[0];
        let pageInfoText = "";
        if (pageInfoContent.json) {
            pageInfoText = pageInfoContent.json.text;
        } else {
            pageInfoText = "Page info not available";
        }

        const browserContent = {
            text: `Current page: ${pageInfoText}`
        };
        printSystem(browserContent);

        toolContent.push(browserContent);

        const toolResultMessage = {
            role: "user",
            content: toolContent
        };
        messages.push(toolResultMessage);

        nbRequest++;

        printSystem(`Sending request ${nbRequest} to Bedrock with ${messages.length} messages...`);
        response = await bedrockClient.send(
            new ConverseCommand({
                modelId,
                system: [{
                    text: systemPrompt
                }],
                messages: messages,
                toolConfig: {
                    tools: bedrockTools
                }
            })
        );

        outputMessage = response.output.message;
        messages.push(outputMessage);
        stopReason = response.stopReason;

        printAssistant(outputMessage);
    }
}

const transport = new StdioClientTransport({
    command: "node",
    args: ["10-mcp-server.js"]
});

const client = new Client(
    {
        name: "example-client",
        version: "1.0.0"
    }
);

await client.connect(transport);

run();