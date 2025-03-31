import json
import boto3
import asyncio
import uuid
import os
from playwright.async_api import async_playwright

MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
INITIAL_PROMPT = "Search the price of AAA Amazon Basics batteries"
SYSTEM_PROMPT = """You are a web navigation assistant with vision capabilities. 
When you don't know something DO NOT stop or make assumptions, ASK the user for feedback so we can continue. 
When you see a screenshot, analyze it carefully to identify elements and their positions. 
First click on elements like form fields, then use the type tool to enter text. You can submit forms by setting submit=true when typing.
You can scroll up or down to see more content on the page.
Think step by step and take screenshot between each to ensure you are doing what you think you are doing.
"""
SESSION_ID = str(uuid.uuid4())

# Create screenshot directory if it doesn't exist
os.makedirs(f"screenshot/{SESSION_ID}", exist_ok=True)

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
    {
        "toolSpec": {
            "name": "scroll",
            "description": "Scroll the page up or down",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "description": "Direction to scroll: 'up' or 'down'"
                        },
                        "amount": {
                            "type": "number",
                            "description": "Amount to scroll in pixels (default: 500)"
                        }
                    },
                    "required": ["direction"]
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
    print(f"Navigating to: {url}")
    await page.goto(url, wait_until='networkidle')
    # Wait a bit more to ensure page is stable
    await asyncio.sleep(1)
    return {"title": await page.title()}

async def take_screenshot(page):
    filename = f"screenshot/{SESSION_ID}/screenshot_{uuid.uuid4()}.png"
    print(f"Taking screenshot: {filename}")
    await page.screenshot(path=filename)
    
    # Return the filename for later use
    return {
        "filename": filename
    }

async def click(page, x, y):
    print(f"Clicking at coordinates: ({x}, {y})")
    await page.mouse.click(x, y)
    # Wait a bit for any navigation or page changes to stabilize
    await asyncio.sleep(1)
    return {"clicked_at": {"x": x, "y": y}}

async def scroll(page, direction, amount=500):
    print(f"Scrolling {direction} by {amount} pixels")
    if direction.lower() == "down":
        await page.evaluate(f"window.scrollBy(0, {amount})")
    elif direction.lower() == "up":
        await page.evaluate(f"window.scrollBy(0, -{amount})")
    else:
        return {"scrolled": False, "error": f"Invalid direction: {direction}"}
    
    # Wait a bit for the scroll to complete and content to load
    await asyncio.sleep(1)
    return {"scrolled": True, "direction": direction, "amount": amount}

async def type_text(page, text, submit=False):
    print(f"Typing text: '{text}'")
    try:
        await page.keyboard.type(text)
        
        if submit:
            print("Pressing Enter to submit")
            await page.keyboard.press('Enter')
            return {"typed": True, "text": text, "submitted": True}
        
        return {"typed": True, "text": text, "submitted": False}
    except Exception as e:
        print(f"Error typing text: {str(e)}")
        return {"typed": False, "error": str(e)}

async def ask_user(question):
    print("\n" + "-" * 50)
    print(f"QUESTION: {question}")
    print("-" * 50)
    user_response = input("Your answer: ")
    print("-" * 50 + "\n")
    return {"response": user_response}

async def get_page_info(page):
    try:
        title = await page.title()
        url = page.url
        return {"title": title, "url": url}
    except Exception as e:
        print(f"Error getting page info: {str(e)}")
        return {"title": "Unknown", "url": "Unknown"}

async def run_example():
    # Initialize browser - minimal setup
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    
    try:
        # Set up AWS Bedrock client
        bedrock_client = boto3.client('bedrock-runtime')
        
        messages = [{
            "role": "user",
            "content": [{"text": INITIAL_PROMPT}]
        }]
        nb_request = 1
        # Send to model
        print(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")
        print(f"User prompt: {messages[0]['content'][0]['text']}")
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            system=[{"text":SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": web_tools}
        )
        
        # Process response
        output_message = response.get('output', {}).get('message', {})
        output_message = filter_empty_text_content(output_message)
        messages.append(output_message)
        stop_reason = response.get('stopReason')

        print(f"Model response {json.dumps(output_message, indent=2)}")
        
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
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": result}]
                            }
                        })
                        
                    elif tool_name == 'screenshot':
                        result = await take_screenshot(page)
                        filename = result["filename"]
                        
                        # Read the image file as binary data
                        with open(filename, "rb") as image_file:
                            image_bytes = image_file.read()
                        
                        # Create a message with both text and image content
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [
                                    {"json": {"filename": filename}},
                                    {
                                        "image": {
                                            "format": "png",
                                            "source": {
                                                "bytes": image_bytes
                                            }
                                        }
                                    }
                                ]
                            }
                        })
                    
                    elif tool_name == 'click':
                        x = tool_input.get('x', 0)
                        y = tool_input.get('y', 0)
                        result = await click(page, x, y)
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": result}]
                            }
                        })
                    
                    elif tool_name == 'scroll':
                        direction = tool_input.get('direction', 'down')
                        amount = tool_input.get('amount', 500)
                        result = await scroll(page, direction, amount)
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": result}]
                            }
                        })
                    
                    elif tool_name == 'type':
                        text = tool_input.get('text', '')
                        submit = tool_input.get('submit', False)
                        result = await type_text(page, text, submit)
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": result}]
                            }
                        })
                    
                    elif tool_name == 'ask_user':
                        question = tool_input.get('question', 'What would you like to do next?')
                        result = await ask_user(question)
                        tool_content.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": result}]
                            }
                        })

            # Browser context content - safely get page info
            page_info = await get_page_info(page)
            browser_content = {"text": f"Current page: Title: '{page_info['title']}', URL: '{page_info['url']}'"}
            print(f"Browser context: {json.dumps(browser_content, indent=2)}")
            
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
            print(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")

            output_message = response.get('output', {}).get('message', {})
            output_message = filter_empty_text_content(output_message)
            messages.append(output_message)
            stop_reason = response.get('stopReason')
            
            print(f"Model response {json.dumps(output_message, indent=2)}")

                            
        print("Task completed")
    
    finally:
        # Clean up
        await browser.close()
        await playwright.stop()

# Main entry point
if __name__ == "__main__":
    print("AWS Bedrock Web Tools Minimal Example")
    print("------------------------------------")
    asyncio.run(run_example())
