# AWS Bedrock Web Tools - Components Overview

This document provides a simplified overview of the key components for each step in the project.

## Step 1: Basic Setup (No Tools)

```mermaid
flowchart LR
    subgraph "Components"
        M1["Model: us.amazon.nova-lite-v1:0"]
        L1["Loop: None (Single Request)"]
        T1["Tools: None"]
        B1["Browser: None"]
        F1["Generated Files: None"]
    end
```

## Step 2: Tool Definition

```mermaid
flowchart LR
    subgraph "Components"
        M2["Model: us.amazon.nova-lite-v1:0"]
        L2["Loop: None (Single Request)"]
        T2["Tools:
            - navigate
            - screenshot"]
        B2["Browser: None"]
        F2["Generated Files: None"]
                
        %% Highlight what's new compared to Step 1
        style T2 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 3: Tool Loop

```mermaid
flowchart LR
    subgraph "Components"
        M3["Model: us.amazon.nova-lite-v1:0"]
        L3["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T3["Tools:
            - navigate
            - screenshot"]
        B3["Browser: None"]
        F3["Generated Files: None"]
                
        %% Highlight what's new compared to Step 2
        style L3 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 4: Tool Invocation

```mermaid
flowchart LR
    subgraph "Components"
        M4["Model: us.amazon.nova-lite-v1:0"]
        L4["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T4["Tools:
            - navigate
            - screenshot"]
        B4["Browser: None (Simulated)"]
        F4["Generated Files:
            - screenshot_[uuid].png (Simulated)"]
        
        %% Highlight what's new compared to Step 3
        style B4 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style F4 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 5: Headless Browser

```mermaid
flowchart LR
    subgraph "Components"
        M5["Model: us.anthropic.claude-3-5-haiku-20241022-v1:0"]
        L5["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T5["Tools:
            - navigate
            - screenshot"]
        B5["Browser: Playwright Chromium"]
        F5["Generated Files:
            - screenshot_[uuid].png"]
        
        %% Highlight what's new compared to Step 4
        style M5 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style B5 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 6: Human-in-the-Loop

```mermaid
flowchart LR
    subgraph "Components"
        M6["Model: us.anthropic.claude-3-5-haiku-20241022-v1:0"]
        L6["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T6["Tools:
            - navigate
            - screenshot
            - ask_user"]
        B6["Browser: Playwright Chromium"]
        F6["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png"]
        
        %% Highlight what's new compared to Step 5
        style T6 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style F6 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 7: Vision Capabilities

```mermaid
flowchart LR
    subgraph "Components"
        M7["Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0"]
        L7["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T7["Tools:
            - navigate
            - screenshot
            - click
            - ask_user"]
        B7["Browser: Playwright Chromium"]
        F7["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png"]
        
        %% Highlight what's new compared to Step 6
        style M7 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style T7 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 8: Text Input with Form Submission

```mermaid
flowchart LR
    subgraph "Components"
        M8["Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0"]
        L8["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T8["Tools:
            - navigate
            - screenshot
            - click
            - type (with submit option)
            - scroll
            - ask_user"]
        B8["Browser: Playwright Chromium"]
        F8["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png"]
        
        %% Highlight what's new compared to Step 7
        style T8 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 9: File Writing

```mermaid
flowchart LR
    subgraph "Components"
        M9["Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0"]
        L9["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T9["Tools:
            - navigate
            - screenshot
            - click
            - type (with submit option)
            - scroll
            - write_file
            - ask_user"]
        B9["Browser: Playwright Chromium"]
        F9["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png
            - artefacts/[session_id]/[filename].md"]
        
        %% Highlight what's new compared to Step 8
        style T9 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style F9 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 10: MCP Integration

```mermaid
flowchart LR
    subgraph "Components"
        M10["Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0"]
        L10["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T10["Tools:
            - navigate
            - screenshot
            - click
            - type (with submit option)
            - scroll
            - write_file
            - get_page_info"]
        MCP["MCP:
            - Client: Bedrock integration
            - Server: Tool provider
            - Resources: artifact://[session_id]/[filename]"]
        B10["Browser: Playwright Chromium"]
        F10["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png
            - artefacts/[session_id]/[filename].md
            - downloads/[session_id]/[filename].md"]
        
        %% Highlight what's new compared to Step 9
        style T10 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style MCP fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
        style F10 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Step 11: Conversation History Management

```mermaid
flowchart LR
    subgraph "Components"
        M11["Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0"]
        L11["Loop: Tool Use Loop
            (Process tool requests until completion)"]
        T11["Tools:
            - navigate
            - screenshot
            - click
            - type (with submit option)
            - scroll
            - write_file
            - get_page_info"]
        MCP11["MCP:
            - Client: Bedrock integration
            - Server: Tool provider
            - Resources: artifact://[session_id]/[filename]"]
        B11["Browser: Playwright Chromium"]
        F11["Generated Files:
            - screenshot/[session_id]/screenshot_[uuid].png
            - artefacts/[session_id]/[filename].md
            - downloads/[session_id]/[filename].md"]
        CM11["Conversation Management:
            - remove_media_except_last_turn()
            - summarize_conversation()"]
        
        %% Highlight new components
        style CM11 fill:#0066cc,stroke:#333,stroke-width:2px,color:#ffffff
    end
```

## Model Evolution

```mermaid
flowchart LR
    M1["Steps 1-4: Amazon Nova Lite
        us.amazon.nova-lite-v1:0"] -->
    M2["Steps 5-6: Claude 3.5 Haiku
        us.anthropic.claude-3-5-haiku-20241022-v1:0"] -->
    M3["Steps 7-11: Claude 3.7 Sonnet
        us.anthropic.claude-3-7-sonnet-20250219-v1:0"] -->    
    M4["Step 11: Amazon Nova Micro
        (Summarization)"]

```

### Key Model Transition Points

1. **Nova Lite to Claude 3.5 Haiku (Step 4 → 5)**:
   - Enabled sending both tool results and browser context in the same conversation turn

2. **Claude 3.5 Haiku to Claude 3.7 Sonnet (Step 6 → 7)**:
   - Stronger reasoning capabilities for complex web navigation tasks
   - Near pixel-perfect vision for analyzing screenshots
   - Enhanced ability to identify and interact with visual elements
   - Better performance with vision-based clicking and form interactions

3. **MCP Integration (Step 10)**:
   - Standardized communication protocol between model and tools
   - Separation of client (model interface) and server (tool provider)
   - Resource handling for artifacts with URI-based addressing
   - Enhanced modularity and extensibility of the system

4. **Conversation Management (Step 11)**:
   - Efficient token usage through media removal and conversation summarization
   - Multi-model approach: Claude 3.7 Sonnet for main conversation, Amazon Nova Micro for summarization
   - Tool use/result pair preservation for API validation compliance</span>

## Tool Evolution

```mermaid
flowchart TD
    T1["Step 1: None"] -->
    T2["Step 2-4: navigate, screenshot"] -->
    T5["Step 5: navigate, screenshot (real browser)"] -->
    T6["Step 6: + ask_user"] -->
    T7["Step 7: + click"] -->
    T8["Step 8: + type, scroll"] -->
    T9["Step 9: + write_file"] -->
    T10["Step 10: + MCP integration"] -->
    T11["Step 11: + Conversation Management"]