# Intercom to Gamma Analysis Tool - Dual Mode

A comprehensive Python application that extracts Intercom conversation data and generates **two types of Gamma presentations**:

1. **Voice of Customer Analysis** - Monthly executive reports with specific metrics and insights
2. **General Purpose Trend Analysis** - Flexible reports for any time period with customizable focus areas

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

### Finn Performance Analysis
- Sub-topic performance breakdown (when SubTopicDetectionAgent is enabled)
- Data-rooted quality metrics: resolution rate, knowledge gap rate, escalation rate, average conversation rating
- Tier 2 sub-topics from Intercom data (tags, custom attributes, topics)
- Tier 3 emerging themes from LLM analysis

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
