"""
Fin Metrics Calculator - Dual metric approach for transparency

Provides TWO ways to measure Fin performance:
1. Intercom-Compatible: Matches Intercom's native reporting (for validation)
2. Quality-Adjusted: Stricter criteria for true helpfulness (for honest assessment)

This allows comparison to Intercom reports while maintaining quality standards.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def calculate_dual_metrics(conversations: List[Dict]) -> Dict[str, Any]:
    """
    Calculate both Intercom-compatible and quality-adjusted Fin metrics.
    
    Args:
        conversations: List of Fin-involved conversations
        
    Returns:
        Dict with both metric sets and comparison
    """
    if not conversations:
        return {
            'intercom_compatible': _empty_metrics(),
            'quality_adjusted': _empty_metrics(),
            'comparison': {}
        }
    
    total = len(conversations)
    
    # Calculate Intercom-compatible metrics
    intercom_metrics = _calculate_intercom_compatible(conversations)
    
    # Calculate quality-adjusted metrics (existing strict criteria)
    quality_metrics = _calculate_quality_adjusted(conversations)
    
    # Calculate the gap
    comparison = {
        'deflection_gap': intercom_metrics['deflection_rate'] - quality_metrics['resolution_rate'],
        'deflection_gap_count': intercom_metrics['deflected_count'] - quality_metrics['resolved_count'],
        'interpretation': _interpret_gap(
            intercom_metrics['deflection_rate'],
            quality_metrics['resolution_rate']
        )
    }
    
    return {
        'intercom_compatible': intercom_metrics,
        'quality_adjusted': quality_metrics,
        'comparison': comparison,
        'total_conversations': total
    }


def _calculate_intercom_compatible(conversations: List[Dict]) -> Dict[str, Any]:
    """
    Calculate Intercom-compatible metrics (matches their native reporting).
    
    Deflection = Fin answered AND customer didn't escalate to human
    (Liberal criteria - similar to Intercom's)
    """
    total = len(conversations)
    deflected = []
    
    for conv in conversations:
        # Check if customer escalated to human
        # Intercom considers it "deflected" if no admin response
        admin_assignee_id = conv.get('admin_assignee_id')
        
        # Also check if customer explicitly requested human in text
        from src.utils.conversation_utils import extract_conversation_text
        text = extract_conversation_text(conv, clean_html=True).lower()
        
        escalation_phrases = [
            'speak to human', 'talk to agent', 'real person',
            'human support', 'talk to someone', 'speak to someone'
        ]
        requested_human = any(phrase in text for phrase in escalation_phrases)
        
        # Deflected = No admin AND customer didn't explicitly request human
        if not admin_assignee_id and not requested_human:
            deflected.append(conv)
    
    return {
        'deflected_count': len(deflected),
        'deflection_rate': round(len(deflected) / total * 100, 1) if total > 0 else 0,
        'definition': 'Fin answered and customer did not escalate to human support',
        'methodology': 'Intercom-compatible (liberal criteria)'
    }


def _calculate_quality_adjusted(conversations: List[Dict]) -> Dict[str, Any]:
    """
    Calculate quality-adjusted metrics (stricter criteria for true helpfulness).
    
    Resolution = Fin actually solved the problem (not just deflected)
    (Strict criteria - honest assessment of quality)
    """
    from src.services.fin_escalation_analyzer import is_fin_resolved
    
    total = len(conversations)
    resolved = [conv for conv in conversations if is_fin_resolved(conv)]
    
    return {
        'resolved_count': len(resolved),
        'resolution_rate': round(len(resolved) / total * 100, 1) if total > 0 else 0,
        'definition': 'Fin truly resolved: closed OR low effort, no admin, no bad rating',
        'methodology': 'Quality-adjusted (strict criteria for true helpfulness)'
    }


def _interpret_gap(deflection_rate: float, resolution_rate: float) -> str:
    """
    Interpret the gap between deflection and resolution rates.
    
    Args:
        deflection_rate: Intercom-compatible deflection %
        resolution_rate: Quality-adjusted resolution %
        
    Returns:
        Human-readable interpretation
    """
    gap = deflection_rate - resolution_rate
    
    if gap < 10:
        return f"Small gap ({gap:.1f}%) - Fin is genuinely helpful when it deflects"
    elif gap < 30:
        return f"Moderate gap ({gap:.1f}%) - Some deflections may not be true resolutions"
    elif gap < 50:
        return f"Significant gap ({gap:.1f}%) - Many customers stopped responding but may not be satisfied"
    else:
        return f"Large gap ({gap:.1f}%) - High deflection doesn't indicate true helpfulness"


def _empty_metrics() -> Dict[str, Any]:
    """Return empty metrics structure"""
    return {
        'deflected_count': 0,
        'deflection_rate': 0,
        'resolved_count': 0,
        'resolution_rate': 0,
        'definition': '',
        'methodology': ''
    }


def format_dual_metrics_markdown(metrics: Dict[str, Any]) -> str:
    """
    Format dual metrics for markdown output.
    
    Args:
        metrics: Output from calculate_dual_metrics()
        
    Returns:
        Formatted markdown string
    """
    intercom = metrics['intercom_compatible']
    quality = metrics['quality_adjusted']
    comparison = metrics['comparison']
    
    output = []
    
    output.append("### Fin Performance Metrics")
    output.append("")
    output.append("**Intercom-Compatible Metrics** (for validation against Intercom reports):")
    output.append(f"- Deflection Rate: {intercom['deflection_rate']}% ({intercom['deflected_count']:,} conversations)")
    output.append(f"- Definition: {intercom['definition']}")
    output.append("")
    
    output.append("**Quality-Adjusted Metrics** (stricter assessment of true helpfulness):")
    output.append(f"- Resolution Rate: {quality['resolution_rate']}% ({quality['resolved_count']:,} conversations)")
    output.append(f"- Definition: {quality['definition']}")
    output.append("")
    
    output.append("**Gap Analysis:**")
    output.append(f"- Deflection vs Resolution Gap: {comparison['deflection_gap']:.1f}%")
    output.append(f"- {comparison['interpretation']}")
    output.append(f"- {comparison['deflection_gap_count']:,} conversations: Customer stopped responding but issue may not be fully resolved")
    output.append("")
    
    return '\n'.join(output)

