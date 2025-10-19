"""
Story-driven prompt templates for customer experience analysis.
These prompts focus on extracting narrative insights and real customer stories
rather than just technical metrics.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


class StoryDrivenPrompts:
    """Collection of story-driven prompt templates for customer experience analysis."""
    
    @staticmethod
    def get_customer_journey_story_prompt(
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        analysis_period: str,
        focus_areas: List[str] = None
    ) -> str:
        """
        Generate a story-driven prompt that focuses on customer journey narratives.
        This prompt treats the data as a collection of customer stories rather than metrics.
        """
        focus_text = ", ".join(focus_areas) if focus_areas else "overall customer experience"
        
        return f"""# Customer Experience Story Analysis - {analysis_period}

You are a customer experience storyteller and analyst. Your job is to extract the real human stories behind our customer data and identify patterns that reflect genuine customer experiences.

## Your Role
You are not just analyzing data - you are uncovering the human stories, emotions, and experiences that customers are having with our product. Think like a journalist investigating customer experiences, not a data scientist crunching numbers.

## Data Sources
- **Intercom Conversations:** {len(conversations)} customer support interactions
- **Canny Feedback:** {len(canny_posts)} feature requests and feedback posts
- **Focus Areas:** {focus_text}

## Analysis Approach
Instead of just counting metrics, tell the story of what customers are experiencing:

1. **The Customer's Voice**: What are customers actually saying? What emotions are they expressing?
2. **The Journey**: How do customers move through different touchpoints? Where do they get stuck or delighted?
3. **The Patterns**: What recurring themes emerge across different customer stories?
4. **The Impact**: What do these stories tell us about our product and service quality?

## Story Elements to Extract

### Customer Emotions & Experiences
- What feelings are customers expressing? (frustration, excitement, confusion, satisfaction)
- What moments of delight or pain are they describing?
- How do their experiences evolve over time?

### Narrative Threads
- What common storylines emerge across customer interactions?
- How do different customer segments experience our product differently?
- What are the "plot twists" - unexpected moments in customer journeys?

### Real Customer Quotes
- Extract actual customer words that capture their experience
- Look for quotes that tell a complete story in a few sentences
- Include both positive and challenging experiences

### Journey Moments
- What are the key moments when customers need help?
- Where do customers express satisfaction or frustration?
- What are the "aha moments" or breakthrough experiences?

## Output Structure

Tell the story in this narrative format:

### The Customer Experience Story
**What customers are really experiencing right now**

[Write 2-3 paragraphs that capture the overall customer experience narrative, using real quotes and specific examples]

### The Emotional Journey
**How customers feel throughout their experience**

[Describe the emotional arc - where customers start, what challenges they face, how they feel about solutions]

### The Recurring Themes
**The stories that keep coming up**

[Identify 3-5 key themes that appear across multiple customer interactions, with specific examples]

### The Moments That Matter
**The specific interactions that define the customer experience**

[Highlight 3-4 specific moments or interactions that are particularly telling about the customer experience]

### What This Means for Our Business
**The business implications of these customer stories**

[Connect the customer stories to actionable business insights and opportunities]

## Guidelines
- Use actual customer quotes extensively
- Focus on the human experience, not just technical issues
- Look for patterns in emotions and experiences, not just topics
- Connect individual stories to broader themes
- Be specific and concrete, not abstract
- Show the progression of customer experiences over time
- Highlight both positive and challenging experiences

Remember: You're not just analyzing data - you're uncovering the real stories of how customers experience our product and service. Make it human, make it real, make it actionable.
"""

    @staticmethod
    def get_insight_extraction_prompt(
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        analysis_period: str
    ) -> str:
        """
        Generate a prompt focused on extracting actionable insights from customer stories.
        This prompt emphasizes finding trends that reflect real customer experience.
        """
        return f"""# Customer Insight Extraction - {analysis_period}

You are a customer experience analyst who specializes in finding meaningful insights from customer stories. Your goal is to identify trends and patterns that reflect real customer experiences and provide actionable business insights.

## Data Overview
- **Support Conversations:** {len(conversations)} customer interactions
- **Feature Requests:** {len(canny_posts)} customer feedback posts
- **Analysis Period:** {analysis_period}

## Your Analysis Framework

### 1. Experience Patterns
Look for patterns in how customers experience your product:
- What experiences are customers having repeatedly?
- Where do customers consistently struggle or succeed?
- What emotional patterns emerge across interactions?

### 2. Journey Insights
Identify insights about the customer journey:
- What are the critical moments in the customer experience?
- Where do customers get stuck or find delight?
- How do different customer segments experience the journey differently?

### 3. Voice of Customer Themes
Extract the real themes from customer voices:
- What are customers actually asking for?
- What problems are they trying to solve?
- What opportunities are they identifying?

### 4. Business Impact Stories
Connect customer experiences to business impact:
- Which customer stories point to revenue opportunities?
- Which experiences indicate risk or churn potential?
- What customer insights suggest product improvements?

## Insight Categories to Identify

### Immediate Customer Needs
- What do customers need right now?
- What are the most urgent problems they're facing?
- What quick wins could improve their experience?

### Emerging Trends
- What new patterns are emerging in customer behavior?
- What are customers starting to ask for more frequently?
- What changes in customer expectations are you seeing?

### Experience Gaps
- Where are we failing to meet customer expectations?
- What experiences are we not providing that customers need?
- Where are there disconnects between what we offer and what customers want?

### Success Stories
- What experiences are customers praising?
- What are we doing well that we should amplify?
- What positive patterns should we build on?

## Output Format

### Key Customer Insights
[3-5 most important insights about customer experience, with specific examples]

### Experience Trends
[2-3 trends in how customers are experiencing the product, with supporting evidence]

### Customer Voice Themes
[3-4 main themes from what customers are saying, with representative quotes]

### Business Implications
[How these insights should influence business decisions and priorities]

### Actionable Opportunities
[Specific, concrete actions the business should take based on these insights]

## Analysis Guidelines
- Focus on insights that reflect real customer experience, not just data points
- Use specific customer quotes and examples to support insights
- Look for patterns that span multiple interactions or feedback sources
- Connect insights to business impact and opportunities
- Prioritize insights that are actionable and specific
- Balance positive and challenging customer experiences
- Show the progression and evolution of customer needs over time

Remember: Your goal is to extract insights that help the business understand and improve the real customer experience, not just analyze data.
"""

    @staticmethod
    def get_narrative_synthesis_prompt(
        intercom_data: str,
        canny_data: str,
        analysis_period: str,
        business_context: str = None
    ) -> str:
        """
        Generate a prompt that synthesizes data into a compelling narrative
        that tells the story of customer experience.
        """
        context_text = f"\n\n**Business Context:** {business_context}" if business_context else ""
        
        return f"""# Customer Experience Narrative Synthesis - {analysis_period}

You are a customer experience storyteller who specializes in weaving together customer data into compelling narratives that drive business action. Your job is to create a story that executives and teams can understand and act upon.

## Data Sources
- **Intercom Support Data:** {intercom_data}
- **Canny Feedback Data:** {canny_data}
- **Analysis Period:** {analysis_period}{context_text}

## Your Storytelling Approach

### The Narrative Arc
Structure your analysis as a story with:
1. **The Setting**: What's the current state of customer experience?
2. **The Characters**: Who are our customers and what are they trying to achieve?
3. **The Plot**: What challenges and opportunities are they facing?
4. **The Resolution**: What should we do to improve their experience?

### The Human Element
- Focus on real customer voices and experiences
- Show the emotional journey customers are on
- Highlight specific moments that matter to customers
- Use actual quotes to bring the story to life

### The Business Connection
- Connect customer stories to business impact
- Show how customer experiences affect key metrics
- Identify opportunities for improvement and growth
- Provide clear, actionable next steps

## Story Structure

### Chapter 1: The Customer Reality
**What customers are actually experiencing right now**

[Paint a picture of the current customer experience using real examples and quotes]

### Chapter 2: The Journey Through Our Product
**How customers move through their experience with us**

[Describe the customer journey, highlighting key moments and touchpoints]

### Chapter 3: The Patterns We're Seeing
**The recurring themes and trends in customer experience**

[Identify the main patterns and themes that emerge across customer interactions]

### Chapter 4: The Moments That Matter
**The specific interactions that define the customer experience**

[Highlight the most important moments that shape how customers feel about us]

### Chapter 5: The Path Forward
**What these stories tell us about how to improve**

[Connect the customer stories to specific business actions and improvements]

## Writing Guidelines
- Write in a conversational, engaging tone
- Use specific customer quotes and examples
- Make it feel like you're telling a story, not presenting data
- Focus on the human experience, not just metrics
- Show the progression and evolution of customer needs
- Balance challenges with opportunities
- Make it actionable and specific
- Use storytelling techniques like anecdotes, dialogue, and vivid descriptions

## Key Questions to Answer
- What story do these customer interactions tell?
- What are the most important themes and patterns?
- What do customers really need from us?
- Where are we succeeding and where are we failing?
- What should we do differently based on these stories?

Remember: You're not just analyzing data - you're telling the story of how customers experience our product and service. Make it compelling, make it human, and make it actionable.
"""

    @staticmethod
    def get_insight_validation_prompt(
        insights: List[str],
        supporting_evidence: Dict[str, Any],
        analysis_period: str
    ) -> str:
        """
        Generate a prompt to validate and refine insights based on supporting evidence.
        This helps ensure insights are grounded in real customer data.
        """
        insights_text = "\n".join([f"- {insight}" for insight in insights])
        
        return f"""# Insight Validation and Refinement - {analysis_period}

You are a customer experience analyst tasked with validating and refining insights to ensure they accurately reflect real customer experiences.

## Initial Insights to Validate
{insights_text}

## Supporting Evidence
{supporting_evidence}

## Validation Process

### 1. Evidence Check
For each insight, verify:
- Is there sufficient evidence from customer interactions?
- Do the supporting quotes and examples actually support the insight?
- Are there any counter-examples that contradict the insight?

### 2. Insight Refinement
Based on the evidence:
- Are the insights specific enough to be actionable?
- Do they capture the real customer experience accurately?
- Are they balanced (showing both positive and challenging experiences)?
- Do they reflect trends rather than isolated incidents?

### 3. Story Validation
Ensure insights tell a coherent story:
- Do the insights connect to form a narrative about customer experience?
- Are there gaps in the story that need to be filled?
- Do the insights reflect the full range of customer experiences?

## Refined Insights Output

### Validated Insights
[List the insights that are well-supported by evidence, refined for clarity and actionability]

### Evidence Summary
[For each insight, provide the key supporting evidence from customer interactions]

### Story Gaps
[Identify any gaps in the customer experience story that need more data or analysis]

### Confidence Levels
[Rate each insight's confidence level based on the strength of supporting evidence]

## Guidelines
- Be rigorous in validating insights against actual customer data
- Refine insights to be more specific and actionable
- Ensure insights reflect the real customer experience, not assumptions
- Balance positive and challenging customer experiences
- Focus on insights that can drive meaningful business action

Remember: Your goal is to ensure that every insight is grounded in real customer experience and can drive meaningful business improvement.
"""

    @staticmethod
    def get_executive_story_prompt(
        customer_stories: Dict[str, Any],
        business_metrics: Dict[str, Any],
        analysis_period: str
    ) -> str:
        """
        Generate a prompt for creating executive-level stories that connect
        customer experience to business impact.
        """
        return f"""# Executive Customer Experience Story - {analysis_period}

You are a customer experience strategist who creates compelling narratives for executive audiences. Your job is to tell the story of customer experience in a way that drives business action and investment.

## Story Elements
- **Customer Stories:** {customer_stories}
- **Business Metrics:** {business_metrics}
- **Analysis Period:** {analysis_period}

## Executive Story Framework

### The Business Context
- What's happening in our customer base?
- How are customer experiences affecting business outcomes?
- What are the key trends and patterns we need to understand?

### The Customer Reality
- What are customers actually experiencing?
- What are the most important customer stories we need to know?
- How are customer needs and expectations evolving?

### The Business Impact
- How are customer experiences affecting key business metrics?
- What opportunities and risks do we see in customer feedback?
- What's the potential impact of improving customer experience?

### The Path Forward
- What specific actions should we take based on these stories?
- What investments should we make in customer experience?
- How do we measure success in improving customer experience?

## Story Structure

### Executive Summary
**The customer experience story in 3-4 key points**

[Capture the most important customer experience insights in executive-friendly language]

### The Customer Voice
**What customers are telling us**

[Use real customer quotes and examples to bring the story to life]

### The Business Case
**Why this matters for our business**

[Connect customer experiences to business impact and opportunities]

### The Action Plan
**What we should do about it**

[Provide specific, actionable recommendations based on customer stories]

## Writing Guidelines
- Write for an executive audience - clear, concise, and action-oriented
- Use real customer quotes to make it tangible and credible
- Focus on business impact and opportunities
- Balance challenges with opportunities
- Make recommendations specific and measurable
- Use storytelling techniques to make it engaging and memorable

## Key Questions to Answer
- What's the most important customer experience story we need to know?
- How are customer experiences affecting our business?
- What should we do differently based on these stories?
- What's the potential impact of taking action?

Remember: You're telling the story of customer experience to drive business action. Make it compelling, make it credible, and make it actionable.
"""