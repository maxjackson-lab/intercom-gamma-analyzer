# Railway Background Execution Guide

## Overview

For production workloads (multi-agent analysis, Gamma generation, large datasets), use **background execution** instead of SSE streaming to avoid timeout issues.

## Configuration

Railway environment variables are now set to **2-hour timeout**:
- `MAX_EXECUTION_DURATION=7200` (2 hours)
- `MAX_SSE_DURATION=7200` (2 hours)

## When to Use Background Execution

Use `/execute/start` (background) for:
- ✅ Multi-agent analysis (`--multi-agent`)
- ✅ Full week/month/quarter analysis
- ✅ Gamma presentation generation (`--generate-gamma`)
- ✅ Any task expected to run longer than 5-10 minutes
- ✅ Production workloads where stability matters

Use `/execute` (SSE streaming) for:
- ⚡ Quick queries (< 5 minutes)
- ⚡ Test mode (`--test-mode`)
- ⚡ Interactive debugging with live output

## Background Execution Workflow

### 1. Start the Task

**POST** `/execute/start`

```bash
curl -X POST "https://agile-exploration-production.up.railway.app/execute/start" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python",
    "args": [
      "src/main.py",
      "voice-of-customer",
      "--analysis-type", "topic-based",
      "--multi-agent",
      "--time-period", "week",
      "--ai-model", "openai",
      "--generate-gamma"
    ]
  }'
```

**Response:**
```json
{
  "execution_id": "exec_1762548673499_vqx7d3cpo",
  "status": "queued",
  "queue_position": 0,
  "message": "Execution started in background"
}
```

### 2. Poll for Status

**GET** `/execute/status/{execution_id}`

```bash
curl "https://agile-exploration-production.up.railway.app/execute/status/exec_1762548673499_vqx7d3cpo" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (Running):**
```json
{
  "execution_id": "exec_1762548673499_vqx7d3cpo",
  "status": "running",
  "command": "python",
  "args": ["src/main.py", "voice-of-customer", ...],
  "queue_position": null,
  "created_at": "2025-01-07T19:11:13.499000",
  "started_at": "2025-01-07T19:11:15.001000",
  "completed_at": null,
  "duration_seconds": 120,
  "return_code": null,
  "error_message": null
}
```

**Response (Completed):**
```json
{
  "execution_id": "exec_1762548673499_vqx7d3cpo",
  "status": "completed",
  "return_code": 0,
  "completed_at": "2025-01-07T19:25:30.123000",
  "duration_seconds": 857
}
```

### 3. Get Results

Once status is `completed`, access results:

**GET** `/execute/output/{execution_id}`

```bash
curl "https://agile-exploration-production.up.railway.app/execute/output/exec_1762548673499_vqx7d3cpo" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Status Values

| Status | Description |
|--------|-------------|
| `queued` | Task is waiting in queue |
| `running` | Task is currently executing |
| `completed` | Task finished successfully |
| `failed` | Task exited with error code |
| `timeout` | Task exceeded MAX_EXECUTION_DURATION |
| `cancelled` | Task was manually cancelled |
| `error` | Internal error occurred |

## JavaScript Example

```javascript
// Start background execution
async function startBackgroundAnalysis() {
  const response = await fetch('/execute/start', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      command: 'python',
      args: [
        'src/main.py',
        'voice-of-customer',
        '--analysis-type', 'topic-based',
        '--multi-agent',
        '--time-period', 'week',
        '--ai-model', 'openai',
        '--generate-gamma'
      ]
    })
  });
  
  const { execution_id } = await response.json();
  return execution_id;
}

// Poll for status
async function pollStatus(executionId) {
  const pollInterval = 5000; // 5 seconds
  
  while (true) {
    const response = await fetch(`/execute/status/${executionId}`, {
      headers: { 'Authorization': `Bearer ${API_TOKEN}` }
    });
    
    const status = await response.json();
    console.log(`Status: ${status.status} (${status.duration_seconds}s elapsed)`);
    
    if (['completed', 'failed', 'timeout', 'error'].includes(status.status)) {
      return status;
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
}

// Complete workflow
async function runLongAnalysis() {
  console.log('Starting background analysis...');
  const executionId = await startBackgroundAnalysis();
  
  console.log(`Execution ID: ${executionId}`);
  console.log('Polling for completion...');
  
  const finalStatus = await pollStatus(executionId);
  
  if (finalStatus.status === 'completed') {
    console.log('✅ Analysis completed successfully!');
    // Fetch results
    const results = await fetch(`/execute/output/${executionId}`);
    console.log(await results.json());
  } else {
    console.error(`❌ Analysis failed: ${finalStatus.error_message}`);
  }
}
```

## Benefits of Background Execution

1. **No Connection Timeout**: Task runs independently of client connection
2. **Resumable**: Poll status from any client at any time
3. **Mobile-Friendly**: Works with unstable connections
4. **Queue Management**: Tasks are queued and processed in order
5. **Cancellable**: Can cancel running tasks via `/execute/cancel/{execution_id}`
6. **Persistent Results**: Results are stored and accessible after completion

## Troubleshooting

### Task Stuck in Queue
- Check `/execute/list` to see all tasks
- Check server logs for concurrency limits
- Default max concurrent tasks: 5

### Task Timeout
- Default timeout: 2 hours (7200 seconds)
- Increase `MAX_EXECUTION_DURATION` environment variable if needed
- Use `--test-mode` to reduce data processing time

### No Output
- Ensure task status is `completed`
- Check `/execute/output/{execution_id}` for results
- Check `/outputs/` directory for generated files

## Related Endpoints

- `POST /execute/start` - Start background task
- `GET /execute/status/{execution_id}` - Check task status
- `GET /execute/output/{execution_id}` - Get task output
- `GET /execute/list` - List all tasks
- `POST /execute/cancel/{execution_id}` - Cancel running task

## See Also

- `DEPLOYMENT_GUIDE.md` - Railway deployment instructions
- `RAILWAY_TROUBLESHOOTING.md` - Common Railway issues
- `deploy/railway_web.py` - Implementation details

