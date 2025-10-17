# Railway.app Deployment Guide

## Overview

This guide covers deploying the Intercom Analysis Tool to Railway.app with both web-based chat interface and scheduled execution using cron jobs.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI**: Install with `npm install -g @railway/cli`
3. **API Keys**: Ensure you have all required API keys

## Setup Steps

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Authenticate with Railway

```bash
railway login
```

### 3. Initialize Railway Project

```bash
railway init
```

### 4. Set Environment Variables

Set your API keys as environment variables:

```bash
railway variables set INTERCOM_ACCESS_TOKEN=your_intercom_token
railway variables set OPENAI_API_KEY=your_openai_key
railway variables set GAMMA_API_KEY=your_gamma_key
railway variables set INTERCOM_WORKSPACE_ID=your_workspace_id
```

### 5. Deploy the Application

#### Web Interface Deployment

For the web-based chat interface:

```bash
railway up
```

This will deploy the web interface accessible at your Railway URL.

#### Cron Job Deployment

For scheduled analysis jobs:

```bash
railway up --environment cron
```

This will deploy the cron job service for scheduled analysis.

### 6. Set Up Cron Jobs

Railway supports cron jobs through environment variables and scheduled deployments.

#### Weekly Analysis Cron

```bash
railway variables set ANALYSIS_TYPE=weekly
railway variables set CRON_SCHEDULE="0 9 * * 1"  # Every Monday at 9 AM UTC
```

#### Monthly Analysis Cron

```bash
railway variables set ANALYSIS_TYPE=monthly
railway variables set CRON_SCHEDULE="0 9 1 * *"  # 1st of every month at 9 AM UTC
```

#### Custom Analysis Cron

```bash
railway variables set ANALYSIS_TYPE=custom
railway variables set ANALYSIS_START_DATE=2024-01-01
railway variables set ANALYSIS_END_DATE=2024-01-07
railway variables set MAX_CONVERSATIONS=2000
railway variables set GAMMA_STYLE=executive
railway variables set GAMMA_EXPORT=pdf
```

## Web Interface Features

The web-based chat interface provides:

### Natural Language Processing
- **Command Translation**: Convert natural language to CLI commands
- **Custom Filter Building**: Generate complex filters from descriptions
- **Feature Suggestions**: Intelligent suggestions for unimplemented features

### Security Features
- **Input Validation**: Multi-layer security validation
- **Command Whitelisting**: Only approved commands can be executed
- **Human-in-the-Loop**: Approval workflows for high-risk operations

### API Endpoints
- `GET /` - Web chat interface
- `POST /chat` - Process chat queries
- `GET /health` - Health check
- `GET /api/commands` - List available commands
- `GET /api/filters` - List supported filters
- `GET /api/stats` - Performance statistics

## Configuration

### Railway.json Settings

The `railway.json` file configures:
- **Builder**: Dockerfile for consistent builds
- **Start Command**: Web server startup command
- **Health Check**: Basic health endpoint
- **Restart Policy**: Automatic restart on failure

### Environment Variables

Required environment variables:
- `INTERCOM_ACCESS_TOKEN`: Your Intercom API token
- `OPENAI_API_KEY`: Your OpenAI API key
- `GAMMA_API_KEY`: Your Gamma API key
- `INTERCOM_WORKSPACE_ID`: Your Intercom workspace ID

Optional configuration:
- `ANALYSIS_TYPE`: weekly, monthly, or custom
- `MAX_CONVERSATIONS`: Maximum conversations to analyze
- `GAMMA_STYLE`: executive, detailed, or training
- `GAMMA_EXPORT`: pdf or pptx

## Running Analysis

### Manual Execution

Run analysis manually using Railway CLI:

```bash
# Weekly analysis
railway run python deploy/railway_cron.py

# With custom environment
railway run --env ANALYSIS_TYPE=weekly python deploy/railway_cron.py
```

### Scheduled Execution

Railway automatically runs cron jobs based on the `CRON_SCHEDULE` environment variable.

### Web Interface

Access your Railway dashboard to:
- View deployment logs
- Monitor resource usage
- Manage environment variables
- Trigger manual deployments

## Monitoring and Logs

### View Logs

```bash
railway logs
```

### Follow Logs

```bash
railway logs --follow
```

### Check Status

```bash
railway status
```

## Cost Optimization

### Resource Limits

Railway automatically scales resources based on usage. Monitor costs in the dashboard.

### Execution Time

Optimize analysis parameters to reduce execution time:
- Limit `MAX_CONVERSATIONS` for faster runs
- Use `executive` style for quicker Gamma generation
- Skip exports for development runs

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Timeout Errors**: Increase timeout in Railway settings
3. **Memory Errors**: Railway automatically scales memory
4. **Environment Variable Errors**: Verify all required variables are set

### Debug Mode

Run with debug logging:

```bash
railway variables set DEBUG=true
railway run python deploy/railway_cron.py
```

### Local Testing

Test the cron script locally:

```bash
# Set environment variables
export INTERCOM_ACCESS_TOKEN=your_token
export OPENAI_API_KEY=your_key
export GAMMA_API_KEY=your_key
export INTERCOM_WORKSPACE_ID=your_id
export ANALYSIS_TYPE=weekly

# Run the script
python deploy/railway_cron.py
```

## Security Best Practices

1. **Environment Variables**: Never commit API keys to version control
2. **Access Control**: Use Railway's team features for collaboration
3. **Network Security**: Railway provides secure, isolated environments
4. **Data Privacy**: No data is stored on Railway's infrastructure

## Scaling Considerations

### High Volume Analysis

For large datasets (>5000 conversations):
- Consider breaking into smaller date ranges
- Use multiple Railway services for parallel processing
- Monitor memory usage in the dashboard

### Concurrent Execution

Railway handles:
- Automatic scaling
- Load balancing
- Resource allocation

## Integration with External Systems

### Webhook Integration

Add webhook notifications to the cron script:

```python
import requests

def notify_completion(result):
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json=result)
```

### Database Integration

Store results in external databases:

```python
import psycopg2

def store_results(result):
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    # Store results
```

## Maintenance

### Updates

To update the deployment:

1. Push changes to your repository
2. Railway automatically redeploys
3. Monitor logs for any issues

### Monitoring

Set up alerts for:
- Deployment failures
- High execution times
- Resource usage spikes

## Comparison with Other Platforms

### Railway vs Modal

| Feature | Railway | Modal |
|---------|---------|-------|
| Setup | Simple | Moderate |
| Cost | Pay-per-use | Pay-per-use |
| Scaling | Automatic | Manual |
| Cron Jobs | Environment-based | Function-based |

### Railway vs GitHub Actions

| Feature | Railway | GitHub Actions |
|---------|---------|----------------|
| Setup | Simple | Moderate |
| Cost | Pay-per-use | Free tier |
| Execution Time | No limits | 6 hours max |
| Persistence | No | No |

## Support

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Community**: [Railway Discord](https://discord.gg/railway)
- **Issues**: Create GitHub issues for tool-specific problems




