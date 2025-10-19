# Story-Driven Customer Experience Analysis Implementation

## Overview

This implementation enhances the existing Intercom and Canny data preprocessing pipeline with story-driven analysis capabilities that focus on extracting real customer experiences and narratives rather than just technical metrics.

## Key Improvements

### 1. Story-Driven Prompts (`src/config/story_driven_prompts.py`)

**New prompt templates that focus on:**
- **Customer Journey Stories**: Extract narrative threads from customer interactions
- **Emotional Analysis**: Identify customer emotions and experiences
- **Insight Extraction**: Find actionable insights from customer stories
- **Narrative Synthesis**: Create compelling stories for executive audiences
- **Insight Validation**: Ensure insights are grounded in real customer data

**Key Features:**
- Human-centered language that treats data as customer stories
- Focus on emotions, experiences, and journey moments
- Emphasis on real customer quotes and specific examples
- Business impact connection for actionable insights

### 2. Story-Driven Preprocessor (`src/services/story_driven_preprocessor.py`)

**Enhanced preprocessing that:**
- Extracts customer stories from conversations and Canny posts
- Identifies emotional patterns and journey stages
- Generates story summaries using AI analysis
- Logs ChatGPT analysis before Gamma API calls
- Focuses on narrative elements rather than just technical metrics

**Key Capabilities:**
- Emotional tone analysis across all interactions
- Customer journey stage identification
- Story element extraction (goals, pain points, success moments)
- Real customer quote extraction
- Narrative synthesis for executive consumption

### 3. Story-Driven Orchestrator (`src/services/story_driven_orchestrator.py`)

**Comprehensive orchestration that:**
- Coordinates story-driven analysis across all components
- Generates customer journey stories
- Extracts actionable insights from narratives
- Creates executive-level narratives
- Integrates with existing Gamma presentation generation

**Key Features:**
- Complete story analysis pipeline
- Insight validation and refinement
- Executive narrative creation
- ChatGPT analysis logging
- Quick story analysis for immediate insights

### 4. Enhanced Main Orchestrator (`src/services/orchestrator.py`)

**Integration with existing system:**
- Added `run_story_driven_analysis()` method
- Seamless integration with current analysis pipeline
- Optional story-driven analysis alongside traditional metrics
- Canny data integration for comprehensive customer view

### 5. Prompt Integration (`src/config/story_driven_prompts_integration.py`)

**Flexible prompt system that:**
- Allows switching between traditional and story-driven approaches
- Integrates Canny data when available
- Provides enhanced prompts for different analysis types
- Includes ChatGPT analysis logging prompts

## Usage Examples

### Basic Story-Driven Analysis

```python
from services.orchestrator import AnalysisOrchestrator
from datetime import datetime

orchestrator = AnalysisOrchestrator()

# Run story-driven analysis
results = await orchestrator.run_story_driven_analysis(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    options={
        'generate_gamma_presentation': True,
        'include_canny_data': True,
        'gamma_style': 'executive'
    }
)
```

### Quick Story Analysis

```python
from services.story_driven_orchestrator import StoryDrivenOrchestrator

orchestrator = StoryDrivenOrchestrator()

# Quick analysis for immediate insights
results = await orchestrator.run_quick_story_analysis(
    conversations=conversations,
    canny_posts=canny_posts,
    analysis_period="January 2024",
    options={'focus_areas': ['onboarding', 'billing']}
)
```

## Key Benefits

### 1. Human-Centered Analysis
- Focuses on real customer experiences rather than just metrics
- Extracts emotional journeys and customer stories
- Provides context and narrative flow to data

### 2. Actionable Insights
- Identifies specific customer pain points and success moments
- Connects customer experiences to business impact
- Provides concrete, actionable recommendations

### 3. Executive-Ready Narratives
- Creates compelling stories for executive audiences
- Balances challenges with opportunities
- Uses real customer quotes to make insights tangible

### 4. Comprehensive Customer View
- Integrates Intercom and Canny data for complete picture
- Analyzes customer journey across multiple touchpoints
- Identifies patterns and themes across different data sources

### 5. ChatGPT Analysis Logging
- Logs all ChatGPT analysis before Gamma API calls
- Provides transparency and audit trail
- Enables analysis quality assessment

## Implementation Details

### File Structure
```
src/
├── config/
│   ├── story_driven_prompts.py          # Story-driven prompt templates
│   └── story_driven_prompts_integration.py  # Integration with existing prompts
├── services/
│   ├── story_driven_preprocessor.py     # Story-focused data preprocessing
│   ├── story_driven_orchestrator.py     # Story-driven analysis orchestration
│   └── orchestrator.py                  # Enhanced main orchestrator
```

### Key Classes
- `StoryDrivenPrompts`: Collection of story-focused prompt templates
- `StoryDrivenPreprocessor`: Preprocesses data with story focus
- `StoryDrivenOrchestrator`: Coordinates story-driven analysis
- `StoryDrivenPromptIntegration`: Integrates with existing prompt system

### Configuration Options
- `use_story_driven`: Enable/disable story-driven analysis
- `include_canny_data`: Include Canny feedback in analysis
- `focus_areas`: Specific areas to focus analysis on
- `generate_gamma_presentation`: Generate Gamma presentation
- `gamma_style`: Style of Gamma presentation (executive, detailed, training)

## Integration with Existing System

The story-driven analysis is designed to work alongside the existing analysis pipeline:

1. **Backward Compatible**: Existing analysis methods continue to work
2. **Optional Enhancement**: Story-driven analysis is opt-in
3. **Seamless Integration**: Uses existing data sources and infrastructure
4. **Enhanced Outputs**: Provides richer, more narrative-focused results

## Future Enhancements

1. **Advanced NLP**: Implement more sophisticated natural language processing
2. **Sentiment Analysis**: Enhanced emotional analysis across languages
3. **Journey Mapping**: Visual customer journey mapping capabilities
4. **Real-time Analysis**: Live story analysis for ongoing insights
5. **Custom Themes**: User-defined theme detection and analysis

## Conclusion

This implementation transforms the customer data analysis from a metrics-focused approach to a story-driven approach that captures the real human experiences behind the data. It provides actionable insights that are grounded in actual customer stories and emotions, making them more valuable for business decision-making.

The system maintains compatibility with existing workflows while adding powerful new capabilities for understanding and acting on customer experience insights.