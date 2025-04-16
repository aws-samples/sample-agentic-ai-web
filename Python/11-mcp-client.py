#!/usr/bin/env python
import asyncio
import json
import os
import uuid
import base64
import copy
from typing import Dict, Any, List, Optional
import traceback
import boto3
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import ListToolsResult, Tool, CallToolResult, ReadResourceResult, TextResourceContents
from pydantic.networks import AnyUrl

# Define the initial prompt for the web automation task
INITIAL_PROMPT = "Search the price of AAA Amazon Basics batteries and write a summary of your findings in markdown format to a file named 'search-results.md'"

# Define the system prompt that instructs the model how to use the tools
SYSTEM_PROMPT = """You are a web navigation assistant with vision capabilities.
When you don't know something DO NOT stop or make assumptions, ASK the user for feedback so we can continue.
When you see a screenshot, analyze it carefully to identify elements and their positions.
First click on elements like form fields, then use the type tool to enter text. You can submit forms by setting submit=true when typing.
You can scroll up or down to see more content on the page.
After completing your search, use the write_file tool to save your findings in markdown format.
Think step by step and take screenshots between each step to ensure you are doing what you think you are doing.
"""

# AWS Bedrock model ID
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
# Model ID for summarization (using a smaller model for efficiency)
SUMMARY_MODEL_ID = "us.amazon.nova-micro-v1:0"#"us.anthropic.claude-3-5-haiku-20241022-v1:0"

# Configuration for conversation management
SUMMARIZATION_TOKEN_THRESHOLD = 5000  # Threshold for triggering summarization
KEEP_LAST_TURNS = 2  # Number of recent turns to keep intact during summarization

# List to track artifact URIs
artifact_uris : List[AnyUrl] = []

# Define the server parameters for connecting to our MCP server
server_params = StdioServerParameters(
    command="python",
    args=["11-mcp-server.py"],
    env=None  # No special environment variables needed
)

# Function to filter out empty text content
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

# Function to remove images/documents from all but the last turn of conversation
def remove_media_except_last_turn(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove images and documents from all messages except for the last turn of conversation.
    Ensures each message has at least one content item.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        List of messages with images/documents removed except in the last turn
    """
    if not messages or len(messages) < 2:
        return messages
    
    # Create a deep copy to avoid modifying the original messages
    processed_messages = copy.deepcopy(messages)
    
    # Keep the last user and assistant message pair intact (last turn)
    # Find the index of the second-to-last user message (if it exists)
    last_user_index = None
    second_last_user_index = None
    
    for i in range(len(processed_messages) - 1, -1, -1):
        if processed_messages[i]['role'] == 'user':
            if last_user_index is None:
                last_user_index = i
            else:
                second_last_user_index = i
                break
    
    # Process all messages except the last turn
    for i in range(len(processed_messages)):
        # Skip processing the last turn
        if (last_user_index is not None and i >= last_user_index) or (i == len(processed_messages) - 1):
            continue
            
        message = processed_messages[i]
        if 'content' not in message:
            continue
            
        new_content = []
        removed_media = False
        
        for content_item in message['content']:
            # Keep text content
            if 'text' in content_item:
                new_content.append(content_item)
            # Remove images and other media
            elif 'image' in content_item or 'json' in content_item:
                removed_media = True
            else:
                new_content.append(content_item)
        
        # If we removed media and have no content left, add a placeholder
        if removed_media and not new_content:
            new_content.append({
                "text": "An image or document was removed for brevity."
            })
            
        message['content'] = new_content
    
    return processed_messages

# Function to summarize conversation history
async def summarize_conversation(messages: List[Dict[str, Any]], bedrock_client) -> List[Dict[str, Any]]:
    """
    Summarize the conversation history, keeping the first message and the last X turns intact.
    
    Args:
        messages: List of conversation messages
        bedrock_client: AWS Bedrock client for calling the summarization model
        
    Returns:
        List of messages with middle part summarized
    """
    print("\n--- Starting conversation summarization ---")
    print(f"Original message count: {len(messages)}")
    
    # Debug: Print message roles and content types
    print("\nOriginal message structure:")
    for i, msg in enumerate(messages):
        content_types = []
        for content_item in msg.get('content', []):
            for key in content_item:
                content_types.append(key)
        print(f"  {i}: {msg['role']} - Content types: {', '.join(content_types)}")
    
    if not messages or len(messages) <= KEEP_LAST_TURNS * 2 + 1:  # +1 for the first message
        print("Not enough messages to summarize, returning original messages")
        return messages
    
    # Create a deep copy to avoid modifying the original messages
    processed_messages = copy.deepcopy(messages)
    
    # Keep the first message
    first_message = processed_messages[0]
    print(f"Keeping first message (role: {first_message['role']})")
    
    # Keep the last X turns (user-assistant pairs)
    last_messages = []
    message_count = 0
    turn_count = 0
    
    # Collect the last X turns
    for i in range(len(processed_messages) - 1, -1, -1):
        last_messages.insert(0, processed_messages[i])
        message_count += 1
        
        # Count a turn as a user-assistant pair
        if processed_messages[i]['role'] == 'user' and i > 0 and processed_messages[i-1]['role'] == 'assistant':
            turn_count += 1
            
        if turn_count >= KEEP_LAST_TURNS:
            break
    
    print(f"Keeping last {message_count} messages ({turn_count} turns)")
    
    # Messages to summarize (excluding first message and last X turns)
    to_summarize = processed_messages[1:len(processed_messages) - message_count]
    
    print(f"Messages to summarize: {len(to_summarize)}")
    
    if not to_summarize:
        print("No messages to summarize, returning original messages")
        return processed_messages
    
    # Check if the last message to summarize has any tool use requests
    last_message_to_summarize = to_summarize[-1] if to_summarize else None
    tool_use_content = []
    
    if last_message_to_summarize and last_message_to_summarize['role'] == 'assistant':
        print("Checking last message to summarize for tool use requests...")
        for content_item in last_message_to_summarize.get('content', []):
            if 'toolUse' in content_item:
                print(f"Found tool use request: {content_item['toolUse']['name']}")
                tool_use_content.append(content_item)
    
    # Prepare the conversation for summarization
    summarization_prompt = """Please summarize the following conversation while preserving key information, decisions, and context.
Focus on the steps we went through and what we've accomplished so far. Include any important findings or decisions made.
Provide a concise but comprehensive summary that will help continue the conversation effectively:

"""
    
    for msg in to_summarize:
        role = msg['role']
        content_text = ""
        
        for content_item in msg.get('content', []):
            if 'text' in content_item:
                content_text += content_item['text'] + " "
            elif 'json' in content_item:
                content_text += f"[JSON data] "
            elif 'image' in content_item:
                content_text += "[IMAGE] "
            elif 'toolUse' in content_item:
                content_text += f"[TOOL USE: {content_item['toolUse']['name']}] "
            elif 'toolResult' in content_item:
                content_text += "[TOOL RESULT] "
        
        if content_text.strip():
            summarization_prompt += f"{role.upper()}: {content_text}\n\n"
    
    print(f"Summarization prompt length: {len(summarization_prompt)} characters")
    
    # Call the model to generate a summary
    try:
        print("Calling summarization model...")
        summary_response = bedrock_client.converse(
            modelId=SUMMARY_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": summarization_prompt}]}]
        )
        
        summary_text = ""
        output_message = summary_response.get('output', {}).get('message', {})
        
        for content_item in output_message.get('content', []):
            if 'text' in content_item:
                summary_text += content_item['text']
        
        print(f"Generated summary length: {len(summary_text)} characters")
        print(f"Summary: {summary_text[:100]}...")
        print(f"Summary: {summary_text}...")

        
        # Create a new summary message with the summary text
        summary_content = [{
            "text": f"[CONVERSATION SUMMARY: {summary_text}]"
        }]
        
        # If there were tool use requests in the last message, add them to the summary message
        if tool_use_content:
            print(f"Adding {len(tool_use_content)} tool use requests to summary message")
            summary_content.extend(tool_use_content)
        
        summary_message = {
            "role": "assistant",
            "content": summary_content
        }
        
        # Build the final message list: first message + summary + last X turns
        result = [first_message, summary_message]
        result.extend(last_messages)
        
        print(f"Final message count after summarization: {len(result)}")
        
        # Debug: Print message roles and content types
        print("\nMessage structure after summarization:")
        for i, msg in enumerate(result):
            content_types = []
            for content_item in msg.get('content', []):
                for key in content_item:
                    content_types.append(key)
            print(f"  {i}: {msg['role']} - Content types: {', '.join(content_types)}")
        
        # Verify tool use and tool result pairs are maintained
        tool_use_count = 0
        tool_result_count = 0
        
        for msg in result:
            if msg['role'] == 'assistant':
                for content_item in msg.get('content', []):
                    if 'toolUse' in content_item:
                        tool_use_count += 1
            elif msg['role'] == 'user':
                for content_item in msg.get('content', []):
                    if 'toolResult' in content_item:
                        tool_result_count += 1
        
        print(f"Tool use count: {tool_use_count}, Tool result count: {tool_result_count}")
        if tool_use_count != tool_result_count:
            print("WARNING: Tool use and tool result counts don't match!")
            # In this case, return the original messages to avoid API errors
            return messages
        
        return result
        
    except Exception as e:
        print(f"Error during summarization: {str(e)}")
        traceback.print_exc()
        # If summarization fails, return the original messages
        return processed_messages

# Define a function to handle model responses
async def handle_model_response(response: Dict[str, Any]) -> None:
    """Process and display model responses"""
    if "content" in response:
        for content_item in response.get("content", []):
            if "text" in content_item:
                print(f"Model: {content_item['text']}")
            elif "toolUse" in content_item:
                tool = content_item["toolUse"]
                print(f"Model wants to use tool: {tool['name']}")
                print(f"  with parameters: {json.dumps(tool.get('input', {}), indent=2)}")

# Define a function to handle tool results
async def handle_tool_result(result: Dict[str, Any]) -> None:
    """Process and display tool results"""
    print(f"Tool result: {result}")

# Generic function to process tool requests
async def process_tool_request(session: ClientSession, tool_name: str, tool_id: str, tool_input: Dict[str, Any]) -> Dict:
    """Process a tool request generically based on the tool name and input
    
    Args:
        session: The MCP client session
        tool_name: The name of the tool to call
        tool_id: The unique ID of the tool use request
        tool_input: The input parameters for the tool
        
    Returns:
        A formatted tool result for Bedrock based on the content types in the result
        (handles TextContent, ImageContent, and EmbeddedResource)
    """
    print(f"Processing tool request: {tool_name} with ID {tool_id}")
    
    try:
        # Call the tool with the provided input
        result = await session.call_tool(tool_name, tool_input)
        
        # Process the result based on content types
        bedrock_content = []
        
        # Check if we have a proper CallToolResult with content
        if hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                # Check content type
                if hasattr(content_item, 'type'):
                    # Handle ImageContent
                    if content_item.type == 'image' and hasattr(content_item, 'data'):
                        image_data = base64.b64decode(content_item.data)
                        bedrock_content.append({"json": {"filename": "screenshot.jpeg"}})
                        # Use the image in Bedrock format
                        bedrock_content.append({
                            "image": {
                                "format": "jpeg",
                                "source": {
                                    "bytes": image_data
                                }
                            }
                        })
                    
                    # Handle TextContent
                    elif content_item.type == 'text' and hasattr(content_item, 'text'):
                        bedrock_content.append({"json": {"text": content_item.text}})
                    
                    # Handle EmbeddedResource
                    elif content_item.type == 'resource' and hasattr(content_item, 'resource'):
                        resource = content_item.resource
                        if hasattr(resource, 'uri'):
                            bedrock_content.append({"json": {"resource": resource.uri.unicode_string()}})
                            artifact_uris.append(resource.uri)
                            print(f"Tracked artifact URI: {resource.uri}")                            
                        if hasattr(resource, 'text'):
                            bedrock_content.append({"json": {"resource": resource.text}})

        

        return {
            "toolResult": {
                "toolUseId": tool_id,
                "content": bedrock_content
            }
        }
    except Exception as e:
        print(f"Error executing tool {tool_name}: {str(e)}")
        return {
            "toolResult": {
                "toolUseId": tool_id,
                "content": [{"json": {"error": str(e)}}]
            }
        }

# Convert MCP tools to Bedrock format
def convert_to_bedrock_tools(mcp_tools : ListToolsResult):
    bedrock_tools = []
    
    for tool in mcp_tools.tools:
        # Extract tool information
        name = tool.name
        description = tool.description or f"Use the {name} tool"
        
        # Create Bedrock tool spec
        bedrock_tool = {
            "toolSpec": {
                "name": name,
                "description": description,
                "inputSchema": {
                    "json" : tool.inputSchema if hasattr(tool, 'inputSchema') else {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        }

        # filter out ctx param
        if bedrock_tool['toolSpec']['inputSchema']['json']['properties'].get('ctx'):
            del bedrock_tool['toolSpec']['inputSchema']['json']['properties']['ctx']
        
        bedrock_tools.append(bedrock_tool)
    
    return bedrock_tools

# Main function to run the client
async def run_client():
    print("Starting Web Automation MCP Client with Bedrock Integration")
    print("--------------------------------------------------------")
    
    try:
        # Connect to the MCP server
        async with stdio_client(server_params) as (read, write):
            # Create a client session
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools from MCP server
                mcp_tools = await session.list_tools()
                print(f"Available MCP tools: {[tool.name for tool in mcp_tools.tools]}")
                
                # Set up AWS Bedrock client
                bedrock_client = boto3.client('bedrock-runtime')
                
                # Dynamically convert MCP tools to Bedrock format
                bedrock_tools = convert_to_bedrock_tools(mcp_tools)
                print(f"Converted {len(bedrock_tools)} tools to Bedrock format")
                
                # Initialize conversation with the model
                messages = [{
                    "role": "user",
                    "content": [{"text": INITIAL_PROMPT}]
                }]
                
                print("\nStarting conversation with model...")
                print(f"User: {INITIAL_PROMPT}")
                
                # Request counter
                nb_request = 1
                
                # Send initial request to model
                print(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")
                response = bedrock_client.converse(
                    modelId=MODEL_ID,
                    system=[{"text": SYSTEM_PROMPT}],
                    messages=messages,
                    toolConfig={"tools": bedrock_tools}
                )
                
                # Process response
                output_message = response.get('output', {}).get('message', {})
                output_message = filter_empty_text_content(output_message)
                messages.append(output_message)
                stop_reason = response.get('stopReason')
                
                print(f"Model response: {json.dumps(output_message, indent=2)}")
                
                # Process tool requests in a loop
                while stop_reason == 'tool_use':
                    tool_content = []
                    
                    for content in output_message.get('content', []):
                        if 'toolUse' in content:
                            tool = content['toolUse']
                            tool_name = tool['name']
                            tool_id = tool.get('toolUseId')
                            
                            # Parse tool input
                            tool_input = tool.get('input', {})
                            if isinstance(tool_input, str):
                                tool_input = json.loads(tool_input)
                            
                            print(f"\nExecuting tool: {tool_name}")
                            print(f"Tool input: {json.dumps(tool_input, indent=2)}")
                            
                            # Process the tool request using our generic function
                            result_content = await process_tool_request(session, tool_name, tool_id, tool_input)
                            tool_content.append(result_content)
                    
                    # Get page info for context using our generic function
                    page_info_result = await process_tool_request(session, "get_page_info", "page_info", {})
                    
                    # Extract the content from the result - handle different possible formats
                    page_info_content = page_info_result["toolResult"]["content"][0]
                    if "json" in page_info_content:
                        if isinstance(page_info_content["json"], dict) and "text" in page_info_content["json"]:
                            page_info_text = page_info_content["json"]["text"]
                        else:
                            page_info_text = str(page_info_content["json"])
                    else:
                        page_info_text = "Page info not available"
                    
                    browser_content = {"text": f"Current page: {page_info_text}"}
                    print(f"Browser context: {json.dumps(browser_content, indent=2)}")
                    
                    # Add browser context to message
                    tool_content.append(browser_content)                    
                    
                    # Send results back to model
                    tool_result_message = {
                        "role": "user",
                        "content": tool_content
                    }
                    messages.append(tool_result_message)
                    
                    # Apply conversation management before sending to model
                    # 1. Remove media except for the last turn
                    processed_messages = remove_media_except_last_turn(messages)
                    
                    # Get token usage from previous response
                    input_tokens = response.get('usage', {}).get('inputTokens', 0)
                    print(f"Current input tokens: {input_tokens}")
                    
                    # 2. Summarize conversation if token threshold is exceeded
                    if input_tokens > SUMMARIZATION_TOKEN_THRESHOLD:
                        print(f"Token threshold exceeded ({input_tokens} > {SUMMARIZATION_TOKEN_THRESHOLD}), summarizing conversation...")
                        processed_messages = await summarize_conversation(processed_messages, bedrock_client)
                        print(f"Conversation summarized, new message count: {len(processed_messages)}")
                    messages=processed_messages

                    nb_request += 1
                    # Continue conversation with processed messages
                    print(f"Sending request {nb_request} to Bedrock with {len(processed_messages)} messages...")
                    response = bedrock_client.converse(
                        modelId=MODEL_ID,
                        system=[{"text": SYSTEM_PROMPT}],
                        messages=messages,
                        toolConfig={"tools": bedrock_tools}
                    )
                    
                    output_message = response.get('output', {}).get('message', {})
                    output_message = filter_empty_text_content(output_message)
                    messages.append(output_message)
                    stop_reason = response.get('stopReason')
                    
                    print(f"Model response: {json.dumps(output_message, indent=2)}")
                
                # Download all artifacts at the end of the task
                if artifact_uris:
                    print("\nDownloading artifacts...")
                    for uri in artifact_uris:
                        try:
                            # Extract session_id and filename from URI
                            filename = uri.path
                            if filename:                                
                                
                                # Read the artifact using the resource
                                resource_contents : ReadResourceResult = await session.read_resource(uri)
                                
                                if resource_contents:
                                    contents = resource_contents.contents
                                    for content in contents:
                                        if isinstance(content,TextResourceContents):
                                            text_content : TextResourceContents = content 
                                            text = json.loads(text_content.text)[0]["text"]
                                            # Create a local directory for downloads if it doesn't exist
                                            download_dir = f"downloads/{uri.host}"
                                            os.makedirs(download_dir, exist_ok=True)
                                            
                                            # Save the artifact to the downloads directory
                                            download_path = f"{download_dir}{filename}"
                                            with open(download_path, 'w', encoding="utf-8") as f:
                                                f.write(text)
                                            
                                            print(f"Downloaded artifact: {uri} to {download_path}")
                                else:
                                    print(f"Failed to download artifact: {uri} - No content returned")
                            else:
                                print(f"Failed to parse artifact URI: {uri}")
                        except Exception as e:
                            print(f"Error downloading artifact {uri}: {str(e)}")
                    
                    print(f"\nAll artifacts downloaded to the 'downloads' directory")
                
                print("\nTask completed")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        print("Try running the server first with: python 11-mcp-server.py")
        print("Make sure you have AWS credentials configured for Bedrock access")

# Run the client when this script is executed directly
if __name__ == "__main__":
    # Create directories for screenshots, artifacts, and downloads
    os.makedirs("downloads", exist_ok=True)
    
    print("AWS Bedrock Web Tools with MCP Integration")
    print("------------------------------------------")
    asyncio.run(run_client())