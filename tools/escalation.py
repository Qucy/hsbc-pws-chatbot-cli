"""Human escalation tool for pattern matching and intent detection."""

import re
import structlog
from typing import Dict, Any, List
from pydantic_ai import RunContext

logger = structlog.get_logger(__name__)

# Escalation Categories
ESCALATION_CATEGORIES = {
    'FRAUD_SECURITY': {
        'name': 'Fraud & Security',
        'priority': 'CRITICAL',
        'department': 'Security Operations',
        'sla_minutes': 2,
        'escalation_line': '+852 2233 3322'
    },
    'COMPLAINT_DISPUTE': {
        'name': 'Complaints & Disputes',
        'priority': 'HIGH',
        'department': 'Customer Relations',
        'sla_minutes': 15,
        'escalation_line': '+852 2233 3000'
    },
    'TECHNICAL_ISSUE': {
        'name': 'Technical Issues',
        'priority': 'MEDIUM',
        'department': 'Technical Support',
        'sla_minutes': 30,
        'escalation_line': '+852 2233 3100'
    },
    'ACCOUNT_ACCESS': {
        'name': 'Account Access Problems',
        'priority': 'HIGH',
        'department': 'Account Services',
        'sla_minutes': 10,
        'escalation_line': '+852 2233 3200'
    },
    'INVESTMENT_ADVISORY': {
        'name': 'Investment Advisory',
        'priority': 'MEDIUM',
        'department': 'Investment Services',
        'sla_minutes': 45,
        'escalation_line': '+852 2233 3400'
    },
    'BEREAVEMENT_ESTATE': {
        'name': 'Bereavement & Estate',
        'priority': 'HIGH',
        'department': 'Estate Services',
        'sla_minutes': 20,
        'escalation_line': '+852 2233 3500'
    },
    'BUSINESS_BANKING': {
        'name': 'Business Banking',
        'priority': 'MEDIUM',
        'department': 'Business Services',
        'sla_minutes': 30,
        'escalation_line': '+852 2233 3600'
    },
    'MORTGAGE_LOANS': {
        'name': 'Mortgage & Loans',
        'priority': 'MEDIUM',
        'department': 'Lending Services',
        'sla_minutes': 60,
        'escalation_line': '+852 2233 3700'
    },
    'REGULATORY_COMPLIANCE': {
        'name': 'Regulatory & Compliance',
        'priority': 'HIGH',
        'department': 'Compliance',
        'sla_minutes': 30,
        'escalation_line': '+852 2233 3800'
    },
    'VIP_PREMIER': {
        'name': 'VIP & Premier Services',
        'priority': 'HIGH',
        'department': 'Premier Banking',
        'sla_minutes': 5,
        'escalation_line': '+852 2233 3900'
    },
    'GENERAL_INQUIRY': {
        'name': 'General Customer Service',
        'priority': 'STANDARD',
        'department': 'Customer Service',
        'sla_minutes': 20,
        'escalation_line': '+852 2233 3000'
    }
}

async def check_escalation(ctx: RunContext[Dict[str, Any]], intent: str, user_message: str = "") -> str:
    """Determine if human escalation is needed based on intent analysis.
    
    Args:
        ctx: PydanticAI run context with dependencies
        intent: Detected intent or classification
        user_message: Original user message for additional context
        
    Returns:
        Escalation assessment and guidance
    """
    try:
        # Extract context information
        session_data = ctx.deps or {}
        user_profile = session_data.get('user_profile', {})
        conversation_history = session_data.get('conversation_history', [])
        previous_escalations = session_data.get('previous_escalations', 0)
        customer_tier = user_profile.get('tier', 'standard')  # standard, premium, vip
        interaction_count = len(conversation_history)
        
        logger.info("Checking escalation need", 
                   intent=intent, 
                   message_length=len(user_message),
                   customer_tier=customer_tier,
                   interaction_count=interaction_count,
                   previous_escalations=previous_escalations)
        
        # Determine escalation category and priority
        escalation_category = _determine_escalation_category(intent, user_message)
        category_info = ESCALATION_CATEGORIES.get(escalation_category, ESCALATION_CATEGORIES['GENERAL_INQUIRY'])
        
        # Enhanced pattern matching with context
        combined_text = f"{intent} {user_message}".strip()
        
        # Critical escalation patterns (immediate escalation)
        critical_patterns = [
            r'(?i)(fraud|unauthorized|stolen|hacked|security breach)',
            r'(?i)(emergency|crisis|urgent help|immediate assistance)',
            r'(?i)(death|deceased|bereavement|inheritance|estate)',
            r'(?i)(legal action|lawsuit|court|solicitor|ombudsman)',
        ]
        
        # High priority patterns
        high_priority_patterns = [
            r'(?i)(complaint|dispute|dissatisfied|terrible service)',
            r'(?i)(cannot access|locked out|account blocked)',
            r'(?i)(premier|vip|private banking|wealth management)',
            r'(?i)(regulatory|compliance|suspicious activity)',
        ]
        
        # Medium priority patterns
        medium_priority_patterns = [
            r'(?i)(complex|complicated|multiple accounts|business)',
            r'(?i)(investment advice|financial planning|mortgage)',
            r'(?i)(technical issue|system error|website problem)',
            r'(?i)(speak to manager|supervisor|human agent)',
        ]
        
        # Context-based escalation rules
        
        # VIP/Premier customers get priority escalation
        if customer_tier in ['vip', 'premier'] and escalation_category != 'GENERAL_INQUIRY':
            escalation_category = 'VIP_PREMIER'
            category_info = ESCALATION_CATEGORIES['VIP_PREMIER']
        
        # Multiple interactions suggest escalation need
        if interaction_count >= 3 and previous_escalations == 0:
            return _format_escalation_response(
                category=escalation_category,
                category_info=category_info,
                reason='Multiple interaction attempts without resolution',
                user_message=user_message,
                ctx=ctx
            )
        
        # Previous escalation attempts
        if previous_escalations >= 1:
            return _format_escalation_response(
                category='COMPLAINT_DISPUTE',
                category_info=ESCALATION_CATEGORIES['COMPLAINT_DISPUTE'],
                reason='Previous escalation - requires senior agent',
                user_message=user_message,
                ctx=ctx
            )
        
        # Check for critical escalation
        for pattern in critical_patterns:
            if re.search(pattern, combined_text):
                # Override category for critical issues
                if 'fraud' in combined_text.lower() or 'unauthorized' in combined_text.lower():
                    escalation_category = 'FRAUD_SECURITY'
                elif 'death' in combined_text.lower() or 'bereavement' in combined_text.lower():
                    escalation_category = 'BEREAVEMENT_ESTATE'
                elif 'legal' in combined_text.lower():
                    escalation_category = 'REGULATORY_COMPLIANCE'
                
                return _format_escalation_response(
                    category=escalation_category,
                    category_info=ESCALATION_CATEGORIES[escalation_category],
                    reason='Critical issue detected - immediate escalation required',
                    user_message=user_message,
                    ctx=ctx
                )
        
        # Check for high priority escalation
        for pattern in high_priority_patterns:
            if re.search(pattern, combined_text):
                return _format_escalation_response(
                    category=escalation_category,
                    category_info=category_info,
                    reason='High priority issue requiring specialist assistance',
                    user_message=user_message,
                    ctx=ctx
                )
        
        # Check for medium priority escalation
        for pattern in medium_priority_patterns:
            if re.search(pattern, combined_text):
                return _format_escalation_response(
                    category=escalation_category,
                    category_info=category_info,
                    reason='Complex issue requiring human expertise',
                    user_message=user_message,
                    ctx=ctx
                )
        
        # Check for repeated requests for human help
        human_request_patterns = [
            r'(?i)(human|person|agent|representative|operator)',
            r'(?i)(speak to|talk to|connect me|transfer me)',
            r'(?i)(not helping|can\'t help|unable to help)',
        ]
        
        human_requests = sum(1 for pattern in human_request_patterns if re.search(pattern, combined_text))
        
        if human_requests >= 2:
            return _format_escalation_response(
                category='GENERAL_INQUIRY',
                category_info=ESCALATION_CATEGORIES['GENERAL_INQUIRY'],
                reason='Multiple requests for human assistance',
                user_message=user_message,
                ctx=ctx
            )
        
        # No escalation needed
        return _format_no_escalation_response(ctx)
        
    except Exception as e:
        logger.error("Error in escalation check", 
                    intent=intent, 
                    error=str(e))
        
        # Default to general inquiry escalation on error
        return _format_escalation_response(
            category='GENERAL_INQUIRY',
            category_info=ESCALATION_CATEGORIES['GENERAL_INQUIRY'],
            reason='System error during escalation assessment',
            user_message=user_message,
            ctx=ctx
        )

def _determine_escalation_category(intent: str, user_message: str) -> str:
    """Determine the appropriate escalation category based on intent and message content."""
    combined_text = f"{intent} {user_message}".lower()
    
    # Category mapping patterns
    category_patterns = {
        'FRAUD_SECURITY': [
            r'(fraud|unauthorized|stolen|hacked|security|breach|suspicious)',
            r'(card.*stolen|account.*hacked|unauthorized.*transaction)',
        ],
        'COMPLAINT_DISPUTE': [
            r'(complaint|dispute|dissatisfied|unhappy|terrible)',
            r'(poor.*service|bad.*experience|not.*satisfied)',
        ],
        'TECHNICAL_ISSUE': [
            r'(technical|system|website|app|error|broken|not.*working)',
            r'(login.*problem|access.*issue|website.*down)',
        ],
        'ACCOUNT_ACCESS': [
            r'(cannot.*access|locked.*out|blocked|suspended|frozen)',
            r'(password.*reset|account.*locked|login.*blocked)',
        ],
        'INVESTMENT_ADVISORY': [
            r'(investment|advisory|financial.*planning|portfolio)',
            r'(wealth.*management|asset.*allocation|retirement.*planning)',
        ],
        'BEREAVEMENT_ESTATE': [
            r'(death|deceased|bereavement|inheritance|estate|probate)',
            r'(passed.*away|family.*member.*died|estate.*planning)',
        ],
        'BUSINESS_BANKING': [
            r'(business|commercial|corporate|trade|import|export)',
            r'(business.*account|commercial.*banking|corporate.*services)',
        ],
        'MORTGAGE_LOANS': [
            r'(mortgage|loan|lending|credit|refinance|property)',
            r'(home.*loan|mortgage.*rate|loan.*application)',
        ],
        'REGULATORY_COMPLIANCE': [
            r'(regulatory|compliance|legal|lawsuit|court|ombudsman)',
            r'(legal.*action|compliance.*issue|regulatory.*matter)',
        ],
        'VIP_PREMIER': [
            r'(premier|vip|private.*banking|wealth|high.*net.*worth)',
            r'(premier.*customer|vip.*service|private.*banker)',
        ],
    }
    
    # Check patterns in order of priority
    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                return category
    
    return 'GENERAL_INQUIRY'

def _format_escalation_response(category: str, category_info: Dict[str, Any], reason: str, user_message: str, ctx: RunContext[Dict[str, Any]]) -> str:
    """Format escalation response with structured information."""
    import time
    
    # Generate escalation ID with category prefix
    timestamp = int(time.time())
    category_prefix = category.split('_')[0][:3].upper()
    escalation_id = f"{category_prefix}-ESC-{timestamp}"
    
    # Extract context information
    session_data = ctx.deps or {}
    user_profile = session_data.get('user_profile', {})
    customer_id = user_profile.get('customer_id', 'UNKNOWN')
    customer_tier = user_profile.get('tier', 'standard')
    
    response = f"🔄 **Human Escalation Required**\n\n"
    response += f"**Category:** {category_info['name']}\n"
    response += f"**Priority:** {category_info['priority']}\n"
    response += f"**Department:** {category_info['department']}\n"
    response += f"**Reason:** {reason}\n"
    response += f"**Escalation ID:** {escalation_id}\n"
    if customer_tier != 'standard':
        response += f"**Customer Tier:** {customer_tier.upper()}\n"
    response += "\n"
    
    # Priority-based messaging
    if category_info['priority'] == 'CRITICAL':
        response += ("🚨 **CRITICAL ISSUE** - I understand this is an extremely urgent matter. "
                    "You are being immediately connected to our priority response team.\n\n")
        response += f"⚡ **Expected wait time:** < {category_info['sla_minutes']} minutes\n"
        response += f"📞 **Emergency line:** {category_info['escalation_line']}\n"
        response += "🔒 **Security verification:** May be required for your protection\n"
    elif category_info['priority'] == 'HIGH':
        response += ("⚡ I understand this needs urgent attention. I'm connecting you "
                    "with a specialist from our {department} team.\n\n".format(department=category_info['department']))
        response += f"🕐 **Expected wait time:** {category_info['sla_minutes']} minutes\n"
        response += f"📞 **Direct line:** {category_info['escalation_line']}\n"
    else:
        response += ("I'll connect you with a specialist from our {department} team "
                    "who can provide expert assistance with your inquiry.\n\n".format(department=category_info['department']))
        response += f"🕐 **Expected wait time:** {category_info['sla_minutes']} minutes\n"
        response += f"📞 **Contact line:** {category_info['escalation_line']}\n"
    
    # Add context for the human agent
    response += f"\n**Agent Reference:**\n"
    response += f"- Customer ID: {customer_id}\n"
    response += f"- Tier: {customer_tier}\n"
    response += f"- Category: {category}\n"
    if user_message:
        truncated_message = user_message[:150] + "..." if len(user_message) > 150 else user_message
        response += f"- Query: {truncated_message}\n"
    
    # Update context with escalation
    if 'previous_escalations' not in session_data:
        session_data['previous_escalations'] = 0
    session_data['previous_escalations'] += 1
    
    logger.info("Escalation triggered", 
               category=category,
               priority=category_info['priority'], 
               reason=reason, 
               escalation_id=escalation_id,
               customer_tier=customer_tier,
               customer_id=customer_id)
    
    return response

def _format_no_escalation_response(ctx: RunContext[Dict[str, Any]]) -> str:
    """Format response when no escalation is needed."""
    session_data = ctx.deps or {}
    user_profile = session_data.get('user_profile', {})
    customer_tier = user_profile.get('tier', 'standard')
    
    base_response = ("I can continue helping you with your inquiry. If at any point you'd prefer to "
                    "speak with a human representative, just let me know and I'll be happy to connect you.")
    
    if customer_tier in ['vip', 'premier']:
        base_response += ("\n\n💎 As a valued {tier} customer, you also have access to our "
                         "dedicated customer service line at +852 2233 3900 for immediate assistance.".format(tier=customer_tier.title()))
    
    return base_response

async def analyze_sentiment(ctx: RunContext[Dict[str, Any]], message: str) -> str:
    """Analyze message sentiment to help with escalation decisions.
    
    Args:
        ctx: PydanticAI run context with dependencies
        message: User message to analyze
        
    Returns:
        Sentiment analysis result
    """
    try:
        # Simple sentiment analysis patterns
        negative_patterns = [
            r'(?i)(terrible|awful|horrible|worst|hate|angry|furious)',
            r'(?i)(useless|pathetic|ridiculous|stupid|waste)',
            r'(?i)(frustrated|annoyed|disappointed|upset)',
        ]
        
        positive_patterns = [
            r'(?i)(excellent|great|wonderful|fantastic|love|amazing)',
            r'(?i)(helpful|satisfied|pleased|happy|good)',
            r'(?i)(thank you|thanks|appreciate)',
        ]
        
        negative_count = sum(1 for pattern in negative_patterns if re.search(pattern, message))
        positive_count = sum(1 for pattern in positive_patterns if re.search(pattern, message))
        
        if negative_count > positive_count and negative_count >= 2:
            return "NEGATIVE"
        elif positive_count > negative_count:
            return "POSITIVE"
        else:
            return "NEUTRAL"
            
    except Exception as e:
        logger.error("Error in sentiment analysis", error=str(e))
        return "NEUTRAL" 