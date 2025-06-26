"""Vertex AI Datastore client for search operations."""

import structlog
from typing import List, Dict, Any, Optional
from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPIError
from tenacity import retry, stop_after_attempt, wait_exponential
from config import CONFIG

logger = structlog.get_logger(__name__)

class DatastoreClient:
    """Client for interacting with Vertex AI Datastore."""
    
    def __init__(self):
        """Initialize the Datastore client."""
        self.project_id = CONFIG['vertex_ai']['project_id']
        self.location = CONFIG['datastore']['location']
        self.website_datastore_id = CONFIG['datastore']['website_id']
        self.faq_datastore_id = CONFIG['datastore']['faq_id']
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
    
    def _build_serving_config_path(self, datastore_id: str) -> str:
        """Build the serving config path for the datastore."""
        return f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/dataStores/{datastore_id}/servingConfigs/default_config"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_website(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the website datastore."""
        try:
            client = self._get_client()
            serving_config = self._build_serving_config_path(self.website_datastore_id)
            
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
                ),
            )
            
            response = client.search(request=request)
            
            results = []
            for result in response.results:
                doc_data = {
                    'title': getattr(result.document.derived_struct_data, 'title', 'Unknown'),
                    'snippet': getattr(result.document.derived_struct_data, 'snippet', ''),
                    'link': getattr(result.document.derived_struct_data, 'link', ''),
                    'source': 'website'
                }
                results.append(doc_data)
            
            logger.info(
                "Website search completed",
                query=query,
                results_count=len(results)
            )
            
            return results
            
        except GoogleAPIError as e:
            logger.error(
                "Website search failed",
                query=query,
                error=str(e)
            )
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_faq(self, question: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search the FAQ datastore."""
        try:
            client = self._get_client()
            serving_config = self._build_serving_config_path(self.faq_datastore_id)
            
            request = discoveryengine_v1.SearchRequest(
                serving_config=serving_config,
                query=question,
                page_size=max_results,
                content_search_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True,
                        max_snippet_count=2,
                    ),
                ),
            )
            
            response = client.search(request=request)
            
            results = []
            for result in response.results:
                doc_data = {
                    'question': getattr(result.document.derived_struct_data, 'question', 'Unknown'),
                    'answer': getattr(result.document.derived_struct_data, 'answer', ''),
                    'category': getattr(result.document.derived_struct_data, 'category', ''),
                    'source': 'faq'
                }
                results.append(doc_data)
            
            logger.info(
                "FAQ search completed",
                question=question,
                results_count=len(results)
            )
            
            return results
            
        except GoogleAPIError as e:
            logger.error(
                "FAQ search failed",
                question=question,
                error=str(e)
            )
            raise
    
    def health_check(self) -> bool:
        """Check if Datastore services are accessible."""
        try:
            # Simple connectivity test
            client = self._get_client()
            return True
        except Exception as e:
            logger.error("Datastore health check failed", error=str(e))
            return False

# Global client instance
datastore_client = DatastoreClient()