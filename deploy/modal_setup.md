# Modal Labs Deployment Guide

## Overview

This guide covers deploying the Intercom Analysis Tool to Modal Labs for serverless execution with scheduled and on-demand analysis capabilities.

## Prerequisites

1. **Modal Labs Account**: Sign up at [modal.com](https://modal.com)
2. **Modal CLI**: Install with `pip install modal`
3. **API Keys**: Ensure you have all required API keys

## Setup Steps

### 1. Install Modal CLI

```bash
pip install modal
```

### 2. Authenticate with Modal

```bash
modal token new
```

Follow the prompts to authenticate with your Modal account.

### 3. Create Modal Secrets

Create a secret with your API keys:

```bash
modal secret create intercom-analysis-secrets \
  INTERCOM_ACCESS_TOKEN=your_intercom_token \
  OPENAI_API_KEY=your_openai_key \
  GAMMA_API_KEY=your_gamma_key \
  INTERCOM_WORKSPACE_ID=your_workspace_id
```

### 4. Deploy the Application

```bash
modal deploy deploy/modal_app.py
```

### 5. Test the Deployment

Run a test analysis:

```bash
modal run deploy/modal_app.py::run_custom_analysis --start-date 2024-01-01 --end-date 2024-01-07
```

## Available Functions

### Scheduled Functions

- **Weekly Analysis**: Runs every Monday at 9 AM UTC
  - Analyzes last 7 days
  - Generates executive-style presentation
  - Exports as PDF

- **Monthly Analysis**: Runs on 1st of every month at 9 AM UTC
  - Analyzes last 30 days
  - Generates detailed-style presentation
  - Exports as PPTX

### On-Demand Functions

- **Custom Analysis**: `run_custom_analysis(start_date, end_date, max_conversations, gamma_style, gamma_export)`
  - Flexible date ranges
  - Configurable conversation limits
  - Multiple presentation styles

## Configuration

### Resource Allocation

The Modal functions are configured with:
- **Memory**: 2GB
- **CPU**: 2 cores
- **Timeout**: 1 hour
- **Image**: Debian slim with Python 3.11

### Environment Variables

All required environment variables are automatically injected from the Modal secret:
- `INTERCOM_ACCESS_TOKEN`
- `OPENAI_API_KEY`
- `GAMMA_API_KEY`
- `INTERCOM_WORKSPACE_ID`

## Monitoring and Logs

### View Function Logs

```bash
modal logs intercom-analysis-tool
```

### Monitor Scheduled Runs

```bash
modal app list
modal app logs intercom-analysis-tool
```

### Check Function Status

```bash
modal function list
```

## Cost Optimization

### Resource Tuning

Adjust resources in `deploy/modal_app.py`:

```python
@app.function(
    image=image,
    timeout=1800,  # 30 minutes
    memory=1024,   # 1GB
    cpu=1,         # 1 CPU core
)
```

### Usage Monitoring

Monitor costs in the Modal dashboard:
- Function execution time
- Memory usage
- CPU utilization

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are in the `image.pip_install()` list
2. **Timeout Errors**: Increase timeout for large datasets
3. **Memory Errors**: Increase memory allocation
4. **Secret Errors**: Verify secret is created and named correctly

### Debug Mode

Run functions locally for debugging:

```bash
modal run deploy/modal_app.py::run_custom_analysis --start-date 2024-01-01 --end-date 2024-01-02
```

### Log Analysis

```bash
modal logs intercom-analysis-tool --follow
```

## Security Best Practices

1. **Secrets Management**: Never hardcode API keys
2. **Access Control**: Use Modal's team features for collaboration
3. **Network Security**: Functions run in isolated containers
4. **Data Privacy**: No data is stored on Modal's infrastructure

## Scaling Considerations

### High Volume Analysis

For large datasets (>5000 conversations):
- Increase memory to 4GB
- Increase CPU to 4 cores
- Consider breaking into smaller date ranges

### Concurrent Execution

Modal automatically handles:
- Function queuing
- Resource allocation
- Error retry logic

## Integration with External Systems

### Webhook Integration

Add webhook endpoints to notify external systems:

```python
@app.function()
def notify_completion(result: Dict[str, Any]):
    # Send webhook notification
    pass
```

### Database Integration

Store results in external databases:

```python
@app.function()
def store_results(result: Dict[str, Any]):
    # Store in database
    pass
```

## Maintenance

### Updates

To update the deployment:

1. Modify `deploy/modal_app.py`
2. Redeploy: `modal deploy deploy/modal_app.py`

### Monitoring

Set up alerts for:
- Function failures
- High execution times
- Resource usage spikes

## Support

- **Modal Documentation**: [docs.modal.com](https://docs.modal.com)
- **Community**: [Modal Discord](https://discord.gg/modal)
- **Issues**: Create GitHub issues for tool-specific problems




