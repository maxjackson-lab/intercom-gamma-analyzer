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

**CRITICAL CONTEXT FOR SUPPORT DATA:**
- Support tickets are NORMAL business operations - customers contact support when they have issues
- Negative sentiment in support does NOT automatically mean product failure
- Focus on actionable metrics: Resolution time, Escalation rate, First Contact Resolution, Volume trends
- NOT meaningful: "98% negative sentiment" (it's support - customers are unhappy by definition)
- MEANINGFUL: "Billing resolution time increased 23% vs last month" or "Escalation rate dropped from 15% to 12%"
- Compare to baselines and trends over time, not absolute sentiment scores
- What matters: Resolution quality, efficiency improvements, churn indicators, NPS/CSAT correlation

**CRITICAL: GRANULAR BREAKDOWN REQUIRED**
- We have a detailed taxonomy with 13 primary categories and 100+ subcategories
- For EACH top-level category, drill down into specific issues within that category
- Don't just report "Account issues - 234 conversations"
- Instead provide: "Email change failures - 89 conversations (38% of account issues)"
- For each specific issue, identify the pattern and include a representative quote
- Show percentages within each category to highlight the most common problems

**Example of Good Analysis:**
```
BAD: "Product questions - 234 conversations"

GOOD: "Product Questions (234 conversations, 28% of total volume)
├─ Email & Account Management (89 conversations, 38% of product issues)
│  ├─ Email change failures: 45 conversations
│  │  Pattern: Users receiving 'email already in use' error
│  │  Quote: 'I've been trying to change my email for weeks but keep getting an error...'
│  │  Impact: Users can't update their contact information
│  ├─ Password reset issues: 34 conversations  
│  │  Pattern: Reset emails not arriving for Gmail users
│  │  Quote: 'I never received the password reset email...'
│  │  Impact: Users locked out of their accounts
│  └─ Two-factor setup confusion: 10 conversations
│     Pattern: Users don't understand QR code setup process
│     Quote: 'I scanned the code but nothing happened...'
│     Impact: Security feature adoption blocked
└─ Feature Access (67 conversations, 29% of product issues)
   ├─ Export functionality confusion: 34 conversations
   ├─ Publishing permissions: 23 conversations
   └─ Template access issues: 10 conversations"
```

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

## Top Contact Categories (with Granular Breakdown)

For each category below, provide the detailed breakdown format shown in the example above:

{{top_contact_reasons_analysis}}

\\n---\\n

## Billing Questions (Detailed Breakdown)

{{billing_analysis}}

\\n---\\n

## Product Questions (Detailed Breakdown)

{{product_questions_analysis}}

\\n---\\n

## Account Questions (Detailed Breakdown)

{{account_questions_analysis}}

\\n---\\n

## Technical Issues (Detailed Breakdown)

{{technical_issues_analysis}}

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

**CRITICAL: GRANULAR TREND ANALYSIS REQUIRED**
- We have a detailed taxonomy with 13 primary categories and 100+ subcategories
- For EACH trend identified, drill down into specific issues and their changes over time
- Don't just report "API issues increased 15%"
- Instead provide: "API Integration Issues increased 15% (156 → 179 conversations)
  ├─ Webhook timeout errors: +23% (67 → 82 conversations)
  │  Pattern: Zapier integrations failing more frequently
  │  Quote: 'My Zapier webhooks keep timing out...'
  │  Impact: Customer automation workflows breaking
  ├─ Authentication token expiration: +12% (45 → 50 conversations)
  │  Pattern: Tokens expiring faster than expected
  │  Impact: Users locked out of integrations
  └─ Rate limiting confusion: +8% (44 → 48 conversations)
     Pattern: Users hitting limits during bulk operations
     Impact: Workflow efficiency reduced"
- Show percentage changes and absolute numbers for each specific issue
- Identify the root cause or pattern behind each trend

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Intercom Trend Analysis
Analysis of {{total_conversations}} conversations from {date_range}

## Executive Summary

{{executive_summary}}

\\n---\\n

## Key Trends (with Granular Breakdown)

For each trend, provide the detailed breakdown format showing specific issues and their changes:

{{trend_analysis}}

\\n---\\n

## Detailed Insights (Category-by-Category Analysis)

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

**TAXONOMY REFERENCE:**
- We have a detailed taxonomy with 13 primary categories and 100+ subcategories
- When analyzing categories, drill down into specific issues within each category
- Use the granular breakdown format when appropriate for the custom analysis
- Show percentages and patterns for specific issues, not just high-level categories

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

**CRITICAL: GRANULAR TECHNICAL BREAKDOWN REQUIRED**
- We have a detailed taxonomy with 13 primary categories and 100+ subcategories
- For EACH technical issue category, drill down into specific problems and their solutions
- Don't just report "Browser issues - 89 conversations"
- Instead provide: "Browser Compatibility Issues (89 conversations, 23% of technical issues)
  ├─ Chrome extension conflicts: 34 conversations (38% of browser issues)
  │  Pattern: Users reporting 'page not loading' after extension updates
  │  Common Solution: 'Try disabling extensions one by one'
  │  Success Rate: 78% resolved with extension troubleshooting
  │  Quote: 'The page was blank until I disabled my ad blocker...'
  ├─ Safari rendering problems: 28 conversations (31% of browser issues)
  │  Pattern: Layout issues and missing elements on Safari
  │  Common Solution: 'Clear Safari cache and cookies'
  │  Success Rate: 85% resolved with cache clearing
  │  Quote: 'Everything looks broken on Safari but works fine in Chrome...'
  └─ Firefox performance issues: 27 conversations (30% of browser issues)
     Pattern: Slow loading and timeouts on Firefox
     Common Solution: 'Update Firefox to latest version'
     Success Rate: 92% resolved with browser update
     Quote: 'It takes forever to load on Firefox...'"
- For each specific issue, provide the most common agent response and success rate
- Identify patterns that could be automated with macros

Output markdown only. No JSON. No preambles. Use \\n---\\n to separate major sections into cards.

\\n---\\n

# Technical Troubleshooting Analysis
Analysis of {{total_conversations}} conversations from {date_range}

## Executive Summary

{{executive_summary}}

\\n---\\n

## Most Common Technical Issues (Detailed Breakdown)

For each technical category, provide the granular breakdown format:

{{common_issues_analysis}}

\\n---\\n

## Agent Response Patterns (by Issue Type)

{{agent_response_patterns}}

\\n---\\n

## Escalation Analysis (Specific Triggers)

{{escalation_analysis}}

\\n---\\n

## Recommended Macros (Based on Common Patterns)

{{macro_recommendations}}

\\n---\\n

## Training Opportunities (Specific Skills Needed)

{{training_opportunities}}

\\n---\\n

## Customer Success Stories (Resolution Examples)

{{success_stories}}

\\n---\\n

*Based on {{total_conversations}} conversations from {date_range}*"""

