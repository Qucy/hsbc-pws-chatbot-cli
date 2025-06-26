"""Website search tool using Vertex AI Datastore."""
#TODO: integrate on maplequad
import structlog
from typing import Dict, Any
from pydantic_ai import RunContext
from services.app_search_engine import app_search_engine_client

logger = structlog.get_logger(__name__)

async def search_website(ctx: RunContext[Dict[str, Any]], query: str) -> str:
    """Search public website content using Vertex AI App Engine (Enterprise Edition).
    
    Args:
        ctx: PydanticAI run context with dependencies
        query: Search query string
        
    Returns:
        Formatted search results as string
    """
    try:
        if not query or not query.strip():
            return "Please provide a search query to search the website."
        
        logger.info("Performing website search with App Engine", query=query)
        
        # Search using the new App Engine client
        results = await app_search_engine_client.search_website(query.strip(), max_results=5)
        
        if not results:
            return f"No results found for '{query}' on the HSBC website. Please try a different search term or browse our main sections."
        
        # Format results for the agent
        formatted_results = []
        formatted_results.append(f"Found {len(results)} relevant results for '{query}':\n")
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Unknown Title')
            snippet = result.get('snippet', 'No description available')
            link = result.get('link', '')
            source = result.get('source', 'website')
            
            # Special formatting for AI summary
            if source == 'ai_summary':
                formatted_result = f"📋 **{title}**\n"
                formatted_result += f"   {snippet}\n\n"
            else:
                formatted_result = f"{i}. **{title}**\n"
                if snippet:
                    formatted_result += f"   {snippet}\n"
                if link:
                    formatted_result += f"   🔗 [{link}]({link})\n"
                
                # Add extractive answers if available
                if 'extractive_answers' in result and result['extractive_answers']:
                    formatted_result += f"   💡 Key insights: {'; '.join(result['extractive_answers'])}\n"
            
            formatted_results.append(formatted_result)
        
        response = "\n".join(formatted_results)
        
        logger.info(
            "Website search response formatted",
            query=query,
            response_length=len(response)
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error while searching the website: {str(e)}"
        logger.error(
            "Website search error",
            query=query,
            error=str(e),
            event="Website search failed"
        )
        return error_msg