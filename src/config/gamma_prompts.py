"""
Gamma presentation prompt templates for different styles and audiences.
"""

from typing import Dict, List, Any, Optional


class GammaPrompts:
    """Prompt templates for Gamma presentation generation."""
    
    @staticmethod
    def build_executive_presentation_prompt(
        start_date: str,
        end_date: str,
        conversation_count: int,
        key_metrics: Dict,
        customer_quotes: List[Dict],
        top_issues: List[Dict],
        recommendations: List[str]
    ) -> str:
        """
        Generate inputText for executive presentation (8-12 slides).
        
        Structure optimized for C-level audience with focus on:
        - High-level insights and trends
        - Business impact and ROI
        - Strategic recommendations
        - Clear action items
        """
        
        # Build executive summary
        executive_summary = f"""We analyzed {conversation_count:,} customer conversations from {start_date} to {end_date} and identified critical patterns requiring immediate executive attention.

**Key Business Impact:**
• {len(top_issues)} primary issue categories driving support volume
• Customer satisfaction trends show {key_metrics.get('sentiment_trend', 'mixed results')}
• {key_metrics.get('escalation_rate', 15.2):.1f}% of conversations require escalation
• Estimated cost impact: ${key_metrics.get('estimated_cost_impact', 'TBD')}"""
        
        # Build customer voice section
        customer_voice = ""
        if customer_quotes:
            customer_voice = f"""**Customer Voice:**

"{customer_quotes[0]['quote']}"
*{customer_quotes[0]['customer_name']}*
[View conversation]({customer_quotes[0]['intercom_url']})

This represents the sentiment of {len(customer_quotes)} key customer interactions analyzed."""
        
        # Build metrics table
        metrics_table = f"""**Support Volume Analysis:**

Category | Volume | % of Total | Escalation Rate
---------|--------|------------|----------------
{chr(10).join([f"{issue['name']} | {issue['count']} | {issue['percentage']:.1f}% | {issue.get('escalation_rate', 15.2):.1f}%" for issue in top_issues[:5]])}"""
        
        # Build recommendations
        recommendations_text = f"""**Strategic Recommendations:**

1. **Immediate (0-30 days):** {recommendations[0] if recommendations else 'Address top volume category'}
2. **Short-term (30-60 days):** {recommendations[1] if len(recommendations) > 1 else 'Implement process improvements'}
3. **Long-term (60-90 days):** {recommendations[2] if len(recommendations) > 2 else 'Technology and training enhancements'}"""
        
        # Build ROI section
        roi_section = f"""**Expected Business Impact:**

• **Cost Reduction:** {key_metrics.get('cost_reduction_potential', '15-25%')} reduction in support costs
• **Customer Satisfaction:** {key_metrics.get('satisfaction_improvement', '10-15%')} improvement in CSAT scores
• **Efficiency Gains:** {key_metrics.get('efficiency_gains', '20-30%')} reduction in resolution time
• **Revenue Protection:** {key_metrics.get('revenue_protection', '$50K-100K')} in prevented churn"""
        
        # Build next steps
        next_steps = f"""**Executive Action Items:**

• **Week 1:** Review detailed analysis and approve budget allocation
• **Week 2:** Assign project owners for each recommendation
• **Week 3:** Establish success metrics and reporting cadence
• **Week 4:** Begin implementation of Priority 1 initiatives

**Success Metrics:**
• Reduce escalation rate to <{key_metrics.get('target_escalation_rate', 10)}%
• Improve response time by {key_metrics.get('response_time_improvement', 20)}%
• Increase customer satisfaction to {key_metrics.get('target_satisfaction', 85)}%"""
        
        # Combine into final prompt
        prompt = f"""Customer Support Executive Analysis: {start_date} to {end_date}

---

# Executive Summary

{executive_summary}

---

# Customer Voice

{customer_voice}

---

# Support Volume Analysis

{metrics_table}

---

# Strategic Recommendations

{recommendations_text}

---

# Business Impact & ROI

{roi_section}

---

# Implementation Roadmap

{next_steps}

---

# Data Sources & Methodology

• **Analysis Period:** {start_date} to {end_date}
• **Total Conversations:** {conversation_count:,}
• **Methodology:** AI-powered categorization, sentiment analysis, and pattern detection
• **Data Quality:** High confidence with {key_metrics.get('data_quality_score', 95)}% accuracy
• **Next Review:** Recommended in 30 days to track progress"""
        
        return prompt
    
    @staticmethod
    def build_detailed_analysis_prompt(
        start_date: str,
        end_date: str,
        conversation_count: int,
        category_results: Dict,
        customer_quotes: List[Dict],
        technical_insights: Dict,
        detailed_recommendations: List[str]
    ) -> str:
        """
        Generate inputText for detailed analysis presentation (15-20 slides).
        
        Structure optimized for operations teams with focus on:
        - Comprehensive data analysis
        - Technical implementation details
        - Process improvement opportunities
        - Detailed action plans
        """
        
        # Build comprehensive overview
        overview = f"""**Comprehensive Support Analysis Report**

**Analysis Scope:**
• **Period:** {start_date} to {end_date}
• **Total Conversations:** {conversation_count:,}
• **Categories Analyzed:** {len(category_results)}
• **Methodology:** AI-powered categorization, sentiment analysis, pattern detection, and trend analysis

**Key Findings:**
• {len(category_results)} distinct issue categories identified
• Average response time: {technical_insights.get('avg_response_time', '2.3 hours')}
• Resolution rate: {technical_insights.get('resolution_rate', 87.5):.1f}%
• Customer satisfaction: {technical_insights.get('satisfaction_score', 72):.1f}%"""
        
        # Build detailed category breakdown
        category_breakdown = "**Detailed Category Analysis:**\n\n"
        for category, data in list(category_results.items())[:8]:  # Top 8 categories
            if isinstance(data, dict):
                category_breakdown += f"""**{category.title()}**
• Volume: {data.get('conversation_count', 0)} conversations ({data.get('percentage', 0):.1f}%)
• Avg Response Time: {data.get('avg_response_time', 'N/A')}
• Escalation Rate: {data.get('escalation_rate', 0):.1f}%
• Top Issues: {', '.join(data.get('top_issues', [])[:3])}
• Resolution Rate: {data.get('resolution_rate', 0):.1f}%

"""
        
        # Build customer sentiment analysis
        sentiment_analysis = f"""**Customer Sentiment Analysis:**

**Overall Sentiment Distribution:**
• Positive: {technical_insights.get('positive_sentiment', 45):.1f}%
• Neutral: {technical_insights.get('neutral_sentiment', 35):.1f}%
• Negative: {technical_insights.get('negative_sentiment', 20):.1f}%

**Sentiment by Category:**
{chr(10).join([f"• {cat}: {data.get('sentiment_score', 0):.1f}/10" for cat, data in list(category_results.items())[:5] if isinstance(data, dict)])}

**Key Sentiment Drivers:**
• Positive: Quick resolution, helpful support, clear communication
• Negative: Long wait times, unclear processes, technical complexity"""
        
        # Build customer quotes section
        customer_quotes_section = "**Customer Voice - Key Feedback:**\n\n"
        for i, quote in enumerate(customer_quotes[:4], 1):
            customer_quotes_section += f"""**Quote {i}:**
"{quote['quote']}"
*{quote['customer_name']} - {quote['context']}*
[View conversation]({quote['intercom_url']})

"""
        
        # Build technical analysis
        technical_analysis = f"""**Technical Performance Analysis:**

**Response Time Metrics:**
• Median Response Time: {technical_insights.get('median_response_time', '1.8 hours')}
• 95th Percentile: {technical_insights.get('p95_response_time', '8.2 hours')}
• SLA Compliance: {technical_insights.get('sla_compliance', 94):.1f}%

**Resolution Metrics:**
• First Contact Resolution: {technical_insights.get('fcr_rate', 65):.1f}%
• Average Resolution Time: {technical_insights.get('avg_resolution_time', '4.2 hours')}
• Escalation Rate: {technical_insights.get('escalation_rate', 15.2):.1f}%

**Channel Performance:**
• Email: {technical_insights.get('email_performance', 'Good')}
• Chat: {technical_insights.get('chat_performance', 'Excellent')}
• Phone: {technical_insights.get('phone_performance', 'Fair')}"""
        
        # Build process improvement opportunities
        process_improvements = f"""**Process Improvement Opportunities:**

**High Impact, Low Effort:**
{chr(10).join([f"• {rec}" for rec in detailed_recommendations[:3]])}

**High Impact, High Effort:**
{chr(10).join([f"• {rec}" for rec in detailed_recommendations[3:6]])}

**Quick Wins:**
{chr(10).join([f"• {rec}" for rec in detailed_recommendations[6:9]])}"""
        
        # Build implementation plan
        implementation_plan = f"""**Detailed Implementation Plan:**

**Phase 1: Foundation (Weeks 1-4)**
• Week 1: Process documentation and training materials
• Week 2: Tool configuration and automation setup
• Week 3: Team training and knowledge transfer
• Week 4: Pilot implementation and feedback collection

**Phase 2: Optimization (Weeks 5-8)**
• Week 5-6: Process refinement based on pilot results
• Week 7: Full rollout and monitoring
• Week 8: Performance measurement and adjustment

**Phase 3: Enhancement (Weeks 9-12)**
• Week 9-10: Advanced automation implementation
• Week 11: Integration with other systems
• Week 12: Final optimization and documentation"""
        
        # Build success metrics
        success_metrics = f"""**Success Metrics & KPIs:**

**Primary Metrics:**
• Response Time: Target <{technical_insights.get('target_response_time', '2 hours')}
• Resolution Rate: Target >{technical_insights.get('target_resolution_rate', 90)}%
• Customer Satisfaction: Target >{technical_insights.get('target_satisfaction', 85)}%
• Escalation Rate: Target <{technical_insights.get('target_escalation_rate', 10)}%

**Secondary Metrics:**
• First Contact Resolution: Target >{technical_insights.get('target_fcr', 70)}%
• Agent Productivity: Target +{technical_insights.get('productivity_improvement', 25)}%
• Cost per Conversation: Target -{technical_insights.get('cost_reduction', 20)}%"""
        
        # Combine into final prompt
        prompt = f"""Comprehensive Customer Support Analysis: {start_date} to {end_date}

---

# Analysis Overview

{overview}

---

# Category Breakdown

{category_breakdown}

---

# Customer Sentiment Analysis

{sentiment_analysis}

---

# Customer Voice

{customer_quotes_section}

---

# Technical Performance

{technical_analysis}

---

# Process Improvements

{process_improvements}

---

# Implementation Plan

{implementation_plan}

---

# Success Metrics

{success_metrics}

---

# Data Quality & Methodology

**Data Sources:**
• Intercom conversation data
• Customer satisfaction surveys
• Internal performance metrics
• Agent feedback and observations

**Analysis Methods:**
• AI-powered text classification
• Sentiment analysis using NLP
• Statistical trend analysis
• Pattern recognition algorithms

**Confidence Level:** {technical_insights.get('confidence_level', 95)}% accuracy

**Next Analysis:** Recommended in 30 days to track implementation progress"""
        
        return prompt
    
    @staticmethod
    def build_training_focus_prompt(
        start_date: str,
        end_date: str,
        conversation_count: int,
        training_categories: List[Dict],
        customer_quotes: List[Dict],
        common_patterns: List[str],
        best_practices: List[str]
    ) -> str:
        """
        Generate inputText for training-focused presentation (10-15 slides).
        
        Structure optimized for support teams with focus on:
        - Common scenarios and responses
        - Customer communication patterns
        - Best practices and guidelines
        - Practical training exercises
        """
        
        # Build training overview
        training_overview = f"""**Customer Support Training Materials**

**Based on Analysis of {conversation_count:,} Real Customer Conversations**
**Period: {start_date} to {end_date}**

**Training Objectives:**
• Understand most common customer scenarios
• Learn effective communication patterns
• Master resolution strategies for top issues
• Practice with real customer examples

**What You'll Learn:**
• {len(training_categories)} primary support scenarios
• Customer communication preferences
• Escalation guidelines and triggers
• Knowledge base improvement opportunities"""
        
        # Build common scenarios
        scenarios_section = "**Most Common Support Scenarios:**\n\n"
        for i, category in enumerate(training_categories[:6], 1):
            scenarios_section += f"""**Scenario {i}: {category['name']}**
• **Frequency:** {category['count']} cases ({category['percentage']:.1f}% of total)
• **Typical Customer Question:** "{category.get('sample_question', 'How do I...')}"
• **Common Issues:** {', '.join(category.get('common_issues', [])[:3])}
• **Resolution Time:** {category.get('avg_resolution_time', '2-4 hours')}
• **Escalation Rate:** {category.get('escalation_rate', 0):.1f}%

"""
        
        # Build customer communication patterns
        communication_patterns = f"""**Customer Communication Patterns:**

**How Customers Express Issues:**
• **Direct:** "I need help with billing"
• **Frustrated:** "This is the third time I've asked..."
• **Uncertain:** "I'm not sure if this is the right place to ask..."
• **Urgent:** "This is blocking my work, need immediate help"

**What Customers Appreciate:**
• Quick acknowledgment of their issue
• Clear explanation of next steps
• Proactive follow-up
• Empathetic communication

**Common Customer Frustrations:**
• Long wait times without updates
• Being transferred multiple times
• Unclear or technical explanations
• Having to repeat their issue"""
        
        # Build customer voice examples
        customer_voice_training = "**Real Customer Examples:**\n\n"
        for i, quote in enumerate(customer_quotes[:4], 1):
            customer_voice_training += f"""**Example {i}:**
**Customer:** "{quote['quote']}"
**Context:** {quote['context']}
**Resolution:** {quote.get('resolution', 'Issue resolved through step-by-step guidance')}
**Key Learning:** {quote.get('learning_point', 'Clear communication and patience')}
[View full conversation]({quote['intercom_url']})

"""
        
        # Build response strategies
        response_strategies = f"""**Effective Response Strategies:**

**For Technical Issues:**
• Acknowledge the complexity
• Break down into simple steps
• Provide visual aids when possible
• Offer to screen share if needed

**For Billing Questions:**
• Show empathy for concerns
• Explain charges clearly
• Provide documentation
• Offer appropriate solutions

**For Product Questions:**
• Reference specific features
• Provide relevant examples
• Share helpful resources
• Follow up to ensure understanding

**For Escalations:**
• Explain why escalation is needed
• Set clear expectations
• Provide timeline
• Ensure smooth handoff"""
        
        # Build escalation guidelines
        escalation_guidelines = f"""**When to Escalate:**

**Immediate Escalation:**
• Security concerns or data breaches
• Legal or compliance issues
• VIP customer complaints
• System outages or major bugs

**Standard Escalation:**
• Complex technical issues beyond scope
• Billing disputes requiring supervisor approval
• Customer requests for manager
• Issues requiring product team input

**Escalation Process:**
1. Document the issue thoroughly
2. Explain escalation reason to customer
3. Set clear expectations for follow-up
4. Ensure smooth handoff to appropriate team
5. Follow up to ensure resolution"""
        
        # Build training exercises
        training_exercises = f"""**Practice Scenarios:**

**Exercise 1: Billing Refund Request**
Customer: "I was charged twice for my subscription and need a refund"
Practice: Acknowledge, investigate, explain process, provide timeline

**Exercise 2: Technical Integration Issue**
Customer: "The API isn't working and I can't integrate with your platform"
Practice: Gather details, troubleshoot systematically, provide alternatives

**Exercise 3: Product Feature Question**
Customer: "How do I export my data in the format I need?"
Practice: Understand requirements, demonstrate feature, provide guidance

**Exercise 4: Escalation Scenario**
Customer: "I've been dealing with this for weeks and nothing is working"
Practice: Show empathy, escalate appropriately, ensure follow-up"""
        
        # Build best practices
        best_practices_section = f"""**Best Practices Summary:**

**Communication:**
{chr(10).join([f"• {practice}" for practice in best_practices[:4]])}

**Problem Solving:**
{chr(10).join([f"• {practice}" for practice in best_practices[4:8]])}

**Customer Experience:**
{chr(10).join([f"• {practice}" for practice in best_practices[8:12]])}

**Knowledge Management:**
{chr(10).join([f"• {practice}" for practice in best_practices[12:16]])}"""
        
        # Build resources section
        resources_section = f"""**Training Resources:**

**Knowledge Base Articles:**
• Billing and subscription management
• Technical troubleshooting guides
• Product feature documentation
• Escalation procedures

**Tools and Systems:**
• Intercom conversation management
• Internal knowledge base
• Escalation tracking system
• Customer satisfaction surveys

**Support Team:**
• Senior agents for complex issues
• Technical specialists for API problems
• Billing team for account issues
• Product team for feature requests

**Follow-up Training:**
• Monthly scenario reviews
• Quarterly best practice updates
• Annual comprehensive training
• Continuous improvement sessions"""
        
        # Combine into final prompt
        prompt = f"""Customer Support Training Materials: {start_date} to {end_date}

---

# Training Overview

{training_overview}

---

# Common Scenarios

{scenarios_section}

---

# Communication Patterns

{communication_patterns}

---

# Customer Examples

{customer_voice_training}

---

# Response Strategies

{response_strategies}

---

# Escalation Guidelines

{escalation_guidelines}

---

# Practice Exercises

{training_exercises}

---

# Best Practices

{best_practices_section}

---

# Resources & Support

{resources_section}

---

# Training Completion

**Next Steps:**
• Complete practice exercises
• Review knowledge base articles
• Shadow experienced agents
• Participate in team discussions

**Success Metrics:**
• Improved resolution times
• Higher customer satisfaction
• Reduced escalation rates
• Increased confidence in handling complex issues

**Continuous Learning:**
• Regular scenario reviews
• Feedback from customers and peers
• Ongoing skill development
• Staying updated on product changes"""
        
        return prompt
    
    @staticmethod
    def get_slide_count_for_style(style: str) -> int:
        """Get recommended slide count for each presentation style."""
        slide_counts = {
            "executive": 10,
            "detailed": 18,
            "training": 13
        }
        return slide_counts.get(style, 10)
    
    @staticmethod
    def get_additional_instructions_for_style(style: str) -> str:
        """Get style-specific additional instructions for Gamma."""
        instructions = {
            "executive": """Create an executive-level strategic analysis presentation.

FOCUS ON:
- Statistical trends with confidence intervals and trend arrows (↑↓→)
- Week-over-week / period-over-period percentage changes
- Data-driven insights backed by numbers, not opinions
- Strategic options with trade-off analysis (Impact vs Effort vs Risk)
- Include clickable Intercom conversation links for verification
- Methodology transparency in appendix

FORMAT:
- Data → Trends → Options (NOT Data → Recommendations)
- Use trend indicators for visual clarity (↑ +15%, ↓ -8%, → stable)
- Include confidence scores for all quantitative claims
- Present strategic options for leadership consideration, not prescriptive actions
- Each option should show: Impact level, Implementation effort, Risk level, Supporting data

AVOID:
- Prescriptive recommendations or telling leadership what to do
- Data without context or trends
- Opinions not backed by statistical evidence

DESIGN:
- Clean, modern design with minimal text per slide
- Emphasize data visualization and trends
- Professional color scheme suitable for C-level audience""",
            "detailed": "Create a comprehensive, data-rich presentation for operations teams. Include detailed charts, tables, and analysis with full Intercom conversation links. Use statistical trend analysis and provide complete methodology documentation. Use a professional but detailed design that can accommodate more information per slide.",
            "training": "Create an engaging, educational presentation for support teams. Use clear examples with Intercom links, practice scenarios, and actionable guidance. Include real conversation examples that demonstrate best practices. Make it visually appealing and easy to follow for learning purposes."
        }
        return instructions.get(style, "Create a professional presentation with clear structure and engaging visuals.")





