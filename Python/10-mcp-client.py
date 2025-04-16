#!/usr/bin/env python
import asyncio
import json
import os
import uuid
import base64
from typing import Dict, Any, List
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
#MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

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

# List to track artifact URIs
artifact_uris : List[AnyUrl] = []

# Define the server parameters for connecting to our MCP server
server_params = StdioServerParameters(
    command="python",
    args=["10-mcp-server.py"],
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

# Define a function to handle model responses
async def handle_model_response(response: Dict[str, Any]) -> None:
    """Process and display model responses"""
    if "content" in response:
        for content_item in response.get("content", []):
            if "text" in content_item:
                print_assistant(f"Model: {content_item['text']}")
            elif "toolUse" in content_item:
                tool = content_item["toolUse"]
                print_assistant(f"Model wants to use tool: {tool['name']}")
                print_assistant(f"  with parameters: {json.dumps(tool.get('input', {}), indent=2)}")

# Define a function to handle tool results
async def handle_tool_result(result: Dict[str, Any]) -> None:
    """Process and display tool results"""
    print_system(f"Tool result: {result}")

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
    print_system(f"Processing tool request: {tool_name} with ID {tool_id}")
    
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
                            print_system(f"Tracked artifact URI: {resource.uri}")                            
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
    print_system("Starting Web Automation MCP Client with Bedrock Integration")
    print_system("--------------------------------------------------------")
    
    try:
        # Connect to the MCP server
        async with stdio_client(server_params) as (read, write):
            # Create a client session
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools from MCP server
                mcp_tools = await session.list_tools()
                print_system(f"Available MCP tools: {[tool.name for tool in mcp_tools.tools]}")
                
                # Set up AWS Bedrock client
                bedrock_client = boto3.client('bedrock-runtime')
                
                # Dynamically convert MCP tools to Bedrock format
                bedrock_tools = convert_to_bedrock_tools(mcp_tools)
                print_system(f"Converted {len(bedrock_tools)} tools to Bedrock format")
                
                # Initialize conversation with the model
                messages = [{
                    "role": "user",
                    "content": [{"text": INITIAL_PROMPT}]
                }]
                
                print_system("\nStarting conversation with model...")
                print_user(f"User: {INITIAL_PROMPT}")
                
                # Request counter
                nb_request = 1
                
                # Send initial request to model
                print_system(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")
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
                
                print_assistant(f"Model response: {json.dumps(output_message, indent=2)}")
                
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
                            
                            print_assistant(f"\nExecuting tool: {tool_name}")
                            print_assistant(f"Tool input: {json.dumps(tool_input, indent=2)}")
                            
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
                    print_system(f"Browser context: {json.dumps(browser_content, indent=2)}")
                    
                    # Add browser context to message
                    tool_content.append(browser_content)                    
                    
                    # Send results back to model
                    tool_result_message = {
                        "role": "user",
                        "content": tool_content
                    }
                    messages.append(tool_result_message)
                    
                    nb_request += 1
                    # Continue conversation
                    print_system(f"Sending request {nb_request} to Bedrock with {len(messages)} messages...")
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
                    
                    print_assistant(f"Model response: {json.dumps(output_message, indent=2)}")
                
                # Download all artifacts at the end of the task
                if artifact_uris:
                    print_system("\nDownloading artifacts...")
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
                                            
                                            print_system(f"Downloaded artifact: {uri} to {download_path}")
                                else:
                                    print_system(f"Failed to download artifact: {uri} - No content returned")
                            else:
                                print_system(f"Failed to parse artifact URI: {uri}")
                        except Exception as e:
                            print_system(f"Error downloading artifact {uri}: {str(e)}")
                    
                    print_system(f"\nAll artifacts downloaded to the 'downloads' directory")
                
                print_system("\nTask completed")
    except Exception as e:
        print_system(f"Error: {str(e)}")
        traceback.print_exc()
        print_system("Try running the server first with: python 10-mcp-server.py")
        print_system("Make sure you have AWS credentials configured for Bedrock access")

# Run the client when this script is executed directly
if __name__ == "__main__":
    # Create directories for screenshots, artifacts, and downloads
    os.makedirs("downloads", exist_ok=True)
    
    print_system("AWS Bedrock Web Tools with MCP Integration")
    print_system("------------------------------------------")
    asyncio.run(run_client())