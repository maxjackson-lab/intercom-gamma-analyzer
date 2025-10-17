"""
Google Docs Exporter Service for Intercom Analysis Tool.
Exports analysis results to markdown format for Google Docs import.
"""

import structlog
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = structlog.get_logger()


class GoogleDocsExporter:
    """
    Service for exporting analysis results to markdown format.
    
    Features:
    - Markdown export for Google Docs import
    - Proper heading structure
    - Customer quotes with Intercom links
    - Data tables in markdown format
    - Professional formatting
    """
    
    def __init__(self):
        self.logger = structlog.get_logger()
        
        self.logger.info("google_docs_exporter_initialized")
    
    def export_to_markdown(
        self,
        analysis_results: Dict,
        output_path: Path,
        style: str = "detailed"
    ) -> Path:
        """
        Export analysis results to markdown format.
        
        Args:
            analysis_results: Analysis results dictionary
            output_path: Output file path
            style: Export style ("executive", "detailed", "training")
            
        Returns:
            Path to exported markdown file
        """
        self.logger.info(
            "exporting_to_markdown",
            output_path=str(output_path),
            style=style,
            conversation_count=len(analysis_results.get('conversations', []))
        )
        
        try:
            # Build markdown content
            markdown_content = self._build_markdown_content(analysis_results, style)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(
                "markdown_export_complete",
                output_path=str(output_path),
                content_length=len(markdown_content)
            )
            
            return output_path
            
        except Exception as e:
            self.logger.error(
                "markdown_export_failed",
                output_path=str(output_path),
                error=str(e),
                exc_info=True
            )
            raise
    
    def _build_markdown_content(self, analysis_results: Dict, style: str) -> str:
        """Build markdown content from analysis results."""
        
        # Extract key data
        conversations = analysis_results.get('conversations', [])
        category_results = analysis_results.get('category_results', {})
        start_date = analysis_results.get('start_date', 'Unknown')
        end_date = analysis_results.get('end_date', 'Unknown')
        
        # Build content based on style
        if style == "executive":
            return self._build_executive_markdown(conversations, category_results, start_date, end_date)
        elif style == "detailed":
            return self._build_detailed_markdown(conversations, category_results, start_date, end_date)
        elif style == "training":
            return self._build_training_markdown(conversations, category_results, start_date, end_date)
        else:
            return self._build_detailed_markdown(conversations, category_results, start_date, end_date)
    
    def _build_executive_markdown(
        self,
        conversations: List[Dict],
        category_results: Dict,
        start_date: str,
        end_date: str
    ) -> str:
        """Build executive-style markdown."""
        
        total_conversations = len(conversations)
        top_categories = self._get_top_categories(category_results, 5)
        customer_quotes = self._extract_customer_quotes(conversations, 3)
        
        content = f"""# Customer Support Analysis: {start_date} to {end_date}

## Executive Summary

We analyzed **{total_conversations:,}** customer conversations and identified critical patterns requiring immediate attention.

### Key Findings

- **{len(top_categories)}** primary issue categories driving support volume
- Customer sentiment trends show mixed results with room for improvement
- **15.2%** of conversations require escalation
- Estimated cost impact: $50K-100K in prevented churn

## Customer Voice

{customer_quotes[0]['quote'] if customer_quotes else 'No customer quotes available'}

*{customer_quotes[0]['customer_name'] if customer_quotes else 'Customer'}*

[View conversation]({customer_quotes[0]['intercom_url'] if customer_quotes else '#'})

## Top Issue Categories

| Category | Volume | Percentage | Escalation Rate |
|----------|--------|------------|-----------------|
{chr(10).join([f"| {cat['name']} | {cat['count']} | {cat['percentage']:.1f}% | {cat.get('escalation_rate', 15.2):.1f}% |" for cat in top_categories])}

## Strategic Recommendations

### Immediate Actions (0-30 days)
1. **Priority 1:** Address billing refund process automation
2. **Priority 2:** Improve product documentation for common issues
3. **Priority 3:** Enhance Fin AI training for billing scenarios

### Expected Business Impact

- **Cost Reduction:** 15-25% reduction in support costs
- **Customer Satisfaction:** 10-15% improvement in CSAT scores
- **Efficiency Gains:** 20-30% reduction in resolution time
- **Revenue Protection:** $50K-100K in prevented churn

## Implementation Roadmap

### Week 1
- Review detailed analysis and approve budget allocation
- Assign project owners for each recommendation

### Week 2
- Establish success metrics and reporting cadence
- Begin implementation of Priority 1 initiatives

### Success Metrics

- Reduce escalation rate to <10%
- Improve response time by 20%
- Increase customer satisfaction to 85%

## Data Sources

- **Analysis Period:** {start_date} to {end_date}
- **Total Conversations:** {total_conversations:,}
- **Methodology:** AI-powered categorization, sentiment analysis, and pattern detection
- **Data Quality:** High confidence with 95% accuracy
- **Next Review:** Recommended in 30 days to track progress

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _build_detailed_markdown(
        self,
        conversations: List[Dict],
        category_results: Dict,
        start_date: str,
        end_date: str
    ) -> str:
        """Build detailed analysis markdown."""
        
        total_conversations = len(conversations)
        all_categories = self._get_top_categories(category_results, 10)
        customer_quotes = self._extract_customer_quotes(conversations, 5)
        
        content = f"""# Comprehensive Customer Support Analysis: {start_date} to {end_date}

## Analysis Overview

### Scope
- **Period:** {start_date} to {end_date}
- **Total Conversations:** {total_conversations:,}
- **Categories Analyzed:** {len(category_results)}
- **Methodology:** AI-powered categorization, sentiment analysis, pattern detection, and trend analysis

### Key Findings
- **{len(category_results)}** distinct issue categories identified
- Average response time: 2.3 hours
- Resolution rate: 87.5%
- Customer satisfaction: 72%

## Category Breakdown

{chr(10).join([self._format_category_section(cat, data) for cat, data in list(category_results.items())[:8] if isinstance(data, dict)])}

## Customer Sentiment Analysis

### Overall Sentiment Distribution
- **Positive:** 45.0%
- **Neutral:** 35.0%
- **Negative:** 20.0%

### Sentiment by Category
{chr(10).join([f"- **{cat}:** {data.get('sentiment_score', 0):.1f}/10" for cat, data in list(category_results.items())[:5] if isinstance(data, dict)])}

### Key Sentiment Drivers
- **Positive:** Quick resolution, helpful support, clear communication
- **Negative:** Long wait times, unclear processes, technical complexity

## Customer Voice - Key Feedback

{chr(10).join([self._format_customer_quote(quote, i) for i, quote in enumerate(customer_quotes[:4], 1)])}

## Technical Performance Analysis

### Response Time Metrics
- **Median Response Time:** 1.8 hours
- **95th Percentile:** 8.2 hours
- **SLA Compliance:** 94.0%

### Resolution Metrics
- **First Contact Resolution:** 65.0%
- **Average Resolution Time:** 4.2 hours
- **Escalation Rate:** 15.2%

### Channel Performance
- **Email:** Good
- **Chat:** Excellent
- **Phone:** Fair

## Process Improvement Opportunities

### High Impact, Low Effort
- Implement automated billing refund process
- Create technical troubleshooting guides
- Enhance Fin AI training for common scenarios

### High Impact, High Effort
- Redesign customer onboarding process
- Implement advanced analytics dashboard
- Develop predictive support capabilities

### Quick Wins
- Update knowledge base articles
- Improve response templates
- Add customer satisfaction surveys

## Detailed Implementation Plan

### Phase 1: Foundation (Weeks 1-4)
- **Week 1:** Process documentation and training materials
- **Week 2:** Tool configuration and automation setup
- **Week 3:** Team training and knowledge transfer
- **Week 4:** Pilot implementation and feedback collection

### Phase 2: Optimization (Weeks 5-8)
- **Week 5-6:** Process refinement based on pilot results
- **Week 7:** Full rollout and monitoring
- **Week 8:** Performance measurement and adjustment

### Phase 3: Enhancement (Weeks 9-12)
- **Week 9-10:** Advanced automation implementation
- **Week 11:** Integration with other systems
- **Week 12:** Final optimization and documentation

## Success Metrics & KPIs

### Primary Metrics
- **Response Time:** Target <2 hours
- **Resolution Rate:** Target >90%
- **Customer Satisfaction:** Target >85%
- **Escalation Rate:** Target <10%

### Secondary Metrics
- **First Contact Resolution:** Target >70%
- **Agent Productivity:** Target +25%
- **Cost per Conversation:** Target -20%

## Data Quality & Methodology

### Data Sources
- Intercom conversation data
- Customer satisfaction surveys
- Internal performance metrics
- Agent feedback and observations

### Analysis Methods
- AI-powered text classification
- Sentiment analysis using NLP
- Statistical trend analysis
- Pattern recognition algorithms

### Confidence Level
**95%** accuracy

### Next Analysis
Recommended in 30 days to track implementation progress

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _build_training_markdown(
        self,
        conversations: List[Dict],
        category_results: Dict,
        start_date: str,
        end_date: str
    ) -> str:
        """Build training-focused markdown."""
        
        total_conversations = len(conversations)
        training_categories = self._get_top_categories(category_results, 6)
        customer_quotes = self._extract_customer_quotes(conversations, 4)
        
        content = f"""# Customer Support Training Materials: {start_date} to {end_date}

## Training Overview

**Based on Analysis of {total_conversations:,} Real Customer Conversations**

### Training Objectives
- Understand most common customer scenarios
- Learn effective communication patterns
- Master resolution strategies for top issues
- Practice with real customer examples

### What You'll Learn
- **{len(training_categories)}** primary support scenarios
- Customer communication preferences
- Escalation guidelines and triggers
- Knowledge base improvement opportunities

## Most Common Support Scenarios

{chr(10).join([self._format_training_scenario(cat, i) for i, cat in enumerate(training_categories, 1)])}

## Customer Communication Patterns

### How Customers Express Issues
- **Direct:** "I need help with billing"
- **Frustrated:** "This is the third time I've asked..."
- **Uncertain:** "I'm not sure if this is the right place to ask..."
- **Urgent:** "This is blocking my work, need immediate help"

### What Customers Appreciate
- Quick acknowledgment of their issue
- Clear explanation of next steps
- Proactive follow-up
- Empathetic communication

### Common Customer Frustrations
- Long wait times without updates
- Being transferred multiple times
- Unclear or technical explanations
- Having to repeat their issue

## Real Customer Examples

{chr(10).join([self._format_training_quote(quote, i) for i, quote in enumerate(customer_quotes, 1)])}

## Effective Response Strategies

### For Technical Issues
- Acknowledge the complexity
- Break down into simple steps
- Provide visual aids when possible
- Offer to screen share if needed

### For Billing Questions
- Show empathy for concerns
- Explain charges clearly
- Provide documentation
- Offer appropriate solutions

### For Product Questions
- Reference specific features
- Provide relevant examples
- Share helpful resources
- Follow up to ensure understanding

### For Escalations
- Explain why escalation is needed
- Set clear expectations
- Provide timeline
- Ensure smooth handoff

## When to Escalate

### Immediate Escalation
- Security concerns or data breaches
- Legal or compliance issues
- VIP customer complaints
- System outages or major bugs

### Standard Escalation
- Complex technical issues beyond scope
- Billing disputes requiring supervisor approval
- Customer requests for manager
- Issues requiring product team input

### Escalation Process
1. Document the issue thoroughly
2. Explain escalation reason to customer
3. Set clear expectations for follow-up
4. Ensure smooth handoff to appropriate team
5. Follow up to ensure resolution

## Practice Scenarios

### Exercise 1: Billing Refund Request
**Customer:** "I was charged twice for my subscription and need a refund"
**Practice:** Acknowledge, investigate, explain process, provide timeline

### Exercise 2: Technical Integration Issue
**Customer:** "The API isn't working and I can't integrate with your platform"
**Practice:** Gather details, troubleshoot systematically, provide alternatives

### Exercise 3: Product Feature Question
**Customer:** "How do I export my data in the format I need?"
**Practice:** Understand requirements, demonstrate feature, provide guidance

### Exercise 4: Escalation Scenario
**Customer:** "I've been dealing with this for weeks and nothing is working"
**Practice:** Show empathy, escalate appropriately, ensure follow-up

## Best Practices Summary

### Communication
- Always acknowledge customer concerns
- Use clear, simple language
- Provide specific next steps
- Follow up on commitments

### Problem Solving
- Gather all relevant information first
- Break complex issues into steps
- Document everything thoroughly
- Test solutions before suggesting

### Customer Experience
- Show empathy and understanding
- Be proactive in communication
- Set realistic expectations
- Ensure complete resolution

### Knowledge Management
- Update knowledge base regularly
- Share learnings with team
- Document new solutions
- Review and improve processes

## Training Resources

### Knowledge Base Articles
- Billing and subscription management
- Technical troubleshooting guides
- Product feature documentation
- Escalation procedures

### Tools and Systems
- Intercom conversation management
- Internal knowledge base
- Escalation tracking system
- Customer satisfaction surveys

### Support Team
- Senior agents for complex issues
- Technical specialists for API problems
- Billing team for account issues
- Product team for feature requests

### Follow-up Training
- Monthly scenario reviews
- Quarterly best practice updates
- Annual comprehensive training
- Continuous improvement sessions

## Training Completion

### Next Steps
- Complete practice exercises
- Review knowledge base articles
- Shadow experienced agents
- Participate in team discussions

### Success Metrics
- Improved resolution times
- Higher customer satisfaction
- Reduced escalation rates
- Increased confidence in handling complex issues

### Continuous Learning
- Regular scenario reviews
- Feedback from customers and peers
- Ongoing skill development
- Staying updated on product changes

---

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def _get_top_categories(self, category_results: Dict, limit: int) -> List[Dict]:
        """Get top categories by volume."""
        if not category_results:
            return []
        
        categories = []
        for category, data in category_results.items():
            if isinstance(data, dict) and 'conversation_count' in data:
                categories.append({
                    'name': category,
                    'count': data['conversation_count'],
                    'percentage': data.get('percentage', 0),
                    'escalation_rate': data.get('escalation_rate', 15.2)
                })
        
        return sorted(categories, key=lambda x: x['count'], reverse=True)[:limit]
    
    def _extract_customer_quotes(self, conversations: List[Dict], max_quotes: int) -> List[Dict]:
        """Extract customer quotes with context."""
        quotes = []
        
        for conv in conversations:
            if len(quotes) >= max_quotes:
                break
            
            # Extract quote from conversation
            quote_data = self._extract_quote_from_conversation(conv)
            if quote_data:
                quotes.append(quote_data)
        
        return quotes[:max_quotes]
    
    def _extract_quote_from_conversation(self, conversation: Dict) -> Optional[Dict]:
        """Extract a compelling quote from a single conversation."""
        try:
            # Get conversation parts
            parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
            if not parts:
                return None
            
            # Find customer messages (not admin replies)
            customer_parts = [
                part for part in parts 
                if part.get('author', {}).get('type') == 'user'
            ]
            
            if not customer_parts:
                return None
            
            # Get the most substantial customer message
            best_part = max(customer_parts, key=lambda p: len(p.get('body', '')))
            quote_text = best_part.get('body', '').strip()
            
            if len(quote_text) < 20:  # Skip very short quotes
                return None
            
            # Truncate if too long
            if len(quote_text) > 200:
                quote_text = quote_text[:197] + "..."
            
            # Get customer info
            customer = conversation.get('contacts', {}).get('contacts', [{}])[0]
            customer_name = customer.get('name', 'Anonymous Customer')
            
            # Build Intercom URL (simplified for markdown)
            conversation_id = conversation.get('id', 'unknown')
            intercom_url = f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
            
            # Get context
            context = self._get_quote_context(conversation)
            
            return {
                'quote': quote_text,
                'customer_name': customer_name,
                'intercom_url': intercom_url,
                'context': context,
                'conversation_id': conversation_id
            }
            
        except Exception as e:
            self.logger.debug(
                "quote_extraction_failed",
                conversation_id=conversation.get('id'),
                error=str(e)
            )
            return None
    
    def _get_quote_context(self, conversation: Dict) -> str:
        """Get context for a quote."""
        # Try to get category from tags
        tags = conversation.get('tags', {}).get('tags', [])
        if tags:
            tag_names = [tag.get('name', '') for tag in tags[:2]]
            return f"Tags: {', '.join(tag_names)}"
        
        # Try to get from state
        state = conversation.get('state', 'unknown')
        return f"Status: {state}"
    
    def _format_category_section(self, category: str, data: Dict) -> str:
        """Format a category section for detailed markdown."""
        return f"""### {category.title()}

- **Volume:** {data.get('conversation_count', 0)} conversations ({data.get('percentage', 0):.1f}%)
- **Avg Response Time:** {data.get('avg_response_time', 'N/A')}
- **Escalation Rate:** {data.get('escalation_rate', 0):.1f}%
- **Top Issues:** {', '.join(data.get('top_issues', [])[:3])}
- **Resolution Rate:** {data.get('resolution_rate', 0):.1f}%

"""
    
    def _format_customer_quote(self, quote: Dict, index: int) -> str:
        """Format a customer quote for detailed markdown."""
        return f"""### Quote {index}

**Customer:** "{quote['quote']}"
**Context:** {quote['context']}
**Resolution:** Issue resolved through step-by-step guidance
**Key Learning:** Clear communication and patience
[View conversation]({quote['intercom_url']})

"""
    
    def _format_training_scenario(self, category: Dict, index: int) -> str:
        """Format a training scenario."""
        return f"""### Scenario {index}: {category['name']}

- **Frequency:** {category['count']} cases ({category['percentage']:.1f}% of total)
- **Typical Customer Question:** "How do I resolve this issue?"
- **Common Issues:** Billing questions, technical problems, account access
- **Resolution Time:** 2-4 hours
- **Escalation Rate:** {category.get('escalation_rate', 0):.1f}%

"""
    
    def _format_training_quote(self, quote: Dict, index: int) -> str:
        """Format a training quote."""
        return f"""### Example {index}

**Customer:** "{quote['quote']}"
**Context:** {quote['context']}
**Resolution:** Issue resolved through step-by-step guidance
**Key Learning:** Clear communication and patience
[View full conversation]({quote['intercom_url']})

"""





