import { BedrockRuntimeClient, ConverseCommand } from "@aws-sdk/client-bedrock-runtime";
import chalk from 'chalk';
import { randomUUID } from 'crypto';
import readline from 'readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import * as fs from 'fs';


import {
    chromium
} from 'playwright';

const modelId = "us.anthropic.claude-3-7-sonnet-20250219-v1:0";
const initialPrompt = "Navigate to AWS Machine Learning Blog,then click on the first blog post.";
const systemPrompt = "You are a web navigation assistant with vision capabilities. When you don't know something DO NOT stop or make assumptions, ASK the user for feedback so we can continue. When you see a screenshot, analyze it carefully to identify elements and their positions.";


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
    },
    {
        "toolSpec": {
            "name": "ask_user",
            "description": "Ask the user a question and get their response. Always use this tool when you need user feedback",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the user"
                        }
                    },
                    "required": ["question"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "type",
            "description": "Type text into the last clicked element, with option to submit",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to type into the last clicked element"
                        },
                        "submit": {
                            "type": "boolean",
                            "description": "Whether to press Enter after typing (to submit forms)"
                        }
                    },
                    "required": ["text"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "click",
            "description": "Click at specific coordinates on the page",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate for the click"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate for the click"
                        }
                    },
                    "required": ["x", "y"]
                }
            }
        }
    },
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

async function askUser(question) {
    printSystem(`QUESTION: ${question}`);
    const rl = readline.createInterface({ input, output });
    const userResponse = await rl.question('Your answer: ');
    rl.close();

    return {
        response: userResponse
    };
}

async function typeText(page, text, submit = false) {
    printSystem(`Typing text: ${text}`);
    try {
        await page.keyboard.type(text);

        if (submit) {
            printSystem(`Pressing Enter to submit`);
            await page.keyboard.press('Enter');
            return { typed: true, text, submitted: true };
        }
        return { typed: true, text, submitted: false };
    } catch (error) {
        printSystem(`Error typing text: ${error}`);
        return { typed: false, error: error.message };
    }
}


async function click(page, x, y) {
    printSystem(`Clicking at ${x}, ${y}`);
    await page.mouse.click(x, y);

    return {
        clicked_at: { x, y }
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
    // Set up Amazon Bedrock client
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
                system: [{
                    text: systemPrompt
                }],
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
                        toolContent.push({
                            toolResult: {
                                toolUseId: toolId,
                                content: [
                                    {
                                        json: result
                                    }
                                ]
                            }
                        });
                    } else if (tool.name === "screenshot") {
                        result = await takeScreenshot(page);
                        const filename = result.filename;
                        const imageBytes = fs.readFileSync(filename);

                        toolContent.push({
                            toolResult: {
                                toolUseId: toolId,
                                content: [
                                    {
                                        json: {
                                            filename: filename
                                        }
                                    },
                                    {
                                        image: {
                                            format: "png",
                                            source: {
                                                bytes: imageBytes
                                            }
                                        }
                                    }
                                ]
                            }
                        });
                    } else if (tool.name === "ask_user") {
                        const question = toolInput.question || 'What would you like to do next?';
                        result = await askUser(question);

                        toolContent.push({
                            "toolResult": {
                                "toolUseId": toolId,
                                "content": [{ "json": result }]
                            }
                        })
                    } else if (tool.name === "type") {
                        const text = toolInput.text;
                        const summit = toolInput.submit;
                        result = await typeText(page, text, summit);
                        toolContent.push({
                            toolResult: {
                                toolUseId: toolId,
                                content: [{
                                    json: result
                                }]
                            }
                        });
                    } else if (tool.name === "click") {
                        const x = toolInput.x || 0;
                        const y = toolInput.y || 0;
                        result = await click(page, x, y);
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
            }

            // Browser context content - safely get page info
            const pageInfo = await getPageInfo(page);
            const browserContent = {text: `Current page: Title: '${pageInfo['title']}', URL: '${pageInfo['url']}'`};
            printSystem(browserContent);

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

            // Continue conversation
            response = await bedrockClient.send(
                new ConverseCommand({
                    modelId,
                    system: [{
                        text: systemPrompt
                    }],
                    messages: messages,
                    toolConfig: {
                        tools: webTools
                    }
                })
            );

            printSystem(`Sending request ${nbRequest} to Bedrock with ${messages.length} messages...`);
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
printSystem("Amazon Bedrock Web Tools Minimal Example")
printSystem("----------------------------------------")
run();
