import { BedrockRuntimeClient, ConverseCommand } from "@aws-sdk/client-bedrock-runtime";
import chalk from 'chalk';
import { randomUUID } from 'crypto';

import {
    chromium
} from 'playwright';

const modelId = "us.anthropic.claude-3-5-haiku-20241022-v1:0";
const initialPrompt = "Navigate to AWS homepage and take a screenshot. Do the same for Anthropic homepage";

function printUser(s) {
    console.log(chalk.blue(JSON.stringify(s, null, 2)));
}
function printAssistant(s) {
    console.log(chalk.red(JSON.stringify(s, null, 2)));
}
function printSystem(s) {
    console.log(chalk.green(JSON.stringify(s, null, 2)));
}

// Define web interaction tools - simplified to essential properties
const webTools = [
    {
        "toolSpec": {
            "name": "navigate",
            "description": "Navigate to a specified URL",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "url": { "type": "string" }
                    },
                    "required": ["url"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "screenshot",
            "description": "Take a screenshot of the current page",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    }
];

async function navigate(page, url) {
    printSystem(`Navigating to ${url}`);
    await page.goto(url, { timeout: 80000, waitUntil: 'networkidle' });

    const title = await page.title();

    return {
        title: title
    };
}

async function takeScreenshot(page) {
    const filename = `screenshots/screenshot_${randomUUID()}.png`;
    printSystem(`Taking screenshot ${filename}`);
    await page.screenshot({ path: filename });

    // Return the filename for later use
    return {
        filename
    };
}

async function getPageInfo(page) {
    try {
        const title = await page.title();
        const url = page.url();
        return { title, url };
    } catch (error) {
        printSystem(`Error getting page info: ${error.message}`);
        return { title: "Unknown", url: "Unknown" };
    }
}

async function run() {
    // Initialize browser - minimal setup
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    try {
        // Set up AWS Bedrock client
        const bedrockClient = new BedrockRuntimeClient({ region: "us-west-2" });
        const messages = [
            {
                role: "user",
                content: [
                    {
                        text: initialPrompt
                    }
                ]
            }
        ];

        let nbRequest = 1;
        // Send to model
        printSystem(`Sending request ${nbRequest} to Bedrock with ${messages.length} messages...`)
        printUser(`User prompt: ${messages[0]['content'][0]['text']}`)

        let response = await bedrockClient.send(
            new ConverseCommand({
                modelId,
                messages: messages,
                toolConfig: {
                    tools: webTools
                }
            })
        );

        // Process response
        let outputMessage = response.output.message;
        let stopReason = response.stopReason;

        printAssistant(outputMessage);
        messages.push(outputMessage);

        // Process tool requests - simplified loop
        while (stopReason === "tool_use") {
            const toolContent = [];
            for (const content of outputMessage.content) {
                if (content.toolUse) {
                    const tool = content.toolUse;
                    const toolId = tool.toolUseId;

                    const toolInput = tool.input || {};
                    if (typeof toolInput === 'string') {
                        toolInput = JSON.parse(toolInput);
                    }

                    // Execute requested tool
                    let result = {};
                    if (tool.name === "navigate") {
                        const url = toolInput.url;
                        result = await navigate(page, url);

                    } else if (tool.name === "screenshot") {
                        result = await takeScreenshot(page);
                    }

                    // Concatenate tool content that will be sent back to the model
                    toolContent.push({
                        toolResult: {
                            toolUseId: toolId,
                            content: [{
                                json: result
                            }]
                        }
                    });
                }
            }

            // Browser context content - safely get page info
            const pageInfo = await getPageInfo(page);
            const browserContent = { text: `Current page: Title: '${pageInfo['title']}', URL: '${pageInfo['url']}'` };
            printSystem(`Browser context: ${browserContent}`);

            // Add browser context to message
            toolContent.push(browserContent);

            // Send result back to model
            const toolResultMessage = {
                role: "user",
                content: [
                    ...toolContent
                ]
            };

            messages.push(toolResultMessage);

            nbRequest++;

            printSystem(`Sending request ${nbRequest} to Bedrock with ${messages.length} messages...`);
            printUser(messages.at(-1));

            // Continue conversation
            response = await bedrockClient.send(
                new ConverseCommand({
                    modelId,
                    messages: messages,
                    toolConfig: {
                        tools: webTools
                    }
                })
            );

            outputMessage = response.output.message;
            messages.push(outputMessage);

            printAssistant(outputMessage);
            stopReason = response.stopReason;
        }

    } catch (error) {
        console.error("Error invoking Bedrock model:", error);
    } finally {
        await browser.close();
    }
}

// Main entry point
printSystem("AWS Bedrock Web Tools Minimal Example")
printSystem("------------------------------------")
run();
