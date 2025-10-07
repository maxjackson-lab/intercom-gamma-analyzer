# 📊 Data Export & General Query System Guide

This guide covers the new **spreadsheet export capabilities** and **general query system** that make the Intercom Analysis Tool a versatile data exploration platform.

## 🎯 **Overview**

The tool now supports:
- **📈 Spreadsheet Export**: Excel, CSV, JSON, Parquet formats
- **🔍 General Query System**: Flexible data exploration with pre-built and custom queries
- **📋 Cross-Reference Data**: Multiple export formats for data analysis and reporting

## 📊 **Data Export Commands**

### **Basic Export**
```bash
# Export last 30 days to Excel
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format excel

# Export with calculated metrics
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format excel --include-metrics

# Export to multiple formats
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format all
```

### **Export Formats**

#### **Excel Export** (`--export-format excel`)
Creates a comprehensive Excel workbook with multiple sheets:
- **Conversations**: Raw conversation data with all fields
- **Metrics_Summary**: Calculated metrics and statistics
- **Time_Analysis**: Time-based breakdowns (daily, hourly, weekly)
- **Topic_Analysis**: Topic categorization and analysis
- **Agent_Performance**: Agent response times and performance
- **Customer_Satisfaction**: CSAT ratings and satisfaction analysis

#### **CSV Export** (`--export-format csv`)
Creates separate CSV files for each data category:
- `export_YYYYMMDD_HHMMSS_conversations.csv`
- `export_YYYYMMDD_HHMMSS_metrics.csv`
- `export_YYYYMMDD_HHMMSS_time_analysis.csv`
- `export_YYYYMMDD_HHMMSS_topic_analysis.csv`
- `export_YYYYMMDD_HHMMSS_agent_performance.csv`
- `export_YYYYMMDD_HHMMSS_satisfaction.csv`

#### **JSON Export** (`--export-format json`)
Raw conversation data in JSON format for programmatic access:
- Complete conversation objects
- Metadata (export date, total count)
- Structured for easy parsing

#### **Parquet Export** (`--export-format parquet`)
Efficient columnar format for large datasets:
- Optimized for data analysis tools
- Smaller file sizes
- Fast read/write operations

## 🔍 **General Query System**

### **Available Query Types**

#### **1. Time-Based Queries**
```bash
# Last 7 days
python -m src.main query --query-type time_based --suggestion "Last 7 days"

# Last 30 days
python -m src.main query --query-type time_based --suggestion "Last 30 days"

# This month
python -m src.main query --query-type time_based --suggestion "This month"

# Last quarter
python -m src.main query --query-type time_based --suggestion "Last quarter"
```

#### **2. State-Based Queries**
```bash
# Open conversations
python -m src.main query --query-type state_based --suggestion "Open conversations"

# Closed conversations
python -m src.main query --query-type state_based --suggestion "Closed conversations"

# Snoozed conversations
python -m src.main query --query-type state_based --suggestion "Snoozed conversations"
```

#### **3. Source-Based Queries**
```bash
# Email conversations
python -m src.main query --query-type source_based --suggestion "Email conversations"

# Chat conversations
python -m src.main query --query-type source_based --suggestion "Chat conversations"

# Phone conversations
python -m src.main query --query-type source_based --suggestion "Phone conversations"
```

#### **4. Satisfaction-Based Queries**
```bash
# High satisfaction (4.5+)
python -m src.main query --query-type satisfaction_based --suggestion "High satisfaction (4.5+)"

# Low satisfaction (<3.0)
python -m src.main query --query-type satisfaction_based --suggestion "Low satisfaction (<3.0)"

# Rated conversations only
python -m src.main query --query-type satisfaction_based --suggestion "Rated conversations only"
```

#### **5. Geographic-Based Queries**
```bash
# US customers
python -m src.main query --query-type geographic_based --suggestion "US customers"

# European customers
python -m src.main query --query-type geographic_based --suggestion "European customers"

# Tier 1 countries
python -m src.main query --query-type geographic_based --suggestion "Tier 1 countries"
```

#### **6. Content-Based Queries**
```bash
# Billing related
python -m src.main query --query-type content_based --suggestion "Billing related"

# Technical issues
python -m src.main query --query-type content_based --suggestion "Technical issues"

# Product questions
python -m src.main query --query-type content_based --suggestion "Product questions"

# Account management
python -m src.main query --query-type content_based --suggestion "Account management"
```

### **Custom Queries**

#### **JSON Query Format**
```bash
# Custom query with JSON
python -m src.main query --custom-query '{"operator": "AND", "value": [{"field": "state", "operator": "=", "value": "open"}, {"field": "source.type", "operator": "=", "value": "email"}]}'
```

#### **Complex Query Examples**
```bash
# High satisfaction email conversations from US
python -m src.main query --custom-query '{"operator": "AND", "value": [{"field": "conversation_rating", "operator": ">=", "value": 4.5}, {"field": "source.type", "operator": "=", "value": "email"}, {"field": "contacts.location.country", "operator": "=", "value": "United States"}]}'

# Billing issues from last 30 days
python -m src.main query --custom-query '{"operator": "AND", "value": [{"field": "source.body", "operator": "~", "value": "billing"}, {"field": "created_at", "operator": ">=", "value": 1712016000}]}'
```

### **Query Suggestions**
```bash
# Show all available query suggestions
python -m src.main query-suggestions
```

## 📋 **Export Data Structure**

### **Conversations Sheet/CSV**
| Field | Description |
|-------|-------------|
| conversation_id | Unique conversation identifier |
| created_at | Conversation creation timestamp |
| updated_at | Last update timestamp |
| closed_at | Conversation close timestamp |
| state | Conversation state (open/closed/snoozed) |
| source_type | Communication channel (email/chat/phone) |
| source_subject | Email subject or chat title |
| source_body | Initial message content (truncated) |
| conversation_rating | CSAT rating (1-5) |
| tags | Conversation tags |
| contact_id | Customer contact ID |
| contact_email | Customer email address |
| contact_name | Customer name |
| contact_country | Customer country |
| contact_city | Customer city |
| user_tier | Customer tier (Pro/Plus/Free) |
| total_messages | Total messages in conversation |
| agent_messages | Number of agent responses |
| customer_messages | Number of customer messages |
| first_response_time_seconds | Time to first agent response |
| first_response_time_hours | Time to first agent response (hours) |
| resolution_time_seconds | Time to conversation close |
| resolution_time_hours | Time to conversation close (hours) |

### **Metrics Summary Sheet/CSV**
| Metric | Value | Type |
|--------|-------|------|
| Total Conversations | 1,234 | count |
| Closed Conversations | 1,100 | count |
| Resolution Rate | 89.1% | percentage |
| Average Response Time (hours) | 2.3 | time |
| Median Response Time (hours) | 1.8 | time |
| Average Rating | 4.2 | rating |
| Median Rating | 4.0 | rating |
| Conversations via Email | 800 | count |
| Conversations via Chat | 400 | count |
| Conversations from United States | 600 | count |
| Conversations from Canada | 200 | count |

### **Time Analysis Sheet/CSV**
| Field | Description |
|-------|-------------|
| conversation_id | Unique conversation identifier |
| date | Conversation date |
| hour | Hour of day (0-23) |
| day_of_week | Day of week (Monday-Sunday) |
| week | Week identifier (YYYY-WXX) |
| month | Month identifier (YYYY-MM) |
| quarter | Quarter identifier (YYYY-QX) |
| state | Conversation state |
| source_type | Communication channel |

### **Topic Analysis Sheet/CSV**
| Field | Description |
|-------|-------------|
| conversation_id | Unique conversation identifier |
| primary_topic | Main topic category |
| secondary_topics | Additional topic categories |
| is_billing_related | Boolean flag |
| is_technical_issue | Boolean flag |
| is_product_question | Boolean flag |
| is_account_related | Boolean flag |
| text_length | Total text length |
| word_count | Total word count |

### **Agent Performance Sheet/CSV**
| Field | Description |
|-------|-------------|
| agent_email | Agent email address |
| total_responses | Total number of responses |
| conversations_handled | Number of conversations handled |
| average_response_time_hours | Average response time |
| median_response_time_hours | Median response time |
| average_rating | Average CSAT rating |
| total_ratings | Number of ratings received |

### **Customer Satisfaction Sheet/CSV**
| Field | Description |
|-------|-------------|
| conversation_id | Unique conversation identifier |
| rating | CSAT rating (1-5) |
| rating_category | Rating category (Excellent/Good/Average/Poor/Very Poor) |
| source_type | Communication channel |
| country | Customer country |
| user_tier | Customer tier |
| created_at | Conversation creation timestamp |
| state | Conversation state |

## 🚀 **Use Cases**

### **1. Data Analysis & Reporting**
```bash
# Export comprehensive data for analysis
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format excel --include-metrics

# Use in Excel/Power BI for dashboards and reports
```

### **2. Customer Segmentation**
```bash
# Export high-value customers
python -m src.main query --query-type satisfaction_based --suggestion "High satisfaction (4.5+)" --export-format excel

# Export by geographic region
python -m src.main query --query-type geographic_based --suggestion "US customers" --export-format csv
```

### **3. Performance Analysis**
```bash
# Export agent performance data
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format excel

# Analyze response times and satisfaction by agent
```

### **4. Issue Tracking**
```bash
# Export technical issues
python -m src.main query --query-type content_based --suggestion "Technical issues" --export-format excel

# Export billing-related conversations
python -m src.main query --query-type content_based --suggestion "Billing related" --export-format csv
```

### **5. Trend Analysis**
```bash
# Export time-based data for trend analysis
python -m src.main export --start-date 2024-01-01 --end-date 2024-04-30 --export-format parquet

# Use with pandas, R, or other data analysis tools
```

## 🔧 **Advanced Usage**

### **Batch Processing**
```bash
# Export multiple months
for month in {1..6}; do
    python -m src.main export --start-date 2024-0$month-01 --end-date 2024-0$month-30 --export-format excel
done
```

### **Automated Reporting**
```bash
# Daily export script
#!/bin/bash
DATE=$(date -d "yesterday" +%Y-%m-%d)
python -m src.main export --start-date $DATE --end-date $DATE --export-format excel --include-metrics
```

### **Data Pipeline Integration**
```bash
# Export to Parquet for data pipeline
python -m src.main export --start-date 2024-04-01 --end-date 2024-04-30 --export-format parquet

# Import into data warehouse or analytics platform
```

## 📈 **Integration with Analysis Tools**

### **Excel/Power BI**
- Import Excel files directly
- Use CSV files for data connections
- Create dashboards and reports

### **Python Data Analysis**
```python
import pandas as pd

# Load exported data
df = pd.read_excel('export_20240401_120000.xlsx', sheet_name='Conversations')
metrics = pd.read_excel('export_20240401_120000.xlsx', sheet_name='Metrics_Summary')

# Perform analysis
avg_response_time = df['first_response_time_hours'].mean()
satisfaction_by_country = df.groupby('contact_country')['conversation_rating'].mean()
```

### **R Analysis**
```r
library(readxl)
library(dplyr)

# Load data
conversations <- read_excel("export_20240401_120000.xlsx", sheet = "Conversations")
metrics <- read_excel("export_20240401_120000.xlsx", sheet = "Metrics_Summary")

# Analysis
avg_response_time <- conversations %>% 
  summarise(avg_response = mean(first_response_time_hours, na.rm = TRUE))

satisfaction_trends <- conversations %>%
  group_by(contact_country) %>%
  summarise(avg_rating = mean(conversation_rating, na.rm = TRUE))
```

## 🎯 **Best Practices**

### **1. Data Export**
- Use `--include-metrics` for comprehensive analysis
- Export to Excel for stakeholder reports
- Use Parquet for large datasets and data pipelines
- Use CSV for simple data analysis

### **2. Query Building**
- Start with pre-built suggestions
- Use custom queries for specific business needs
- Combine multiple query types for complex analysis
- Test queries with small date ranges first

### **3. Performance**
- Use `--max-pages` for testing
- Export in batches for large date ranges
- Use Parquet format for large datasets
- Monitor API rate limits

### **4. Data Quality**
- Verify export completeness
- Check for missing or null values
- Validate date ranges and filters
- Review data structure before analysis

---

**The Intercom Analysis Tool is now a comprehensive data exploration platform that can export data in multiple formats and execute flexible queries for any business need!** 🚀

