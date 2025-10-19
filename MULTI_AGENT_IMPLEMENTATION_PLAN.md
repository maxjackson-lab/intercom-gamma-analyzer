# Multi-Agent Implementation Plan
**Project**: Intercom Analysis Tool - Agentic Workflow with Hallucination Prevention  
**Date**: October 19, 2025  
**Status**: Ready for Implementation

---

## Executive Summary

Based on the comprehensive research, we're implementing a **3-agent proof-of-concept** with **feature-flagged deployment** and **integrated hallucination prevention**. This approach minimizes risk while maximizing the quality improvements we've identified.

### Key Decisions Made:
- **Framework**: Custom implementation (fits our scale, minimal dependencies)
- **Agent Count**: 3 agents for POC (DataAgent, AnalysisAgent, OutputAgent)
- **Deployment**: Feature flag in same Railway service
- **Hallucination Prevention**: Integrated into all agent prompts
- **Timeline**: 2-week POC, 4-week full implementation

---

## Part 1: Architecture Design

### 1.1 Agent Specialization

```python
# Agent 1: DataAgent
class DataAgent:
    """Specialized in data fetching, validation, and preprocessing"""
    responsibilities = [
        "Fetch conversations from Intercom API",
        "Validate data completeness and quality", 
        "Preprocess and clean conversation data",
        "Extract metadata (dates, categories, sentiment indicators)"
    ]
    
    hallucination_prevention = [
        "Only use data from Intercom API responses",
        "Flag any missing or incomplete data",
        "Never invent conversation content or metadata"
    ]

# Agent 2: AnalysisAgent  
class AnalysisAgent:
    """Specialized in category classification and sentiment analysis"""
    responsibilities = [
        "Apply taxonomy-based category classification",
        "Perform sentiment analysis on conversation content",
        "Identify patterns and trends in the data",
        "Generate insights with confidence scoring"
    ]
    
    hallucination_prevention = [
        "Only classify using provided taxonomy categories",
        "State confidence levels for all classifications",
        "Never invent new categories or subcategories",
        "Use 'I cannot verify' for uncertain classifications"
    ]

# Agent 3: OutputAgent
class OutputAgent:
    """Specialized in report generation and presentation creation"""
    responsibilities = [
        "Synthesize insights from previous agents",
        "Generate executive summaries",
        "Create Gamma presentations",
        "Format outputs for different audiences"
    ]
    
    hallucination_prevention = [
        "Only use insights from previous agents",
        "Never invent URLs, citations, or references",
        "State limitations when data is incomplete",
        "Use 'According to the analysis' for all claims"
    ]
```

### 1.2 Workflow Orchestration

```python
class MultiAgentOrchestrator:
    """Coordinates the 3-agent workflow with error handling"""
    
    async def execute_analysis(self, analysis_type: str, params: dict):
        """Execute analysis using multi-agent workflow"""
        
        # Initialize workflow state
        workflow_state = WorkflowState(
            analysis_id=generate_id(),
            start_time=datetime.now(),
            mode="multi-agent"
        )
        
        try:
            # Phase 1: Data Collection
            data_result = await self.data_agent.execute(params)
            workflow_state.add_result("data_agent", data_result)
            
            # Phase 2: Analysis
            analysis_result = await self.analysis_agent.execute(
                context=workflow_state.get_context_for_agent("analysis_agent")
            )
            workflow_state.add_result("analysis_agent", analysis_result)
            
            # Phase 3: Output Generation
            output_result = await self.output_agent.execute(
                context=workflow_state.get_context_for_agent("output_agent")
            )
            workflow_state.add_result("output_agent", output_result)
            
            return self._format_final_result(workflow_state)
            
        except AgentError as e:
            return await self._handle_agent_failure(e, workflow_state)
```

### 1.3 Feature Flag Implementation

```python
# config/analysis_modes.yaml
analysis_modes:
  standard:
    enabled: true
    description: "Current monolithic analysis"
    
  multi_agent:
    enabled: false  # Start disabled
    description: "3-agent specialized workflow"
    agents: ["data", "analysis", "output"]
    workflow: "sequential"
    
  hybrid:
    enabled: false
    description: "Multi-agent for complex, standard for simple"
    threshold: "conversation_count > 500"

# Feature flag logic
def get_analysis_mode(analysis_type: str, params: dict) -> str:
    """Determine which analysis mode to use"""
    
    if not config.analysis_modes.multi_agent.enabled:
        return "standard"
    
    # Multi-agent for complex analyses
    if analysis_type in ["comprehensive", "voice-of-customer", "trend-analysis"]:
        return "multi_agent"
    
    # Standard for simple analyses  
    if analysis_type in ["quick-summary", "category-count"]:
        return "standard"
    
    # Hybrid logic
    if config.analysis_modes.hybrid.enabled:
        if params.get("conversation_count", 0) > 500:
            return "multi_agent"
    
    return "standard"
```

---

## Part 2: Hallucination Prevention Integration

### 2.1 Agent-Specific Prompt Templates

```python
class HallucinationPreventionPrompts:
    """Centralized hallucination prevention for all agents"""
    
    @staticmethod
    def get_base_prevention_prompt():
        return """
        CRITICAL HALLUCINATION PREVENTION RULES:
        1. You are FORBIDDEN from inventing URLs, citations, or references
        2. If uncertain about any fact, state "I cannot verify this information"
        3. Only use information from provided context or verified data sources
        4. For each claim, use format: [Claim] - [Source/confidence level]
        5. NEVER fabricate data to fill gaps
        6. If information is not in provided materials, state: "This information is not available"
        """
    
    @staticmethod
    def get_data_agent_prompt():
        return f"""
        {HallucinationPreventionPrompts.get_base_prevention_prompt()}
        
        DATA AGENT SPECIFIC RULES:
        - Only use data from Intercom API responses
        - Flag any missing or incomplete data with "DATA INCOMPLETE: [description]"
        - Never invent conversation content, timestamps, or user information
        - If API returns empty results, state "No conversations found for specified criteria"
        - Validate all data fields before processing
        """
    
    @staticmethod
    def get_analysis_agent_prompt():
        return f"""
        {HallucinationPreventionPrompts.get_base_prevention_prompt()}
        
        ANALYSIS AGENT SPECIFIC RULES:
        - Only classify using provided taxonomy categories (never invent new ones)
        - State confidence levels: "HIGH/MEDIUM/LOW confidence" for each classification
        - Use "I cannot verify this classification" for uncertain cases
        - Never invent patterns or trends not supported by the data
        - Quote exact conversation text when making claims about sentiment
        """
    
    @staticmethod
    def get_output_agent_prompt():
        return f"""
        {HallucinationPreventionPrompts.get_base_prevention_prompt()}
        
        OUTPUT AGENT SPECIFIC RULES:
        - Only use insights from previous agents (never invent new insights)
        - Use "According to the analysis" for all claims
        - Never invent URLs, conversation links, or external references
        - State limitations when data is incomplete: "Analysis limited by [reason]"
        - Use "Based on the provided data" for all conclusions
        """
```

### 2.2 Chain-of-Verification Implementation

```python
class VerificationWorkflow:
    """Implements Chain-of-Verification for multi-agent outputs"""
    
    async def verify_agent_output(self, agent_name: str, output: str, context: dict):
        """Verify agent output using CoVe pattern"""
        
        # Step 1: Generate verification questions
        verification_questions = await self._generate_verification_questions(
            agent_name, output, context
        )
        
        # Step 2: Answer verification questions
        verification_answers = await self._answer_verification_questions(
            verification_questions, context
        )
        
        # Step 3: Compare and revise
        revised_output = await self._revise_based_on_verification(
            output, verification_answers
        )
        
        return revised_output
    
    async def _generate_verification_questions(self, agent_name: str, output: str, context: dict):
        """Generate verification questions specific to agent type"""
        
        if agent_name == "data_agent":
            return [
                "Are all conversation IDs from the actual API response?",
                "Do all timestamps match the provided date range?",
                "Is the conversation count accurate?",
                "Are there any invented user names or emails?"
            ]
        elif agent_name == "analysis_agent":
            return [
                "Are all categories from the provided taxonomy?",
                "Do sentiment scores match the conversation content?",
                "Are confidence levels realistic for the data quality?",
                "Are there any invented patterns or trends?"
            ]
        elif agent_name == "output_agent":
            return [
                "Are all insights derived from previous agent outputs?",
                "Are there any invented URLs or references?",
                "Do all claims have supporting evidence?",
                "Are limitations properly stated?"
            ]
```

### 2.3 Confidence Scoring System

```python
class ConfidenceScorer:
    """Scores confidence levels for agent outputs"""
    
    def score_data_agent_output(self, output: dict) -> float:
        """Score confidence based on data completeness and validation"""
        score = 1.0
        
        # Deduct for missing data
        if output.get("missing_conversations", 0) > 0:
            score -= 0.1 * (output["missing_conversations"] / output["total_expected"])
        
        # Deduct for validation failures
        if output.get("validation_failures", 0) > 0:
            score -= 0.2 * (output["validation_failures"] / output["total_conversations"])
        
        return max(0.0, score)
    
    def score_analysis_agent_output(self, output: dict) -> float:
        """Score confidence based on classification certainty"""
        score = 1.0
        
        # Deduct for low-confidence classifications
        low_confidence_count = sum(1 for item in output["classifications"] 
                                 if item["confidence"] < 0.7)
        if low_confidence_count > 0:
            score -= 0.3 * (low_confidence_count / len(output["classifications"]))
        
        return max(0.0, score)
    
    def score_output_agent_output(self, output: str) -> float:
        """Score confidence based on source attribution and limitations"""
        score = 1.0
        
        # Check for proper source attribution
        if "According to" not in output and "Based on" not in output:
            score -= 0.2
        
        # Check for stated limitations
        if "cannot verify" in output.lower() or "not available" in output.lower():
            score -= 0.1  # Actually good - shows honesty
        
        # Check for invented content
        if "https://" in output and "app.intercom.com" not in output:
            score -= 0.5  # Likely invented URL
        
        return max(0.0, score)
```

---

## Part 3: Implementation Strategy

### 3.1 Phase 1: Proof of Concept (Week 1-2)

**Objective**: Validate multi-agent approach with minimal implementation

**Scope**:
```python
# Minimal 3-agent implementation
agents = {
    "data_agent": DataAgent(),
    "analysis_agent": AnalysisAgent(), 
    "output_agent": OutputAgent()
}

# Sequential workflow only
workflow = SequentialWorkflow(agents)

# Basic error handling
error_handling = BasicErrorHandling()

# Feature flag: disabled by default
feature_flag = "multi_agent_analysis_enabled = false"
```

**Success Criteria**:
- [ ] All 3 agents execute successfully
- [ ] Quality improvement > 20% vs standard mode
- [ ] No critical bugs or hallucinations
- [ ] Execution time < 2x standard mode
- [ ] Easy rollback to standard mode

**Testing Plan**:
```python
# Test with 10 sample analyses
test_cases = [
    "voice-of-customer --days 7",
    "billing-analysis --days 30", 
    "tech-analysis --days 14",
    "api-analysis --days 7",
    "category-analysis billing --days 30"
]

# Compare outputs
for test_case in test_cases:
    standard_result = await run_standard_analysis(test_case)
    multi_agent_result = await run_multi_agent_analysis(test_case)
    
    # Measure quality, time, cost
    quality_score = compare_quality(standard_result, multi_agent_result)
    time_ratio = multi_agent_result.time / standard_result.time
    cost_ratio = multi_agent_result.cost / standard_result.cost
    
    assert quality_score > 1.2  # 20% improvement
    assert time_ratio < 2.0     # Less than 2x slower
    assert cost_ratio < 3.0     # Less than 3x cost
```

### 3.2 Phase 2: Enhanced Implementation (Week 3-4)

**If POC successful, expand to**:

```python
# Enhanced 5-agent implementation
agents = {
    "data_agent": DataAgent(),
    "category_agent": CategoryAgent(),      # Split from analysis
    "sentiment_agent": SentimentAgent(),    # Split from analysis  
    "insight_agent": InsightAgent(),        # New - synthesis
    "presentation_agent": PresentationAgent() # New - Gamma optimization
}

# Parallel workflow where possible
workflow = HybridWorkflow(agents)

# Advanced error handling
error_handling = AdvancedErrorHandling(
    retry_policy=ExponentialBackoff(),
    fallback_agents=True,
    partial_results=True
)

# Feature flag: beta testing
feature_flag = "multi_agent_analysis_enabled = true (beta)"
```

**New Features**:
- Parallel agent execution where possible
- Advanced error handling and fallbacks
- Quality validation and confidence scoring
- Monitoring and metrics collection
- Web UI integration

### 3.3 Phase 3: Production Rollout (Week 5-6)

**If Phase 2 successful**:

```python
# Production-ready implementation
features = {
    "monitoring": True,
    "metrics": True, 
    "web_ui": True,
    "documentation": True,
    "user_training": True
}

# Gradual rollout
rollout_plan = {
    "week_1": "10% of analyses",
    "week_2": "25% of analyses", 
    "week_3": "50% of analyses",
    "week_4": "100% of analyses"
}
```

---

## Part 4: Code Organization

### 4.1 Directory Structure

```
src/
├── services/                    # Current code (unchanged)
│   ├── orchestrator.py         # Current orchestrator
│   └── ...
├── agents/                     # New multi-agent code
│   ├── __init__.py
│   ├── base_agent.py          # Abstract base class
│   ├── data_agent.py          # Data fetching and validation
│   ├── analysis_agent.py      # Category and sentiment analysis
│   ├── output_agent.py        # Report generation
│   ├── orchestrator.py        # Multi-agent orchestrator
│   ├── workflow_state.py      # State management
│   ├── error_handling.py      # Error handling and fallbacks
│   └── verification.py        # Chain-of-verification
├── config/
│   ├── analysis_modes.yaml    # Feature flags and configuration
│   └── agent_prompts.py       # Hallucination prevention prompts
└── main.py                    # Updated with mode selection
```

### 4.2 Integration Points

```python
# src/main.py - Updated entry point
async def run_analysis(analysis_type: str, **kwargs):
    """Main entry point with mode selection"""
    
    # Determine analysis mode
    mode = get_analysis_mode(analysis_type, kwargs)
    
    if mode == "standard":
        # Use current orchestrator
        orchestrator = AnalysisOrchestrator()
        return await orchestrator.run_comprehensive_analysis(analysis_type, **kwargs)
    
    elif mode == "multi_agent":
        # Use multi-agent orchestrator
        orchestrator = MultiAgentOrchestrator()
        return await orchestrator.execute_analysis(analysis_type, kwargs)
    
    else:
        raise ValueError(f"Unknown analysis mode: {mode}")

# src/services/orchestrator.py - Current orchestrator (unchanged)
class AnalysisOrchestrator:
    """Current orchestrator - no changes needed"""
    # ... existing code ...

# src/agents/orchestrator.py - New multi-agent orchestrator
class MultiAgentOrchestrator:
    """New multi-agent orchestrator"""
    # ... new implementation ...
```

### 4.3 Configuration Management

```python
# config/analysis_modes.yaml
analysis_modes:
  standard:
    enabled: true
    description: "Current monolithic analysis"
    
  multi_agent:
    enabled: false  # Start disabled
    description: "3-agent specialized workflow"
    agents:
      data_agent:
        model: "gpt-4o-mini"
        temperature: 0.1
        max_tokens: 2000
      analysis_agent:
        model: "gpt-4o"
        temperature: 0.3
        max_tokens: 4000
      output_agent:
        model: "gpt-4o"
        temperature: 0.7
        max_tokens: 6000
    workflow:
      mode: "sequential"
      timeout: 600
      retry_policy:
        max_attempts: 3
        backoff: "exponential"
    quality_thresholds:
      min_confidence: 0.7
      max_hallucination_rate: 0.05
      min_quality_improvement: 1.2

# config/agent_prompts.py
class AgentPrompts:
    """Centralized prompt management with hallucination prevention"""
    
    @staticmethod
    def get_prompt(agent_name: str, analysis_type: str) -> str:
        """Get agent-specific prompt with hallucination prevention"""
        base_prevention = HallucinationPreventionPrompts.get_base_prevention_prompt()
        agent_specific = HallucinationPreventionPrompts.get_agent_prompt(agent_name)
        analysis_context = AnalysisContextPrompts.get_context(analysis_type)
        
        return f"""
        {base_prevention}
        
        {agent_specific}
        
        {analysis_context}
        
        Your task: {get_agent_task(agent_name, analysis_type)}
        """
```

---

## Part 5: Monitoring and Metrics

### 5.1 Quality Metrics

```python
class QualityMetrics:
    """Track quality improvements from multi-agent approach"""
    
    def __init__(self):
        self.metrics = {
            "hallucination_rate": 0.0,
            "confidence_scores": [],
            "user_satisfaction": 0.0,
            "analysis_accuracy": 0.0,
            "insight_relevance": 0.0
        }
    
    def measure_hallucination_rate(self, output: str) -> float:
        """Measure rate of hallucinated content"""
        hallucination_indicators = [
            "https://" not in "app.intercom.com",  # Invented URLs
            "cannot verify" not in output.lower(),  # Missing uncertainty
            "according to" not in output.lower(),   # Missing attribution
        ]
        
        # Count potential hallucinations
        potential_hallucinations = sum(hallucination_indicators)
        total_claims = len(output.split("."))
        
        return potential_hallucinations / total_claims if total_claims > 0 else 0.0
    
    def measure_confidence_scores(self, agent_outputs: dict) -> list:
        """Measure confidence scores across all agents"""
        scores = []
        for agent_name, output in agent_outputs.items():
            scorer = ConfidenceScorer()
            score = scorer.score_agent_output(agent_name, output)
            scores.append(score)
        return scores
```

### 5.2 Performance Metrics

```python
class PerformanceMetrics:
    """Track performance impact of multi-agent approach"""
    
    def __init__(self):
        self.metrics = {
            "execution_time": 0.0,
            "api_calls": 0,
            "cost_per_analysis": 0.0,
            "error_rate": 0.0,
            "retry_count": 0
        }
    
    def compare_with_standard(self, multi_agent_result: dict, standard_result: dict):
        """Compare multi-agent vs standard performance"""
        return {
            "time_ratio": multi_agent_result["time"] / standard_result["time"],
            "cost_ratio": multi_agent_result["cost"] / standard_result["cost"],
            "quality_ratio": multi_agent_result["quality"] / standard_result["quality"],
            "api_calls_ratio": multi_agent_result["api_calls"] / standard_result["api_calls"]
        }
```

### 5.3 Monitoring Dashboard

```python
# Simple monitoring endpoint
@app.get("/metrics/multi-agent")
async def get_multi_agent_metrics():
    """Get multi-agent performance metrics"""
    return {
        "quality_metrics": quality_metrics.get_summary(),
        "performance_metrics": performance_metrics.get_summary(),
        "comparison_with_standard": comparison_metrics.get_summary(),
        "feature_flag_status": get_feature_flag_status(),
        "last_updated": datetime.now().isoformat()
    }
```

---

## Part 6: Risk Mitigation

### 6.1 Rollback Strategy

```python
class RollbackManager:
    """Manages rollback to standard mode if issues arise"""
    
    def __init__(self):
        self.rollback_triggers = {
            "error_rate": 0.1,      # 10% error rate
            "quality_degradation": 0.8,  # 20% quality drop
            "cost_increase": 5.0,   # 5x cost increase
            "time_increase": 3.0,   # 3x time increase
        }
    
    def check_rollback_conditions(self, metrics: dict) -> bool:
        """Check if rollback conditions are met"""
        for trigger, threshold in self.rollback_triggers.items():
            if metrics.get(trigger, 0) > threshold:
                return True
        return False
    
    async def execute_rollback(self):
        """Execute rollback to standard mode"""
        # Disable multi-agent mode
        config.analysis_modes.multi_agent.enabled = False
        
        # Log rollback event
        logger.warning("Multi-agent mode disabled due to performance issues")
        
        # Notify administrators
        await notify_administrators("Multi-agent rollback executed")
```

### 6.2 Error Handling

```python
class MultiAgentErrorHandler:
    """Handles errors in multi-agent workflow"""
    
    async def handle_agent_failure(self, agent_name: str, error: Exception, workflow_state: WorkflowState):
        """Handle individual agent failures"""
        
        if agent_name == "data_agent":
            # Critical failure - abort analysis
            return await self._abort_analysis("Data collection failed", workflow_state)
        
        elif agent_name == "analysis_agent":
            # Try fallback to standard analysis
            return await self._fallback_to_standard_analysis(workflow_state)
        
        elif agent_name == "output_agent":
            # Generate basic output without presentation
            return await self._generate_basic_output(workflow_state)
    
    async def _fallback_to_standard_analysis(self, workflow_state: WorkflowState):
        """Fallback to standard analysis if multi-agent fails"""
        data_result = workflow_state.get_result("data_agent")
        
        # Use standard orchestrator with the data we have
        standard_orchestrator = AnalysisOrchestrator()
        return await standard_orchestrator.run_comprehensive_analysis(
            analysis_type=workflow_state.analysis_type,
            conversations=data_result["conversations"]
        )
```

---

## Part 7: Implementation Timeline

### Week 1: Foundation
- [ ] Create agent base classes and interfaces
- [ ] Implement basic 3-agent workflow
- [ ] Add hallucination prevention prompts
- [ ] Create feature flag system
- [ ] Write unit tests for agents

### Week 2: Integration
- [ ] Integrate with existing orchestrator
- [ ] Add error handling and fallbacks
- [ ] Implement confidence scoring
- [ ] Create monitoring endpoints
- [ ] Test with sample data

### Week 3: Enhancement
- [ ] Add parallel execution where possible
- [ ] Implement Chain-of-Verification
- [ ] Add quality metrics tracking
- [ ] Create comparison testing framework
- [ ] Optimize performance

### Week 4: Production
- [ ] Add web UI integration
- [ ] Implement gradual rollout
- [ ] Add comprehensive monitoring
- [ ] Create documentation
- [ ] Train users on new features

---

## Part 8: Success Criteria

### Technical Success
- [ ] All agents execute without errors
- [ ] Quality improvement > 20% vs standard mode
- [ ] Execution time < 2x standard mode
- [ ] Cost increase < 3x standard mode
- [ ] Hallucination rate < 5%

### Business Success
- [ ] User satisfaction improvement
- [ ] Better insights leading to action
- [ ] Reduced support tickets
- [ ] Increased analysis frequency
- [ ] Positive user feedback

### Operational Success
- [ ] Easy rollback capability
- [ ] Comprehensive monitoring
- [ ] Clear error messages
- [ ] Maintainable codebase
- [ ] Good documentation

---

## Part 9: Next Steps

1. **Review and approve this plan** - Confirm approach and timeline
2. **Set up development environment** - Create feature branch
3. **Implement Phase 1** - 3-agent POC with hallucination prevention
4. **Test and validate** - Compare with standard mode
5. **Make go/no-go decision** - Based on POC results
6. **Plan full implementation** - If POC successful

---

## Part 10: Questions for Discussion

1. **Risk tolerance**: Are we comfortable with 2-3x cost increase for quality improvement?

2. **Timeline**: Is 4-week implementation timeline acceptable?

3. **Rollback**: What's our threshold for rolling back to standard mode?

4. **Quality bar**: What improvement level justifies the investment?

5. **User impact**: How do we communicate changes to users?

---

This implementation plan combines the best of both worlds: the proven hallucination prevention techniques from Claude's research with a practical multi-agent architecture that fits our small-scale application. The feature-flagged approach ensures we can safely experiment while maintaining our working system.
