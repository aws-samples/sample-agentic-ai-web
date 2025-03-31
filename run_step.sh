#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display usage information
show_usage() {
    echo -e "${BLUE}Usage:${NC} $0 <step_number> [--no-color]"
    echo -e "${BLUE}Example:${NC} $0 1     ${GREEN}# Run step 1 with colored output${NC}"
    echo -e "${BLUE}Example:${NC} $0 4 --no-color ${GREEN}# Run step 4 without colored output${NC}"
    
    echo -e "\n${BLUE}Available steps:${NC}"
    
    # Find all step files and display them
    for file in $(find . -maxdepth 1 -name "[0-9][0-9]-*.py" | sort); do
        # Extract step number and name
        filename=$(basename "$file")
        step_num=$(echo "$filename" | sed -E 's/^0*([0-9]+).*/\1/')
        step_name=$(echo "$filename" | sed -E 's/^[0-9]+-(.*)\.py/\1/')
        step_name=$(echo "$step_name" | tr '-' ' ')
        
        echo -e "  ${GREEN}$step_num${NC} - $step_name"
    done
}

# Check if at least one argument is provided
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

# Parse arguments
STEP_NUMBER=$1
USE_COLOR=true

if [ $# -gt 1 ] && [ "$2" == "--no-color" ]; then
    USE_COLOR=false
fi

# Validate step number is a number
if ! [[ "$STEP_NUMBER" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid step number. Please provide a valid number.${NC}"
    show_usage
    exit 1
fi

# Format step number with leading zero if needed
STEP_NUMBER_PADDED=$(printf "%02d" "$STEP_NUMBER")

# Find the matching Python file
PYTHON_FILE=""
for file in $(find . -maxdepth 1 -name "${STEP_NUMBER_PADDED}-*.py"); do
    PYTHON_FILE=$(basename "$file")
    break
done

# Check if a matching file was found
if [ -z "$PYTHON_FILE" ]; then
    echo -e "${RED}Error: No Python file found for step $STEP_NUMBER.${NC}"
    show_usage
    exit 1
fi

# Check if the file exists (redundant but safe)
if [ ! -f "$PYTHON_FILE" ]; then
    echo -e "${RED}Error: Python file '$PYTHON_FILE' not found.${NC}"
    exit 1
fi

# Extract step name for display
STEP_NAME=$(echo "$PYTHON_FILE" | sed -E 's/^[0-9]+-(.*)\.py/\1/')
STEP_NAME=$(echo "$STEP_NAME" | tr '-' ' ')

# Run the Python file
echo -e "${CYAN}Running step $STEP_NUMBER: $STEP_NAME${NC}"
echo -e "${CYAN}$(printf '=%.0s' "$(seq 1 40)")${NC}"

python "$PYTHON_FILE"