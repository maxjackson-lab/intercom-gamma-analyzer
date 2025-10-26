# QA Rubric Integration Analysis
## Mapping Gamma's QA Criteria to Agent Performance Metrics

**Source**: [Gamma QA Score Tracking](https://gamma.app/docs/Gamma-Quality-Assurance-Score-Tracking-4o4efvowiu7kqg0?mode=doc)  
**Date**: October 26, 2025

---

## 📊 EXISTING METRICS OVERVIEW

Your current `IndividualAgentMetrics` model already tracks:

### Quantitative Metrics (Data-Driven)
- ✅ **FCR Rate** - First Contact Resolution
- ✅ **CSAT Score** - Customer satisfaction (1-5 stars)
- ✅ **Escalation Rate** - How often issues are escalated
- ✅ **Resolution Time** - Median hours to resolution
- ✅ **Troubleshooting Score** - Quality of diagnostic approach
- ✅ **Reopen Rate** - Conversations that come back
- ✅ **Diagnostic Questions** - Thoroughness of troubleshooting

### Qualitative Indicators (Inferred)
- ✅ **Premature Escalation Rate** - Escalated without adequate effort
- ✅ **Category Performance** - Which topics handled well vs poorly
- ✅ **Worst CSAT Examples** - Specific problem conversations

---

## 🎯 QA RUBRIC MAPPING

### **Category 1: Customer Connection**

| QA Criteria | Can Auto-Measure? | Existing Analogue | Integration Recommendation |
|------------|-------------------|-------------------|---------------------------|
| **Voice, tone, and brand alignment** | ⚠️ Partial | CSAT score indirectly reflects | **NEW METRIC**: Add `communication_quality_score` (AI-evaluated) |
| **Warm greeting & customer name usage** | ✅ Yes | None | **NEW METRIC**: `greeting_quality_score` (text analysis) |
| **Empathetic response to mood** | ⚠️ Partial | CSAT correlation with negative sentiment | **ENHANCE**: Add `empathy_indicators` to CSAT analysis |
| **Willingness to help & initiative** | ⚠️ Partial | Premature escalation rate (inverse), FCR rate | **MAP**: Low premature_escalation + High FCR = High initiative |

**Integration Strategy: HYBRID APPROACH**

```python
class CustomerConnectionMetrics(BaseModel):
    """New metrics for customer connection quality"""
    
    # Automated metrics
    greeting_present: bool = Field(description="Did agent greet customer?")
    customer_name_used: bool = Field(description="Did agent use customer's name?")
    greeting_quality_score: float = Field(ge=0, le=1, description="Quality of opening (0-1)")
    
    # AI-evaluated metrics (using LLM on sample conversations)
    tone_alignment_score: float = Field(ge=0, le=1, description="Brand voice alignment (0-1)")
    empathy_score: float = Field(ge=0, le=1, description="Empathetic language usage (0-1)")
    proactive_help_score: float = Field(ge=0, le=1, description="Initiative and helpfulness (0-1)")
    
    # Composite
    customer_connection_score: float = Field(ge=0, le=1, description="Overall connection quality")
```

**✅ RECOMMENDED**: Implement automated greeting detection + AI evaluation on sample conversations

---

### **Category 2: Communication**

| QA Criteria | Can Auto-Measure? | Existing Analogue | Integration Recommendation |
|------------|-------------------|-------------------|---------------------------|
| **Grammar and spelling** | ✅ Yes | None | **NEW METRIC**: `grammar_error_rate` (automated checker) |
| **Visual formatting & paragraphs** | ✅ Yes | None | **NEW METRIC**: `formatting_quality_score` (line breaks, structure) |
| **Reading comprehension & acknowledgment** | ⚠️ Partial | Reopen rate, Diagnostic questions | **ENHANCE**: Add `comprehension_indicators` |

**Integration Strategy: MOSTLY AUTOMATED**

```python
class CommunicationQualityMetrics(BaseModel):
    """Communication quality metrics"""
    
    # Automated text analysis
    avg_grammar_errors_per_message: float = Field(description="Grammar/spelling errors per message")
    avg_message_length_chars: int = Field(description="Average message length")
    proper_paragraph_usage_rate: float = Field(ge=0, le=1, description="% messages with proper breaks")
    
    # Readability metrics
    avg_readability_score: float = Field(description="Flesch Reading Ease or similar")
    avg_sentences_per_paragraph: float = Field(description="Paragraph structure quality")
    
    # Comprehension indicators (inferred from conversation flow)
    acknowledgment_rate: float = Field(ge=0, le=1, description="% of customer issues acknowledged")
    clarification_questions_asked: int = Field(description="Clarifying questions to ensure understanding")
    
    # Composite
    communication_quality_score: float = Field(ge=0, le=1, description="Overall communication quality")
```

**✅ RECOMMENDED**: Implement - High ROI, mostly automatable

---

### **Category 3: Correct/Complete Content**

| QA Criteria | Can Auto-Measure? | Existing Analogue | Integration Recommendation |
|------------|-------------------|-------------------|---------------------------|
| **Correct & complete answers** | ⚠️ Partial | FCR rate, Reopen rate | **MAP**: Already captured by FCR/reopen metrics |
| **Internal processes followed** | ❌ No | None | **SKIP**: Requires internal process documentation |
| **Anticipating follow-up questions** | ⚠️ Partial | Reopen rate (inverse) | **ENHANCE**: Add `proactive_guidance_score` |
| **Correct macros applied** | ❌ No | None | **SKIP**: Requires macro tracking in Intercom |
| **Correct tagging** | ❌ No | None | **SKIP**: No reference for "correct" tags available |

**Integration Strategy: USE EXISTING + MINOR ENHANCEMENTS**

```python
class ContentCompletenessMetrics(BaseModel):
    """Content correctness and completeness"""
    
    # Existing metrics (already tracked)
    fcr_rate: float  # Proxy for correct/complete answers
    reopen_rate: float  # Proxy for incomplete answers
    
    # New AI-evaluated metrics
    proactive_guidance_score: float = Field(
        ge=0, le=1, 
        description="Did agent anticipate follow-ups? (AI-evaluated on samples)"
    )
    answer_thoroughness_score: float = Field(
        ge=0, le=1,
        description="Completeness of answers (AI-evaluated)"
    )
    
    # Skipped (not measurable without internal data)
    # - internal_processes_followed: Requires process documentation
    # - macro_usage_correctness: Requires macro inventory
    # - tagging_accuracy: Requires ground truth tags
```

**⚠️ PARTIAL**: Use existing FCR/reopen as primary indicators, add AI evaluation for samples

---

## 🎨 PROPOSED ENHANCED MODEL

### Option 1: Add QA Metrics to Existing Model (RECOMMENDED)

**Extend `IndividualAgentMetrics` with new optional fields:**

```python
class IndividualAgentMetrics(BaseModel):
    # ... existing fields ...
    
    # QA Rubric Metrics (optional, requires AI evaluation)
    qa_metrics: Optional[QAPerformanceMetrics] = Field(
        None,
        description="Quality assurance metrics based on Gamma QA rubric"
    )

class QAPerformanceMetrics(BaseModel):
    """Quality metrics based on Gamma QA rubric"""
    
    # Customer Connection (30% weight)
    customer_connection_score: float = Field(ge=0, le=1)
    greeting_quality: float = Field(ge=0, le=1)
    empathy_score: float = Field(ge=0, le=1)
    initiative_score: float = Field(ge=0, le=1)
    
    # Communication (35% weight)
    communication_quality_score: float = Field(ge=0, le=1)
    grammar_quality: float = Field(ge=0, le=1)
    formatting_quality: float = Field(ge=0, le=1)
    comprehension_quality: float = Field(ge=0, le=1)
    
    # Content Correctness (35% weight)
    content_quality_score: float = Field(ge=0, le=1)
    answer_completeness: float = Field(ge=0, le=1)
    proactive_guidance: float = Field(ge=0, le=1)
    
    # Overall QA Score
    overall_qa_score: float = Field(
        ge=0, le=1,
        description="Weighted average of all QA dimensions"
    )
    
    # Sample size
    conversations_evaluated: int = Field(
        description="Number of conversations used for QA scoring"
    )
    evaluation_method: str = Field(
        description="'automated', 'ai_evaluated', or 'manual'"
    )
```

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Automated Metrics (Easy Win) ✅

**Measurable without AI evaluation:**

1. **Greeting Detection**
   - Search for greeting patterns in first agent message
   - Check for customer name usage
   - Effort: 2-3 hours

2. **Grammar & Formatting**
   - Use LanguageTool API or similar
   - Count line breaks, paragraph structure
   - Effort: 4-6 hours

3. **Message Statistics**
   - Length, readability score
   - Response patterns
   - Effort: 2 hours

**Code Example:**
```python
def analyze_greeting_quality(conversation: Dict) -> Dict[str, Any]:
    """Analyze first agent message for greeting quality"""
    first_agent_message = get_first_agent_message(conversation)
    
    greeting_keywords = ['hi', 'hello', 'hey', 'good morning', 'good afternoon']
    has_greeting = any(kw in first_agent_message.lower() for kw in greeting_keywords)
    
    customer_name = conversation.get('customer', {}).get('name', '')
    used_name = customer_name.lower() in first_agent_message.lower() if customer_name else False
    
    return {
        'greeting_present': has_greeting,
        'customer_name_used': used_name,
        'greeting_quality_score': (0.5 if has_greeting else 0) + (0.5 if used_name else 0)
    }
```

---

### Phase 2: AI-Evaluated Metrics (Medium Effort) ⚠️

**Requires LLM evaluation on sample conversations:**

1. **Empathy & Tone**
   - Sample 10-20 conversations per agent
   - Use GPT-4 to score tone alignment
   - Effort: 8-10 hours

2. **Proactive Help**
   - Evaluate if agent anticipated needs
   - Check for unsolicited helpful information
   - Effort: 6-8 hours

**Code Example:**
```python
async def evaluate_empathy_with_ai(conversation: Dict) -> float:
    """Use AI to evaluate empathetic language"""
    prompt = f"""
    Evaluate the agent's empathy in this customer service conversation.
    
    Customer messages: {customer_messages}
    Agent messages: {agent_messages}
    
    Rate 0-1 based on:
    - Did agent acknowledge customer's emotions?
    - Did agent use empathetic language?
    - Did agent match customer's tone appropriately?
    
    Return only a score between 0 and 1.
    """
    
    response = await openai_client.generate(prompt)
    return float(response)
```

---

### Phase 3: Integration into Coaching (High Value) 🎯

**Use QA scores to enhance coaching insights:**

```python
def generate_qa_coaching_insights(metrics: IndividualAgentMetrics) -> List[str]:
    """Generate coaching based on QA scores"""
    insights = []
    
    if metrics.qa_metrics:
        qa = metrics.qa_metrics
        
        # Customer connection coaching
        if qa.customer_connection_score < 0.7:
            if qa.greeting_quality < 0.6:
                insights.append("🎯 Greeting Quality: Agent should consistently greet customers warmly and use their names")
            if qa.empathy_score < 0.6:
                insights.append("🎯 Empathy: Agent should acknowledge customer emotions and use empathetic language")
        
        # Communication coaching
        if qa.communication_quality_score < 0.7:
            if qa.grammar_quality < 0.8:
                insights.append("📝 Grammar: Review messages for spelling/grammar errors")
            if qa.formatting_quality < 0.7:
                insights.append("📝 Formatting: Use proper paragraphs and line breaks for readability")
        
        # Content coaching
        if qa.content_quality_score < 0.7:
            insights.append("💡 Completeness: Provide thorough answers and anticipate follow-up questions")
    
    return insights
```

---

## 🚦 RECOMMENDATION SUMMARY

### ✅ IMPLEMENT IMMEDIATELY (High ROI, Low Effort)

1. **Greeting Quality Detection** - Automated, easy to measure
2. **Grammar & Formatting Analysis** - Automated via libraries
3. **Message Statistics** - Simple text analysis

### ⚠️ IMPLEMENT IN PHASE 2 (Medium ROI, Medium Effort)

4. **AI-Evaluated Empathy** - Sample-based LLM evaluation
5. **Proactive Help Scoring** - AI analysis of conversation flow
6. **Tone Alignment** - Brand voice consistency check

### ❌ SKIP (Not Measurable Without Additional Data)

7. **Internal Process Adherence** - Requires process documentation
8. **Macro Usage Correctness** - Requires macro inventory
9. **Tagging Accuracy** - No ground truth available

---

## 📊 MEASUREMENT APPROACH

### For Automated Metrics:
- Run on **100% of conversations**
- Real-time scoring
- Included in regular reports

### For AI-Evaluated Metrics:
- Sample **10-20 conversations per agent per period**
- Use GPT-4 for consistency
- Cache results to avoid redundant API calls
- Run weekly or monthly

### Weighting Suggestion:
```
Overall QA Score = 
  (Customer Connection × 0.30) +
  (Communication Quality × 0.35) +
  (Content Correctness × 0.35)

Where each component is average of its sub-metrics
```

---

## 🎯 BUSINESS VALUE

### What You Gain:
1. **Objective soft skill measurement** - Quantify "good communication"
2. **Targeted coaching** - Specific areas like "greeting quality" vs generic "improve communication"
3. **Trend tracking** - See if communication quality improves over time
4. **Benchmarking** - Compare agents on consistent criteria
5. **CSAT correlation** - Link soft skills to satisfaction scores

### What You Can't Measure (Without Human Review):
1. **Strict process compliance** - Need internal docs
2. **Macro appropriateness** - Need macro definitions
3. **Tag correctness** - Need ground truth
4. **Nuanced judgment calls** - Some aspects need human QA

---

## 💡 NEXT STEPS

1. **Review & Prioritize**: Which metrics matter most to your team?
2. **Pilot Phase 1**: Implement automated metrics on small sample
3. **Validate Results**: Do scores correlate with human QA assessments?
4. **Expand**: Roll out to full analysis pipeline
5. **Iterate**: Refine scoring based on feedback

**Estimated Total Implementation Time**: 20-30 hours for Phase 1 + Phase 2

---

**Would you like me to implement any of these phases?** I can start with Phase 1 (automated metrics) which would give immediate value with minimal effort.

