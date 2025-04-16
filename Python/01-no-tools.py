import json
import boto3
import asyncio

MODEL_ID = "us.amazon.nova-lite-v1:0"
INITIAL_PROMPT = "Navigate to AWS homepage and take a screenshot. Do the same for Anthropic homepage"

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

async def run_example():
    # Set up AWS Bedrock client
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
        messages=messages,
    )
    
    # Process response
    output_message = response.get('output', {}).get('message', {})
    print_assistant(f"Model response {json.dumps(output_message, indent=2)}")


# Main entry point
if __name__ == "__main__":
    print_system("AWS Bedrock Web Tools Minimal Example")
    print_system("------------------------------------")
    asyncio.run(run_example())
