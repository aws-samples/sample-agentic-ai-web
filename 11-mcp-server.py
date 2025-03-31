#!/usr/bin/env python
import asyncio
import uuid
import os
import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, List

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import Resource, ResourceTemplate, ResourceContents,TextResourceContents,EmbeddedResource
from playwright.async_api import async_playwright, Page, Browser, Playwright
# Create a unique session ID for this run
SESSION_ID = str(uuid.uuid4())

# Create directories for screenshots and artifacts
os.makedirs(f"screenshot/{SESSION_ID}", exist_ok=True)
os.makedirs(f"artefacts/{SESSION_ID}", exist_ok=True)

# Define our application context that will be available to all tools
@dataclass
class AppContext:
    playwright: Playwright
    browser: Browser
    page: Page

# Define the lifespan manager for our server
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and clean up browser resources"""
    print("Initializing browser resources")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://example.com", wait_until='networkidle')
    print("Browser resources initialized")
    
    try:
        # Yield our context with initialized resources
        yield AppContext(
            playwright=playwright,
            browser=browser,
            page=page
        )
    finally:
        # Clean up resources when the server shuts down
        await browser.close()
        await playwright.stop()

# Create our MCP server with the lifespan manager
mcp = FastMCP(
    "Web Automation Server",
    lifespan=app_lifespan,
    description="A server that provides web automation tools using Playwright"
)

# Register resource template for artifacts
@mcp.resource("artifact://{session_id}/{filename}")
async def get_artifact(session_id: str, filename: str) -> List[ResourceContents]:
    """Retrieve an artifact file by session ID and filename"""
    try:
        file_path = f"artefacts/{session_id}/{filename}"
        if not os.path.exists(file_path):
            return [ResourceContents(
                uri=f"artifact://{session_id}/{filename}",
                text=f"Error: Artifact not found: {filename}",
                mimeType="text/plain"
            )]
        
        # Read the file content
        with open(file_path, 'r', encoding="utf-8") as f:
            content = f.read()
        
        # Determine MIME type based on file extension
        mime_type = "text/plain"
        if filename.endswith('.md'):
            mime_type = "text/markdown"
        elif filename.endswith('.html'):
            mime_type = "text/html"
        elif filename.endswith('.json'):
            mime_type = "application/json"
        
        return [TextResourceContents(
            uri=f"artifact://{session_id}/{filename}",
            text=content,
            mimeType=mime_type
        )]
    except Exception as e:
        return [TextResourceContents(
            uri=f"artifact://{session_id}/{filename}",
            text=f"Error: {str(e)}",
            mimeType="text/plain"
        )]

# List available artifacts for the current session
@mcp.resource("artifact://list")
async def list_artifacts() -> List[ResourceContents]:
    """List all artifacts for the current session"""
    try:
        artifacts_dir = f"artefacts/{SESSION_ID}"
        if not os.path.exists(artifacts_dir):
            return [ResourceContents(
                uri="artifact://list",
                text="No artifacts found for this session",
                mimeType="text/plain"
            )]
        
        # Get list of files in the artifacts directory
        files = os.listdir(artifacts_dir)
        
        # Create a formatted list of artifacts with their URIs
        artifact_list = ["Available artifacts:"]
        for file in files:
            artifact_list.append(f"- {file}: artifact://{SESSION_ID}/{file}")
        
        return [ResourceContents(
            uri="artifact://list",
            text="\n".join(artifact_list),
            mimeType="text/plain"
        )]
    except Exception as e:
        return [ResourceContents(
            uri="artifact://list",
            text=f"Error listing artifacts: {str(e)}",
            mimeType="text/plain"
        )]

# Define our tools with proper descriptions and parameter documentation
@mcp.tool()
async def navigate(url: str, ctx: Context) -> dict:
    """Navigate to a specified URL
    
    Args:
        url: The URL to navigate to
        ctx: The MCP context
    
    Returns:
        Information about the loaded page
    """
    page = ctx.request_context.lifespan_context.page
    ctx.info(f"Navigating to: {url}")
    await page.goto(url, wait_until='domcontentloaded')
    # Wait a bit more to ensure page is stable
    await asyncio.sleep(1)
    return {"title": await page.title(), "url": page.url}

@mcp.tool()
async def screenshot(ctx: Context) -> Image:
    """Take a screenshot of the current page
    
    Args:
        ctx: The MCP context
    
    Returns:
        The screenshot as an image and filename information
    """
    page : Page = ctx.request_context.lifespan_context.page
    filename = f"screenshot/{SESSION_ID}/screenshot_{uuid.uuid4()}.jpeg"
    ctx.info(f"Taking screenshot: {filename}")
    await page.screenshot(path=filename,quality=80, type="jpeg")
    #
    return Image(path=filename, format='jpeg')
    


@mcp.tool()
async def click(x: int, y: int, ctx: Context) -> dict:
    """Click at specific coordinates on the page
    
    Args:
        x: X coordinate for the click
        y: Y coordinate for the click
        ctx: The MCP context
    
    Returns:
        Information about the click action
    """
    page = ctx.request_context.lifespan_context.page
    ctx.info(f"Clicking at coordinates: ({x}, {y})")
    await page.mouse.click(x, y)
    # Wait a bit for any navigation or page changes to stabilize
    await asyncio.sleep(1)
    return {"clicked_at": {"x": x, "y": y}}

@mcp.tool()
async def scroll(direction: str, amount: int, ctx: Context) -> dict:
    """Scroll the page up or down
    
    Args:
        direction: Direction to scroll: 'up' or 'down'
        amount: Amount to scroll in pixels
        ctx: The MCP context
    
    Returns:
        Information about the scroll action
    """
    page = ctx.request_context.lifespan_context.page
    ctx.info(f"Scrolling {direction} by {amount} pixels")
    if direction.lower() == "down":
        await page.evaluate(f"window.scrollBy(0, {amount})")
    elif direction.lower() == "up":
        await page.evaluate(f"window.scrollBy(0, -{amount})")
    else:
        return {"scrolled": False, "error": f"Invalid direction: {direction}"}
    
    # Wait a bit for the scroll to complete and content to load
    await asyncio.sleep(1)
    return {"scrolled": True, "direction": direction, "amount": amount}

@mcp.tool()
async def type(text: str, ctx: Context, submit: bool = False) -> dict:
    """Type text into the last clicked element
    
    Args:
        text: Text to type into the last clicked element
        ctx: The MCP context
        submit: Whether to press Enter after typing (to submit forms)
    
    Returns:
        Information about the typing action
    """
    page = ctx.request_context.lifespan_context.page
    ctx.info(f"Typing text: '{text}'")
    try:
        await page.keyboard.type(text)
        
        if submit:
            ctx.info("Pressing Enter to submit")
            await page.keyboard.press('Enter')
            return {"typed": True, "text": text, "submitted": True}
        
        return {"typed": True, "text": text, "submitted": False}
    except Exception as e:
        ctx.error(f"Error typing text: {str(e)}")
        return {"typed": False, "error": str(e)}

@mcp.tool()
def write_file(filename: str, content: str, ctx: Context) -> EmbeddedResource:
    """Write content to a file
    
    Args:
        filename: Name of the file to write to
        content: Content to write to the file
        ctx: The MCP context
    
    Returns:
        Information about the file writing operation including a resource URI
    """
    full_filename = f"artefacts/{SESSION_ID}/{filename}"
    ctx.info(f"Writing to file: {full_filename}")
    try:
        with open(full_filename, 'w', encoding="utf-8") as f:
            f.write(content)
        
        # Create a resource URI for this artifact
        resource_uri = f"artifact://{SESSION_ID}/{filename}"
        
        # Determine MIME type based on file extension
        mime_type = "text/plain"
        if filename.endswith('.md'):
            mime_type = "text/markdown"
        elif filename.endswith('.html'):
            mime_type = "text/html"
        elif filename.endswith('.json'):
            mime_type = "application/json"
        
        # Create a ResourceContents object
        resource = TextResourceContents(
            uri=resource_uri,
            mimeType=mime_type,
            text=content[:100]
        )
        
        return EmbeddedResource(type='resource',resource=resource)
    except Exception as e:
        ctx.error(f"Error writing file: {str(e)}")
        return {"written": False, "error": str(e)}

@mcp.tool()
async def get_page_info(ctx : Context) -> str:
    """Get information about the current page"""
    # Access the context through the server instance
    page = ctx.request_context.lifespan_context.page
    try:
        title = await page.title()
        url = page.url
        return f"Current page: Title: '{title}', URL: '{url}'"
    except Exception as e:
        return f"Error getting page info: {str(e)}"

# Run the server when this script is executed directly
if __name__ == "__main__":
    print("Starting Web Automation MCP Server")
    print("----------------------------------")
    try:
        mcp.run()
    except Exception as e:
        print(f"Error: {str(e)}")