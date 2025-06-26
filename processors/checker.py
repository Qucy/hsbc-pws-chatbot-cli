"""Checker pipeline functions for analyzing agent nodes and responses."""

import structlog
from typing import Callable, List, Optional
from pydantic_ai._agent_graph import AgentNode
from pydantic_ai.result import FinalResult

logger = structlog.get_logger(__name__)

def check_cross_border_verification(nodes: List[AgentNode]) -> Optional[AgentNode]:
    """Check if any agent node contains cross-border verification requirement.
    
    Args:
        nodes: List of agent nodes to check
        
    Returns:
        End node with verification message if cross-border verification needed, None otherwise
    """
    try:
        for node in nodes:
            # Check if node has tool result with cross-border verification
            if hasattr(node, 'result') and isinstance(node.result, dict):
                if "verify_cross_border" in node.result:
                    logger.info("Cross-border verification requirement detected")
                    return FinalResult(data="Please declare your location")
        
        return None
        
    except Exception as e:
        logger.error("Error in cross-border verification check", error=str(e))
        return None

def create_checker_pipeline() -> List[Callable[[List[AgentNode]], Optional[AgentNode]]]:
    """Create ordered list of checker functions.
    
    Returns:
        List of checker functions that return AgentNode or None
    """
    return [
        check_cross_border_verification,
    ]

def apply_checker_pipeline(nodes: List[AgentNode], enabled: bool = True) -> Optional[AgentNode]:
    """Apply all checker functions to agent nodes.
    
    Args:
        nodes: List of agent nodes to check
        enabled: Whether to run the checker pipeline
        
    Returns:
        AgentNode if any checker triggers, None otherwise
    """
    if not enabled or not nodes:
        return None
    
    pipeline = create_checker_pipeline()
    
    for func in pipeline:
        try:
            result = func(nodes)
            if result is not None:
                logger.info(f"Checker function {func.__name__} triggered", result_type=type(result).__name__)
                return result
        except Exception as e:
            logger.error(f"Error in checker function {func.__name__}", error=str(e))
            # Continue with other checkers if one fails
    
    return None