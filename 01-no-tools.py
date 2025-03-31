import json
import boto3
import asyncio

MODEL_ID = "us.amazon.nova-lite-v1:0"
INITIAL_PROMPT = "Navigate to AWS homepage and take a screenshot. Do the same for Anthropic homepage"

async def run_example():
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
        messages=messages,
    )
    
    # Process response
    output_message = response.get('output', {}).get('message', {})
    print(f"Model response {json.dumps(output_message, indent=2)}")


# Main entry point
if __name__ == "__main__":
    print("AWS Bedrock Web Tools Minimal Example")
    print("------------------------------------")
    asyncio.run(run_example())
