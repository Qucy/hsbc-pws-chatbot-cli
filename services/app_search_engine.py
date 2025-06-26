import structlog
from typing import List, Dict, Any, Optional
from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPIError
from tenacity import retry, stop_after_attempt, wait_exponential
from config import CONFIG

logger = structlog.get_logger(__name__)

class AppSearchEngineClient:
    """Client for interacting with Vertex AI App Engine (Enterprise Edition)."""
    
    def __init__(self):
        """Initialize the App Search Engine client."""
        self.project_id = CONFIG['vertex_ai']['project_id']
        self.location = CONFIG['app_engine']['location']
        self.website_engine_id = CONFIG['app_engine']['website_engine_id']
        self.faq_engine_id = CONFIG['app_engine']['faq_engine_id']
        self._client: Optional[discoveryengine_v1.SearchServiceClient] = None
    
    def _get_client(self) -> discoveryengine_v1.SearchServiceClient:
        """Get or create the Discovery Engine client."""
        if self._client is None:
            # Configure regional endpoint based on location
            if self.location != "global":
                # Use regional endpoint: us-discoveryengine.googleapis.com for 'us' location
                api_endpoint = f"{self.location}-discoveryengine.googleapis.com"
                client_options = ClientOptions(api_endpoint=api_endpoint)
                self._client = discoveryengine_v1.SearchServiceClient(client_options=client_options)
            else:
                # Use global endpoint (default)
                self._client = discoveryengine_v1.SearchServiceClient()
        return self._client
    
    def _build_serving_config_path(self, engine_id: str) -> str:
        """Build the serving config path for the app engine."""
        return f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_website(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the website using App Engine (Enterprise Edition)."""
        try:
            client = self._get_client()
            serving_config = self._build_serving_config_path(self.website_engine_id)
            
            logger.info(
                "Starting website search with App Engine",
                query=query,
                serving_config=serving_config
            )
            
            request = discoveryengine_v1.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=max_results,
                content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True,
                        max_snippet_count=3,
                    ),
                    summary_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
                        summary_result_count=max_results,
                        include_citations=True,
                    ),
                    extractive_content_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                        max_extractive_answer_count=3,
                        max_extractive_segment_count=3,
                    ),
                ),
            )
            
            response = client.search(request=request)
            
            results = []
            for result in response.results:
                # Handle both structured and unstructured data
                doc_data = {}
                
                # Try to get structured data first
                if hasattr(result.document, 'derived_struct_data') and result.document.derived_struct_data:
                    struct_data = result.document.derived_struct_data
                    doc_data = {
                        'title': getattr(struct_data, 'title', '') or getattr(struct_data, 'htmlTitle', '') or 'Unknown',
                        'snippet': getattr(struct_data, 'snippet', '') or getattr(struct_data, 'htmlSnippet', ''),
                        'link': getattr(struct_data, 'link', '') or getattr(struct_data, 'formattedUrl', ''),
                        'source': 'website_app_engine'
                    }
                else:
                    # Fallback to document content
                    doc_data = {
                        'title': result.document.id or 'Unknown',
                        'snippet': str(result.document.content)[:200] + '...' if result.document.content else '',
                        'link': result.document.id or '',
                        'source': 'website_app_engine'
                    }
                
                # Add extractive answers if available
                if hasattr(result, 'chunk') and result.chunk:
                    doc_data['extractive_answers'] = []
                    if hasattr(result.chunk, 'content'):
                        doc_data['extractive_answers'].append(result.chunk.content)
                
                results.append(doc_data)
            
            # Add summary if available
            summary_text = ""
            if hasattr(response, 'summary') and response.summary:
                if hasattr(response.summary, 'summary_text'):
                    summary_text = response.summary.summary_text
            
            logger.info(
                "Website search completed with App Engine",
                query=query,
                results_count=len(results),
                has_summary=bool(summary_text)
            )
            
            # Add summary as first result if available
            if summary_text:
                summary_result = {
                    'title': 'AI Generated Summary',
                    'snippet': summary_text,
                    'link': '',
                    'source': 'ai_summary'
                }
                results.insert(0, summary_result)
            
            return results
            
        except GoogleAPIError as e:
            logger.error(
                "Website search failed with App Engine",
                query=query,
                error=str(e),
                serving_config=serving_config
            )
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_faq(self, question: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search the FAQ using App Engine (Enterprise Edition)."""
        try:
            client = self._get_client()
            serving_config = self._build_serving_config_path(self.faq_engine_id)
            
            logger.info(
                "Starting FAQ search with App Engine",
                question=question,
                serving_config=serving_config
            )
            
            request = discoveryengine_v1.SearchRequest(
                serving_config=serving_config,
                query=question,
                page_size=max_results,
                content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True,
                        max_snippet_count=2,
                    ),
                    summary_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SummarySpec(
                        summary_result_count=max_results,
                        include_citations=True,
                    ),
                    extractive_content_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                        max_extractive_answer_count=2,
                        max_extractive_segment_count=2,
                    ),
                ),
            )
            
            response = client.search(request=request)
            
            results = []
            for result in response.results:
                # Handle both structured and unstructured data
                doc_data = {}
                
                # Try to get structured data first
                if hasattr(result.document, 'derived_struct_data') and result.document.derived_struct_data:
                    struct_data = result.document.derived_struct_data
                    doc_data = {
                        'question': getattr(struct_data, 'question', '') or getattr(struct_data, 'title', '') or 'Unknown Question',
                        'answer': getattr(struct_data, 'answer', '') or getattr(struct_data, 'snippet', '') or 'No answer available',
                        'category': getattr(struct_data, 'category', '') or getattr(struct_data, 'section', ''),
                        'source': 'faq_app_engine'
                    }
                else:
                    # Fallback to document content
                    content = str(result.document.content) if result.document.content else ''
                    doc_data = {
                        'question': result.document.id or 'Unknown Question',
                        'answer': content[:300] + '...' if len(content) > 300 else content,
                        'category': '',
                        'source': 'faq_app_engine'
                    }
                
                # Add extractive answers if available
                if hasattr(result, 'chunk') and result.chunk:
                    if hasattr(result.chunk, 'content') and result.chunk.content:
                        # Use extractive answer as the main answer if it's more relevant
                        if len(result.chunk.content) > len(doc_data.get('answer', '')):
                            doc_data['answer'] = result.chunk.content
                
                results.append(doc_data)
            
            # Add summary if available
            summary_text = ""
            if hasattr(response, 'summary') and response.summary:
                if hasattr(response.summary, 'summary_text'):
                    summary_text = response.summary.summary_text
            
            logger.info(
                "FAQ search completed with App Engine",
                question=question,
                results_count=len(results),
                has_summary=bool(summary_text)
            )
            
            # Add summary as first result if available
            if summary_text:
                summary_result = {
                    'question': 'AI Generated Summary',
                    'answer': summary_text,
                    'category': 'AI Summary',
                    'source': 'ai_summary'
                }
                results.insert(0, summary_result)
            
            return results
            
        except GoogleAPIError as e:
            logger.error(
                "FAQ search failed with App Engine",
                question=question,
                error=str(e),
                serving_config=serving_config
            )
            raise
    
    def health_check(self) -> bool:
        """Check if App Search Engine services are accessible."""
        try:
            # Simple connectivity test
            client = self._get_client()
            return True
        except Exception as e:
            logger.error("App Search Engine health check failed", error=str(e))
            return False

# Global client instance
app_search_engine_client = AppSearchEngineClient()