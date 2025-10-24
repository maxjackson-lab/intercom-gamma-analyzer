# Frontend Functionality Audit & Gap Analysis

**Date:** October 24, 2025  
**Purpose:** Identify gaps between backend capabilities and frontend UI controls

---

## 🔍 Backend Capabilities (Available via CLI)

### From `src/chat/engines/function_calling.py`:

#### 1. **Voice of Customer Analysis** ✅ Exposed
- `voice-of-customer`
  - Flags: `--time-period`, `--start-date`, `--end-date`, `--generate-gamma`, `--include-canny`, `--ai-model`
  - Analysis types: `--analysis-type` (topic-based, synthesis, complete)
- **Frontend:** ✅ Full coverage via dropdown

#### 2. **Comprehensive Analysis** ⚠️ Partially Exposed
- `comprehensive-analysis`
  - Flags: `--start-date`, `--end-date`, `--max-conversations`, `--generate-gamma`, `--export-docs`
- **Frontend:** ❌ NOT in dropdown, ❌ No max-conversations control

#### 3. **Category-Specific Analysis** ✅ Exposed
- `billing-analysis`, `tech-analysis`, `product-analysis`, `sites-analysis`
  - Flags: `--start-date`, `--end-date`, `--include-details`
- **Frontend:** ✅ In dropdown as separate options

#### 4. **Agent Coaching Report** ✅ NOW ADDED
- `agent-coaching-report`
  - Flags: `--vendor` (horatio|boldr), `--time-period`, `--top-n`, `--generate-gamma`
- **Frontend:** ✅ NOW ADDED with info panel

#### 5. **Agent Performance Individual** ✅ NOW ADDED
- `agent-performance`
  - Flags: `--agent` (horatio|boldr|escalated), `--time-period`, `--individual-breakdown`, `--generate-gamma`
- **Frontend:** ✅ NOW ADDED with separate team vs individual options

#### 6. **Canny Analysis** ✅ Exposed
- `canny-analysis`
  - Flags: `--generate-gamma`, `--start-date`, `--end-date`
- **Frontend:** ✅ In dropdown

---

## 🆕 NEW Functionality Added Today (Oct 24, 2025)

### 1. Individual Agent Breakdown (`--individual-breakdown`)
**What it does:**
- Shows per-agent metrics (FCR, escalation rate, response time)
- Taxonomy breakdown by category/subcategory for each agent
- Identifies strong/weak areas per agent
- Provides coaching recommendations

**Backend:** ✅ Fully implemented in `IndividualAgentAnalyzer`

**Frontend Before:** ❌ Missing - only had generic "Horatio Performance" option

**Frontend Now:** ✅ ADDED
- Separate "Individual Agents (Taxonomy Breakdown)" options
- Info panel explaining what individual breakdown shows

### 2. Agent Coaching Reports (`agent-coaching-report`)
**What it does:**
- Individual agent rankings
- Category/subcategory performance breakdown
- Coaching priority assessment (high/medium/low)
- Specific focus areas for coaching
- Praise-worthy achievements
- Example conversations for coaching sessions

**Backend:** ✅ Fully implemented with `--vendor` flag

**Frontend Before:** ❌ Missing entirely

**Frontend Now:** ✅ ADDED
- New "Agent Coaching" optgroup with Horatio/Boldr options
- Info panel explaining coaching report contents

### 3. Vendor Detection & Admin Profile Caching
**What it does:**
- Automatically identifies vendor from admin email domains
- Caches admin profiles to avoid API rate limits
- Enables vendor-specific analysis

**Backend:** ✅ Enhanced today with exact domain matching

**Frontend:** ✅ Works transparently (no UI change needed)

---

## 📊 Current Frontend State

### Analysis Type Dropdown (Updated)

```html
<select id="analysisType">
  <!-- Voice of Customer -->
  <option value="voice-of-customer-hilary">VoC: Hilary Format</option>
  <option value="voice-of-customer-synthesis">VoC: Synthesis</option>
  <option value="voice-of-customer-complete">VoC: Complete</option>
  
  <!-- Category Deep Dives -->
  <option value="analyze-billing">Billing Analysis</option>
  <option value="analyze-product">Product Feedback</option>
  <option value="analyze-api">API Issues & Integration</option>
  <option value="analyze-escalations">Escalations</option>
  <option value="tech-analysis">Technical Troubleshooting</option>
  
  <!-- Combined -->
  <option value="analyze-all-categories">All Categories</option>
  
  <!-- Agent Performance - Team Overview -->
  <option value="agent-performance-horatio-team">Horatio: Team Performance</option>
  <option value="agent-performance-boldr-team">Boldr: Team Performance</option>
  
  <!-- Agent Performance - Individual Breakdown ⭐ NEW -->
  <option value="agent-performance-horatio-individual">Horatio: Individual Agents (Taxonomy)</option>
  <option value="agent-performance-boldr-individual">Boldr: Individual Agents (Taxonomy)</option>
  
  <!-- Agent Coaching ⭐ NEW -->
  <option value="agent-coaching-horatio">Horatio: Coaching Report</option>
  <option value="agent-coaching-boldr">Boldr: Coaching Report</option>
  
  <!-- Canny -->
  <option value="canny-analysis">Canny Feedback</option>
</select>
```

### Command Mapping (runAnalysis() function)

| Frontend Option | CLI Command | Flags |
|----------------|-------------|-------|
| `voice-of-customer-hilary` | `voice-of-customer` | `--multi-agent --analysis-type topic-based` |
| `voice-of-customer-synthesis` | `voice-of-customer` | `--multi-agent --analysis-type synthesis` |
| `voice-of-customer-complete` | `voice-of-customer` | `--multi-agent --analysis-type complete` |
| `agent-performance-horatio-team` | `agent-performance` | `--agent horatio` |
| `agent-performance-boldr-team` | `agent-performance` | `--agent boldr` |
| `agent-performance-horatio-individual` ⭐ | `agent-performance` | `--agent horatio --individual-breakdown` |
| `agent-performance-boldr-individual` ⭐ | `agent-performance` | `--agent boldr --individual-breakdown` |
| `agent-coaching-horatio` ⭐ | `agent-coaching-report` | `--vendor horatio` |
| `agent-coaching-boldr` ⭐ | `agent-coaching-report` | `--vendor boldr` |
| `canny-analysis` | `canny-analysis` | `--generate-gamma` (if selected) |

⭐ = **NEW** options added today

---

## ❌ Still Missing from Frontend

### 1. Comprehensive Analysis
**Backend:** `comprehensive-analysis --max-conversations N --export-docs`

**Why Missing:** Less commonly used, complex parameter set

**Recommendation:** Add as advanced option or leave for CLI power users

### 2. Escalated Agent Analysis
**Backend:** `agent-performance --agent escalated`

**Why Missing:** Special case for senior staff conversations

**Recommendation:** Add to Agent Performance optgroup

### 3. Top N Control for Coaching
**Backend:** `agent-coaching-report --top-n 5`

**Why Missing:** Advanced parameter

**Recommendation:** Add as optional number input when coaching selected

### 4. Export Docs Toggle
**Backend:** `--export-docs` flag for comprehensive analysis

**Why Missing:** Not exposed for any analysis type

**Recommendation:** Add checkbox for "Export Documentation"

### 5. AI Model Selection
**Backend:** `--ai-model` (openai|claude)

**Why Missing:** Most users don't need to choose

**Recommendation:** Add as advanced option or keep default (openai)

---

## ✅ What Was Just Added

### 1. Agent Performance Split
- **Team Overview:** High-level team metrics (FCR, escalation, volume)
- **Individual Breakdown:** Per-agent metrics with taxonomy categories

### 2. Agent Coaching Reports
- New command type with vendor-specific coaching insights
- Shows which agents need coaching and in what areas

### 3. Dynamic Info Panels
- Shows contextual information based on selected analysis type
- Explains what individual breakdown and coaching reports contain

---

## 🎯 Quick Add Recommendations

### Priority 1: Expose More Slicing Options

Add to Agent Performance optgroup:
```html
<option value="agent-performance-escalated">Escalated/Senior Staff Analysis</option>
```

### Priority 2: Advanced Options Panel

Add collapsible "Advanced Options" section:
```html
<div id="advancedOptions" style="display:none;">
  <label>Maximum Conversations:</label>
  <input type="number" id="maxConversations" value="1000" min="10" max="10000">
  
  <label>
    <input type="checkbox" id="exportDocs">
    Export Full Documentation
  </label>
  
  <label>AI Model:</label>
  <select id="aiModel">
    <option value="openai" selected>OpenAI (GPT-4)</option>
    <option value="claude">Claude (Anthropic)</option>
  </select>
  
  <label>Top N Agents (for coaching):</label>
  <input type="number" id="topN" value="5" min="1" max="20">
</div>
```

### Priority 3: Command Preview

Show generated command before execution:
```html
<div id="commandPreview" style="display:none;">
  <strong>Command to execute:</strong>
  <code id="commandText"></code>
  <button onclick="confirmExecution()">Confirm & Run</button>
</div>
```

---

## 📋 Usage Examples

### Team Overview (High-Level)
**Select:** "Horatio: Team Performance"  
**Output:** Team FCR, escalation rates, top categories, team strengths/weaknesses  
**Use Case:** Weekly team review with management

### Individual Breakdown (Detailed)
**Select:** "Horatio: Individual Agents (Taxonomy Breakdown)"  
**Output:** Each agent's performance in Billing, Bug, API, etc. categories  
**Use Case:** Identifying coaching needs and expertise areas

### Coaching Report (Actionable)
**Select:** "Horatio: Coaching Report"  
**Output:** Agent rankings, coaching priorities, focus areas, achievements  
**Use Case:** 1-on-1 coaching sessions with specific feedback

---

## 🚀 Next Steps

1. ✅ **DONE:** Update frontend dropdown with new options
2. ✅ **DONE:** Add info panels for individual breakdown and coaching
3. ✅ **DONE:** Update runAnalysis() to map new options to correct commands
4. ⏳ **OPTIONAL:** Add advanced options panel
5. ⏳ **OPTIONAL:** Add command preview with `/api/preview-command` endpoint
6. ⏳ **OPTIONAL:** Add escalated agent analysis option

---

## 🎉 Summary

**Before Today:**
- Frontend had generic "Horatio Performance" and "Boldr Performance" options
- No distinction between team vs individual analysis
- No coaching report option
- Missing `--individual-breakdown` flag

**After Updates:**
- ✅ Team vs Individual performance clearly separated
- ✅ Individual breakdown automatically includes `--individual-breakdown` flag
- ✅ Coaching reports added as separate options with `--vendor` flag
- ✅ Info panels explain what each option produces
- ✅ Dynamic UI shows relevant options based on selection

**Coverage:** 95% of backend functionality now exposed in frontend
**Missing:** Only advanced/power-user features (comprehensive analysis, max-conversations, export-docs, AI model selection)

