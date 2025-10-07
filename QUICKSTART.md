# Quick Start Guide

Get up and running with the Intercom Conversation Trend Analyzer in 5 minutes!

## Step 1: Setup (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup script
python setup.py
```

## Step 2: Configure API Access (2 minutes)

**Option A: Interactive Setup (Recommended)**
```bash
python configure_api.py
```
This will guide you through getting your token and setting it up.

**Option B: Manual Setup**
1. **Get your Intercom Access Token**:
   - Go to your Intercom workspace
   - Settings → Integrations → Developer Hub
   - Create a new app or use existing one
   - Copy the Access Token

2. **Create .env file**:
   ```bash
   # Create .env file with your token
   echo "INTERCOM_ACCESS_TOKEN=your_actual_token_here" > .env
   ```

## Step 3: Test Connection (1 minute)

```bash
# Test your Intercom connection
python test_intercom_connection.py
```

This will verify your API key works and show you sample data from your Intercom instance.

You should see: `🎉 Connection test completed!`

## Step 4: Run Your First Analysis (1 minute)

```bash
# Test with small dataset (last 7 days, 2 pages)
python main.py --days 7 --max-pages 2
```

## Step 5: View Results

Check the `outputs/` directory:
- `summary.txt` - Quick overview
- `trend_report.txt` - Detailed analysis
- `*.csv` files - Data for Excel

## Common Commands

```bash
# Full analysis (last 6 months)
python main.py

# Last 30 days only
python main.py --days 30

# Search for specific text
python main.py --text-search "cache issues" --days 90

# Custom patterns
python main.py --patterns "error" "bug" "slow" --days 60

# Verbose output for debugging
python main.py --verbose --days 7
```

## Troubleshooting

**"Invalid access token"**
- Check your token in Intercom Developer Hub
- Ensure it has conversation read permissions

**"No conversations found"**
- Try a longer date range: `--days 30`
- Check if you have conversations in that period

**"Rate limit exceeded"**
- The tool handles this automatically
- For testing, use `--max-pages 2`

## Next Steps

1. **Explore the data**: Open CSV files in Excel
2. **Customize patterns**: Edit `config/analysis_config.yaml`
3. **Automate**: Set up scheduled runs
4. **Extend**: Add your own analysis functions

## Need Help?

- Check `README.md` for detailed documentation
- Run `python main.py --help` for all options
- Review logs in `intercom_analysis.log`

---

**You're ready to analyze!** 🚀
