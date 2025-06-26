"""HSBC PWS Chatbot Agent - Main agent module for PydanticAI CLI integration."""

import structlog
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

# Import configuration and services
from config import CONFIG, validate_config
from services.datastore import datastore_client

# Import processing pipelines
from processors.input import apply_preprocessing
from processors.output import apply_postprocessing
from processors.checker import apply_checker_pipeline

# Import tools
from tools.website_search import search_website
from tools.faq_search import search_faq
from tools.escalation import check_escalation, analyze_sentiment

import os

# Configure logging with file output
def setup_logging():
    """Setup logging configuration with optional file output"""
    processors = [
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
    ]
    
    # Add appropriate renderer based on format
    if CONFIG['logging']['format'] == 'json':
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Setup file logging if enabled
    if CONFIG['logging']['file_enabled']:
        # Create logs directory if it doesn't exist
        log_file_path = Path(CONFIG['logging']['file_path'])
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=CONFIG['logging']['file_path'],
            maxBytes=CONFIG['logging']['file_max_size'],
            backupCount=CONFIG['logging']['file_backup_count'],
            encoding='utf-8'
        )
        
        # Set log level
        log_level = getattr(logging, CONFIG['logging']['level'].upper(), logging.INFO)
        file_handler.setLevel(log_level)
        
        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(log_level)
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Initialize logging
setup_logging()
logger = structlog.get_logger(__name__)

class ChatbotResponse(BaseModel):
    """Structured response from the HSBC chatbot."""
    response: str
    source: str
    escalation_needed: bool
    confidence: float = 0.8
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)

# Initialize Vertex AI
try:
    validate_config()
    logger.info("HSBC Agent initialized successfully")
except Exception as e:
    logger.error("Failed to initialize HSBC Agent", error=str(e))
    raise

# Create the main agent
agent = Agent(
    model=GoogleModel(
        os.getenv('VERTEX_AI_MODEL_NAME'), 
        provider=GoogleProvider(
            project=os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
            location=os.getenv('VERTEX_AI_LOCATION'),
            vertexai=True
        )
    ),
    deps_type=Dict[str, Any],
    output_type=ChatbotResponse,
    retries=CONFIG['agent']['max_retries'],
    instructions=(
        "You are an intelligent HSBC customer service chatbot for the Hong Kong market. "
        "Your role is to help customers with banking inquiries, account information, "
        "product details, and general banking services.\n\n"
        
        "Core Guidelines:\n"
        "- Always be professional, helpful, and empathetic\n"
        "- Provide accurate information based on search results\n"
        "- Use tools to search for specific information when needed\n"
        "- Escalate to human agents when appropriate\n"
        "- Format responses in clear, easy-to-read markdown\n"
        "- Include relevant links when available\n"
        "- Be concise but comprehensive\n\n"
        
        "Available Tools:\n"
        "1. Website search - for official HSBC website content\n"
        "2. FAQ search - for frequently asked questions\n"
        "3. Escalation check - to determine if human help is needed\n\n"
        
        "Always prioritize customer satisfaction and provide helpful, actionable information."
    )
)

@agent.system_prompt
def dynamic_system_prompt(ctx: RunContext[Dict[str, Any]]) -> str:
    """Dynamic system prompt with current context."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S HKT")
    return f"Current time: {current_time}. HSBC Hong Kong banking services are available 24/7 for most inquiries."

@agent.tool
async def search_hsbc_website(ctx: RunContext[Dict[str, Any]], query: str) -> str:
    """Search the official HSBC website for information.
    
    Use this tool when customers ask about:
    - Product details (accounts, credit cards, loans, mortgages)
    - Banking services and features
    - Branch information and locations
    - Rates and fees
    - General banking procedures
    """
    try:
        logger.info("Website search tool called", query=query)
        result = await search_website(ctx, query)
        return result
    except Exception as e:
        logger.error("Website search tool failed", query=query, error=str(e))
        return f"I encountered an error searching our website. Please try again or contact customer support."

@agent.tool
async def search_hsbc_faq(ctx: RunContext[Dict[str, Any]], question: str) -> str:
    """Search the HSBC FAQ database for answers.
    
    Use this tool when customers ask:
    - Common questions about banking procedures
    - How-to questions
    - Account-related inquiries
    - Service availability questions
    - General banking guidance
    """
    try:
        logger.info("FAQ search tool called", question=question)
        result = await search_faq(ctx, question)
        return result
    except Exception as e:
        logger.error("FAQ search tool failed", question=question, error=str(e))
        return f"I encountered an error searching our FAQ database. Let me try to help you with general information."

@agent.tool
async def evaluate_escalation_need(ctx: RunContext[Dict[str, Any]], intent: str, user_message: str) -> str:
    """Evaluate if the customer inquiry needs human escalation.
    
    Use this tool when:
    - Customer requests human assistance
    - Complex issues that may require specialist help
    - Complaints or urgent matters
    - Issues outside standard FAQ/website content
    """
    try:
        logger.info("Escalation check tool called", intent=intent)
        result = await check_escalation(ctx, intent, user_message)
        return result
    except Exception as e:
        logger.error("Escalation check tool failed", intent=intent, error=str(e))
        return "I'll connect you with a customer service representative to ensure you get the help you need."

@agent.output_validator
def validate_response(ctx: RunContext[Dict[str, Any]], response: ChatbotResponse) -> ChatbotResponse:
    """Validate and postprocess the agent's response."""
    try:
        # Apply postprocessing if enabled
        if CONFIG['processing']['postprocessing_enabled']:
            processed_response = apply_postprocessing(response.response)
            response.response = processed_response
        
        # Determine escalation status from response content
        escalation_keywords = ['escalation', 'human', 'representative', 'transfer']
        response.escalation_needed = any(keyword in response.response.lower() for keyword in escalation_keywords)
        
        # Set source based on content
        if 'website' in response.response.lower():
            response.source = 'website'
        elif 'faq' in response.response.lower():
            response.source = 'faq'
        else:
            response.source = 'agent'
        
        logger.info("Response validated and processed", 
                   escalation_needed=response.escalation_needed,
                   source=response.source)
        
        return response
        
    except Exception as e:
        logger.error("Response validation failed", error=str(e))
        # Return original response if validation fails
        return response

# CLI integration
if __name__ == "__main__":
    """Direct CLI execution support with async iteration."""
    import asyncio
    
    async def run_agent_with_iteration():
        """Run the agent using async iteration pattern."""
        print("🏦 HSBC PWS Chatbot CLI")
        print("=" * 40)
        print("Welcome to HSBC Personal Wealth Solutions!")
        print("I'm here to help you with banking, investments, and financial services.")
        print("\nAvailable services:")
        print("• Website search and information")
        print("• FAQ and support questions")  
        print("• Account assistance and escalation")
        print("\nType 'exit', 'quit', or 'bye' to end the conversation.")
        print("=" * 40)
        
        print("Ready to help! 💬\n")
        
        # Interactive loop using async iteration
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Goodbye! 👋")
                    break
                
                if not user_input:
                    continue
                
                # Process with preprocessing if enabled
                if CONFIG['processing']['preprocessing_enabled']:
                    processed_input = apply_preprocessing(user_input)
                else:
                    processed_input = user_input
                
                # Initialize session data
                session_data = {
                    'user_profile': {
                        'customer_id': 'CLI_USER_001',
                        'tier': 'standard'
                    },
                    'conversation_history': [],
                    'previous_escalations': 0
                }
                
                print("Agent: ", end="", flush=True)
                
                nodes = []
                # Use async iteration over the agent's graph
                conversation_history = nodes_to_messages(nodes) # TODO: add conversation history to session data
                async with agent.iter(message_history, deps=session_data) as agent_run:
                    
                    async for node in agent_run:

                        checker_result = apply_checker_pipeline(nodes + [node])
                        # Exit the async iteration loop if checker result is not None
                        if checker_result:
                            nodes.append(checker_result)
                            break
                        
                        nodes.append(node)

                # print final response
                print(nodes[-1].content)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                logger.error("Error in CLI interaction", error=str(e))
    
    def run_cli():
        """Run the CLI with async support."""
        try:
            asyncio.run(run_agent_with_iteration())
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
    
    run_cli()
