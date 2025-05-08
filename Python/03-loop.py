import json
import boto3
import asyncio

MODEL_ID = "us.amazon.nova-lite-v1:0"
INITIAL_PROMPT = "Navigate to AWS homepage and take a screenshot. Do the same for Anthropic homepage"

RED = '\033[31m'
GREEN = '\033[32m'
BLUE = '\033[34m'

RESET = '\033[0m'

def print_user(s: str):
    print(BLUE + s + RESET)

def print_assistant(s: str):
    print(RED + s + RESET)

def print_system(s: str):
    print(GREEN + s + RESET)

def filter_empty_text_content(message):
    if not message or 'content' not in message:
        return message
    
    filtered_content = []
    for content_item in message.get('content', []):
        # Keep items that don't have 'text' key or have non-empty text
        if 'text' not in content_item or content_item['text'].strip():
            filtered_content.append(content_item)
    
    # Create a new message with filtered content
    filtered_message = message.copy()
    filtered_message['content'] = filtered_content
    return filtered_message

# Define web interaction tools - simplified to essential properties
web_tools = [
    {
        "toolSpec": {
            "name": "navigate",
            "description": "Navigate to a specified URL",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
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
]

async def run_example():
    # Set up Amazon Bedrock client
    bedrock_client = boto3.client('bedrock-runtime')
    
    messages = [{
        "role": "user",
        "content": [{"text": INITIAL_PROMPT}]
    }]
    nb_request = 1
    # Send to model
    print_system(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")
    print_user(f"User prompt: {messages[0]['content'][0]['text']}")
    response = bedrock_client.converse(
        modelId=MODEL_ID,
        messages=messages,
        toolConfig={"tools": web_tools}
    )
    
    # Process response
    output_message = response.get('output', {}).get('message', {})
    output_message = filter_empty_text_content(output_message)
    messages.append(output_message)
    stop_reason = response.get('stopReason')

    print_assistant(f"Model response {json.dumps(output_message, indent=2)}")
    
    # Process tool requests - simplified loop
    while stop_reason == 'tool_use':
        tool_content = []
        for content in output_message.get('content', []):
            if 'toolUse' in content:
                tool = content['toolUse']
                tool_id = tool.get('toolUseId')
                
                # Simplified input handling - always use dictionary format
                tool_input = tool.get('input', {})
                if isinstance(tool_input, str):
                    tool_input = json.loads(tool_input)
                
                # Execute requested tool
                result = {"tool_executed" : True}
                
                # concatenate tool content that will be sent back to the model
                tool_content.append({
                    "toolResult": {
                        "toolUseId": tool_id,
                        "content": [{"json": result}]
                    }
                })

        # Send result back to model
        tool_result_message = {
            "role": "user",
            "content": [
                *tool_content
            ]
        }
        messages.append(tool_result_message)
        
        nb_request += 1
        # Continue conversation
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            messages=messages,
            toolConfig={"tools": web_tools}
        )
        print_system(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")

        output_message = response.get('output', {}).get('message', {})
        output_message = filter_empty_text_content(output_message)
        messages.append(output_message)
        stop_reason = response.get('stopReason')
        
        print_assistant(f"Model response {json.dumps(output_message, indent=2)}")

                        
    print_system("Task completed")

# Main entry point
if __name__ == "__main__":
    print_system("Amazon Bedrock Web Tools Minimal Example")
    print_system("----------------------------------------")
    asyncio.run(run_example())
