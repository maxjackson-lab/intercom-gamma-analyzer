# 🎯 Intercom Analysis Tool - App Overview

## What This App Does

**Transform your Intercom customer conversations into actionable business insights with AI-powered analysis.**

## 🚀 Key Features

### **1. Voice of Customer Analysis (NEW!)**
- **🌍 46+ Languages**: English, Spanish, French, German, Japanese, Chinese, Korean, Arabic, Hindi, and more
- **🤖 Dual AI Models**: OpenAI GPT-4 + Anthropic Claude with automatic fallback
- **👥 Agent Separation**: Distinguish between Finn AI, Boldr, Horatio, and Gamma CX staff
- **📈 Historical Trends**: Track sentiment and volume changes over time
- **🎯 Automated Insights**: Generate actionable recommendations

### **2. Comprehensive Analysis**
- **💰 Billing Issues**: Identify payment problems and subscription concerns
- **🔧 Product Feedback**: Analyze feature requests and usability issues
- **🌐 API Integration**: Track technical integration problems
- **⚡ Site Performance**: Monitor website and app performance issues
- **🛠️ Technical Support**: Analyze troubleshooting patterns

### **3. AI-Powered Intelligence**
- **🧠 Smart Sentiment**: Dynamic analysis using ChatGPT/Claude
- **🌐 Multilingual**: Works with any language automatically
- **📊 Confidence Scoring**: Know how reliable each analysis is
- **🔄 Fallback System**: If one AI fails, automatically tries another
- **📝 Cultural Context**: Understands cultural nuances in feedback

### **4. Beautiful Outputs**
- **📊 Gamma Presentations**: Auto-generated slides (Executive, Detailed, Training)
- **📈 Rich CLI**: Beautiful terminal interface with progress bars
- **📋 JSON Data**: Structured results for further processing
- **📊 Excel/CSV**: Spreadsheet-ready exports
- **🔗 Direct Links**: Click to view original Intercom conversations

## 🎯 Perfect For

### **Customer Success Teams**
- Track customer satisfaction trends
- Identify at-risk customers early
- Monitor agent performance
- Generate weekly/monthly reports

### **Product Teams**
- Prioritize feature requests
- Understand user pain points
- Track product sentiment
- Generate product insights

### **Support Teams**
- Identify common issues
- Track resolution patterns
- Monitor team performance
- Optimize support processes

### **Leadership**
- Executive summaries
- Trend analysis
- Performance metrics
- Strategic insights

## 🚀 Quick Start

### **1. Get API Keys**
```bash
# Required
INTERCOM_ACCESS_TOKEN=your_intercom_token
OPENAI_API_KEY=sk-your_openai_key

# Optional (for enhanced features)
ANTHROPIC_API_KEY=sk-ant-your_claude_key
GAMMA_API_KEY=your_gamma_key
```

### **2. Run Analysis**
```bash
# Voice of Customer (NEW!)
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07

# Comprehensive Analysis
python src/main.py comprehensive-analysis --days 30 --generate-gamma

# Category-Specific
python src/main.py analyze-billing --days 7
```

### **3. Deploy (Recommended: Railway.app)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

## 📊 Example Outputs

### **Voice of Customer Results**
```json
{
  "analysis_results": {
    "Billing": {
      "volume": 25,
      "sentiment": "positive",
      "confidence": 0.85,
      "examples": ["Thank you so much! This really helped."],
      "agent_breakdown": {
        "finn_ai": 15,
        "boldr_support": 10
      },
      "language_breakdown": {
        "en": 20,
        "es": 5
      }
    }
  },
  "insights": [
    "Top volume category: Billing (25 conversations)",
    "Strong positive sentiment in Billing (confidence: 0.85)"
  ]
}
```

### **CLI Output**
```
🎯 Voice of Customer Analysis
================================
Date Range: 2024-01-01 to 2024-01-07
AI Model: openai
Fallback: enabled

📊 Found 150 conversations
🌍 Analyzing sentiment in 8 languages
🤖 Processing with OpenAI GPT-4
📈 Generating insights...

✅ Analysis completed in 15.2s
📁 Results saved to: outputs/voc_analysis_20240115_103045.json

🔍 Key Insights:
• Top volume topic: 'Billing' with 25 conversations
• Sentiment for 'Billing' is predominantly positive (confidence: 0.85)
• Finn AI feedback shows a positive trend (volume: 15)
• Future Look: AI recommends focusing on proactive support for emerging billing issues
```

## 🌟 Why This App is Special

### **1. Truly Multilingual**
- **46+ languages** supported out of the box
- **Dynamic detection** - no hardcoded language lists
- **Cultural context** - understands nuances across cultures
- **High accuracy** - 0.80-0.90 confidence scores

### **2. Intelligent Agent Separation**
- **Finn AI**: Intercom's AI assistant
- **Boldr**: External support team
- **Horatio**: External support team
- **Gamma CX**: Internal customer experience
- **Mixed**: Multiple agent types
- **Customer Only**: No agent responses

### **3. Dual AI Power**
- **OpenAI GPT-4**: Fast, reliable analysis
- **Anthropic Claude**: Alternative perspective
- **Automatic Fallback**: Never fails due to AI issues
- **Cost Optimized**: Choose your preferred model

### **4. Production Ready**
- **Comprehensive Testing**: 100+ unit tests
- **Error Handling**: Graceful degradation
- **Logging**: Detailed operation logs
- **Performance**: Optimized for large datasets
- **Documentation**: Complete user and developer guides

## 🎯 Use Cases

### **Weekly Reports**
```bash
# Every Monday, analyze previous week
python src/main.py voice-of-customer \
  --start-date $(date -d "last monday" +%Y-%m-%d) \
  --end-date $(date -d "last sunday" +%Y-%m-%d) \
  --include-trends
```

### **Emergency Analysis**
```bash
# Quick analysis of today's conversations
python src/main.py voice-of-customer \
  --start-date $(date +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d)
```

### **Monthly Deep Dive**
```bash
# Comprehensive monthly analysis
python src/main.py comprehensive-analysis \
  --days 30 \
  --generate-gamma \
  --gamma-style executive
```

## 🚀 Ready to Deploy?

**Top Recommendation: Railway.app**
- Zero-config deployment
- Automatic scaling
- Built-in environment management
- Free tier available

**Get started in 5 minutes:**
1. Get your API keys
2. Deploy to Railway
3. Run your first analysis
4. Generate beautiful reports

---

**Transform your customer conversations into actionable insights today!** 🎯✨
