import { BedrockRuntimeClient, ConverseCommand } from "@aws-sdk/client-bedrock-runtime";
import chalk from 'chalk';


// const color = {
//   red: "\033[31m",
//   green: "\033[32m",
//   blue: "\033[34m",
//   default: "\033[0m"
// }

const modelId = "us.amazon.nova-lite-v1:0";
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

async function run() {
  // Set up Amazon Bedrock client
  const bedrockClient = new BedrockRuntimeClient({ region: "us-west-2" });

  try {
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
          const result = {
            tool_executed: true
          };

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
  }
}

// Main entry point
printSystem("Amazon Bedrock Web Tools Minimal Example")
printSystem("----------------------------------------")
run();
