# HSBC Public Website Chatbot CLI

An intelligent chatbot for HSBC's public website built with PydanticAI and Vertex AI, providing customer service capabilities through a command-line interface.

## Features

- 🤖 **Intelligent Chatbot**: Natural language conversation interface
- 🔍 **Website Search**: Query public website content via Vertex AI Datastore
- ❓ **FAQ System**: Dedicated FAQ search and retrieval
- 👥 **Human Escalation**: Intelligent routing to human agents when needed
- 🛡️ **Content Processing**: Input sanitization and output formatting
- 🖥️ **CLI Interface**: PydanticAI's built-in `clai` command-line interface

## Tech Stack

- **Agent Framework**: PydanticAI - Type-safe agent framework
- **LLM Model**: Google Vertex AI (Gemini 2.5 Flash)
- **Search Backend**: Vertex AI Datastore & App Engine - Vector search
- **Configuration**: Environment Variables
- **Language**: Python 3.11+

## Installation

### Prerequisites

- Python 3.11 or higher
- Google Cloud SDK
- Vertex AI API enabled
- Service account with appropriate permissions

### Setup

1. **Clone and install dependencies:**
   ```bash
   cd hsbc-pws-chatbot-cli
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Create a `.env` file or set the following environment variables:

   ```bash
   # Vertex AI Configuration
   export GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
   export VERTEX_AI_LOCATION=us-central1
   export VERTEX_AI_MODEL_NAME=gemini-pro

   # Datastore Configuration
   export VERTEX_DATASTORE_ID_WEBSITE=your-website-datastore-id
   export VERTEX_DATASTORE_ID_FAQ=your-faq-datastore-id
   export VERTEX_DATASTORE_LOCATION=global

   # Agent Configuration (optional)
   export AGENT_MAX_RETRIES=3
   export AGENT_TIMEOUT_SECONDS=30
   export AGENT_TEMPERATURE=0.7

   # Processing Configuration (optional)
   export PREPROCESSING_ENABLED=true
   export POSTPROCESSING_ENABLED=true
   export CHECKER_ENABLED=true
   export URL_ALLOWLIST=https://hsbc.com,https://hsbc.com.hk,https://www.hsbc.com.hk

   # Logging Configuration (optional)
   export LOG_LEVEL=INFO
   export LOG_FORMAT=json
   ```

3. **Install PydanticAI CLI (optional):**
   ```bash
   uv tool install clai
   ```

## Usage

### Using PydanticAI CLI (Recommended)

```bash
# Interactive mode with the HSBC agent
clai --agent hsbc_agent:agent

# One-shot query
clai --agent hsbc_agent:agent "How can I open a savings account?"

# With streaming responses
clai --agent hsbc_agent:agent --stream "Tell me about credit cards"
```

### Direct Execution

```bash
# Run the agent directly
python hsbc_agent.py
```

### Special CLI Commands

While in interactive mode, you can use these special commands:

- `/exit` - Exit the session
- `/markdown` - Show the last response in markdown format
- `/multiline` - Toggle multiline input mode (use Ctrl+D to submit)

## Agent Capabilities

### 🔍 Website Search Tool
- Searches official HSBC website content
- Provides relevant snippets with links
- Optimized for product information, services, and procedures

### ❓ FAQ Search Tool  
- Queries comprehensive FAQ database
- Returns structured Q&A format
- Covers common banking inquiries

### 👥 Human Escalation Tool
- Intelligent pattern matching for escalation needs
- Automatic priority classification (HIGH/MEDIUM)
- Structured escalation information with IDs

## Processing Pipeline

### Input Preprocessing
- **Code Escaping**: Safely wraps programming code with backticks
- **Content Masking**: Masks sensitive information (phone numbers, emails, etc.)

### Output Postprocessing
- **URL Validation**: Validates URLs against allowlist
- **Markdown Rendering**: Ensures proper markdown formatting
- **HTML Buttons**: Converts URLs to clickable buttons
- **Watermarking**: Applies invisible content attribution
- **Escalation Parsing**: Formats human escalation commands

### Checker Pipeline
- **Cross-Border Verification**: Monitors tool results for verification requirements
- **Location Declaration**: Triggers location request when cross-border activities detected
- **Async Iteration Control**: Uses PydanticAI's graph iteration for flow control

## Configuration

All configuration is managed through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT_ID` | GCP Project ID | Required |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account key path | Required |
| `VERTEX_DATASTORE_ID_WEBSITE` | Website datastore ID | Required |
| `VERTEX_DATASTORE_ID_FAQ` | FAQ datastore ID | Required |
| `VERTEX_AI_LOCATION` | Vertex AI region | `us-central1` |
| `VERTEX_AI_MODEL_NAME` | Model name | `gemini-pro` |
| `AGENT_MAX_RETRIES` | Max retry attempts | `3` |
| `URL_ALLOWLIST` | Comma-separated allowed domains | HSBC domains |

## Health Checks

Check system health:

```python
from hsbc_agent import health_check
status = health_check()
print(status)
```

## Examples

### Basic Banking Inquiry
```
User: How do I open a savings account?
Agent: I'll help you find information about opening a savings account at HSBC...
[Searches website and FAQ, provides structured response with links]
```

### Complex Issue with Escalation
```
User: I have an urgent issue with unauthorized transactions
Agent: I understand this is an urgent security matter. I'm immediately connecting you 
       with a senior customer service representative...
[Triggers high-priority escalation with structured information]
```

## Development

### Project Structure
```
hsbc-pws-chatbot-cli/
├── hsbc_agent.py             # Main agent module
├── config.py                 # Environment configuration
├── requirements.txt          # Dependencies
├── tools/                    # Agent tools
│   ├── website_search.py     # Website search
│   ├── faq_search.py         # FAQ search
│   └── escalation.py         # Human escalation
├── processors/               # Processing pipeline
│   ├── input.py              # Input preprocessing
│   ├── output.py             # Output postprocessing
│   └── checker.py            # Checker pipeline
└── services/                 # External services
    ├── app_search_engine.py  # App Engine search client
    └── datastore.py          # Datastore client
```

### Testing

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## Security

- Environment variable configuration prevents credential exposure
- Input sanitization through preprocessing pipeline
- URL validation against allowlist
- Sensitive content masking
- Service account based authentication

## Performance

- **Response Time**: < 3 seconds for simple queries, < 10 seconds for complex searches
- **Streaming**: Real-time response streaming support
- **Retry Logic**: Automatic retry with exponential backoff
- **Connection Pooling**: Optimized API connections

## Support

For technical issues or questions:
- Check the logs for detailed error information
- Verify environment variable configuration
- Ensure Vertex AI and Datastore services are accessible
- Contact the development team for assistance

## License

Internal HSBC project - All rights reserved.