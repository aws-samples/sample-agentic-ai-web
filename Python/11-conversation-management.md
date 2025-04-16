# Step 11: Conversation History Management

This step builds on the previous MCP server and client implementation, adding two important conversation history management features:

## Features Added

### 1. Media Content Removal

The `remove_media_except_last_turn()` function removes images and documents from all messages except for the last turn of conversation. This helps reduce token usage while preserving the most recent visual context.

Key aspects:
- Keeps the last user-assistant message pair intact
- Removes images and other media from earlier messages
- Ensures each message has at least one content item by adding a placeholder text if needed
- Preserves all text content for context

### 2. Conversation Summarization

The `summarize_conversation()` function summarizes the middle part of a conversation when the token count exceeds a configurable threshold. This helps manage long conversations while preserving important context.

Key aspects:
- Always keeps the first message intact (to preserve the original task/question)
- Keeps the last X turns intact (configurable via `KEEP_LAST_TURNS`)
- Summarizes the middle part of the conversation using a smaller, more efficient model
- Only triggers when the input token count exceeds the threshold (configurable via `SUMMARIZATION_TOKEN_THRESHOLD`)

## Configuration Options

The following configuration options are available at the top of the client file:

```python
# Model ID for summarization (using a smaller model for efficiency)
SUMMARY_MODEL_ID = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

# Configuration for conversation management
SUMMARIZATION_TOKEN_THRESHOLD = 8000  # Threshold for triggering summarization
KEEP_LAST_TURNS = 3  # Number of recent turns to keep intact during summarization
```

## Implementation Details

### Media Removal Process

1. The function creates a deep copy of the messages to avoid modifying the original
2. It identifies the last turn of conversation (last user-assistant pair)
3. For all messages except the last turn:
   - Keeps all text content
   - Removes images and other media content
   - If all content is removed, adds a placeholder text

### Summarization Process

1. The function creates a deep copy of the messages to avoid modifying the original
2. It preserves the first message and the last X turns
3. For all messages in between:
   - Extracts content from each message (text, tool use, tool results, etc.)
   - Sends this content to a smaller model for summarization
   - Creates a new summary message to replace all middle messages
4. **Important**: If the last message to be summarized contains tool use requests, these are preserved in the summary message to maintain the tool use/result relationship
5. The final message list becomes: first message + summary (with any preserved tool use requests) + last X turns
6. Extensive logging is added to help debug any issues with the summarization process
7. A verification step ensures that tool use and tool result counts match to avoid API validation errors

This approach maintains the simplicity of summarizing the middle section into a single message while ensuring that any tool use requests in the last summarized message are preserved to match their corresponding tool results in the subsequent messages.

## Integration in the Conversation Flow

Both functions are integrated into the main conversation loop:

```python
# Apply conversation management before sending to model
# 1. Remove media except for the last turn
processed_messages = remove_media_except_last_turn(messages)

# Get token usage from previous response
input_tokens = response.get('usage', {}).get('inputTokens', 0)

# 2. Summarize conversation if token threshold is exceeded
if input_tokens > SUMMARIZATION_TOKEN_THRESHOLD:
    processed_messages = await summarize_conversation(processed_messages, bedrock_client)
```

## Benefits

- **Reduced Token Usage**: By removing redundant media and summarizing older parts of the conversation
- **Improved Context Management**: Preserves important context while reducing noise
- **Better User Experience**: Allows for longer, more complex conversations without hitting token limits
- **Cost Efficiency**: Reduces the number of tokens processed by the main model

## Running the Example

To run this example:

1. Make sure you have AWS credentials configured for Bedrock access
2. Start the server: `python 11-mcp-server.py`
3. In a separate terminal, run the client: `python 11-mcp-client.py`

The client will automatically manage the conversation history as the interaction progresses.