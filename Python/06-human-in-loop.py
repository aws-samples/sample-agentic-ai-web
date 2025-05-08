import json
import boto3
import asyncio
import uuid
import os
from playwright.async_api import async_playwright

MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
INITIAL_PROMPT = "Navigate to a homepage and take a screenshot."
SYSTEM_PROMPT ="You are a web navigation assistant. When you dont know something DO NOT stop or make assumption, ASK the user for feedback so we can continue"
SESSION_ID = str(uuid.uuid4())

# Create screenshot directory if it doesn't exist
os.makedirs(f"screenshot/{SESSION_ID}", exist_ok=True)

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
    }
]

async def navigate(page, url):
    print_system(f"Navigating to: {url}")
    await page.goto(url, wait_until='networkidle')
    # Wait a bit more to ensure page is stable
    await asyncio.sleep(1)
    return {"title": await page.title()}

async def take_screenshot(page):
    filename = f"screenshot/{SESSION_ID}/screenshot_{uuid.uuid4()}.png"
    print_system(f"Taking screenshot: {filename}")
    await page.screenshot(path=filename)
    
    # Return the filename for later use
    return {
        "filename": filename
    }

async def ask_user(question):
    print_system("\n" + "-" * 50)
    print_system(f"QUESTION: {question}")
    print_system("-" * 50)
    user_response = input(BLUE + "Your answer: " + RESET)
    print_system("-" * 50 + "\n")
    return {"response": user_response}

async def get_page_info(page):
    try:
        title = await page.title()
        url = page.url
        return {"title": title, "url": url}
    except Exception as e:
        print_system(f"Error getting page info: {str(e)}")
        return {"title": "Unknown", "url": "Unknown"}
async def run_example():
    # Initialize browser - minimal setup
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    
    try:
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
            system=[{"text": SYSTEM_PROMPT}],
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
                    tool_name = tool['name']
                    tool_id = tool.get('toolUseId')
                    
                    # Simplified input handling - always use dictionary format
                    tool_input = tool.get('input', {})
                    if isinstance(tool_input, str):
                        tool_input = json.loads(tool_input)
                    
                    # Execute requested tool
                    result = {}
                    if tool_name == 'navigate':
                        url = tool_input.get('url', 'https://aws.amazon.com')
                        result = await navigate(page, url)
                        
                    elif tool_name == 'screenshot':
                        result = await take_screenshot(page)
                    
                    elif tool_name == 'ask_user':
                        question = tool_input.get('question', 'What would you like to do next?')
                        result = await ask_user(question)
                    
                    # concatenate tool content that will be sent back to the model
                    tool_content.append({
                        "toolResult": {
                            "toolUseId": tool_id,
                            "content": [{"json": result}]
                        }
                    })

            # Browser context content - safely get page info
            page_info = await get_page_info(page)
            browser_content = {"text": f"Current page: Title: '{page_info['title']}', URL: '{page_info['url']}'"}
            print_system(f"Browser context: {json.dumps(browser_content, indent=2)}")
            
            # Add browser context to message
            tool_content.append(browser_content)

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
                system=[{"text": SYSTEM_PROMPT}],
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
    
    finally:
        # Clean up
        await browser.close()
        await playwright.stop()

# Main entry point
if __name__ == "__main__":
    print_system("Amazon Bedrock Web Tools Minimal Example")
    print_system("----------------------------------------")
    asyncio.run(run_example())
