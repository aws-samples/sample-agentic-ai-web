# AWS Bedrock Web Tools Example

This project demonstrates how to use AWS Bedrock with Anthropic Claude and Amazon Nova models to create a web automation assistant with tool use, human-in-the-loop interaction, and vision capabilities.

## Setup Instructions

```bash
# Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium
```

## Project Overview

This project contains a series of progressive examples that demonstrate different capabilities:

### Step 1: Basic Setup (No Tools)
`01-no-tools.py` - A minimal example that sends a request to Claude via AWS Bedrock without any tools.

### Step 2: Tool Definition
`02-tool-definition.py` - Introduces tool definitions for web navigation and screenshots.

### Step 3: Tool Loop
`03-loop.py` - Implements a loop to handle tool requests with simulated responses.

### Step 4: Tool Invocation
`04-invoke-tool.py` - Adds actual tool implementation functions for navigation and screenshots.

### Step 5: Headless Browser
`05-headless-browser.py` - Integrates Playwright to control a real headless browser.

### Step 6: Human-in-the-Loop
`06-human-in-loop.py` - Adds a tool that allows the model to ask the user questions during execution.

### Step 7: Vision Capabilities
`07-vision.py` - Enhances the system with vision capabilities, allowing the model to:
- See screenshots it takes
- Analyze visual content
- Click on specific elements based on visual analysis

### Step 8: Text Input with Form Submission
`08-type-scroll-tools.py` - Adds text input and scrolling tools that enable the model to:
- First click on elements like form fields using vision
- Then type text into the last clicked element
- Submit forms by pressing Enter after typing (optional)
- Scroll up and down to see more content on the page
- Demonstrates a complete e-commerce search workflow

### Step 9: File Writing
`09-write-file.py` - Adds a file writing tool that enables the model to:
- Search for information on the web
- Scroll through search results to find relevant information
- Compile and organize the findings
- Write the results to a markdown file
- Create permanent documentation of web search results

### Step 10: MCP Refactoring
`10-mcp-client.py` - Refactors the application to use the Model Context Protocol:
- Separates the application into client and server components
- Uses FastMCP framework for structured tool definitions
- Implements proper resource lifecycle management with lifespan API
- Provides type-safe context passing between components
- Uses stdio transport for client-server communication
- Maintains all previous functionality with improved architecture
- Automatically starts the MCP server (`10-mcp-server.py`)

### Step 11: Conversation History Management
`11-mcp-client.py` - Adds conversation history management features:
- Implements media content removal to reduce token usage
- Adds conversation summarization for long interactions
- Uses a smaller model (Amazon Nova Micro) for efficient summarization
- Preserves tool use/result pairs for API validation compliance
- Maintains context while reducing token usage
- Enables longer, more complex conversations without hitting token limits
- Automatically starts the MCP server (`11-mcp-server.py`)

## Architecture Diagrams

The project includes a Mermaid diagram that illustrates the architecture and components of each step:

### Simplified Components Overview
- `components-overview.md` - A simplified version with just the essential components for each step

The components overview includes:
- One diagram per step showing only the key components
- Model evolution across steps
- Tool evolution across steps
- Architecture evolution across steps

This diagram helps visualize the progression from a simple API call to a sophisticated web automation assistant with multiple capabilities.

## Usage

### Running Steps with the Helper Script

The project includes a helper script `run_step.sh` that makes it easy to run any step with colored JSON output:

```bash
# Make the script executable
chmod +x run_step.sh

# Show available steps
./run_step.sh

# Run a specific step with colored output
./run_step.sh 1  # Run step 1 (01-no-tools.py)
./run_step.sh 8  # Run step 8 (08-type-scroll-tools.py)
./run_step.sh 9  # Run step 9 (09-write-file.py)

# Run without colored output
./run_step.sh 4 --no-color
```

The script automatically:
- Discovers available steps based on file naming pattern
- Formats JSON output with syntax highlighting using pygmentize
- Detects interactive scripts and ensures they can receive user input
- Installs pygmentize if it's not already available
- Provides helpful usage information

### Running Steps Manually

Each step can also be run directly:

```bash
# Activate the virtual environment if not already activated
source .venv/bin/activate

# Run a specific step
python 01-no-tools.py
python 02-tool-definition.py
python 03-loop.py
python 04-invoke-tool.py
python 05-headless-browser.py
python 06-human-in-loop.py
python 07-vision.py
python 08-type-scroll-tools.py
python 09-write-file.py

# For step 10 (MCP version)
python 10-mcp-client.py  # This will automatically start the MCP server

# For step 11 (Conversation Management)
python 11-mcp-client.py  # This will automatically start the MCP server
```

## Key Features

1. **Web Navigation**: Navigate to specified URLs using Playwright
2. **Screenshots**: Capture screenshots of web pages
3. **Human-in-the-Loop**: Ask the user questions during execution
4. **Vision Capabilities**: Allow the model to see and analyze screenshots
5. **Interactive Clicking**: Click on elements based on visual analysis
6. **Text Input & Form Submission**: Type text into previously clicked elements and optionally submit forms
7. **Page Scrolling**: Scroll up or down to see more content on long pages
8. **File Writing**: Save search results and findings to markdown files for documentation
9. **MCP Architecture**: Client-server architecture with standardized protocol (Step 10)
10. **Conversation Management**: Efficient token usage through media removal and conversation summarization (Step 11)

## AWS Bedrock Configuration

This example assumes you have:
1. AWS CLI configured with appropriate credentials
2. Access to Claude 3 models through AWS Bedrock
3. Appropriate permissions to use the Bedrock API

## Example Workflow

1. The model navigates to a website
2. It takes a screenshot and analyzes the visual content
3. It identifies interactive elements like search boxes
4. It clicks on an element (e.g., a search box) using vision-based coordinates
5. It types text into the clicked element (e.g., search query)
6. It can submit forms by pressing Enter after typing
7. It can scroll through search results to find relevant information
8. It can analyze search results and compile findings
9. It can write results to a markdown file for documentation
10. It can ask the user for input when needed

## Notes

- Screenshots are saved with random UUIDs as filenames
- The browser is automatically cleaned up after execution
- The system prompt instructs the model to use its vision capabilities and ask for help when needed
- Step 8 demonstrates a complete e-commerce search workflow for AAA Amazon Basics batteries
- Step 9 extends the workflow to save search results in markdown format to a file
- Step 10 refactors the application to use the Model Context Protocol (MCP)
- Step 11 adds conversation history management to handle long interactions efficiently
- The type tool includes a submit option that presses Enter after typing, useful for form submissions
- The scroll tool allows the model to navigate through long pages by scrolling up or down
- The approach of clicking first, then typing mimics how humans interact with web interfaces
- The `run_step.sh` script is designed to be extensible - it will automatically discover new step files as they are added
- Interactive scripts (those that ask for user input) are detected automatically and run in a way that preserves input functionality

## Troubleshooting MCP

If you encounter issues with the MCP implementation, try the following:

1. Check your MCP library version: `pip show mcp`
2. Check for error messages in the terminal
3. Ensure you have the necessary permissions to run the MCP client

## Authors

This project was created and is maintained by:

- [Florent Lacroute](https://github.com/FlorentLa)
- [Frederic Visticot](https://github.com/fvisticot)