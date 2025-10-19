"""
Prompt templates for Voice of Customer and trend analysis.
"""

from typing import Dict, List, Optional
from datetime import datetime

# Import story-driven prompts
from config.story_driven_prompts import StoryDrivenPrompts


class PromptTemplates:
    """Collection of prompt templates for different analysis modes."""
    
    @staticmethod
    def get_voice_of_customer_prompt(
        month: int,
        year: int,
        tier1_countries: List[str],
        intercom_data: str
    ) -> str:
        """Generate Voice of Customer analysis prompt."""
        month_name = datetime(year, month, 1).strftime("%B")
        
        return f"""# Voice of Customer Analysis - {month_name} {year}

You will receive a complete Intercom dataset with pre-computed statistics for {month_name} {year}. Create a comprehensive Voice of Customer analysis following the exact structure below.

**Data:** {intercom_data}

**ANALYSIS REQUIREMENTS:**
- Focus on Tier 1 countries: {', '.join(tier1_countries)}
- Use ONLY actual data - no estimates or approximations
- Include exact quotes with working Intercom conversation URLs
- Compare month-over-month trends where applicable
- Highlight both positive trends and areas needing attention
- Provide actionable insights for executive decision-making

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Voice of Customer | {month_name} Edition

Welcome to our monthly customer insights report!

As I move through this data, I will be focusing on our tier 1 countries that comprise our target audience. Target Audience = group of users we choose to serve better than anyone else.

## Tier 1 - Core Focus Countries

{{tier1_analysis}}

\\n---\\n

## By the Numbers

**Support Conversations:** {{total_conversations}} total customer interactions in {month_name}

**AI Resolution:** {{ai_resolution_rate}}% cases handled by AI without human intervention

**Response Time:** {{median_response_time}} median first response time

**Handling Time:** {{median_handling_time}} median time spent by a teammate working on a conversation

**Resolution Time:** {{median_resolution_time}} median time to close

**CSAT:** {{overall_csat}}% Customer Satisfaction Rating

{{month_over_month_analysis}}

\\n---\\n

## Top 3 Reasons for Contact

{{top_contact_reasons_analysis}}

\\n---\\n

## Top Billing Questions

{{billing_analysis}}

\\n---\\n

## Top 15 Product Questions

{{product_questions_analysis}}

\\n---\\n

## Top Account Questions

{{account_questions_analysis}}

\\n---\\n

## Trending {month_name} Friction Points

{{friction_points_analysis}}

\\n---\\n

## Support Happiness Quotes

{{customer_quotes}}

\\n---\\n

*Based on {{total_conversations}} conversations from {month_name} {year}*"""
    
    @staticmethod
    def get_trend_analysis_prompt(
        start_date: str,
        end_date: str,
        focus_areas: List[str],
        custom_instructions: Optional[str],
        intercom_data: str
    ) -> str:
        """Generate general purpose trend analysis prompt."""
        date_range = f"{start_date} to {end_date}"
        
        focus_text = ", ".join(focus_areas) if focus_areas else "general trends"
        custom_text = f"\n\n**Custom Instructions:** {custom_instructions}" if custom_instructions else ""
        
        return f"""# Intercom Trend Analysis - {date_range}

You will receive a complete Intercom dataset with pre-computed statistics for {date_range}. Create a comprehensive trend analysis based on the specific focus areas requested.

**Data:** {intercom_data}

**Focus Areas:** {focus_text}{custom_text}

**ANALYSIS REQUIREMENTS:**
- Use ONLY actual data - no estimates or approximations
- Include exact quotes with working Intercom conversation URLs
- Identify genuine trends and patterns in the data
- Provide actionable insights based on the focus areas
- Highlight both positive trends and areas needing attention

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Intercom Trend Analysis
Analysis of {{total_conversations}} conversations from {date_range}

## Executive Summary

{{executive_summary}}

\\n---\\n

## Key Trends

{{trend_analysis}}

\\n---\\n

## Detailed Insights

{{detailed_insights}}

\\n---\\n

## Notable Customer Feedback

{{notable_quotes}}

\\n---\\n

*Based on {{total_conversations}} conversations from {date_range}*"""
    
    @staticmethod
    def get_custom_analysis_prompt(
        custom_prompt: str,
        start_date: str,
        end_date: str,
        intercom_data: str
    ) -> str:
        """Generate custom analysis prompt."""
        date_range = f"{start_date} to {end_date}"
        
        return f"""# Custom Intercom Analysis - {date_range}

You will receive a complete Intercom dataset with pre-computed statistics for {date_range}. Follow the custom instructions below to create the requested analysis.

**Data:** {intercom_data}

**Custom Instructions:**
{custom_prompt}

**ANALYSIS REQUIREMENTS:**
- Use ONLY actual data - no estimates or approximations
- Include exact quotes with working Intercom conversation URLs
- Follow the custom instructions precisely
- Provide actionable insights based on the specific requirements
- Maintain professional analysis standards

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Custom Analysis Report
Analysis of {{total_conversations}} conversations from {date_range}

{{custom_analysis_content}}

\\n---\\n

*Based on {{total_conversations}} conversations from {date_range}*"""
    
    @staticmethod
    def get_data_summary_prompt(intercom_data: str) -> str:
        """Generate a data summary for context."""
        return f"""# Intercom Data Summary

Please provide a concise summary of the following Intercom conversation data. Focus on key statistics, trends, and notable patterns.

**Data:** {intercom_data}

**Summary Requirements:**
- Total conversation count
- Date range covered
- Key metrics (response times, satisfaction, etc.)
- Notable trends or patterns
- Geographic distribution
- Channel breakdown
- Top topics or issues

Provide a structured summary that can be used as context for further analysis."""
    
    @staticmethod
    def get_quote_extraction_prompt(intercom_data: str, quote_type: str = "positive") -> str:
        """Generate prompt for extracting customer quotes."""
        return f"""# Extract {quote_type.title()} Customer Quotes

From the following Intercom conversation data, extract the most impactful {quote_type} customer quotes.

**Data:** {intercom_data}

**Quote Requirements:**
- Extract 5-10 of the most {quote_type} customer quotes
- Include the full quote text
- Provide context about what the customer was discussing
- Include the conversation ID for reference
- Focus on quotes that provide genuine insight into customer experience

**Output Format:**
For each quote, provide:
1. Quote text (exact wording)
2. Context (what the customer was discussing)
3. Conversation ID
4. Why this quote is significant

Return as a structured list."""
    
    @staticmethod
    def get_metric_explanation_prompt(metric_name: str, metric_value: str, context: str) -> str:
        """Generate prompt for explaining specific metrics."""
        return f"""# Explain Metric: {metric_name}

**Metric Value:** {metric_value}
**Context:** {context}

Please explain what this metric means in business terms:
- What does this number represent?
- Is this good, bad, or neutral performance?
- What are the implications for the business?
- What actions might be recommended based on this metric?
- How does this compare to industry standards (if applicable)?

Provide a clear, executive-friendly explanation."""
    
    @staticmethod
    def get_trend_identification_prompt(intercom_data: str, time_period: str) -> str:
        """Generate prompt for identifying trends."""
        return f"""# Identify Trends - {time_period}

From the following Intercom conversation data, identify the most significant trends over the {time_period} period.

**Data:** {intercom_data}

**Trend Analysis Requirements:**
- Identify 3-5 most significant trends
- For each trend, provide:
  - Trend description
  - Supporting data/evidence
  - Business implications
  - Recommended actions
- Focus on trends that are actionable for the business
- Include both positive and concerning trends

**Output Format:**
For each trend:
1. **Trend Name:** [Clear, descriptive name]
2. **Description:** [What is happening]
3. **Evidence:** [Supporting data]
4. **Implications:** [Business impact]
5. **Recommendations:** [Suggested actions]

Return as a structured analysis."""
    
    @staticmethod
    def get_technical_troubleshooting_prompt(
        start_date: str,
        end_date: str,
        intercom_data: str
    ) -> str:
        """Generate technical troubleshooting analysis prompt."""
        date_range = f"{start_date} to {end_date}"
        
        return f"""# Technical Troubleshooting Analysis - {date_range}

You will receive a complete Intercom dataset with pre-computed statistics for {date_range}. Create a comprehensive technical troubleshooting analysis focusing on common support patterns and agent responses.

**Data:** {intercom_data}

**ANALYSIS REQUIREMENTS:**
- Focus on technical troubleshooting patterns (cache clearing, browser switching, connection issues)
- Identify escalation patterns to Dae-Ho, Hilary, or Max Jackson
- Extract common agent responses for macro creation
- Analyze resolution success rates by issue type
- Use ONLY actual data - no estimates or approximations
- Include exact quotes with working Intercom conversation URLs
- Group findings by issue category for easy macro development

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Technical Troubleshooting Analysis
Analysis of {{total_conversations}} conversations from {date_range}

## Executive Summary

{{executive_summary}}

\\n---\\n

## Most Common Technical Issues

{{common_issues_analysis}}

\\n---\\n

## Agent Response Patterns

{{agent_response_patterns}}

\\n---\\n

## Escalation Analysis

{{escalation_analysis}}

\\n---\\n

## Recommended Macros

{{macro_recommendations}}

\\n---\\n

## Training Opportunities

{{training_opportunities}}

\\n---\\n

## Customer Success Stories

{{success_stories}}

\\n---\\n

*Based on {{total_conversations}} conversations from {date_range}*"""

