# Intercom Analysis Tool - Deployment Guide

## 🚀 Quick Deployment Options

### **Top Recommendation: Railway.app**
**Why Railway?** 
- Zero-config deployments
- Automatic scaling
- Built-in environment management
- GitHub integration
- Free tier available

**Deploy to Railway:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Alternative Options

#### 1. **Modal Labs** (Serverless)
```bash
pip install modal
modal deploy src/main.py
```

#### 2. **AWS Lambda + EventBridge** (Scheduled)
- Deploy as Lambda function
- Schedule with EventBridge
- Use AWS Secrets Manager for API keys

#### 3. **Google Cloud Run + Cloud Scheduler**
- Containerize with Docker
- Deploy to Cloud Run
- Schedule with Cloud Scheduler

#### 4. **Render.com** (Simple)
- Connect GitHub repository
- Auto-deploy on push
- Environment variables in dashboard

## 📋 Required API Keys & Environment Variables

### **Required (Core Functionality)**
```bash
# Intercom API
INTERCOM_ACCESS_TOKEN=your_intercom_token_here

# OpenAI API (for sentiment analysis)
OPENAI_API_KEY=sk-your_openai_key_here
```

### **Optional (Enhanced Features)**
```bash
# Anthropic Claude (alternative AI model)
ANTHROPIC_API_KEY=sk-ant-your_claude_key_here

# Gamma API (for presentation generation)
GAMMA_API_KEY=your_gamma_key_here

# Intercom Workspace ID (for direct conversation links)
INTERCOM_WORKSPACE_ID=your_workspace_id_here
```

### **Configuration (Optional)**
```bash
# AI Model Preferences
VOC_DEFAULT_AI_MODEL=openai  # or claude
VOC_ENABLE_AI_FALLBACK=true
VOC_HISTORICAL_WEEKS=26

# Analysis Settings
DEFAULT_ANALYSIS_DAYS=30
MAX_CONVERSATIONS_PER_REQUEST=150
MIN_CONVERSATIONS_FOR_ANALYSIS=10
```

## 🛠️ What This App Can Do

### **Core Analysis Features**
1. **📊 Comprehensive Analysis**
   - Billing issues analysis
   - Product feedback analysis
   - API integration problems
   - Site performance issues
   - Technical troubleshooting trends

2. **🌍 Voice of Customer (NEW!)**
   - **46+ language support** (English, Spanish, French, German, Japanese, Chinese, Korean, Arabic, Hindi, etc.)
   - **Dynamic sentiment analysis** using ChatGPT/Claude
   - **Agent separation** (Finn AI, Boldr, Horatio, Gamma CX staff)
   - **Historical trend analysis** with weekly snapshots
   - **Automated insights generation**

3. **📈 Advanced Analytics**
   - Category-based filtering
   - Volume trend analysis
   - Sentiment scoring
   - Agent performance metrics
   - International customer insights

### **AI-Powered Features**
- **Dual AI Support**: OpenAI GPT-4 + Anthropic Claude
- **Automatic Fallback**: If one AI fails, automatically tries the other
- **Multilingual Analysis**: Works with any language ChatGPT/Claude supports
- **Cultural Context**: Understands cultural nuances in customer feedback
- **Confidence Scoring**: Provides confidence levels for all analysis

### **Output & Reporting**
- **JSON Analysis Results**: Structured data for further processing
- **Gamma Presentations**: Auto-generated presentations (Executive, Detailed, Training styles)
- **Excel/CSV Exports**: Spreadsheet-ready data
- **Rich CLI Output**: Beautiful terminal interface with progress bars
- **Historical Data**: Trend analysis over weeks/months

### **CLI Commands Available**
```bash
# Voice of Customer Analysis (NEW!)
python src/main.py voice-of-customer --start-date 2024-01-01 --end-date 2024-01-07

# Comprehensive Analysis
python src/main.py comprehensive-analysis --days 30 --generate-gamma

# Category-Specific Analysis
python src/main.py analyze-billing --days 7
python src/main.py analyze-product --days 14
python src/main.py analyze-api --days 30

# Gamma Presentation Generation
python src/main.py generate-gamma --input-file analysis_results.json

# Data Export
python src/main.py export-data --format excel --output-dir exports/
```

## 🔧 Technical Requirements

### **System Requirements**
- **Python**: 3.8 or higher
- **Memory**: 1-2GB RAM (for large datasets)
- **Storage**: 100MB+ for historical data
- **Network**: Stable internet for API calls

### **Dependencies**
All dependencies are in `requirements.txt`:
- Core: requests, pandas, numpy
- AI: openai, anthropic
- CLI: click, rich
- Data: duckdb, beautifulsoup4
- Testing: pytest, pytest-asyncio

## 🚀 Railway.app Deployment (Recommended)

### **Step 1: Prepare Repository**
```bash
# Ensure all files are committed
git add .
git commit -m "Ready for deployment"
git push origin main
```

### **Step 2: Deploy to Railway**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Set environment variables
railway variables set INTERCOM_ACCESS_TOKEN=your_token
railway variables set OPENAI_API_KEY=your_key
railway variables set ANTHROPIC_API_KEY=your_key  # optional

# Deploy
railway up
```

### **Step 3: Schedule Analysis**
```bash
# Add to Railway cron job or external scheduler
# Example: Run VoC analysis every Monday at 9 AM
0 9 * * 1 railway run python src/main.py voice-of-customer --start-date $(date -d "last monday" +%Y-%m-%d) --end-date $(date -d "last sunday" +%Y-%m-%d) --include-trends
```

## 📊 Usage Examples

### **Weekly Voice of Customer Report**
```bash
# Run every Monday for previous week
python src/main.py voice-of-customer \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --ai-model claude \
  --include-trends \
  --generate-gamma
```

### **Emergency Analysis**
```bash
# Quick analysis of today's conversations
python src/main.py voice-of-customer \
  --start-date $(date +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --no-fallback
```

### **Multi-Language Support Test**
```bash
# Test with various languages
python src/main.py voice-of-customer \
  --start-date 2024-01-01 \
  --end-date 2024-01-07 \
  --ai-model openai
```

## 🔍 Monitoring & Maintenance

### **Health Checks**
```bash
# Test API connections
python src/main.py test-connections

# Check data quality
python src/main.py validate-data --days 7
```

### **Logs & Debugging**
- All operations are logged with timestamps
- AI API calls are logged for cost tracking
- Error handling with detailed error messages
- Performance metrics (execution time, memory usage)

### **Cost Management**
- **OpenAI**: ~$0.01-0.03 per 1000 conversations
- **Claude**: ~$0.015-0.045 per 1000 conversations
- **Intercom**: Free (within rate limits)
- **Storage**: Minimal (JSON files)

## 🆘 Troubleshooting

### **Common Issues**
1. **API Key Errors**: Check environment variables
2. **No Conversations**: Verify date range and Intercom token
3. **AI Analysis Fails**: Enable fallback or check API keys
4. **Memory Issues**: Reduce conversation batch size

### **Support**
- Check logs in `logs/` directory
- Run with `--verbose` flag for detailed output
- Test individual components with unit tests

## 🎯 Next Steps After Deployment

1. **Set up monitoring** for API usage and costs
2. **Schedule regular analysis** (weekly/monthly)
3. **Configure alerts** for high error rates
4. **Train team** on interpreting results
5. **Integrate with existing workflows** (Slack, email, etc.)

---

**Ready to deploy?** Start with Railway.app for the easiest setup! 🚀
