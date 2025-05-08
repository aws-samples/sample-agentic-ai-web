# Amazon Bedrock Web Tools Example

This project demonstrates how to use Amazon Bedrock with Anthropic Claude and Amazon Nova models to create a web automation assistant with tool use, human-in-the-loop interaction, and vision capabilities.

## Setup Instructions


## Project Overview

This project contains a series of progressive examples that demonstrate different capabilities:

### Step 1: Basic Setup (No Tools)
`01-no-tools` - A minimal example that sends a request to Claude via Amazon Bedrock without any tools.

### Step 2: Tool Definition
`02-tool-definition` - Introduces tool definitions for web navigation and screenshots.

### Step 3: Tool Loop
`03-loop` - Implements a loop to handle tool requests with simulated responses.

### Step 4: Tool Invocation
`04-invoke-tool` - Adds actual tool implementation functions for navigation and screenshots.

### Step 5: Headless Browser
`05-headless-browser` - Integrates Playwright to control a real headless browser.

### Step 6: Human-in-the-Loop
`06-human-in-loop` - Adds a tool that allows the model to ask the user questions during execution.

### Step 7: Vision Capabilities
`07-vision` - Enhances the system with vision capabilities, allowing the model to:
- See screenshots it takes
- Analyze visual content
- Click on specific elements based on visual analysis

### Step 8: Text Input with Form Submission
`08-type-scroll-tools` - Adds text input and scrolling tools that enable the model to:
- First click on elements like form fields using vision
- Then type text into the last clicked element
- Submit forms by pressing Enter after typing (optional)
- Scroll up and down to see more content on the page
- Demonstrates a complete e-commerce search workflow

### Step 9: File Writing
`09-write-file` - Adds a file writing tool that enables the model to:
- Search for information on the web
- Scroll through search results to find relevant information
- Compile and organize the findings
- Write the results to a markdown file
- Create permanent documentation of web search results

### Step 10: MCP Refactoring
`10-mcp-client` - Refactors the application to use the Model Context Protocol:
- Separates the application into client and server components
- Uses FastMCP framework for structured tool definitions
- Implements proper resource lifecycle management with lifespan API
- Provides type-safe context passing between components
- Uses stdio transport for client-server communication
- Maintains all previous functionality with improved architecture
- Automatically starts the MCP server (`10-mcp-server.py`)

### Step 11: Conversation History Management
`11-mcp-client` - Adds conversation history management features:
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

## Amazon Bedrock Configuration

This example assumes you have:
1. AWS CLI configured with appropriate credentials
2. Access to Claude 3 models through Amazon Bedrock
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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

This project was created and is maintained by:

- [Florent Lacroute](https://github.com/FlorentLa)
- [Frederic Visticot](https://github.com/fvisticot)
- [Olivier Leplus](https://github.com/tagazok)