## Setup Instructions
```bash
# Install dependencies
npm istall

# Install Playwright's Chromium browser
playwright install chromium
```

## Usage

### Running Steps Manually

Each step can also be run directly:

```bash
# Activate the virtual environment if not already activated
source .venv/bin/activate

# Run a specific step
node 01-no-tools.js
node 02-tool-definition.js
node 03-loop.js
node 04-invoke-tool.js
node 05-headless-browser.js
node 06-human-in-loop.js
node 07-vision.js
node 08-type-scroll-tools.js
node 09-write-file.js

# For step 10 (MCP version)
node 10-mcp-client.js  # This will automatically start the MCP server
```