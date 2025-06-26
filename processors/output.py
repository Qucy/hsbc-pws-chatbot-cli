"""Output postprocessing functions with validation and ModelRetry support."""

import re
import structlog
from typing import Callable, List
from urllib.parse import urlparse
import markdown
from pydantic_ai import ModelRetry
from config import CONFIG

logger = structlog.get_logger(__name__)

def validate_and_extract_urls(output_text: str) -> str:
    """Extract URLs and validate against allowlist."""
    if not output_text:
        return output_text
    
    try:
        url_allowlist = CONFIG['processing']['url_allowlist']
        if not url_allowlist:
            logger.warning("No URL allowlist configured, skipping URL validation")
            return output_text
        
        # Pattern to find URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]*'
        urls = re.findall(url_pattern, output_text)
        
        invalid_urls = []
        for url in urls:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check if domain is in allowlist
            is_allowed = any(allowed_domain in domain for allowed_domain in url_allowlist)
            
            if not is_allowed:
                invalid_urls.append(url)
                logger.warning("Invalid URL found", url=url, allowlist=url_allowlist)
        
        if invalid_urls:
            raise ModelRetry(
                f"Found {len(invalid_urls)} invalid URLs that are not in the allowlist. "
                f"Please only include URLs from these domains: {', '.join(url_allowlist)}"
            )
        
        logger.debug("URL validation passed", urls_found=len(urls))
        return output_text
        
    except ModelRetry:
        raise  # Re-raise ModelRetry
    except Exception as e:
        logger.error("Error in URL validation", error=str(e))
        # Don't retry on unexpected errors, just log and continue
        return output_text

def render_markdown(output_text: str) -> str:
    """Convert output to proper markdown format."""
    if not output_text:
        return output_text
    
    try:
        # Clean up and standardize markdown formatting
        result = output_text
        
        # Ensure proper spacing around headers
        result = re.sub(r'(\n|^)(#{1,6})([^\s#])', r'\1\2 \3', result)
        
        # Ensure proper list formatting
        result = re.sub(r'(\n|^)(\*|\-|\+)([^\s])', r'\1\2 \3', result)
        result = re.sub(r'(\n|^)(\d+\.)([^\s])', r'\1\2 \3', result)
        
        # Ensure proper line breaks before and after code blocks
        result = re.sub(r'([^\n])(\n```)', r'\1\n\2', result)
        result = re.sub(r'(```\n?)([^\n])', r'\1\n\2', result)
        
        # Validate markdown syntax by trying to parse it
        try:
            markdown.markdown(result)
        except Exception as md_error:
            logger.warning("Markdown syntax issue detected", error=str(md_error))
            raise ModelRetry(
                f"The response contains invalid markdown syntax: {str(md_error)}. "
                "Please ensure proper markdown formatting."
            )
        
        logger.debug("Markdown rendering completed")
        return result
        
    except ModelRetry:
        raise  # Re-raise ModelRetry
    except Exception as e:
        logger.error("Error in markdown rendering", error=str(e))
        return output_text

def render_url_buttons(output_text: str) -> str:
    """Convert URLs to HTML button elements."""
    if not output_text:
        return output_text
    
    try:
        # Pattern to find URLs with optional link text
        url_pattern = r'\[([^\]]+)\]\((https?://[^\s<>"{}|\\^`\[\]]*)\)'
        markdown_links = re.findall(url_pattern, output_text)
        
        result = output_text
        
        # Convert markdown links to HTML buttons
        for link_text, url in markdown_links:
            button_html = f'<button class="hsbc-link-button" onclick="window.open(\'{url}\', \'_blank\')">{link_text}</button>'
            result = result.replace(f'[{link_text}]({url})', button_html)
        
        # Also convert standalone URLs to buttons
        standalone_url_pattern = r'(?<!\]\()https?://[^\s<>"{}|\\^`\[\]]*'
        standalone_urls = re.findall(standalone_url_pattern, result)
        
        for url in standalone_urls:
            # Create a short display text from the URL
            parsed = urlparse(url)
            display_text = f"{parsed.netloc}{parsed.path[:20]}..." if len(parsed.path) > 20 else f"{parsed.netloc}{parsed.path}"
            button_html = f'<button class="hsbc-link-button" onclick="window.open(\'{url}\', \'_blank\')">{display_text}</button>'
            result = result.replace(url, button_html)
        
        if markdown_links or standalone_urls:
            logger.debug("URLs converted to buttons", markdown_links=len(markdown_links), standalone_urls=len(standalone_urls))
        
        return result
        
    except Exception as e:
        logger.error("Error in URL button rendering", error=str(e))
        return output_text

def apply_watermark(output_text: str) -> str:
    """Replace spaces with \\u00a0 in specific pattern for watermarking."""
    if not output_text:
        return output_text
    
    try:
        # Apply watermark pattern: replace every 5th space with non-breaking space
        # This creates an invisible pattern for content attribution
        words = output_text.split(' ')
        
        if len(words) < 5:
            return output_text  # Don't watermark very short texts
        
        result_words = []
        space_count = 0
        
        for i, word in enumerate(words):
            result_words.append(word)
            if i < len(words) - 1:  # Don't add space after last word
                space_count += 1
                if space_count % 5 == 0:
                    result_words.append('\u00a0')  # Non-breaking space
                else:
                    result_words.append(' ')  # Regular space
        
        result = ''.join(result_words)
        logger.debug("Watermark applied", original_length=len(output_text), watermarked_length=len(result))
        
        return result
        
    except Exception as e:
        logger.error("Error in watermark application", error=str(e))
        return output_text

def parse_escalation_commands(output_text: str) -> str:
    """Parse output for human escalation commands and format appropriately."""
    if not output_text:
        return output_text
    
    try:
        # Patterns that indicate escalation is needed
        escalation_patterns = [
            r'(?i)(transfer to human|escalate to agent|speak to representative)',
            r'(?i)(need human help|require specialist|complex issue)',
            r'(?i)(cannot help with|outside my capabilities|need manual review)',
        ]
        
        escalation_found = False
        for pattern in escalation_patterns:
            if re.search(pattern, output_text):
                escalation_found = True
                break
        
        if escalation_found:
            # Add structured escalation footer
            escalation_footer = (
                "\n\n---\n"
                "🔄 **Human Escalation Requested**\n"
                "This query requires human assistance. A customer service representative will be notified.\n"
                "**Escalation ID**: ESC-{timestamp}\n"
                "**Priority**: Standard\n"
                "---"
            )
            
            import time
            escalation_footer = escalation_footer.replace('{timestamp}', str(int(time.time())))
            
            result = output_text + escalation_footer
            logger.info("Human escalation command parsed and formatted")
            
            return result
        
        return output_text
        
    except Exception as e:
        logger.error("Error in escalation command parsing", error=str(e))
        return output_text

def create_postprocessing_pipeline() -> List[Callable[[str], str]]:
    """Create ordered list of postprocessing functions."""
    return [
        validate_and_extract_urls,
        render_markdown,
        render_url_buttons,
        apply_watermark,
        parse_escalation_commands,
    ]

def apply_postprocessing(text: str, enabled: bool = True) -> str:
    """Apply all postprocessing functions to output text."""
    if not enabled or not text:
        return text
    
    result = text
    pipeline = create_postprocessing_pipeline()
    
    for func in pipeline:
        try:
            result = func(result)
            logger.debug(f"Applied postprocessing function: {func.__name__}")
        except ModelRetry as e:
            logger.info(f"ModelRetry triggered in {func.__name__}", reason=str(e))
            raise  # Let ModelRetry bubble up for agent retry
        except Exception as e:
            logger.error(f"Error in postprocessing function {func.__name__}", error=str(e))
            # Continue with current result if a function fails
    
    return result 