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

## Troubleshooting MCP

If you encounter issues with the MCP implementation, try the following:

1. Check your MCP library version: `pip show mcp`
2. Check for error messages in the terminal
3. Ensure you have the necessary permissions to run the MCP client