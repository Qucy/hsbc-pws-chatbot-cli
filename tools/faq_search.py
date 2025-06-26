"""FAQ search tool using Vertex AI Datastore."""

#TODO: integrate on maplequad
import structlog
from typing import Dict, Any
from pydantic_ai import RunContext
from services.app_search_engine import app_search_engine_client

logger = structlog.get_logger(__name__)

async def search_faq(ctx: RunContext[Dict[str, Any]], question: str) -> str:
    """Search FAQ database using Vertex AI App Engine (Enterprise Edition).
    
    Args:
        ctx: PydanticAI run context with dependencies
        question: User question string
        
    Returns:
        Formatted FAQ results as string
    """
    try:
        if not question or not question.strip():
            return "Please provide a question to search our FAQ database."
        
        logger.info("Performing FAQ search with App Engine", question=question)
        
        # Search using the new App Engine client
        results = await app_search_engine_client.search_faq(question.strip(), max_results=3)

        # log out the response
        logger.info("FAQ search response", results=results)
        
        if not results:
            return (f"I couldn't find specific FAQ entries for '{question}'. "
                   "However, I can help you with general HSBC services. "
                   "Try asking about accounts, credit cards, loans, or banking services.")
        
        # Format results for the agent
        formatted_results = []
        formatted_results.append(f"Here are the most relevant FAQ entries for your question:\n")
        
        for i, result in enumerate(results, 1):
            faq_question = result.get('question', 'Unknown Question')
            answer = result.get('answer', 'No answer available')
            category = result.get('category', '')
            source = result.get('source', 'faq')
            
            # Special formatting for AI summary
            if source == 'ai_summary':
                formatted_result = f"📋 **{faq_question}**\n"
                formatted_result += f"**Answer:** {answer}\n\n"
            else:
                formatted_result = f"**Q{i}: {faq_question}**\n"
                formatted_result += f"**A{i}:** {answer}\n"
                
                if category:
                    formatted_result += f"*Category: {category}*\n"
            
            formatted_results.append(formatted_result)
        
        response = "\n".join(formatted_results)
        
        logger.info(
            "FAQ search response formatted",
            question=question,
            response_length=len(response)
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error while searching the FAQ database: {str(e)}"
        logger.error(
            "FAQ search error",
            question=question,
            error=str(e),
            event="FAQ search failed"
        )
        return error_msg