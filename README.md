# Intercom to Gamma Analysis Tool - Dual Mode

A comprehensive Python application that extracts Intercom conversation data and generates **two types of Gamma presentations**:

1. **Voice of Customer Analysis** - Monthly executive reports with specific metrics and insights
2. **General Purpose Trend Analysis** - Flexible reports for any time period with customizable focus areas

> **⚡ Latest Update (v3.1.0):** Migrated to official Intercom Python SDK for improved reliability, type safety, and future compatibility. All custom Intercom API clients have been replaced with the official `python-intercom` SDK, providing better error handling, automatic pagination, and built-in retry logic.

## 🏗️ **Architecture**

This tool now uses the **official Intercom Python SDK** (`python-intercom`) for all API interactions, providing:
- Type-safe Pydantic models for all API entities
- Built-in pagination with `AsyncPager` support
- Comprehensive error handling with specific exception types
- Automatic rate limiting and retry logic
- Modern async/await patterns for efficient data fetching

The SDK integration is wrapped in `IntercomSDKService` which maintains backward compatibility with existing analyzers and services while leveraging the official SDK's capabilities.

## 🎯 **Key Features**

### **Voice of Customer Metrics**
- **Volume Metrics**: Total conversations, AI resolution rate, response times
- **Efficiency Metrics**: Median first response time, handling time, resolution time
- **Satisfaction**: CSAT scores by user tier (Pro, Plus, Free)
- **Channel Analysis**: Chat vs Email performance
- **Topic Breakdown**: Billing, Product Questions, Account Questions
- **Geographic Segmentation**: Tier 1 countries with specific metrics
- **Friction Points**: Common customer pain points and escalations
- **Success Stories**: Positive customer feedback and quotes

### **General Purpose Analysis**
- **Flexible time periods** (daily, weekly, monthly, custom ranges)
- **Customizable metrics** based on specific business questions
- **Ad-hoc insights** for one-off investigations
- **Trend identification** across any dimension

## 🚀 **Quick Start**

### **1. Installation**
```bash
# Clone the repository
git clone <repository-url>
cd intercom-analyzer

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
INTERCOM_ACCESS_TOKEN=your_intercom_token_here
OPENAI_API_KEY=your_openai_api_key_here
GAMMA_API_KEY=your_gamma_api_key_here  # Optional
```

### **3. Test Setup**
```bash
python -m src.main test
```

### **4. Run Analysis**

#### **Voice of Customer (Monthly Executive Report)**
```bash
python -m src.main voice --month 5 --year 2024 --tier1-countries "US,Brazil,Canada,Mexico,France,UK,Germany,Spain,South Korea,Japan,Australia" --generate-gamma
```

#### **General Trend Analysis**
```bash
python -m src.main trends --start-date 2024-05-01 --end-date 2024-05-31 --focus-areas "billing,product,escalations" --generate-gamma
```

#### **Custom Analysis**
```bash
python -m src.main custom --prompt-file custom_prompts/feature_launch_analysis.txt --start-date 2024-05-15 --end-date 2024-05-31 --generate-gamma
```

## 📊 **Usage Examples**

### **Voice of Customer Analysis**
```bash
# Monthly executive report for May 2024
python -m src.main voice --month 5 --year 2024 --generate-gamma

# With custom tier 1 countries
python -m src.main voice --month 5 --year 2024 --tier1-countries "US,Canada,UK,Germany" --generate-gamma
```

### **VOC-V2 Narrative Mode (Weekly Ops Readout)**
```bash
# Last week with digest narrative + Gamma deck
python src/main.py voc-v2 --time-period week --generate-gamma --digest-mode

# Custom range with test data preview
python src/main.py voc-v2 --start-date 2025-11-12 --end-date 2025-11-19 --test-mode --test-data-count 500
```

VOC-V2 produces the data-rich narrative shared in Hilary's weekly operations meeting:
- Executive storyline that ties topics, Fin gaps, and BPO workloads together
- Embedded Horatio/Boldr summary so vendor performance stays visible
- Inline quotes with Intercom links plus prioritized actions
- Optional `--digest-mode` for a three-minute skim

### **Agent Evaluation (Individual Breakdown)**
```bash
# Horatio weekly individual evaluation with mock data
python src/main.py agent-eval --vendor horatio --time-period week --test-mode --test-data-count micro

# Boldr custom range with Gamma deck
python src/main.py agent-eval --vendor boldr --start-date 2025-11-01 --end-date 2025-11-21 --generate-gamma
```

`agent-eval` is a shortcut to the individual breakdown workflow—Horatio, Boldr, or escalated teams—with taxonomy focus (`--filter-category Billing`) and Gamma export parity with the core agent performance command.

### **Trend Analysis**
```bash
# Last 30 days with billing focus
python -m src.main trends --start-date 2024-04-01 --end-date 2024-04-30 --focus-areas "billing,payment,subscription"

# Custom date range with multiple focus areas
python -m src.main trends --start-date 2024-03-01 --end-date 2024-03-31 --focus-areas "product,technical,escalations" --custom-prompt "Focus on customer satisfaction trends"

# Generate Gamma presentation
python -m src.main trends --start-date 2024-05-01 --end-date 2024-05-31 --generate-gamma --output-format gamma
```

### **Custom Analysis**
```bash
# Create custom prompt file
echo "Analyze customer feedback trends and identify opportunities for product improvement" > custom_prompts/product_feedback.txt

# Run custom analysis
python -m src.main custom --prompt-file custom_prompts/product_feedback.txt --start-date 2024-05-01 --end-date 2024-05-31
```

## 🏗️ **Project Structure**

```
intercom-analyzer/
├── src/
│   ├── config/
│   │   ├── settings.py           # Pydantic settings
│   │   ├── prompts.py            # Prompt templates for both modes
│   │   └── metrics_config.py     # Metric definitions and calculations
│   ├── services/
│   │   ├── intercom_service.py   # Intercom API integration
│   │   ├── metrics_calculator.py # Business metrics calculations
│   │   ├── openai_client.py      # OpenAI GPT-4o integration
│   │   └── gamma_client.py       # Gamma presentation generation
│   ├── models/
│   │   └── analysis_models.py    # Pydantic data models
│   ├── analyzers/
│   │   ├── base_analyzer.py      # Base analysis class
│   │   ├── voice_analyzer.py     # Voice of customer analysis
│   │   └── trend_analyzer.py     # General purpose trend analysis
│   ├── agents/
│   │   ├── base_agent.py         # Base agent class
│   │   ├── fin_performance_agent.py # Finn AI performance analysis
│   │   └── subtopic_detection_agent.py # Sub-topic detection
│   ├── utils/
│   │   └── logger.py             # Logging utility
│   └── main.py                   # CLI application entry point
├── requirements.txt
├── .env.example
├── README.md
└── pyproject.toml
```

## 🤖 **Multi-Agent Workflow**

The TopicOrchestrator coordinates a 7-phase analysis pipeline:

### **Phase 1: Segmentation**
- Separates paid vs free tier conversations
- Identifies Finn AI-participated conversations
- Segments by customer type and language

### **Phase 2: Topic Detection**
- Detects Tier 1 topics from Intercom data
- Calculates topic distribution and volume
- Maps conversations to primary topics

### **Phase 2.5: Sub-Topic Detection** (NEW)
- **Extracts Tier 2 sub-topics** from Intercom structured data (tags, custom attributes, conversation topics)
- **Discovers Tier 3 emerging themes** using LLM semantic analysis
- **Calculates percentage breakdowns** for sub-topics within each Tier 1 category
- **Provides granular context** for downstream Finn performance and output formatting
- Runs after Topic Detection but before Per-Topic Analysis

### **Phase 3: Per-Topic Analysis**
- Analyzes sentiment for each topic (parallel execution)
- Extracts representative examples
- Generates topic-specific insights

### **Phase 4: Finn AI Performance Analysis**
- Sub-topic performance breakdown (when SubTopicDetectionAgent is enabled)
- Data-rooted quality metrics: resolution rate, knowledge gap rate, escalation rate, average conversation rating
- Tier 2 sub-topics from Intercom data (tags, custom attributes, topics)
- Tier 3 emerging themes from LLM analysis
- Separate analysis for free vs paid tiers

### **Phase 5: Trend Analysis**
- Identifies week-over-week trends
- Highlights significant changes in volume, sentiment, and topics
- Provides trend interpretations

### **Phase 6: Output Formatting**
The OutputFormatterAgent formats all analysis results into Hilary's exact card structure for Gamma presentations:
- **3-tier sub-topic hierarchies** within topic cards
- **Tier 2 sub-topics** from Intercom data (tags, custom attributes, topics)
- **Tier 3 AI-discovered themes** from LLM analysis
- **Sub-topic performance metrics** in Finn cards (resolution rate, knowledge gaps, escalation rate, average rating)
- **Graceful backward compatibility** - handles absence of sub-topic data seamlessly

### **Workflow Metrics**
The orchestrator tracks comprehensive metrics across all phases:
- **Phase timings**: Execution time for each phase including sub-topic detection
- **LLM usage**: Total token counts and API calls
- **Sub-topic statistics**: Tier 2 and Tier 3 counts per topic
- **Agent performance**: Success rates and confidence scores
- **Quality indicators**: Example counts, topic coverage, error rates

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Required
INTERCOM_ACCESS_TOKEN=your_token_here
OPENAI_API_KEY=your_openai_key_here

# Optional
GAMMA_API_KEY=your_gamma_key_here
DEFAULT_TIER1_COUNTRIES=US,Brazil,Canada,Mexico,France,UK,Germany,Spain,South Korea,Japan,Australia
OUTPUT_DIRECTORY=outputs
LOG_LEVEL=INFO
```

### **Analysis Configuration**
Edit `src/config/metrics_config.py` to customize:
- Metric definitions and calculations
- Business KPI configurations
- Analysis parameters

## 📈 **Output Formats**

### **Voice of Customer Reports**
- **Executive Summary** with key metrics and performance assessment
- **Tier 1 Country Analysis** with specific regional insights
- **Month-over-Month Comparisons** for trend identification
- **Detailed Breakdowns** by topic, channel, and satisfaction
- **Customer Quotes** with context and significance
- **Actionable Recommendations** for support optimization

### **Trend Analysis Reports**
- **Volume Trends** over time with peak analysis
- **Response Time Trends** with efficiency metrics
- **Satisfaction Trends** with sentiment analysis
- **Topic Trends** with keyword frequency analysis
- **Custom Insights** based on focus areas
- **Trend Explanations** with business implications

### **Output Files**
- **Markdown Reports** (`*.md`) - Human-readable analysis
- **JSON Data** (`*.json`) - Structured data for further processing
- **Gamma Presentations** - Professional presentations with images and formatting

## 🎨 **Gamma Integration**

The tool automatically generates professional Gamma presentations with:
- **Executive-ready formatting** matching business standards
- **Unsplash images** for visual appeal
- **Proper markdown structure** optimized for Gamma
- **Interactive elements** and professional styling

## 🖥️ **Web User Interface**

Everything now runs from **one FastAPI service** (`deploy/railway_web.py`), powered by the modular routers in `deploy/web/`.

### **Unified Analysis UI**
- **Purpose**: Run new analyses, monitor streaming output, browse files, trigger background jobs, and jump into the historical timeline.
- **Features**:
  - Interactive config form for CLI-equivalent analyses
  - Real-time SSE console with keepalive + resume support
  - AI model selection, sample/test mode toggles, digest mode, troubleshooting flags
  - Files tab with live output discovery + ZIP downloads
  - Links to Gamma decks, download logs, Slack notify button
- **Access**:
  - Local: `python deploy/railway_web.py` → `http://localhost:8000`
  - Production: Railway deployment URL defined in `railway.toml`
- **Navigation**: Click "📊 View Historical Analysis" to open `/history` without leaving the service

### **Historical Timeline (Same Service)**
- **Purpose**: Explore weekly/monthly/quarterly snapshots, compare periods, and mark reviews.
- **URL:** `GET /history` (plus `/analysis/view/{id}` and `/analysis/compare/{current}/{prior}`)
- **Features**:
  - Timeline with review status indicators
  - Topic trend charts (Chart.js) when ≥4 snapshots
  - Snapshot detail + period comparison HTML views
  - Review management with bearer token auth
- **Access**:
  - Local/prod: same host as the main UI (`/history`)
  - No more dual deployments or `HISTORICAL_UI_URL`

---

## 📊 **Historical Insights Timeline UI (Details)**

The Historical Timeline UI provides a visual interface for exploring historical Voice of Customer analysis snapshots.

### **Features**

- **Timeline View**: Browse weekly, monthly, and quarterly analysis snapshots
- **Visual Indicators**: 
  - ✓ Reviewed snapshots (green border)
  - ⭐ Current period (orange highlight)
  - Future periods (dashed border)
- **Review Management**: Mark snapshots as reviewed with notes
- **Trend Visualization**: Chart.js charts show topic volume trends (when ≥4 weeks of data)
- **Comparison View**: Side-by-side comparison of any two periods
- **Snapshot Details**: View full analysis reports for any period

### **Accessing the UI**

**Local Development:** `python deploy/railway_web.py` then visit `http://localhost:8000/history`  
**Railway Deployment:** Same base URL as the chat UI—just append `/history`

### **API Endpoints**

**Public Endpoints (No Auth Required):**
- `GET /history` - Timeline UI
- `GET /api/snapshots/list` - List all snapshots
- `GET /api/snapshots/{id}` - Get single snapshot
- `GET /api/snapshots/timeseries` - Get time-series data for charts
- `GET /analysis/history` - Timeline UI (same as root)
- `GET /analysis/view/{id}` - Snapshot detail view
- `GET /analysis/compare/{current}/{prior}` - Comparison view
- `GET /health` - Health check

**Protected Endpoints (Require Auth Token):**
- `POST /api/snapshots/{id}/review` - Mark snapshot as reviewed
  - Header: `Authorization: Bearer <token>`
  - Body: `{"reviewed_by": "user@example.com", "notes": "Optional notes"}`

### **Authentication**

Set the `EXECUTION_API_TOKEN` environment variable to enable authentication for review endpoints **and** secure `/execute*`/`/outputs/*` routes:

```bash
export EXECUTION_API_TOKEN="your-secret-token"
```

If not set, the app runs in development mode (no auth required).

### **Data Storage**

Snapshots are automatically saved to DuckDB after each VoC analysis. The database includes:
- Analysis snapshots (weekly/monthly/quarterly)
- Comparative analyses (week-over-week deltas)
- Metrics time-series (for trend charts)

### **Historical Context**

The UI displays available capabilities based on data history:
- **Week 1**: Basic snapshot viewing
- **Week 2+**: Week-over-week comparison
- **Week 4+**: Trend analysis and forecasting
- **Week 12+**: Seasonality detection

## 🔍 **API Integration**

### **Intercom API**
- **Complete data fetching** with pagination (no 150 limit)
- **Rate limiting** and error handling
- **Flexible querying** by date range, text search, and filters
- **Real-time progress tracking** for large datasets

### **OpenAI Integration**
- **GPT-4o powered insights** for sophisticated analysis
- **Customizable prompts** for different analysis types
- **Sentiment analysis** and trend identification
- **Executive-friendly summaries** and recommendations

### **Gamma API**
- **Professional presentation generation**
- **Template customization** and styling options
- **Image integration** and visual enhancements
- **Export options** for different formats

## 🧪 **Verification & Diagnostic Scripts**

The tool includes verification scripts to help operators validate date calculations, API filters, and conversation counts:

### **1. Verify Date Calculations** (`scripts/verify_date_calculation.py`)
Prints Pacific and UTC timestamps with expected API filter windows to verify date boundary inclusion.

```bash
# Verify a single date
python scripts/verify_date_calculation.py --date 2024-05-15

# Verify a date range
python scripts/verify_date_calculation.py --start-date 2024-05-01 --end-date 2024-05-31

# Verify current date
python scripts/verify_date_calculation.py --date today
```

**Output includes:**
- Pacific and UTC timestamp conversions
- Unix timestamp values for API filters
- Expected boundary inclusion behavior
- Example conversation timestamps and their inclusion status

### **2. Test API Date Filters** (`scripts/test_api_date_filter.py`)
Calls `fetch_conversations_by_date_range()` for tight windows and validates that returned conversations match the requested date range.

```bash
# Test a single date
python scripts/test_api_date_filter.py --date 2024-05-15

# Test a tight date range (3 days)
python scripts/test_api_date_filter.py --start-date 2024-05-01 --end-date 2024-05-03

# Test with conversation limit (faster testing)
python scripts/test_api_date_filter.py --start-date 2024-05-15 --end-date 2024-05-15 --max 100
```

**Output includes:**
- Requested vs actual date ranges in results
- Boundary validation (earliest/latest conversations)
- Detection of conversations outside requested range
- Sample timestamps from fetched data
- Distribution by day

### **3. Diagnose Conversation Counts** (`scripts/diagnose_conversation_count.py`)
Estimates counts over date ranges using `get_conversation_count()` and compares with chunked fetching to verify consistency.

```bash
# Diagnose last 7 days
python scripts/diagnose_conversation_count.py --days 7

# Diagnose last 30 days (skip fetch for speed)
python scripts/diagnose_conversation_count.py --days 30 --skip-fetch

# Diagnose specific date range
python scripts/diagnose_conversation_count.py --start-date 2024-05-01 --end-date 2024-05-31

# Diagnose with fetch limit (faster)
python scripts/diagnose_conversation_count.py --days 7 --max 500
```

**Output includes:**
- API count vs fetched count comparison
- Discrepancy percentage and analysis
- Possible explanations for differences
- Date range validation in fetched data
- Daily distribution with deviation from average

### **Quick Operator Checks**

Use these commands for routine verification:

```bash
# Quick check: Verify today's date calculation
python scripts/verify_date_calculation.py --date today

# Quick check: Test API filter for today (limited fetch)
python scripts/test_api_date_filter.py --date today --max 50

# Quick check: Compare counts for last 7 days (skip full fetch)
python scripts/diagnose_conversation_count.py --days 7 --skip-fetch
```

## 🚀 **Advanced Usage**

### **Custom Prompts**
Create custom analysis prompts in `custom_prompts/` directory:

```bash
# custom_prompts/feature_launch_analysis.txt
Analyze customer feedback related to the new feature launch:
- Identify common issues and pain points
- Measure adoption and usage patterns
- Provide recommendations for improvement
- Include specific customer quotes and examples
```

### **Batch Processing**
```bash
# Analyze multiple months
for month in {1..6}; do
    python -m src.main voice --month $month --year 2024 --generate-gamma
done
```

### **Automated Reporting**
Set up cron jobs for automated monthly reports:
```bash
# Monthly Voice of Customer report
0 9 1 * * cd /path/to/intercom-analyzer && python -m src.main voice --month $(date +%m) --year $(date +%Y) --generate-gamma
```

## 🛠️ **Development**

### **Running Tests**
```bash
python -m pytest tests/
```

### **Code Quality**
```bash
# Format code
black src/
isort src/

# Type checking
mypy src/
```

### **Adding New Metrics**
1. Define metric in `src/config/metrics_config.py`
2. Implement calculation in `src/services/metrics_calculator.py`
3. Add to analysis models in `src/models/analysis_models.py`
4. Update prompt templates in `src/config/prompts.py`

## 📋 **Requirements**

- **Python 3.9+**
- **Intercom API access** with conversation read permissions
- **OpenAI API key** for GPT-4o access
- **Gamma API key** (optional, for presentation generation)

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For issues or questions:
1. Check the troubleshooting section in the README
2. Review logs in `outputs/intercom_analysis.log`
3. Test with small datasets first
4. Verify API keys and permissions

---

**Transform your Intercom data into actionable insights with professional Gamma presentations!** 🚀
