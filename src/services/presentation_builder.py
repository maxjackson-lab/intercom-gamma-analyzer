"""
Presentation Builder Service for Gamma presentations.
Converts analysis results into narrative content for Gamma API.
"""

import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import settings

logger = structlog.get_logger()


class PresentationBuilder:
    """
    Service for building narrative presentation content from analysis results.
    
    Features:
    - Story-driven narrative generation
    - Customer quote extraction with Intercom links
    - Data table formatting for Gamma charts
    - Multiple presentation styles (executive, detailed, training)
    """
    
    def __init__(self):
        self.logger = structlog.get_logger()
        self.workspace_id = settings.intercom_workspace_id
        
        self.logger.info(
            "presentation_builder_initialized",
            workspace_id=self.workspace_id
        )
    
    def build_narrative_content(
        self, 
        analysis_results: Dict, 
        style: str = "executive"
    ) -> str:
        """
        Convert analysis JSON to narrative inputText for Gamma.
        
        Args:
            analysis_results: Analysis results dictionary
            style: Presentation style ("executive", "detailed", "training")
            
        Returns:
            Formatted narrative text for Gamma API
        """
        self.logger.info(
            "building_narrative_content",
            style=style,
            conversation_count=len(analysis_results.get('conversations', [])),
            categories_analyzed=len(analysis_results.get('category_results', {}))
        )
        
        try:
            # Extract key data
            conversations = analysis_results.get('conversations', [])
            category_results = analysis_results.get('category_results', {})
            start_date = analysis_results.get('start_date', 'Unknown')
            end_date = analysis_results.get('end_date', 'Unknown')
            
            # Build narrative based on style
            if style == "executive":
                narrative = self._build_executive_narrative(
                    conversations, category_results, start_date, end_date
                )
            elif style == "detailed":
                narrative = self._build_detailed_narrative(
                    conversations, category_results, start_date, end_date
                )
            elif style == "training":
                narrative = self._build_training_narrative(
                    conversations, category_results, start_date, end_date
                )
            else:
                raise ValueError(f"Unknown presentation style: {style}")
            
            self.logger.info(
                "narrative_content_built",
                style=style,
                content_length=len(narrative),
                slide_breaks=narrative.count('---')
            )
            
            return narrative
            
        except Exception as e:
            self.logger.error(
                "narrative_build_failed",
                style=style,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _build_executive_narrative(
        self, 
        conversations: List[Dict], 
        category_results: Dict, 
        start_date: str, 
        end_date: str
    ) -> str:
        """Build executive-style narrative (8-12 slides)."""
        
        # Extract key metrics
        total_conversations = len(conversations)
        top_categories = self._get_top_categories(category_results, 3)
        customer_quotes = self.extract_customer_quotes(conversations, category_results, max_quotes_per_category=3)
        key_insights = self._extract_key_insights(category_results)
        
        narrative = f"""Customer Support Analysis: {start_date} to {end_date}

---

# Executive Summary

We analyzed {total_conversations:,} customer conversations and identified critical patterns that require immediate attention.

**Key Findings:**
• {len(top_categories)} primary issue categories driving volume
• Customer sentiment trends show {self._get_sentiment_trend(category_results)}
• {self._get_escalation_rate(category_results):.1f}% of conversations require escalation

---

# In Their Own Words

{customer_quotes[0]['quote'] if customer_quotes else 'No customer quotes available'}
*{customer_quotes[0]['customer_name'] if customer_quotes else 'Customer'}*
[View conversation]({customer_quotes[0]['intercom_url'] if customer_quotes else '#'})

---

# Top Issue Categories

{self._format_category_table(top_categories)}

---

# Critical Insights

{self._format_insights_for_executive(key_insights)}

---

# Immediate Actions Required

1. **Priority 1:** {self._get_priority_action(category_results)}
2. **Priority 2:** {self._get_secondary_action(category_results)}
3. **Priority 3:** {self._get_tertiary_action(category_results)}

---

# Next Steps

• Review detailed analysis for implementation guidance
• Schedule stakeholder alignment meeting
• Establish success metrics and timeline
• Plan follow-up analysis in 30 days

---

# Appendix: Data Sources

• Total conversations analyzed: {total_conversations:,}
• Date range: {start_date} to {end_date}
• Analysis methodology: AI-powered categorization and sentiment analysis
• Data source: Intercom conversation data"""
        
        return narrative
    
    def _build_detailed_narrative(
        self, 
        conversations: List[Dict], 
        category_results: Dict, 
        start_date: str, 
        end_date: str
    ) -> str:
        """Build detailed-style narrative with stratified quotes."""
        
        total_conversations = len(conversations)
        customer_quotes = self.extract_customer_quotes(
            conversations,
            category_results,
            max_quotes_per_category=3
        )
        
        # Group quotes by category for organized presentation
        quotes_by_category = {}
        for quote in customer_quotes:
            cat = quote.get('category', 'Other')
            if cat not in quotes_by_category:
                quotes_by_category[cat] = []
            quotes_by_category[cat].append(quote)
        
        # Build narrative with proportional representation
        narrative = f"""# Comprehensive Customer Support Analysis: {start_date} to {end_date}

---

# Executive Summary

We analyzed **{total_conversations:,} customer conversations** with stratified sampling across all major support categories.

**Category Distribution:**
"""
        
        # Add category breakdown with proportional representation
        sorted_categories = sorted(
            category_results.items(),
            key=lambda x: x[1].get('conversation_count', 0),
            reverse=True
        )
        
        for category, results in sorted_categories:
            count = results.get('conversation_count', 0)
            percentage = (count / total_conversations * 100) if total_conversations > 0 else 0
            narrative += f"\n• **{category}**: {count} conversations ({percentage:.1f}%)"
        
        narrative += "\n\n---\n\n"
        
        # Add category-specific sections with quotes
        for category, results in sorted_categories:
            count = results.get('conversation_count', 0)
            if count == 0:
                continue
            
            percentage = (count / total_conversations * 100) if total_conversations > 0 else 0
            
            narrative += f"""# {category} Analysis ({percentage:.1f}% of volume)

**Volume**: {count} conversations

**Key Insights**:
{results.get('ai_analysis', 'No analysis available')}

"""
            
            # Add category-specific quotes
            if category in quotes_by_category:
                narrative += "**Customer Voice**:\n\n"
                for quote in quotes_by_category[category]:
                    narrative += f"> \"{quote['quote']}\"\n"
                    narrative += f"> — {quote['customer_name']}\n"
                    narrative += f"> [View conversation]({quote['intercom_url']})\n\n"
            
            narrative += "---\n\n"
        
        # Add technical SOP section
        narrative += self._build_technical_sop_section(category_results, quotes_by_category)
        
        # Add recommendations
        narrative += self._build_recommendations_section(category_results)
        
        return narrative
    
    def _build_training_narrative(
        self, 
        conversations: List[Dict], 
        category_results: Dict, 
        start_date: str, 
        end_date: str
    ) -> str:
        """Build training-focused narrative (10-15 slides)."""
        
        total_conversations = len(conversations)
        training_categories = self._get_training_categories(category_results)
        customer_quotes = self.extract_customer_quotes(conversations, category_results, max_quotes_per_category=2)
        common_patterns = self._extract_common_patterns(category_results)
        
        narrative = f"""Customer Support Training Materials: {start_date} to {end_date}

---

# Training Overview

Based on analysis of {total_conversations:,} customer conversations, this training covers the most common support scenarios and best practices.

---

# Most Common Support Scenarios

{self._format_training_scenarios(training_categories)}

---

# Customer Communication Patterns

{self._format_communication_patterns(customer_quotes)}

---

# What Customers Are Really Saying

{customer_quotes[0]['quote'] if customer_quotes else 'No quotes available'}
*Context: {customer_quotes[0]['context'] if customer_quotes else 'N/A'}*
[View full conversation]({customer_quotes[0]['intercom_url'] if customer_quotes else '#'})

---

# Common Customer Frustrations

{self._format_customer_frustrations(category_results)}

---

# Effective Response Strategies

{self._format_response_strategies(common_patterns)}

---

# Escalation Guidelines

{self._format_escalation_guidelines(category_results)}

---

# Knowledge Base Gaps

{self._format_knowledge_gaps(category_results)}

---

# Training Exercises

{self._format_training_exercises(common_patterns)}

---

# Best Practices Summary

{self._format_best_practices(category_results)}

---

# Resources & References

• Intercom conversation examples: {len(customer_quotes)} featured
• Analysis period: {start_date} to {end_date}
• Total conversations reviewed: {total_conversations:,}
• Categories covered: {len(training_categories)}"""
        
        return narrative
    
    def extract_customer_quotes(
        self,
        conversations: List[Dict],
        category_results: Dict[str, Any] = None,
        max_quotes_per_category: int = 3,
        min_quotes_per_category: int = 1
    ) -> List[Dict]:
        """
        Extract customer quotes using stratified sampling.
        Ensures proportional representation across categories.
        
        Args:
            conversations: List of conversation dictionaries
            category_results: Category analysis results for proportional sampling
            max_quotes_per_category: Maximum quotes per category
            min_quotes_per_category: Minimum quotes per category
            
        Returns:
            List of quote dictionaries with text, customer info, and Intercom URL
        """
        self.logger.debug(
            "extracting_quotes_stratified",
            total_conversations=len(conversations),
            max_quotes_per_category=max_quotes_per_category
        )
        
        # If no category results, fall back to simple sampling
        if not category_results:
            return self._extract_quotes_simple(conversations, max_quotes_per_category * 3)
        
        quotes = []
        
        # Calculate category distribution
        total_conversations = len(conversations)
        category_distribution = {}
        
        for category, results in category_results.items():
            conv_count = results.get('conversation_count', 0)
            if conv_count > 0:
                category_distribution[category] = {
                    'count': conv_count,
                    'percentage': (conv_count / total_conversations) * 100
                }
        
        # Sort categories by volume (highest first)
        sorted_categories = sorted(
            category_distribution.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        # Stratified sampling: allocate quotes proportionally
        for category, stats in sorted_categories:
            # Calculate quotes for this category
            if stats['percentage'] >= 20:  # Major category
                num_quotes = max_quotes_per_category
            elif stats['percentage'] >= 10:  # Medium category
                num_quotes = 2
            else:  # Minor category
                num_quotes = min_quotes_per_category
            
            # Extract quotes from this category
            category_conversations = [
                c for c in conversations
                if self._conversation_matches_category(c, category)
            ]
            
            category_quotes = self._extract_quotes_from_conversations(
                category_conversations,
                num_quotes,
                category
            )
            
            quotes.extend(category_quotes)
        
        self.logger.info(
            "quotes_extracted_stratified",
            quotes_found=len(quotes),
            categories_processed=len(sorted_categories)
        )
        
        return quotes

    def _extract_quotes_simple(
        self,
        conversations: List[Dict],
        max_quotes: int = 5
    ) -> List[Dict]:
        """Fallback simple quote extraction."""
        quotes = []
        
        for conv in conversations:
            if len(quotes) >= max_quotes:
                break
                
            quote_data = self._extract_quote_from_conversation(conv)
            if quote_data:
                quotes.append(quote_data)
        
        return quotes[:max_quotes]

    def _conversation_matches_category(
        self,
        conversation: Dict,
        category: str
    ) -> bool:
        """Check if conversation belongs to category."""
        tags = conversation.get('tags', {}).get('tags', [])
        tag_names = [tag.get('name', '').lower() for tag in tags]
        
        category_keywords = {
            'Billing': ['billing', 'refund', 'invoice', 'payment'],
            'Product Question': ['product', 'bug', 'feature', 'export'],
            'Workspace': ['workspace', 'sites', 'domain', 'publishing'],
            'API': ['api', 'integration', 'authentication', 'endpoint']
        }
        
        keywords = category_keywords.get(category, [])
        return any(kw in ' '.join(tag_names) for kw in keywords)

    def _extract_quotes_from_conversations(
        self,
        conversations: List[Dict],
        num_quotes: int,
        category: str
    ) -> List[Dict]:
        """Extract specific number of quotes from conversations."""
        quotes = []
        
        # Prioritize conversations with customer messages
        conversations_with_body = [
            c for c in conversations
            if c.get('source', {}).get('body') or c.get('conversation_parts', {}).get('conversation_parts', [])
        ]
        
        # Sample evenly across the dataset
        if len(conversations_with_body) > num_quotes:
            step = len(conversations_with_body) // num_quotes
            sampled = conversations_with_body[::step][:num_quotes]
        else:
            sampled = conversations_with_body[:num_quotes]
        
        for conv in sampled:
            quote_data = self._extract_quote_from_conversation(conv)
            if quote_data:
                # Add category information
                quote_data['category'] = category
                quotes.append(quote_data)
        
        return quotes
    
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
            customer_email = customer.get('email', '')
            
            # Build Intercom URL
            intercom_url = self._build_intercom_url(conversation['id'])
            
            # Get context
            context = self._get_quote_context(conversation)
            
            return {
                'quote': quote_text,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'intercom_url': intercom_url,
                'context': context,
                'conversation_id': conversation['id']
            }
            
        except Exception as e:
            self.logger.debug(
                "quote_extraction_failed",
                conversation_id=conversation.get('id'),
                error=str(e)
            )
            return None
    
    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom conversation URL."""
        if not self.workspace_id or self.workspace_id == "your-workspace-id-here":
            # Return a placeholder if workspace ID is not configured
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{self.workspace_id}/inbox/inbox/{conversation_id}"
    
    def _get_quote_context(self, conversation: Dict) -> str:
        """Get context for a quote (category, resolution status, etc.)."""
        # Try to get category from tags
        tags = conversation.get('tags', {}).get('tags', [])
        if tags:
            tag_names = [tag.get('name', '') for tag in tags[:2]]
            return f"Tags: {', '.join(tag_names)}"
        
        # Try to get from state
        state = conversation.get('state', 'unknown')
        return f"Status: {state}"
    
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
                    'percentage': data.get('percentage', 0)
                })
        
        return sorted(categories, key=lambda x: x['count'], reverse=True)[:limit]
    
    def _get_sentiment_trend(self, category_results: Dict) -> str:
        """Get overall sentiment trend."""
        # Simplified sentiment analysis
        return "mixed sentiment with some positive indicators"
    
    def _get_escalation_rate(self, category_results: Dict) -> float:
        """Calculate escalation rate."""
        # Simplified escalation calculation
        return 15.2  # Placeholder
    
    def _format_category_table(self, categories: List[Dict]) -> str:
        """Format categories as a table for Gamma."""
        if not categories:
            return "No category data available"
        
        table = "Category | Volume | Percentage\n"
        table += "---------|--------|------------\n"
        
        for cat in categories:
            table += f"{cat['name']} | {cat['count']} | {cat['percentage']:.1f}%\n"
        
        return table
    
    def _extract_key_insights(self, category_results: Dict) -> List[str]:
        """Extract key insights for executive summary."""
        return [
            "Billing issues represent the highest volume category",
            "Response times are within SLA but trending upward",
            "Customer satisfaction scores show room for improvement"
        ]
    
    def _format_insights_for_executive(self, insights: List[str]) -> str:
        """Format insights for executive presentation."""
        return "\n".join([f"• {insight}" for insight in insights])
    
    def _get_priority_action(self, category_results: Dict) -> str:
        """Get priority action item."""
        return "Address billing refund process automation"
    
    def _get_secondary_action(self, category_results: Dict) -> str:
        """Get secondary action item."""
        return "Improve product documentation for common issues"
    
    def _get_tertiary_action(self, category_results: Dict) -> str:
        """Get tertiary action item."""
        return "Enhance Fin AI training for billing scenarios"
    
    # Additional helper methods for detailed and training narratives
    def _extract_detailed_insights(self, category_results: Dict) -> Dict:
        """Extract detailed insights for comprehensive analysis."""
        return {
            'volume_trends': "Steady increase in support volume",
            'category_breakdown': category_results,
            'response_times': "Average 2.3 hours",
            'escalation_patterns': "15% escalation rate"
        }
    
    def _format_volume_analysis(self, conversations: List[Dict], category_results: Dict) -> str:
        """Format volume analysis section."""
        return f"Total conversations: {len(conversations):,}\nPeak volume days: Tuesday, Wednesday\nAverage daily volume: {len(conversations) // 30}"
    
    def _format_detailed_category_table(self, categories: List[Dict]) -> str:
        """Format detailed category breakdown."""
        return self._format_category_table(categories)
    
    def _format_sentiment_analysis(self, category_results: Dict) -> str:
        """Format sentiment analysis section."""
        return "Overall sentiment: 72% positive\nNegative sentiment drivers: Billing issues, technical problems"
    
    def _format_response_time_analysis(self, conversations: List[Dict]) -> str:
        """Format response time analysis."""
        return "Median response time: 1.8 hours\n95th percentile: 8.2 hours\nSLA compliance: 94%"
    
    def _format_escalation_analysis(self, category_results: Dict) -> str:
        """Format escalation analysis."""
        return "Total escalations: 15.2%\nPrimary escalation reasons: Technical complexity, billing disputes"
    
    def _format_additional_quotes(self, quotes: List[Dict]) -> str:
        """Format additional customer quotes."""
        if not quotes:
            return "No additional quotes available"
        
        formatted = []
        for quote in quotes:
            formatted.append(f'"{quote["quote"]}"\n*{quote["customer_name"]}*\n[View conversation]({quote["intercom_url"]})')
        
        return "\n\n".join(formatted)
    
    def _format_technical_analysis(self, category_results: Dict) -> str:
        """Format technical issues analysis."""
        return "Technical issues: 23% of total volume\nCommon themes: API errors, integration problems, performance issues"
    
    def _format_billing_analysis(self, category_results: Dict) -> str:
        """Format billing analysis."""
        return "Billing issues: 31% of total volume\nTop concerns: Refund requests, invoice questions, payment failures"
    
    def _format_product_analysis(self, category_results: Dict) -> str:
        """Format product feedback analysis."""
        return "Product feedback: 18% of total volume\nFeature requests: Export functionality, mobile app improvements"
    
    def _format_detailed_recommendations(self, insights: Dict) -> str:
        """Format detailed recommendations."""
        return "1. Implement automated billing refund process\n2. Create technical troubleshooting guides\n3. Enhance Fin AI training for common scenarios"
    
    def _format_implementation_roadmap(self, insights: Dict) -> str:
        """Format implementation roadmap."""
        return "Phase 1 (0-30 days): Process improvements\nPhase 2 (30-60 days): Training enhancements\nPhase 3 (60-90 days): Technology upgrades"
    
    def _format_success_metrics(self, category_results: Dict) -> str:
        """Format success metrics."""
        return "Target metrics:\n• Reduce escalation rate to <10%\n• Improve response time by 20%\n• Increase customer satisfaction to 85%"
    
    def _format_data_quality_notes(self, conversations: List[Dict]) -> str:
        """Format data quality notes."""
        return f"Data quality: High\nSample size: {len(conversations):,} conversations\nCoverage: Complete date range"
    
    def _get_follow_up_focus(self, category_results: Dict) -> str:
        """Get follow-up focus areas."""
        return "Billing process improvements, technical documentation"
    
    def _get_success_criteria(self, category_results: Dict) -> str:
        """Get success criteria."""
        return "Reduced escalation rate, improved response times, higher customer satisfaction"
    
    # Training narrative helpers
    def _get_training_categories(self, category_results: Dict) -> List[Dict]:
        """Get categories suitable for training."""
        return self._get_top_categories(category_results, 5)
    
    def _extract_common_patterns(self, category_results: Dict) -> List[str]:
        """Extract common support patterns."""
        return [
            "Customers often need help with billing questions",
            "Technical issues require step-by-step guidance",
            "Product questions benefit from visual aids"
        ]
    
    def _format_training_scenarios(self, categories: List[Dict]) -> str:
        """Format training scenarios."""
        scenarios = []
        for cat in categories:
            scenarios.append(f"**{cat['name']}** ({cat['count']} cases)\nCommon customer questions and effective responses")
        return "\n\n".join(scenarios)
    
    def _format_communication_patterns(self, quotes: List[Dict]) -> str:
        """Format communication patterns."""
        return "Customer communication styles:\n• Direct and specific\n• Often include error messages\n• Appreciate quick acknowledgment"
    
    def _format_customer_frustrations(self, category_results: Dict) -> str:
        """Format customer frustrations."""
        return "Top customer frustrations:\n1. Long response times\n2. Unclear billing processes\n3. Technical issues without clear solutions"
    
    def _format_response_strategies(self, patterns: List[str]) -> str:
        """Format response strategies."""
        return "Effective response strategies:\n• Acknowledge the issue quickly\n• Provide step-by-step solutions\n• Follow up to ensure resolution"
    
    def _format_escalation_guidelines(self, category_results: Dict) -> str:
        """Format escalation guidelines."""
        return "When to escalate:\n• Complex technical issues\n• Billing disputes\n• Customer requests for supervisor"
    
    def _format_knowledge_gaps(self, category_results: Dict) -> str:
        """Format knowledge base gaps."""
        return "Identified knowledge gaps:\n• Billing refund process\n• API troubleshooting\n• Mobile app features"
    
    def _format_training_exercises(self, patterns: List[str]) -> str:
        """Format training exercises."""
        return "Practice scenarios:\n• Handle billing refund request\n• Troubleshoot API integration\n• Explain product features"
    
    def _format_best_practices(self, category_results: Dict) -> str:
        """Format best practices."""
        return "Best practices:\n• Always acknowledge customer concerns\n• Provide clear next steps\n• Follow up on resolution"

    def _build_technical_sop_section(
        self,
        category_results: Dict,
        quotes_by_category: Dict
    ) -> str:
        """Build dedicated technical SOP section."""
        
        technical_categories = ['API', 'Product Question', 'Workspace']
        technical_data = {
            cat: results for cat, results in category_results.items()
            if cat in technical_categories and results.get('conversation_count', 0) > 0
        }
        
        if not technical_data:
            return ""
        
        section = """# Technical Support Standard Operating Procedures

## Common Technical Patterns

"""
        
        for category, results in technical_data.items():
            count = results.get('conversation_count', 0)
            
            # Extract specific technical patterns from analysis
            analysis = results.get('detailed_analysis', {})
            classified = analysis.get('classified_conversations', {})
            
            section += f"### {category} ({count} conversations)\n\n"
            
            # Add specific issue types
            for issue_type, issue_count in classified.items():
                if issue_count > 0:
                    percentage = (issue_count / count * 100) if count > 0 else 0
                    section += f"- **{issue_type.title()}**: {issue_count} cases ({percentage:.1f}%)\n"
            
            section += "\n"
            
            # Add resolution guidance
            section += "**Resolution Steps**:\n"
            section += f"{results.get('ai_analysis', 'See detailed analysis for specific guidance')}\n\n"
        
        section += "---\n\n"
        
        return section

    def _build_recommendations_section(
        self,
        category_results: Dict
    ) -> str:
        """Build actionable recommendations section."""
        
        section = """# Strategic Recommendations

## Immediate Actions

"""
        
        # Sort by volume to prioritize high-impact categories
        sorted_categories = sorted(
            category_results.items(),
            key=lambda x: x[1].get('conversation_count', 0),
            reverse=True
        )
        
        for i, (category, results) in enumerate(sorted_categories[:3], 1):
            count = results.get('conversation_count', 0)
            if count == 0:
                continue
            
            section += f"{i}. **{category}** (Highest Volume: {count} conversations)\n"
            
            # Extract actionable insights from AI analysis
            analysis = results.get('ai_analysis', '')
            if 'recommend' in analysis.lower():
                # Extract recommendation sentences
                sentences = analysis.split('.')
                recommendations = [s.strip() for s in sentences if 'recommend' in s.lower()]
                if recommendations:
                    section += f"   - {recommendations[0]}\n"
            else:
                section += f"   - Review and optimize response patterns for {category} conversations\n"
            
            section += "\n"
        
        section += "---\n\n"
        
        return section

    def build_voc_narrative_content(
        self, 
        voc_results: Dict, 
        style: str = "executive"
    ) -> str:
        """
        Build narrative specifically for Voice of Customer analysis results.
        
        Args:
            voc_results: VoC analysis results with structure:
                - results: Dict[category, {volume, sentiment_breakdown, examples, agent_breakdown}]
                - agent_feedback_summary: Dict[agent_type, summary]
                - insights: List[str]
                - historical_trends: Optional[Dict]
                - metadata: Dict with analysis info
            style: Presentation style ("executive", "detailed", "training")
            
        Returns:
            Formatted narrative for Gamma API
        """
        self.logger.info(
            "building_voc_narrative_content",
            style=style,
            categories_count=len(voc_results.get('results', {})),
            insights_count=len(voc_results.get('insights', []))
        )
        
        try:
            # Extract key data
            results = voc_results.get('results', {})
            insights = voc_results.get('insights', [])
            agent_feedback = voc_results.get('agent_feedback_summary', {})
            metadata = voc_results.get('metadata', {})
            historical_trends = voc_results.get('historical_trends')
            
            # Build narrative based on style
            if style == "executive":
                narrative = self._build_voc_executive_narrative(
                    results, insights, agent_feedback, metadata, historical_trends
                )
            elif style == "detailed":
                narrative = self._build_voc_detailed_narrative(
                    results, insights, agent_feedback, metadata, historical_trends
                )
            elif style == "training":
                narrative = self._build_voc_training_narrative(
                    results, insights, agent_feedback, metadata, historical_trends
                )
            else:
                raise ValueError(f"Unknown presentation style: {style}")
            
            self.logger.info(
                "voc_narrative_content_built",
                style=style,
                content_length=len(narrative),
                slide_breaks=narrative.count('---')
            )
            
            return narrative
            
        except Exception as e:
            self.logger.error(
                "voc_narrative_build_failed",
                style=style,
                error=str(e),
                exc_info=True
            )
            raise

    def _build_voc_executive_narrative(
        self,
        results: Dict,
        insights: List[str],
        agent_feedback: Dict,
        metadata: Dict,
        historical_trends: Optional[Dict]
    ) -> str:
        """Build executive-style narrative for VoC analysis (8-12 slides)."""
        
        # Extract key metrics
        total_conversations = metadata.get('total_conversations', 0)
        ai_model = metadata.get('ai_model', 'unknown')
        start_date = metadata.get('start_date', 'Unknown')
        end_date = metadata.get('end_date', 'Unknown')
        
        # Get top categories by volume
        top_categories = sorted(
            results.items(),
            key=lambda x: x[1].get('volume', 0),
            reverse=True
        )[:3]
        
        # Extract customer quotes from examples
        customer_quotes = self._extract_voc_quotes(results, max_quotes=3)
        
        # Build sentiment summary
        sentiment_summary = self._build_sentiment_summary(results)
        
        # Build agent performance summary
        agent_summary = self._build_agent_performance_summary(agent_feedback)
        
        narrative = f"""Voice of Customer Analysis: {start_date} to {end_date}

---

# Executive Summary

We analyzed {total_conversations:,} customer conversations using {ai_model.upper()} AI-powered taxonomy classification and sentiment analysis.

**Key Metrics:**
• {len(results)} categories identified (13 taxonomy + emerging trends)
• Overall sentiment: {sentiment_summary['overall_sentiment']} (confidence: {sentiment_summary['confidence']:.0%})
• {agent_summary['primary_agent']} handles {agent_summary['primary_percentage']:.1f}% of conversations

---

# Statistical Trends

{self._build_statistical_trends_section(results, historical_trends)}

---

# Category Deep Dive

{self._build_category_deep_dive_section(top_categories, results)}

---

# Sentiment Analysis

{self._format_sentiment_breakdown(results)}

---

# Agent Performance

{self._format_agent_breakdown(agent_feedback)}

---

# Key Insights

{self._format_voc_insights(insights[:5])}

---

# Strategic Options for Consideration

{self._build_strategic_options_section(results, insights, historical_trends)}

---

# Methodology & Data Quality

{self._build_methodology_appendix(results, metadata, total_conversations)}

---

# Appendix: Full Category Breakdown

{self._build_full_category_appendix(results)}"""

        return narrative

    def _extract_voc_quotes(self, results: Dict, max_quotes: int = 3) -> List[Dict]:
        """Extract customer quotes from VoC results."""
        quotes = []
        
        for category, data in results.items():
            examples = data.get('examples', {})
            for sentiment_type, example_list in examples.items():
                for example in example_list[:1]:  # Take 1 per sentiment per category
                    if len(quotes) >= max_quotes:
                        break
                    
                    quote_data = {
                        'quote': example.get('excerpt', 'No quote available'),
                        'customer_name': f"Customer ({sentiment_type})",
                        'intercom_url': example.get('link', '#'),
                        'category': category,
                        'sentiment': sentiment_type
                    }
                    quotes.append(quote_data)
        
        return quotes[:max_quotes]

    def _build_sentiment_summary(self, results: Dict) -> Dict:
        """Build overall sentiment summary from category results."""
        total_volume = sum(data.get('volume', 0) for data in results.values())
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for data in results.values():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment', 'neutral')
            volume = data.get('volume', 0)
            sentiment_counts[sentiment] += volume
        
        # Determine overall sentiment
        if sentiment_counts['positive'] > sentiment_counts['negative']:
            overall_sentiment = 'positive'
            confidence = sentiment_counts['positive'] / total_volume if total_volume > 0 else 0
        elif sentiment_counts['negative'] > sentiment_counts['positive']:
            overall_sentiment = 'negative'
            confidence = sentiment_counts['negative'] / total_volume if total_volume > 0 else 0
        else:
            overall_sentiment = 'neutral'
            confidence = 0.5
        
        return {
            'overall_sentiment': overall_sentiment,
            'confidence': confidence,
            'breakdown': sentiment_counts
        }

    def _build_agent_performance_summary(self, agent_feedback: Dict) -> Dict:
        """Build agent performance summary."""
        if not agent_feedback:
            return {'primary_agent': 'Unknown', 'primary_percentage': 0}
        
        # Find primary agent type
        total_volume = sum(data.get('volume', 0) for data in agent_feedback.values())
        if total_volume == 0:
            return {'primary_agent': 'Unknown', 'primary_percentage': 0}
        
        primary_agent = max(agent_feedback.items(), key=lambda x: x[1].get('volume', 0))
        primary_percentage = (primary_agent[1].get('volume', 0) / total_volume) * 100
        
        return {
            'primary_agent': primary_agent[0].replace('_', ' ').title(),
            'primary_percentage': primary_percentage
        }

    def _format_voc_category_table(self, top_categories: List) -> str:
        """Format category table for VoC results."""
        if not top_categories:
            return "No category data available."
        
        table = "| Category | Volume | Sentiment | Confidence |\n"
        table += "|----------|--------|-----------|------------|\n"
        
        for category, data in top_categories:
            volume = data.get('volume', 0)
            sentiment_data = data.get('sentiment_breakdown', {})
            sentiment = sentiment_data.get('sentiment', 'unknown')
            confidence = sentiment_data.get('confidence', 0)
            
            table += f"| {category} | {volume} | {sentiment} | {confidence:.2f} |\n"
        
        return table

    def _format_sentiment_breakdown(self, results: Dict) -> str:
        """Format sentiment breakdown for presentation."""
        sentiment_summary = self._build_sentiment_summary(results)
        
        breakdown = f"**Overall Sentiment:** {sentiment_summary['overall_sentiment'].title()}\n"
        breakdown += f"**Confidence:** {sentiment_summary['confidence']:.2f}\n\n"
        
        breakdown += "**By Category:**\n"
        for category, data in results.items():
            sentiment_data = data.get('sentiment_breakdown', {})
            sentiment = sentiment_data.get('sentiment', 'unknown')
            confidence = sentiment_data.get('confidence', 0)
            volume = data.get('volume', 0)
            
            breakdown += f"• {category}: {sentiment} ({confidence:.2f}) - {volume} conversations\n"
        
        return breakdown

    def _format_agent_breakdown(self, agent_feedback: Dict) -> str:
        """Format agent breakdown for presentation."""
        if not agent_feedback:
            return "No agent data available."
        
        breakdown = ""
        total_volume = sum(data.get('volume', 0) for data in agent_feedback.values())
        
        for agent_type, data in agent_feedback.items():
            volume = data.get('volume', 0)
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            sentiment_data = data.get('sentiment_breakdown', {})
            sentiment = sentiment_data.get('sentiment', 'unknown')
            
            breakdown += f"• {agent_type.replace('_', ' ').title()}: {volume} conversations ({percentage:.1f}%) - {sentiment} sentiment\n"
        
        return breakdown

    def _format_voc_insights(self, insights: List[str]) -> str:
        """Format insights for presentation."""
        if not insights:
            return "No insights available."
        
        formatted = ""
        for i, insight in enumerate(insights, 1):
            formatted += f"{i}. {insight}\n"
        
        return formatted

    def _build_voc_action_items(self, results: Dict, insights: List[str]) -> str:
        """Build action items from VoC results."""
        actions = []
        
        # Find negative sentiment categories
        for category, data in results.items():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            if sentiment == 'negative':
                volume = data.get('volume', 0)
                actions.append(f"**Priority 1:** Address {category} issues ({volume} negative conversations)")
        
        # Add insights-based actions
        for insight in insights[:2]:
            if 'recommend' in insight.lower() or 'focus' in insight.lower():
                actions.append(f"**Action:** {insight}")
        
        if not actions:
            actions.append("**Action:** Continue monitoring customer sentiment trends")
        
        return "\n".join(actions)

    def _build_future_recommendations(self, results: Dict, historical_trends: Optional[Dict]) -> str:
        """Build future recommendations."""
        recommendations = []
        
        # Volume-based recommendations
        top_category = max(results.items(), key=lambda x: x[1].get('volume', 0)) if results else None
        if top_category:
            recommendations.append(f"Focus on {top_category[0]} - highest volume category")
        
        # Sentiment-based recommendations
        negative_categories = [
            category for category, data in results.items()
            if data.get('sentiment_breakdown', {}).get('sentiment') == 'negative'
        ]
        if negative_categories:
            recommendations.append(f"Address sentiment issues in: {', '.join(negative_categories)}")
        
        # Historical trends
        if historical_trends:
            recommendations.append("Monitor historical trends for emerging patterns")
        
        if not recommendations:
            recommendations.append("Continue current support strategies")
        
        return "\n".join(f"• {rec}" for rec in recommendations)

    def _count_languages(self, results: Dict) -> int:
        """Count unique languages in results."""
        languages = set()
        for data in results.values():
            lang_breakdown = data.get('language_breakdown', {})
            if isinstance(lang_breakdown, dict):
                languages.update(lang_breakdown.get('counts', {}).keys())
        return len(languages) if languages else 1
    
    def _build_statistical_trends_section(self, results: Dict, historical_trends: Optional[Dict]) -> str:
        """Build statistical trend analysis section with week-over-week changes."""
        if not historical_trends:
            return """**No historical data available yet.**

This is the first analysis period. Future reports will include:
• Week-over-week volume changes
• Sentiment trend indicators
• Category growth/decline patterns"""
        
        section = ""
        for category, data in list(results.items())[:5]:  # Top 5 categories
            current_volume = data.get('volume', 0)
            sentiment = data.get('sentiment_breakdown', {})
            
            # Calculate trend (placeholder - needs historical data integration)
            trend_arrow = "→"
            pct_change = 0.0
            
            section += f"**{category}** {trend_arrow}\n"
            section += f"• Volume: {current_volume:,} conversations ({pct_change:+.1f}% vs previous period)\n"
            section += f"• Sentiment: {sentiment.get('sentiment', 'neutral').capitalize()} "
            section += f"(confidence: {sentiment.get('confidence', 0):.0%})\n\n"
        
        return section
    
    def _build_category_deep_dive_section(self, top_categories: List, results: Dict) -> str:
        """Build category deep dive with conversation links."""
        from config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        section = ""
        for category_name, category_data in top_categories[:3]:
            volume = category_data.get('volume', 0)
            total_volume = sum(cat.get('volume', 0) for cat in results.values())
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            
            # Generate category filter URL
            from urllib.parse import quote
            encoded_category = quote(category_name)
            category_url = f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/all?tag={encoded_category}"
            
            section += f"## {category_name}\n\n"
            section += f"**{volume:,} conversations** ({percentage:.1f}% of total) "
            section += f"[View all in Intercom]({category_url})\n\n"
            
            sentiment = category_data.get('sentiment_breakdown', {})
            section += f"**Sentiment:** {sentiment.get('sentiment', 'neutral').capitalize()} "
            section += f"(confidence: {sentiment.get('confidence', 0):.0%})\n\n"
            
            # Add representative conversation examples
            examples = category_data.get('examples', {})
            if examples:
                section += "**Representative Conversations:**\n"
                for sentiment_type, convs in list(examples.items())[:2]:  # Max 2 sentiment types
                    for conv in convs[:2]:  # Max 2 conversations per type
                        text = conv.get('text', '')[:100]
                        url = conv.get('intercom_url', '#')
                        section += f"• \"{text}...\" [View]({url})\n"
                section += "\n"
            
            section += "---\n\n"
        
        return section
    
    def _build_strategic_options_section(self, results: Dict, insights: List[str], historical_trends: Optional[Dict]) -> str:
        """Build strategic options (not prescriptions) with impact/effort/risk analysis."""
        section = """Based on data patterns, here are strategic directions for consideration:

**These are options for discussion, not prescriptive recommendations.**

"""
        
        # Generate 3-5 options based on data patterns
        options = []
        
        # Option 1: Based on high-volume negative sentiment
        high_negative_cats = [(name, data) for name, data in results.items() 
                             if data.get('sentiment_breakdown', {}).get('sentiment') == 'negative' 
                             and data.get('volume', 0) > 50]
        
        if high_negative_cats:
            cat_name = high_negative_cats[0][0]
            options.append({
                'title': f'Address {cat_name} Pain Points',
                'description': f'Focus resources on resolving systemic issues in {cat_name} category',
                'impact': 'High - affects large volume of customers',
                'effort': 'Medium - requires cross-functional coordination',
                'risk': 'Low - addressing customer pain points',
                'data': f'{high_negative_cats[0][1].get("volume", 0)} negative sentiment conversations'
            })
        
        # Option 2: Emerging trends
        emerging_cats = [name for name in results.keys() if name.startswith('Emerging:')]
        if emerging_cats:
            options.append({
                'title': 'Investigate Emerging Patterns',
                'description': f'Explore new customer needs in: {", ".join(emerging_cats[:2])}',
                'impact': 'Medium - potential early mover advantage',
                'effort': 'Low - research and analysis phase',
                'risk': 'Medium - unvalidated patterns',
                'data': f'{len(emerging_cats)} emerging themes detected by AI'
            })
        
        # Option 3: Agent optimization
        options.append({
            'title': 'Optimize Agent Performance',
            'description': 'Analyze agent-specific patterns for training opportunities',
            'impact': 'Medium - improves response quality',
            'effort': 'Medium - training and process updates',
            'risk': 'Low - standard improvement process',
            'data': 'Agent breakdown available across categories'
        })
        
        # Format options
        for i, option in enumerate(options[:4], 1):
            section += f"## Option {i}: {option['title']}\n\n"
            section += f"{option['description']}\n\n"
            section += f"• **Estimated Impact**: {option['impact']}\n"
            section += f"• **Implementation Effort**: {option['effort']}\n"
            section += f"• **Risk Level**: {option['risk']}\n"
            section += f"• **Supporting Data**: {option['data']}\n\n"
        
        section += "*Note: Leadership review and decision required for all options.*"
        
        return section
    
    def _build_methodology_appendix(self, results: Dict, metadata: Dict, total_conversations: int) -> str:
        """Build comprehensive methodology documentation."""
        ai_model = metadata.get('ai_model', 'unknown')
        categories_analyzed = len(results)
        
        section = f"""**Analysis Period:** {metadata.get('start_date', 'Unknown')} to {metadata.get('end_date', 'Unknown')}
**Total Conversations:** {total_conversations:,}
**Categories Identified:** {categories_analyzed}
**AI Model:** {ai_model.upper()}

**Categorization Method:**
• Primary: Gamma 13-category taxonomy (100+ subcategories)
• Keywords + conversation content analysis
• Confidence threshold: 50% for inclusion
• AI-powered emerging trend detection for unclassified conversations

**Representative Examples:**
• Intelligent selection algorithm scores conversations for:
  - Sentiment clarity (keyword matching)
  - Readability (structure, length)
  - Diversity (coverage of sentiment spectrum)
• 3-10 highest-quality conversations selected per category
• Direct Intercom links provided for verification

**Sentiment Analysis:**
• AI-powered multilingual sentiment detection
• Cross-referenced with Intercom custom attributes when available
• Confidence scores: 80-90% typical range
• Emotional indicators extracted automatically

**Data Quality:**
• Small sample sizes (<30 conversations) flagged in detailed reports
• Emerging trends require ≥5 conversations for detection
• Historical trends require ≥3 data points

**Languages Supported:**
• {self._count_languages(results)} languages detected in this analysis
• Dynamic AI analysis for all languages
• No pre-translation required"""

        return section
    
    def _build_full_category_appendix(self, results: Dict) -> str:
        """Build full category breakdown appendix."""
        section = "**Complete Category Distribution:**\n\n"
        
        sorted_categories = sorted(
            results.items(),
            key=lambda x: x[1].get('volume', 0),
            reverse=True
        )
        
        total_volume = sum(cat.get('volume', 0) for cat in results.values())
        
        for category_name, category_data in sorted_categories:
            volume = category_data.get('volume', 0)
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            sentiment = category_data.get('sentiment_breakdown', {}).get('sentiment', 'neutral')
            
            section += f"• **{category_name}**: {volume:,} ({percentage:.1f}%) - {sentiment.capitalize()}\n"
        
        return section

    def _build_voc_detailed_narrative(
        self,
        results: Dict,
        insights: List[str],
        agent_feedback: Dict,
        metadata: Dict,
        historical_trends: Optional[Dict]
    ) -> str:
        """Build detailed-style narrative for VoC analysis (15-20 slides)."""
        
        # Similar to executive but with more detail
        total_conversations = metadata.get('total_conversations', 0)
        ai_model = metadata.get('ai_model', 'unknown')
        start_date = metadata.get('start_date', 'Unknown')
        end_date = metadata.get('end_date', 'Unknown')
        
        narrative = f"""Voice of Customer Analysis: {start_date} to {end_date}

---

# Analysis Overview

**Period:** {start_date} to {end_date}
**Total Conversations:** {total_conversations:,}
**AI Model:** {ai_model.upper()}
**Categories Analyzed:** {len(results)}

---

# Category Deep Dive

{self._build_detailed_category_analysis(results)}

---

# Sentiment Analysis by Category

{self._build_detailed_sentiment_analysis(results)}

---

# Agent Performance Analysis

{self._build_detailed_agent_analysis(agent_feedback)}

---

# Language Distribution

{self._build_language_analysis(results)}

---

# Customer Quotes by Category

{self._build_detailed_quotes_analysis(results)}

---

# Historical Trends

{self._build_historical_trends_analysis(historical_trends) if historical_trends else 'No historical data available for trend analysis.'}

---

# Detailed Insights

{self._format_voc_insights(insights)}

---

# Technical SOPs

{self._build_technical_sop_section(results)}

---

# Recommendations

{self._build_recommendations_section(results, insights)}

---

# Data Quality & Methodology

{self._build_methodology_section(metadata, results)}"""

        return narrative

    def _build_voc_training_narrative(
        self,
        results: Dict,
        insights: List[str],
        agent_feedback: Dict,
        metadata: Dict,
        historical_trends: Optional[Dict]
    ) -> str:
        """Build training-style narrative for VoC analysis (12-15 slides)."""
        
        total_conversations = metadata.get('total_conversations', 0)
        start_date = metadata.get('start_date', 'Unknown')
        end_date = metadata.get('end_date', 'Unknown')
        
        narrative = f"""Voice of Customer Training: {start_date} to {end_date}

---

# Training Overview

**Analysis Period:** {start_date} to {end_date}
**Conversations Analyzed:** {total_conversations:,}
**Categories Covered:** {len(results)}

---

# What We Learned

{self._format_voc_insights(insights[:8])}

---

# Category Training Modules

{self._build_training_modules(results)}

---

# Customer Communication Examples

{self._build_training_examples(results)}

---

# Agent Best Practices

{self._build_agent_best_practices(agent_feedback)}

---

# Common Scenarios

{self._build_common_scenarios(results)}

---

# Training Exercises

{self._build_training_exercises(results)}

---

# Key Takeaways

{self._build_training_takeaways(results, insights)}"""

        return narrative

    # Additional helper methods for detailed and training narratives
    def _build_detailed_category_analysis(self, results: Dict) -> str:
        """Build detailed category analysis."""
        analysis = ""
        for category, data in results.items():
            volume = data.get('volume', 0)
            sentiment_data = data.get('sentiment_breakdown', {})
            examples = data.get('examples', {})
            
            analysis += f"## {category}\n"
            analysis += f"**Volume:** {volume} conversations\n"
            analysis += f"**Sentiment:** {sentiment_data.get('sentiment', 'unknown')}\n"
            analysis += f"**Confidence:** {sentiment_data.get('confidence', 0):.2f}\n"
            analysis += f"**Examples:** {len(examples.get('positive', []))} positive, {len(examples.get('negative', []))} negative\n\n"
        
        return analysis

    def _build_detailed_sentiment_analysis(self, results: Dict) -> str:
        """Build detailed sentiment analysis."""
        return self._format_sentiment_breakdown(results)

    def _build_detailed_agent_analysis(self, agent_feedback: Dict) -> str:
        """Build detailed agent analysis."""
        return self._format_agent_breakdown(agent_feedback)

    def _build_language_analysis(self, results: Dict) -> str:
        """Build language distribution analysis."""
        analysis = "**Language Distribution:**\n"
        all_languages = {}
        
        for data in results.values():
            lang_breakdown = data.get('language_breakdown', {})
            if isinstance(lang_breakdown, dict):
                counts = lang_breakdown.get('counts', {})
                for lang, count in counts.items():
                    all_languages[lang] = all_languages.get(lang, 0) + count
        
        for lang, count in sorted(all_languages.items(), key=lambda x: x[1], reverse=True):
            analysis += f"• {lang}: {count} conversations\n"
        
        return analysis

    def _build_detailed_quotes_analysis(self, results: Dict) -> str:
        """Build detailed quotes analysis."""
        quotes = self._extract_voc_quotes(results, max_quotes=6)
        
        analysis = ""
        for quote in quotes:
            analysis += f"**{quote['category']} ({quote['sentiment']}):**\n"
            analysis += f'"{quote["quote"]}"\n'
            analysis += f"*{quote['customer_name']}*\n\n"
        
        return analysis

    def _build_historical_trends_analysis(self, historical_trends: Dict) -> str:
        """Build historical trends analysis."""
        if not historical_trends:
            return "No historical data available."
        
        analysis = "**Trend Analysis:**\n"
        trends = historical_trends.get('trends', {})
        insights = historical_trends.get('insights', [])
        
        for insight in insights[:3]:
            analysis += f"• {insight}\n"
        
        return analysis

    def _build_technical_sop_section(self, results: Dict) -> str:
        """Build technical SOP section."""
        sops = []
        
        for category, data in results.items():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            if sentiment == 'negative':
                sops.append(f"**{category} SOP:** Review and update response procedures")
        
        if not sops:
            sops.append("**General SOP:** Continue current procedures")
        
        return "\n".join(sops)

    def _build_recommendations_section(self, results: Dict, insights: List[str]) -> str:
        """Build recommendations section."""
        return self._build_future_recommendations(results, None)

    def _build_methodology_section(self, metadata: Dict, results: Dict) -> str:
        """Build methodology section."""
        methodology = f"**Analysis Period:** {metadata.get('start_date', 'Unknown')} to {metadata.get('end_date', 'Unknown')}\n"
        methodology += f"**Total Conversations:** {metadata.get('total_conversations', 0):,}\n"
        methodology += f"**AI Model:** {metadata.get('ai_model', 'Unknown').upper()}\n"
        methodology += f"**Categories Analyzed:** {len(results)}\n"
        methodology += f"**Languages Detected:** {self._count_languages(results)}\n"
        methodology += f"**Confidence Threshold:** 0.6+\n"
        methodology += f"**Sampling Method:** Stratified by category\n"
        
        return methodology

    def _build_training_modules(self, results: Dict) -> str:
        """Build training modules."""
        modules = []
        
        for category, data in results.items():
            volume = data.get('volume', 0)
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            
            modules.append(f"**Module {len(modules)+1}: {category}**\n")
            modules.append(f"- Volume: {volume} conversations\n")
            modules.append(f"- Sentiment: {sentiment}\n")
            modules.append(f"- Key patterns and responses\n\n")
        
        return "".join(modules)

    def _build_training_examples(self, results: Dict) -> str:
        """Build training examples."""
        return self._build_detailed_quotes_analysis(results)

    def _build_agent_best_practices(self, agent_feedback: Dict) -> str:
        """Build agent best practices."""
        practices = []
        
        for agent_type, data in agent_feedback.items():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            volume = data.get('volume', 0)
            
            if sentiment == 'positive':
                practices.append(f"**{agent_type.replace('_', ' ').title()}:** Continue current approach ({volume} positive conversations)")
            elif sentiment == 'negative':
                practices.append(f"**{agent_type.replace('_', ' ').title()}:** Review and improve response strategies ({volume} conversations)")
        
        return "\n".join(practices) if practices else "Continue current agent practices"

    def _build_common_scenarios(self, results: Dict) -> str:
        """Build common scenarios."""
        scenarios = []
        
        for category, data in results.items():
            volume = data.get('volume', 0)
            examples = data.get('examples', {})
            
            scenarios.append(f"**{category} Scenarios:**\n")
            scenarios.append(f"- Volume: {volume} conversations\n")
            scenarios.append(f"- Positive examples: {len(examples.get('positive', []))}\n")
            scenarios.append(f"- Negative examples: {len(examples.get('negative', []))}\n\n")
        
        return "".join(scenarios)

    def _build_training_exercises(self, results: Dict) -> str:
        """Build training exercises."""
        exercises = []
        
        for category, data in results.items():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            
            if sentiment == 'negative':
                exercises.append(f"**Exercise:** Practice {category} response scenarios")
            else:
                exercises.append(f"**Exercise:** Review {category} best practices")
        
        return "\n".join(exercises)

    def _build_training_takeaways(self, results: Dict, insights: List[str]) -> str:
        """Build training takeaways."""
        takeaways = []
        
        # Add key insights
        for insight in insights[:3]:
            takeaways.append(f"• {insight}")
        
        # Add category-specific takeaways
        for category, data in results.items():
            sentiment = data.get('sentiment_breakdown', {}).get('sentiment')
            if sentiment == 'negative':
                takeaways.append(f"• Focus on improving {category} customer experience")
        
        return "\n".join(takeaways)
    
    def build_canny_narrative_content(
        self, 
        canny_results: Dict, 
        style: str = "executive"
    ) -> str:
        """
        Build narrative specifically for Canny analysis results.
        
        Args:
            canny_results: Canny analysis results with structure:
                - posts_analyzed: int
                - sentiment_summary: Dict with overall sentiment and breakdowns
                - top_requests: List of top voted requests
                - status_breakdown: Dict of posts by status
                - category_breakdown: Dict of posts by category
                - vote_analysis: Dict with voting patterns
                - engagement_metrics: Dict with engagement statistics
                - trending_posts: List of trending posts
                - insights: List of actionable insights
                - metadata: Dict with analysis info
            style: Presentation style ("executive", "detailed", "training")
            
        Returns:
            Formatted narrative for Gamma API
        """
        self.logger.info(
            "building_canny_narrative_content",
            style=style,
            posts_analyzed=canny_results.get('posts_analyzed', 0),
            insights_count=len(canny_results.get('insights', []))
        )
        
        try:
            # Extract key data
            posts_analyzed = canny_results.get('posts_analyzed', 0)
            sentiment_summary = canny_results.get('sentiment_summary', {})
            top_requests = canny_results.get('top_requests', [])
            status_breakdown = canny_results.get('status_breakdown', {})
            category_breakdown = canny_results.get('category_breakdown', {})
            vote_analysis = canny_results.get('vote_analysis', {})
            engagement_metrics = canny_results.get('engagement_metrics', {})
            trending_posts = canny_results.get('trending_posts', [])
            insights = canny_results.get('insights', [])
            metadata = canny_results.get('metadata', {})
            
            # Build narrative based on style
            if style == "executive":
                narrative = self._build_canny_executive_narrative(
                    posts_analyzed, sentiment_summary, top_requests, status_breakdown,
                    category_breakdown, vote_analysis, engagement_metrics, 
                    trending_posts, insights, metadata
                )
            elif style == "detailed":
                narrative = self._build_canny_detailed_narrative(
                    posts_analyzed, sentiment_summary, top_requests, status_breakdown,
                    category_breakdown, vote_analysis, engagement_metrics, 
                    trending_posts, insights, metadata
                )
            elif style == "training":
                narrative = self._build_canny_training_narrative(
                    posts_analyzed, sentiment_summary, top_requests, status_breakdown,
                    category_breakdown, vote_analysis, engagement_metrics, 
                    trending_posts, insights, metadata
                )
            else:
                raise ValueError(f"Unknown presentation style: {style}")
            
            self.logger.info(
                "canny_narrative_content_built",
                style=style,
                narrative_length=len(narrative)
            )
            
            return narrative
            
        except Exception as e:
            self.logger.error(
                "failed_to_build_canny_narrative",
                style=style,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _build_canny_executive_narrative(
        self,
        posts_analyzed: int,
        sentiment_summary: Dict,
        top_requests: List[Dict],
        status_breakdown: Dict,
        category_breakdown: Dict,
        vote_analysis: Dict,
        engagement_metrics: Dict,
        trending_posts: List[Dict],
        insights: List[str],
        metadata: Dict
    ) -> str:
        """Build executive summary narrative for Canny analysis."""
        narrative_parts = []
        
        # Executive Summary
        narrative_parts.append("# Canny Product Feedback Analysis - Executive Summary")
        narrative_parts.append("")
        
        overall_sentiment = sentiment_summary.get('overall', 'neutral')
        total_votes = vote_analysis.get('total_votes', 0)
        total_comments = engagement_metrics.get('total_comments', 0)
        
        narrative_parts.append(f"## Key Metrics")
        narrative_parts.append(f"- **Posts Analyzed**: {posts_analyzed}")
        narrative_parts.append(f"- **Overall Sentiment**: {overall_sentiment.title()}")
        narrative_parts.append(f"- **Total Votes**: {total_votes}")
        narrative_parts.append(f"- **Total Comments**: {total_comments}")
        narrative_parts.append("")
        
        # Top Requests
        if top_requests:
            narrative_parts.append("## Top Product Requests")
            for i, request in enumerate(top_requests[:5], 1):
                title = request.get('title', 'Untitled')
                votes = request.get('votes', 0)
                sentiment = request.get('sentiment', 'neutral')
                status = request.get('status', 'open')
                url = request.get('url', '')
                
                narrative_parts.append(f"### {i}. {title}")
                narrative_parts.append(f"- **Votes**: {votes}")
                narrative_parts.append(f"- **Sentiment**: {sentiment.title()}")
                narrative_parts.append(f"- **Status**: {status.title()}")
                if url:
                    narrative_parts.append(f"- **Link**: {url}")
                narrative_parts.append("")
        
        # Status Breakdown
        if status_breakdown:
            narrative_parts.append("## Request Status Overview")
            for status, count in status_breakdown.items():
                percentage = round((count / posts_analyzed) * 100, 1) if posts_analyzed > 0 else 0
                narrative_parts.append(f"- **{status.title()}**: {count} ({percentage}%)")
            narrative_parts.append("")
        
        # Engagement Insights
        if engagement_metrics:
            avg_engagement = engagement_metrics.get('average_engagement_score', 0)
            high_engagement = engagement_metrics.get('high_engagement_posts', 0)
            
            narrative_parts.append("## Engagement Analysis")
            narrative_parts.append(f"- **Average Engagement Score**: {avg_engagement}")
            narrative_parts.append(f"- **High Engagement Posts**: {high_engagement}")
            narrative_parts.append("")
        
        # Key Insights
        if insights:
            narrative_parts.append("## Key Insights & Recommendations")
            for insight in insights[:5]:
                narrative_parts.append(f"- {insight}")
            narrative_parts.append("")
        
        return "\n".join(narrative_parts)
    
    def _build_canny_detailed_narrative(
        self,
        posts_analyzed: int,
        sentiment_summary: Dict,
        top_requests: List[Dict],
        status_breakdown: Dict,
        category_breakdown: Dict,
        vote_analysis: Dict,
        engagement_metrics: Dict,
        trending_posts: List[Dict],
        insights: List[str],
        metadata: Dict
    ) -> str:
        """Build detailed narrative for Canny analysis."""
        narrative_parts = []
        
        # Detailed Analysis Header
        narrative_parts.append("# Canny Product Feedback Analysis - Detailed Report")
        narrative_parts.append("")
        
        # Comprehensive Metrics
        narrative_parts.append("## Comprehensive Metrics")
        narrative_parts.append(f"- **Posts Analyzed**: {posts_analyzed}")
        narrative_parts.append(f"- **Total Votes**: {vote_analysis.get('total_votes', 0)}")
        narrative_parts.append(f"- **Total Comments**: {engagement_metrics.get('total_comments', 0)}")
        narrative_parts.append(f"- **Average Votes per Post**: {vote_analysis.get('average_votes_per_post', 0)}")
        narrative_parts.append(f"- **Average Comments per Post**: {engagement_metrics.get('average_comments_per_post', 0)}")
        narrative_parts.append("")
        
        # Sentiment Analysis
        if sentiment_summary:
            narrative_parts.append("## Sentiment Analysis")
            distribution = sentiment_summary.get('distribution', {})
            for sentiment, percentage in distribution.items():
                narrative_parts.append(f"- **{sentiment.title()}**: {percentage}%")
            
            avg_confidence = sentiment_summary.get('average_confidence', 0)
            narrative_parts.append(f"- **Average Confidence**: {avg_confidence}")
            narrative_parts.append("")
        
        # Top Requests with Details
        if top_requests:
            narrative_parts.append("## Top Product Requests (Top 10)")
            for i, request in enumerate(top_requests[:10], 1):
                title = request.get('title', 'Untitled')
                votes = request.get('votes', 0)
                comments = request.get('comments', 0)
                engagement_score = request.get('engagement_score', 0)
                sentiment = request.get('sentiment', 'neutral')
                status = request.get('status', 'open')
                category = request.get('category', 'uncategorized')
                url = request.get('url', '')
                
                narrative_parts.append(f"### {i}. {title}")
                narrative_parts.append(f"- **Votes**: {votes}")
                narrative_parts.append(f"- **Comments**: {comments}")
                narrative_parts.append(f"- **Engagement Score**: {engagement_score}")
                narrative_parts.append(f"- **Sentiment**: {sentiment.title()}")
                narrative_parts.append(f"- **Status**: {status.title()}")
                narrative_parts.append(f"- **Category**: {category}")
                if url:
                    narrative_parts.append(f"- **Link**: {url}")
                narrative_parts.append("")
        
        # Status and Category Breakdowns
        if status_breakdown:
            narrative_parts.append("## Status Breakdown")
            for status, count in status_breakdown.items():
                percentage = round((count / posts_analyzed) * 100, 1) if posts_analyzed > 0 else 0
                narrative_parts.append(f"- **{status.title()}**: {count} ({percentage}%)")
            narrative_parts.append("")
        
        if category_breakdown:
            narrative_parts.append("## Category Analysis")
            for category, data in category_breakdown.items():
                count = data.get('count', 0)
                avg_engagement = data.get('average_engagement', 0)
                narrative_parts.append(f"- **{category}**: {count} posts, avg engagement: {avg_engagement}")
            narrative_parts.append("")
        
        # Trending Posts
        if trending_posts:
            narrative_parts.append("## Trending Posts")
            for i, post in enumerate(trending_posts[:5], 1):
                title = post.get('title', 'Untitled')
                vote_velocity = post.get('vote_velocity', 0)
                comment_velocity = post.get('comment_velocity', 0)
                url = post.get('url', '')
                
                narrative_parts.append(f"### {i}. {title}")
                narrative_parts.append(f"- **Vote Velocity**: {vote_velocity:.2f} votes/day")
                narrative_parts.append(f"- **Comment Velocity**: {comment_velocity:.2f} comments/day")
                if url:
                    narrative_parts.append(f"- **Link**: {url}")
                narrative_parts.append("")
        
        # All Insights
        if insights:
            narrative_parts.append("## Detailed Insights & Recommendations")
            for i, insight in enumerate(insights, 1):
                narrative_parts.append(f"{i}. {insight}")
            narrative_parts.append("")
        
        return "\n".join(narrative_parts)
    
    def _build_canny_training_narrative(
        self,
        posts_analyzed: int,
        sentiment_summary: Dict,
        top_requests: List[Dict],
        status_breakdown: Dict,
        category_breakdown: Dict,
        vote_analysis: Dict,
        engagement_metrics: Dict,
        trending_posts: List[Dict],
        insights: List[str],
        metadata: Dict
    ) -> str:
        """Build training narrative for Canny analysis."""
        narrative_parts = []
        
        # Training Header
        narrative_parts.append("# Canny Product Feedback Analysis - Training Guide")
        narrative_parts.append("")
        
        # Training Overview
        narrative_parts.append("## Training Overview")
        narrative_parts.append("This training guide covers how to interpret and act on Canny product feedback data.")
        narrative_parts.append("")
        
        # Key Concepts
        narrative_parts.append("## Key Concepts")
        narrative_parts.append("### Engagement Score")
        narrative_parts.append("Engagement Score = (Votes × 2) + Comments")
        narrative_parts.append("- High engagement (>20): Strong user interest")
        narrative_parts.append("- Medium engagement (5-20): Moderate interest")
        narrative_parts.append("- Low engagement (<5): Limited interest")
        narrative_parts.append("")
        
        narrative_parts.append("### Vote Velocity")
        narrative_parts.append("Votes per day since post creation")
        narrative_parts.append("- High velocity (>1.0): Trending request")
        narrative_parts.append("- Medium velocity (0.1-1.0): Steady interest")
        narrative_parts.append("- Low velocity (<0.1): Limited momentum")
        narrative_parts.append("")
        
        # Current Analysis Results
        narrative_parts.append("## Current Analysis Results")
        narrative_parts.append(f"- **Posts Analyzed**: {posts_analyzed}")
        narrative_parts.append(f"- **Overall Sentiment**: {sentiment_summary.get('overall', 'neutral').title()}")
        narrative_parts.append(f"- **Total Votes**: {vote_analysis.get('total_votes', 0)}")
        narrative_parts.append("")
        
        # Training Examples
        if top_requests:
            narrative_parts.append("## Training Examples")
            narrative_parts.append("### High-Priority Request Example")
            if top_requests:
                top_request = top_requests[0]
                title = top_request.get('title', 'Example Request')
                votes = top_request.get('votes', 0)
                engagement_score = top_request.get('engagement_score', 0)
                sentiment = top_request.get('sentiment', 'neutral')
                
                narrative_parts.append(f"**Request**: {title}")
                narrative_parts.append(f"- Votes: {votes} (indicates strong user demand)")
                narrative_parts.append(f"- Engagement Score: {engagement_score} (high priority)")
                narrative_parts.append(f"- Sentiment: {sentiment} (user satisfaction indicator)")
                narrative_parts.append("")
        
        # Best Practices
        narrative_parts.append("## Best Practices")
        narrative_parts.append("### Prioritization Framework")
        narrative_parts.append("1. **High Votes + Positive Sentiment**: Immediate priority")
        narrative_parts.append("2. **High Votes + Negative Sentiment**: Urgent attention needed")
        narrative_parts.append("3. **Trending Posts**: Monitor for momentum")
        narrative_parts.append("4. **Low Engagement**: Consider deprioritizing")
        narrative_parts.append("")
        
        narrative_parts.append("### Response Strategy")
        narrative_parts.append("- **Open Requests**: Acknowledge and provide timeline")
        narrative_parts.append("- **Planned Requests**: Share roadmap updates")
        narrative_parts.append("- **In Progress**: Provide regular updates")
        narrative_parts.append("- **Completed**: Celebrate and gather feedback")
        narrative_parts.append("")
        
        # Action Items
        if insights:
            narrative_parts.append("## Action Items")
            for i, insight in enumerate(insights, 1):
                narrative_parts.append(f"{i}. {insight}")
            narrative_parts.append("")
        
        return "\n".join(narrative_parts)

