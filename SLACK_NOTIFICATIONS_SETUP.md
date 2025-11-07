# Slack Notifications Setup Guide

## Overview

Get notified in Slack when your long-running analyses complete! Works even if you close the browser.

## Two Notification Methods

### 1. Browser Notifications (No Setup - Works Immediately) ✅

**How it works:**
- First time you run a job, browser asks: "Allow notifications?"
- Click "Allow"
- Get desktop notifications when job completes (even if browser is closed)
- Click notification to jump back to results

**Example notification:**
```
✅ Analysis Completed!
Your analysis finished in 45m 23s. Click to view results.
```

**Supported browsers:** Chrome, Firefox, Safari, Edge (all modern browsers)

---

### 2. Slack Notifications (Optional - Requires Quick Setup) 📱

**How it works:**
- Someone creates a Slack Incoming Webhook (takes 2 minutes)
- Set `SLACK_WEBHOOK_URL` on Railway
- All job completions post to Slack automatically

**Setup Steps:**

#### Step 1: Create Slack Incoming Webhook (Ask Any Channel Member)

You don't need to be a Slack admin! Any member of a channel can create a webhook.

1. Go to: https://api.slack.com/messaging/webhooks
2. Click **"Create your Slack app"** → **"From scratch"**
3. App name: `Intercom Analysis Notifier`
4. Choose your workspace
5. Click **"Incoming Webhooks"** → Toggle **"Activate Incoming Webhooks" to ON**
6. Click **"Add New Webhook to Workspace"**
7. Select channel (e.g., `#data-analysis`, `#analytics`, or your DMs)
8. Click **"Allow"**
9. Copy the webhook URL (looks like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`)

**Note:** You can post to your own DMs by selecting "Slackbot" as the channel!

#### Step 2: Configure Railway

Using Railway CLI:
```bash
railway variables --set SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Or via Railway Dashboard:
1. Go to your Railway project
2. Select `agile-exploration` service
3. Go to **Variables** tab
4. Click **"+ New Variable"**
5. Name: `SLACK_WEBHOOK_URL`
6. Value: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
7. Click **"Add"**

#### Step 3: Test It!

Run any analysis. When it completes, you'll get a Slack message:

```
✅ Analysis Completed!

Execution ID: exec_1762548673499_vqx7d3cpo
Duration: 45m 23s

View Results
```

---

## What Gets Notified

Both notification methods trigger when:
- ✅ Job completes successfully
- ❌ Job fails or times out
- ⚠️ Job encounters an error

## Example Slack Messages

**Success:**
```
✅ Analysis Completed!

Execution ID: exec_1762548673499_vqx7d3cpo
Duration: 45m 23s

Status    │ Completed
Duration  │ 45m 23s

View Results → [Link to Railway app]
```

**Failure:**
```
❌ Analysis Failed

Execution ID: exec_1762548673499_vqx7d3cpo  
Duration: 12m 5s

Status    │ Failed
Duration  │ 12m 5s

View Logs → [Link to Railway app]
```

---

## Troubleshooting

### Browser Notifications Not Working

**Check:**
1. Did you click "Allow" when prompted?
2. Check browser notification settings (should be allowed for your Railway domain)
3. On Mac: System Preferences → Notifications → Chrome/Firefox → Allow notifications

**Re-enable:**
- Click the lock icon in the address bar
- Change Notifications from "Block" to "Allow"
- Refresh the page and start a new job

### Slack Notifications Not Working

**Check:**
1. Is `SLACK_WEBHOOK_URL` set correctly on Railway?
   ```bash
   railway variables --list | grep SLACK
   ```

2. Test webhook directly:
   ```bash
   curl -X POST YOUR_WEBHOOK_URL \
     -H 'Content-Type: application/json' \
     -d '{"text": "Test notification from Intercom Analysis Tool"}'
   ```

3. Check Railway logs for errors:
   ```bash
   railway logs
   ```

**Common issues:**
- Webhook URL expired → Create new webhook
- Wrong channel permissions → Recreate webhook with different channel
- Webhook URL has typos → Copy-paste carefully

---

## Advanced: Custom Slack Messages

If you want to customize the Slack message format, edit:
```python
# deploy/railway_web.py, line ~2560
text = f"✅ *Analysis Completed!*\n\n..."
```

You can add:
- Conversation count from execution metadata
- Specific analysis type (VoC, Agent Performance, etc.)
- Links to generated Gamma presentations
- @mentions for specific team members

---

## Privacy & Security

**Browser notifications:**
- Only visible to you on your device
- No data sent to external services
- Fully private

**Slack notifications:**
- Posted to channel you selected during webhook setup
- Visible to all channel members
- Only contains: execution ID, status, duration (no sensitive data)
- No conversation content or customer data included

---

## Disable Notifications

**Browser:**
- Just click "Block" when asked for permission
- Or change in browser settings later

**Slack:**
- Remove `SLACK_WEBHOOK_URL` from Railway variables:
  ```bash
  railway variables --delete SLACK_WEBHOOK_URL
  ```

---

## See Also

- `RAILWAY_BACKGROUND_EXECUTION_GUIDE.md` - Background execution workflow
- `DEPLOYMENT_GUIDE.md` - Railway deployment instructions
- Slack Incoming Webhooks: https://api.slack.com/messaging/webhooks

