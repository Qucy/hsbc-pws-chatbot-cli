# HSBC PWS Chatbot CLI - Product Design Document

## Overview

The HSBC PWS Chatbot CLI leverages PydanticAI's built-in CLI (`clai`) to provide an intelligent chatbot interface for public website interactions. The system consists of a custom PydanticAI agent with integrated tools for search, FAQ handling, and human escalation, accessible through the standard `clai` command-line interface.

## Technical Architecture

### Core Technology Stack

- **Agent Framework**: PydanticAI - Type-safe agent framework with structured outputs
- **LLM Model**: Google Vertex AI - Enterprise-grade language model
- **Search Backend**: Vertex AI Datastore - Vector search for structured and unstructured data
- **Configuration**: Environment Variables - Zero-config deployment approach
- **Language**: Python 3.11+

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  PydanticAI CLI │    │   HSBC Agent     │    │  Vertex AI      │
│     (clai)      │    │                  │    │                 │
│ • Interactive   │───▶│ • PydanticAI     │───▶│ • Gemini Pro    │
│ • Streaming     │    │ • Tools & Logic  │    │ • Datastore     │
│ • Commands      │    │ • Preprocessing  │    │ • Vector Search │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Functional Requirements

### Core Capabilities

1. **Intelligent Chatbot**: Natural language conversation interface
2. **Website Search**: Query public website content via Vertex AI Datastore
3. **FAQ System**: Dedicated FAQ search and retrieval
4. **Human Escalation**: Intelligent routing to human agents when needed
5. **Content Processing**: Input sanitization and output formatting
6. **CLI Interface**: PydanticAI's built-in `clai` command-line interface

### Agent Tools

#### 1. Public Website Search Tool
- **Purpose**: Search through public website content
- **Backend**: Vertex AI Datastore with structured/unstructured data
- **Input**: User query string
- **Output**: Relevant website content snippets

#### 2. FAQ Datastore Tool
- **Purpose**: Query frequently asked questions database
- **Backend**: Vertex AI Datastore optimized for FAQ retrieval
- **Input**: User question
- **Output**: Matching FAQ entries with answers

#### 3. Human Agent Escalation Tool
- **Purpose**: Determine when and how to escalate to human agents
- **Logic**: Pattern matching and intent detection
- **Output**: Escalation commands and routing information

## Processing Pipeline

### Input Preprocessing Functions

All preprocessing functions follow the signature: `Callable[[str], Union[str, None]]`

#### 1. Code Escaping Function
```python
def escape_code_blocks(input_text: str) -> Union[str, None]:
    """Safely wrap programming code with ``` to escape them"""
```

#### 2. Content Masking Function
```python
def mask_sensitive_content(input_text: str) -> Union[str, None]:
    """Mask sensitive content with *** based on regex patterns"""
```

### Output Postprocessing Functions

All postprocessing functions can raise `ModelRetry` for validation and chaining.

#### 1. URL Validation Function
```python
def validate_and_extract_urls(output_text: str) -> str:
    """Extract URLs and validate against allowlist"""
```

#### 2. Markdown Rendering Function
```python
def render_markdown(output_text: str) -> str:
    """Convert output to proper markdown format"""
```

#### 3. HTML Button Rendering Function
```python
def render_url_buttons(output_text: str) -> str:
    """Convert URLs to HTML button elements"""
```

#### 4. Watermark Implementation Function
```python
def apply_watermark(output_text: str) -> str:
    """Replace spaces with \u00a0 in specific pattern for watermarking"""
```

#### 5. Human Escalation Parser Function
```python
def parse_escalation_commands(output_text: str) -> str:
    """Parse output for human escalation commands and format appropriately"""
```

## Configuration Management

### Environment Variables

All system configuration is managed through environment variables:

```bash
# Vertex AI Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL_NAME=gemini-pro

# Datastore Configuration
VERTEX_DATASTORE_ID_WEBSITE=website-datastore-id
VERTEX_DATASTORE_ID_FAQ=faq-datastore-id
VERTEX_DATASTORE_LOCATION=global

# Agent Configuration
AGENT_MAX_RETRIES=3
AGENT_TIMEOUT_SECONDS=30
AGENT_TEMPERATURE=0.7

# Processing Configuration
PREPROCESSING_ENABLED=true
POSTPROCESSING_ENABLED=true
URL_ALLOWLIST=https://hsbc.com,https://hsbc.com.hk

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Component Design

### 1. Main Agent Module (`hsbc_agent.py`)

The core agent module that can be used with PydanticAI's CLI:

```python
from pydantic_ai import Agent
from pydantic import BaseModel

class ChatbotResponse(BaseModel):
    response: str
    source: str
    escalation_needed: bool

# Main agent that can be used with clai --agent hsbc_agent:agent
agent = Agent(
    model='vertex-ai:gemini-pro',
    deps_type=dict,
    output_type=ChatbotResponse,
    instructions="You are an HSBC customer service chatbot..."
)

# Also support direct CLI launch
if __name__ == "__main__":
    agent.to_cli_sync()
```

### 2. Environment Configuration (`config.py`)

```python
import os
from typing import Dict, Any

def get_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    return {
        'vertex_ai': {
            'project_id': os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
            'location': os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
            'model_name': os.getenv('VERTEX_AI_MODEL_NAME', 'gemini-pro'),
        },
        'datastore': {
            'website_id': os.getenv('VERTEX_DATASTORE_ID_WEBSITE'),
            'faq_id': os.getenv('VERTEX_DATASTORE_ID_FAQ'),
            'location': os.getenv('VERTEX_DATASTORE_LOCATION', 'global'),
        },
        'agent': {
            'max_retries': int(os.getenv('AGENT_MAX_RETRIES', '3')),
            'timeout': int(os.getenv('AGENT_TIMEOUT_SECONDS', '30')),
            'temperature': float(os.getenv('AGENT_TEMPERATURE', '0.7')),
        },
        'processing': {
            'preprocessing_enabled': os.getenv('PREPROCESSING_ENABLED', 'true').lower() == 'true',
            'postprocessing_enabled': os.getenv('POSTPROCESSING_ENABLED', 'true').lower() == 'true',
            'url_allowlist': os.getenv('URL_ALLOWLIST', '').split(','),
        }
    }
```

### 3. Tool Implementations (`tools/`)

#### Website Search Tool (`tools/website_search.py`)
```python
@agent.tool
async def search_website(ctx: RunContext[dict], query: str) -> str:
    """Search public website content"""
    # Vertex AI Datastore integration
    pass
```

#### FAQ Tool (`tools/faq_search.py`)
```python
@agent.tool
async def search_faq(ctx: RunContext[dict], question: str) -> str:
    """Search FAQ database"""
    # Vertex AI Datastore FAQ search
    pass
```

#### Escalation Tool (`tools/escalation.py`)
```python
@agent.tool
async def check_escalation(ctx: RunContext[dict], intent: str) -> str:
    """Determine if human escalation is needed"""
    # Pattern matching and escalation logic
    pass
```

### 4. Processing Pipeline (`processors/`)

#### Preprocessing (`processors/input.py`)
```python
from typing import Union, Callable

def create_preprocessing_pipeline() -> list[Callable[[str], Union[str, None]]]:
    """Create ordered list of preprocessing functions"""
    return [
        escape_code_blocks,
        mask_sensitive_content,
    ]
```

#### Postprocessing (`processors/output.py`)
```python
from pydantic_ai import ModelRetry

def create_postprocessing_pipeline() -> list[Callable[[str], str]]:
    """Create ordered list of postprocessing functions"""
    return [
        validate_and_extract_urls,
        render_markdown,
        render_url_buttons,
        apply_watermark,
        parse_escalation_commands,
    ]
```

## Project Structure

```
hsbc-pws-chatbot-cli/
├── __init__.py
├── hsbc_agent.py             # Main agent module (entry point)
├── config.py                 # Environment configuration
├── requirements.txt          # Python dependencies
├── tools/
│   ├── __init__.py
│   ├── website_search.py     # Website search tool
│   ├── faq_search.py         # FAQ search tool
│   └── escalation.py         # Human escalation tool
├── processors/
│   ├── __init__.py
│   ├── input.py              # Input preprocessing
│   └── output.py             # Output postprocessing
├── services/
│   ├── __init__.py
│   ├── vertex_ai.py          # Vertex AI client
│   └── datastore.py          # Datastore client
```

## Data Flow

### Request Processing Flow

1. **CLI Input** → User provides message via `clai`
2. **Preprocessing** → Apply input preprocessing functions within agent
3. **Agent Processing** → PydanticAI agent processes with tools
4. **Tool Execution** → Execute relevant tools (search, FAQ, escalation)
5. **Postprocessing** → Apply output postprocessing functions via validators
6. **Response** → Return formatted response through `clai` interface

### Error Handling

- **ModelRetry**: Postprocessing functions can trigger retries
- **Validation Errors**: Structured output validation
- **Tool Failures**: Graceful degradation with fallback responses
- **Rate Limiting**: Vertex AI API rate limit handling

## Security Considerations

### Data Protection
- Environment variable configuration prevents credential exposure
- Input sanitization through preprocessing pipeline
- URL validation against allowlist
- Sensitive content masking

### Access Control
- Service account based authentication
- Minimal required permissions for Vertex AI resources
- Audit logging for all interactions

## Performance Requirements

### Response Time
- Target: < 3 seconds for simple queries
- Target: < 10 seconds for complex searches

### Scalability
- Stateless design for horizontal scaling
- Connection pooling for Vertex AI services
- Caching for frequently accessed content

## Monitoring and Observability

### Logging
- Structured JSON logging
- Request/response tracking
- Performance metrics
- Error tracking and alerting

## Deployment

### Prerequisites
- Python 3.11+
- Google Cloud SDK
- Vertex AI API enabled
- Service account with appropriate permissions

### Installation and Usage

```bash
# Install the package
pip install -e .

python hsbc_agent.py
```