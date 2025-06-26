"""Input preprocessing functions."""

import re
import structlog
from typing import Union, Callable, List

logger = structlog.get_logger(__name__)

def escape_code_blocks(input_text: str) -> Union[str, None]:
    """Safely wrap programming code with ``` to escape them."""
    if not input_text:
        return input_text
    
    try:
        # Pattern to detect code-like content
        code_patterns = [
            # Function calls with parentheses
            r'(\w+\s*\([^)]*\))',
            # Variable assignments with =
            r'(\w+\s*=\s*[^,\n]+)',
            # Code snippets with common keywords
            r'((?:if|for|while|def|class|import|from)\s+[^.!?]*)',
            # HTML/XML tags
            r'(<[^>]+>)',
            # SQL-like statements
            r'((?:SELECT|INSERT|UPDATE|DELETE|CREATE)\s+[^.!?]*)',
        ]
        
        result = input_text
        for pattern in code_patterns:
            # Find code-like patterns and wrap them in backticks if not already wrapped
            matches = re.finditer(pattern, result, re.IGNORECASE)
            for match in reversed(list(matches)):  # Reverse to avoid index issues
                code_snippet = match.group(1)
                # Don't wrap if already in code blocks
                if not (code_snippet.startswith('`') and code_snippet.endswith('`')):
                    start, end = match.span(1)
                    result = result[:start] + f'`{code_snippet}`' + result[end:]
        
        logger.debug("Code escaping applied", original_length=len(input_text), processed_length=len(result))
        return result
        
    except Exception as e:
        logger.error("Error in code escaping", error=str(e))
        return input_text  # Return original on error

def mask_sensitive_content(input_text: str) -> Union[str, None]:
    """Mask sensitive content with *** based on regex patterns."""
    if not input_text:
        return input_text
    
    try:
        # Sensitive patterns to mask
        sensitive_patterns = [
            # Phone numbers (various formats)
            (r'\b(\+?[\d\s\-\(\)]{7,15})\b', '***-***-****'),
            # Email addresses
            (r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', '***@***.com'),
            # Credit card numbers (basic pattern)
            (r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b', '****-****-****-****'),
            # NRIC/ID numbers (Hong Kong format and others)
            (r'\b([A-Z]\d{6}\([A-Z0-9]\))\b', '****(*)'),
            # Account numbers (6-12 digits)
            (r'\b(account\s*(?:number|no\.?)\s*:?\s*(\d{6,12}))\b', r'account number: ******'),
            # Social Security numbers
            (r'\b(\d{3}-\d{2}-\d{4})\b', '***-**-****'),
        ]
        
        result = input_text
        masked_count = 0
        
        for pattern, replacement in sensitive_patterns:
            matches = re.findall(pattern, result, re.IGNORECASE)
            if matches:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                masked_count += len(matches)
        
        if masked_count > 0:
            logger.info("Sensitive content masked", patterns_masked=masked_count)
        
        return result
        
    except Exception as e:
        logger.error("Error in content masking", error=str(e))
        return input_text  # Return original on error

def create_preprocessing_pipeline() -> List[Callable[[str], Union[str, None]]]:
    """Create ordered list of preprocessing functions."""
    return [
        escape_code_blocks,
        mask_sensitive_content,
    ]

def apply_preprocessing(text: str, enabled: bool = True) -> str:
    """Apply all preprocessing functions to input text."""
    if not enabled or not text:
        return text
    
    result = text
    pipeline = create_preprocessing_pipeline()
    
    for func in pipeline:
        try:
            processed = func(result)
            if processed is not None:
                result = processed
            else:
                logger.warning(f"Preprocessing function {func.__name__} returned None")
        except Exception as e:
            logger.error(f"Error in preprocessing function {func.__name__}", error=str(e))
            # Continue with original text if a function fails
    
    return result 