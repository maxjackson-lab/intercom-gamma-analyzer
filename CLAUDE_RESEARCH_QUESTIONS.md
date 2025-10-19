# Research Questions for Claude - Gamma Quality and System Improvements

## Context
I'm working on an Intercom Analysis Tool that generates Voice of Customer reports and creates Gamma presentations. The system works but has significant quality issues with the Gamma presentations and some UI/UX problems.

## Critical Issues Identified

### 1. Gamma Presentation Quality Problems

**Current Issues:**
- Gamma presentations are too severe/formal in tone
- Too high-level, lacks specific trends and actionable insights  
- Hallucin

ates/invents Intercom ticket URLs that don't exist
- Shows lists of tickets instead of thematic insights
- Slide count artificially limited (10-18 slides) even when more data exists
- Not showing what trends mean or why they matter

**Current Approach:**
- Using Gamma API v0.2
- Three prompt templates: executive, detailed, training
- Hardcoded slide limits: executive=10, detailed=18, training=13
- Prompts in `src/config/gamma_prompts.py`
- Example prompt structure includes customer quotes with Intercom URLs

**Questions:**
1. **How should I structure Gamma prompts to get conversational, insightful tone instead of formal/severe?**
   - What specific prompt engineering techniques work best for executive presentations?
   - How to request "analyst briefing executive" tone vs corporate formal?
   
2. **How do I prevent AI from hallucinating/inventing links when real data doesn't have them?**
   - Should I explicitly say "DO NOT invent URLs" in the prompt?
   - Should I remove conversation links entirely from the template?
   - Best practice for providing real data vs allowing AI to fill gaps?

3. **What's the best way to prompt for insights vs lists?**
   - Instead of "35 tickets about API issues", want "35% of technical issues relate to API timeouts, up 12% from last month"
   - How to request thematic analysis with representative examples?
   - Prompt patterns that encourage synthesis over enumeration?

4. **Should I remove slide count limits entirely?**
   - Current: hardcoded limits (10, 18, 13 slides)
   - Gamma API allows up to 75 slides
   - Better to have complete analysis than arbitrary truncation?
   - Any downsides to unlimited slides with real data?

5. **How to structure data for better Gamma output?**
   - Current: JSON with metrics, quotes, top issues
   - Should I pre-process to highlight trends?
   - Include historical comparison data?
   - What data structure produces best AI presentations?

### 2. Category Filtering Not Working

**Issue**: Category filters (API, billing, technical) don't properly filter conversations

**Code Location**: `src/services/category_filters.py`

**Questions:**
1. Common patterns for hierarchical category filtering in conversation analysis?
2. Should filtering happen at DB query level or in-memory after fetch?
3. Best practices for fuzzy category matching (e.g., "api error" matches "API" category)?

### 3. Web Interface UX Issues

**Current State:**
- Polling-based job execution (works around Railway 5-min HTTP timeout)
- Shows raw terminal output only
- No visual summary or clickable Gamma links
- Job history persists to disk but hard to navigate

**Questions:**
1. **Best UX pattern for long-running job results display?**
   - Tabs (Terminal | Summary | Files | Gamma)?
   - Accordion sections?
   - Single scrolling view with anchors?

2. **How to present analysis results visually in web UI?**
   - What metrics to highlight in cards?
   - How to show trends effectively?
   - Best way to make Gamma link prominent?

3. **File download UI best practices?**
   - List with download buttons?
   - Preview before download?
   - Indicate file types/sizes?

## Technical Constraints

- **Platform**: Railway.app (Docker containers)
- **Storage**: File-based (/app/outputs/) - no database
- **Users**: 1-5 concurrent users (internal tool)
- **Analysis Time**: 5-30 minutes per job
- **HTTP Timeout**: 5 minutes (hence polling architecture)

## Prompt Engineering Weaknesses

I need specific guidance on:

1. **Gamma-specific prompt patterns** that produce high-quality presentations
2. **Preventing hallucination** while keeping output rich and detailed
3. **Balancing specificity vs readability** in prompts
4. **Data preprocessing** before sending to Gamma API
5. **Error handling** for poor-quality generations (how to detect and retry?)

## Expected Research Output

Please provide:
1. Specific prompt templates or patterns for Gamma presentation generation
2. Code examples for data preprocessing that improves AI output quality
3. Best practices for preventing hallucinated links/data
4. Recommendations on slide count limits (remove? dynamic based on data?)
5. UX patterns for displaying long-running analysis results
6. Category filtering implementation patterns

## Success Criteria

After implementing recommendations:
- ✅ Gamma presentations are conversational and insightful
- ✅ No invented/hallucinated Intercom links
- ✅ Shows trends and patterns, not just data lists
- ✅ As many slides as needed to tell complete story
- ✅ Category filtering works correctly
- ✅ Web UI clearly shows results with clickable Gamma links
- ✅ Professional, executive-ready output quality

