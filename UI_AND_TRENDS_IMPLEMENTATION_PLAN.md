# UI, Storage, Trends, and Automation Implementation Plan

**Created**: 2025-10-31  
**Status**: Planning Phase  
**Timeline**: 2-3 weeks for complete implementation

---

## Part 1: Web UI Terminal Display (Rich Formatting)

**Problem**: Terminal output cramped, hard to read, small text.

**Solution**: Enhance Web UI log display using Rich library features:
- Larger font size in terminal window
- More vertical spacing between log lines (line-height: 1.6 or 1.8)
- Expand terminal window width/height
- Better visual hierarchy using Rich panels and separators
- Color-coded sections (fetching=blue, analysis=green, errors=red)
- Progress bars for long operations

**Files to Modify**:
- `deploy/railway_web.py` - Update terminal display CSS/styling
- Web UI template (HTML) - Increase terminal container size
- CSS styling - Adjust font-size, line-height, padding

**Rich Terminal Features to Use**:
- `Panel()` for section boundaries
- `Rule()` for visual separators
- Emoji indicators for status (✅ ❌ 📊 🔍)
- Better spacing with newlines between major steps

**Effort**: 1-2 days  
**Priority**: High (Quick UX win)

---

## Part 2: Enhanced Date-by-Date Logging

**Problem**: Logs show "Fetched 50, 100, 150..." but not which date is being processed.

**Solution**: Add date-specific progress logging:

```
📅 Starting fetch for date range: 2025-10-24 to 2025-10-30
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📆 Day 1/7: 2025-10-24
   🔍 Fetching conversations...
   ✅ Completed: 1,234 conversations (2.3 minutes)

📆 Day 2/7: 2025-10-25
   🔍 Fetching conversations...
   ✅ Completed: 1,567 conversations (2.8 minutes)

Progress: ████████░░░░░░░░░░░░ 35% (2/7 days)
```

**Files to Modify**:
- `src/services/chunked_fetcher.py` - Add Rich formatted date logging
- `src/services/intercom_sdk_service.py` - Add date context

**Effort**: 1 day  
**Priority**: Medium (Better visibility)

---

## Part 3: Fix File Naming (Date Ranges)

**Current**: `analysis_week_20251024.md`  
**New**: `VoC_Analysis_2025-10-24_to_2025-10-30.md`

**Benefits**:
- Clearer date ranges
- More descriptive
- Better for archival and searching

**Files to Update**:
- `src/utils/time_utils.py` - filename generation helper
- All analyzer output code
- Gamma generation code

**Effort**: 1 day  
**Priority**: Medium (Better organization)

---

## Part 4: Database Storage for Analysis Metadata

**Problem**: No persistent tracking of analyses, Gamma URLs, or topics across runs.

**Solution**: SQLite database to store all analysis metadata.

### Database Schema:

```sql
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_type TEXT,
    date_range_start DATE,
    date_range_end DATE,
    gamma_url TEXT,
    markdown_file TEXT,
    json_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    conversations_count INTEGER
);

CREATE TABLE analysis_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    topic_name TEXT,
    normalized_topic_name TEXT,
    sentiment_score REAL,
    volume INTEGER,
    percentage REAL,
    example_quotes TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analysis_runs(id)
);

CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    recipient TEXT,
    sent_at TIMESTAMP,
    success BOOLEAN,
    error_message TEXT,
    FOREIGN KEY (analysis_id) REFERENCES analysis_runs(id)
);
```

**Files to Modify**:
- `deploy/railway_web.py` - Add SQLite database and models
- Analysis output code - Insert metadata into database
- Gamma generation code - Save URL to database
- Web UI - Display analysis history from database

**Benefits**:
- Track all analyses
- Query historical data
- Foundation for trend analysis
- Store Gamma URLs persistently

**Effort**: 2-3 days  
**Priority**: High (Foundation for everything else)

---

## Part 5: Railway Volume Setup

**Problem**: Files are lost on every Railway redeploy (no persistent storage).

**Solution**: Add Railway volume mount.

### Setup Steps:
1. Railway Dashboard → Service → Volumes → Add Volume
2. Mount path: `/app/outputs`
3. That's it! (No code changes needed)

**Optional Code Enhancement**:
- Add environment variable check: `RAILWAY_VOLUME_MOUNT_PATH`
- Log confirmation that volume is mounted
- Health check for write permissions

**Effort**: 2 minutes (dashboard setup)  
**Priority**: CRITICAL (Must do first!)

**Note**: Alternative is storing everything in database as text, but volume is cleaner.

---

## Part 6: Long-Term Trend Analysis (Quarterly/Yearly)

**Goal**: Aggregate multiple weekly/monthly analyses into quarterly or yearly trend reports.

### Phase 1 - Data Foundation (Part 4)
- Store structured topic data in database
- Track topic names, sentiment, volume per analysis

### Phase 2 - Topic Normalization (3-5 days)

**Problem**: Same topic appears with different names:
- Week 1: "Login issues"
- Week 2: "Authentication problems"
- Week 3: "Can't sign in"

**Solution**: AI-powered topic normalization:

```python
normalize_topics({
    "Login issues",
    "Authentication problems", 
    "Can't sign in"
}) 
→ "Authentication & Login"
```

**Implementation**:
- Use AI embeddings or LLM call to normalize topic names
- Store as `normalized_topic_name` in database
- Enable cross-analysis topic matching

**Files to Create**:
- `src/services/topic_normalizer.py`

### Phase 3 - Trend Aggregation (2-3 days)

**Goal**: Query and aggregate analyses across time periods.

```python
# Query all analyses in date range
quarterly_analyses = db.query(
    start='2025-01-01', 
    end='2025-03-31'
)

# Aggregate by normalized topic
for topic in unique_topics:
    trend = {
        'topic': topic,
        'weekly_volumes': [...],
        'sentiment_trend': [...],
        'status': 'rising|declining|stable|new|resolved'
    }
```

**Files to Create**:
- `src/services/trend_aggregator.py`

### Phase 4 - Trend Report Generation (2-3 days)

**Features**:
- Use existing AI agents to generate quarterly summary
- Include:
  - Top rising topics (📈)
  - Resolved topics (✅)
  - New emerging topics (🆕)
  - Persistent issues (⚠️)
  - Sentiment trends over time
- Generate Gamma presentation for quarterly review

**Files to Create**:
- `src/analyzers/quarterly_trend_analyzer.py`

### Phase 5 - Web UI Integration (1-2 days)

**Features**:
- Add "Trend Analysis" tab in Web UI
- Date range selector:
  - Q1 2025
  - Q2 2025
  - Q3 2025
  - Q4 2025
  - Full Year 2025
  - Custom Range
- "Generate Quarterly Trends" button
- Display historical topic evolution charts

**Files to Modify**:
- `deploy/railway_web.py` - Add trend analysis route
- Web UI template - Add trend analysis tab

**Total Effort**: 8-12 days (phased implementation)  
**Priority**: Medium-Low (Nice to have, requires database first)

**Benefits**:
- See topic evolution over months/quarters
- Identify seasonal patterns
- Track resolution effectiveness
- Predictive insights (topics trending up)
- Executive quarterly reviews with rich historical data

---

## Part 7: Automated Weekly Email Reports (SendGrid)

**Goal**: Send formatted weekly VoC report to boss every Monday at midnight Pacific.

### Setup Steps

#### 1. SendGrid Account Setup (10 minutes)
- Sign up at sendgrid.com (free tier: 100 emails/day)
- Verify email domain or use single sender
- Generate API key
- Add to Railway environment: `SENDGRID_API_KEY=SG.xxx`

#### 2. Railway Cron Configuration (5 minutes)
- Railway Dashboard → Cron Service
- Set schedule: `0 8 * * 1` (Monday 8:00 UTC = Midnight Pacific)
- Add environment variables:
  - `SENDGRID_API_KEY`
  - `EMAIL_RECIPIENT=boss@company.com`
  - `EMAIL_FROM=you@company.com`
  - `CRON_TIMEZONE=America/Los_Angeles`

#### 3. Email Template (HTML + Plain text)

```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>📊 Weekly VoC Analysis Report</h2>
  <p><strong>Week of {start_date} - {end_date}</strong></p>
  
  <h3>🔑 Key Highlights:</h3>
  <ul>
    <li><strong>{top_topic_1}</strong>: {volume} conversations ({sentiment_emoji})</li>
    <li><strong>{top_topic_2}</strong>: {volume} conversations ({sentiment_emoji})</li>
    <li><strong>{top_topic_3}</strong>: {volume} conversations ({sentiment_emoji})</li>
  </ul>
  
  <h3>📈 Trends This Week:</h3>
  <ul>
    <li><strong>Rising Issues:</strong> {rising_topics}</li>
    <li><strong>Resolved Issues:</strong> {resolved_topics}</li>
    <li><strong>New Topics:</strong> {new_topics}</li>
  </ul>
  
  <h3>📊 Interactive Report:</h3>
  <p>
    <a href="{gamma_url}" 
       style="display: inline-block; background-color:#4CAF50; color:white; 
              padding:12px 24px; text-decoration:none; border-radius:4px; 
              font-weight: bold;">
      View Full Gamma Presentation →
    </a>
  </p>
  
  <hr style="border: 1px solid #eee; margin: 20px 0;">
  <p style="color:#666; font-size:12px;">
    Total Conversations Analyzed: {count} | 
    Generated: {timestamp}
  </p>
</body>
</html>
```

#### 4. Implementation

**New Files to Create**:
- `src/services/email_service.py` - SendGrid integration
- `src/scheduled/weekly_report.py` - Cron job handler
- `templates/email/weekly_report.html` - Email template
- `templates/email/weekly_report.txt` - Plain text fallback

**Code Structure**:

```python
# src/services/email_service.py
import sendgrid
from sendgrid.helpers.mail import Mail

class EmailService:
    def __init__(self):
        self.sg = sendgrid.SendGridAPIClient(
            api_key=settings.sendgrid_api_key
        )
    
    def send_weekly_report(
        self, 
        recipient: str,
        summary: Dict,
        gamma_url: str
    ):
        # Render template
        html = render_email_template(summary, gamma_url)
        
        # Create mail object
        mail = Mail(
            from_email=settings.email_from,
            to_emails=recipient,
            subject=f"Weekly VoC Report: {summary['date_range']}",
            html_content=html
        )
        
        # Send via SendGrid
        response = self.sg.send(mail)
        return response.status_code == 202
```

```python
# src/scheduled/weekly_report.py
async def run_weekly_report():
    # 1. Calculate last week's date range (Pacific time)
    last_week = get_last_week_range_pacific()
    
    # 2. Run VoC analysis
    analysis = await run_voc_analysis(
        start_date=last_week['start'],
        end_date=last_week['end'],
        analysis_type='topic-based',
        generate_gamma=True
    )
    
    # 3. Extract key highlights for email
    summary = extract_email_summary(analysis)
    
    # 4. Send email
    email_service = EmailService()
    success = email_service.send_weekly_report(
        recipient=settings.email_recipient,
        summary=summary,
        gamma_url=analysis['gamma_url']
    )
    
    # 5. Log result
    logger.info(f"Weekly email sent: {success}")
    
    # 6. Save to database
    db.save_email_sent_record(analysis.id, recipient, success)
```

**Environment Variables Required**:
```bash
SENDGRID_API_KEY=SG.xxxxxxxxx
EMAIL_RECIPIENT=boss@company.com
EMAIL_FROM=you@company.com
CRON_TIMEZONE=America/Los_Angeles
```

**Error Handling**:
- Retry failed sends (max 3 attempts)
- Send error notification email if analysis fails
- Log all email attempts to database
- Include fallback plain text email

**Testing**:
- Test email template rendering
- Test SendGrid connection
- Run manual cron job test
- Verify Pacific timezone handling

**Effort**: 2-3 hours  
**Priority**: Medium (Nice automation)  
**Difficulty**: 🟢 Easy (SendGrid is very straightforward)

**Nice-to-have Enhancements**:
- CC yourself on emails
- Include inline charts/graphs
- Configurable recipients list
- Email preferences (daily/weekly/monthly)
- Unsubscribe link (if sending to multiple people)

---

## Implementation Priority

### Phase 1: Critical Foundation (1 week)
1. ✅ **Part 5 (Railway volume)** - 2 minutes, MUST DO FIRST
2. **Part 4 (Database)** - 2-3 days, foundation for everything
3. **Part 1 (UI formatting)** - 1-2 days, quick UX win
4. **Part 2 (Date logging)** - 1 day, better visibility
5. **Part 3 (File naming)** - 1 day, better organization

### Phase 2: Automation (1 week)
6. **Part 7 (Email reports)** - 2-3 hours, automated reporting

### Phase 3: Long-Term Features (1-2 weeks)
7. **Part 6 (Trend analysis)** - 8-12 days, phased implementation
   - Phase 1: Data foundation (done in Part 4)
   - Phase 2: Topic normalization
   - Phase 3: Trend aggregation
   - Phase 4: Report generation
   - Phase 5: UI integration

---

## Total Timeline

**Complete Implementation**: 2-3 weeks

**Quick Wins** (Week 1):
- Railway volume setup
- Database foundation
- Better UI display
- Improved logging
- Better file naming

**Automation** (Week 2):
- Weekly email reports

**Advanced Features** (Weeks 2-3):
- Long-term trend analysis
- Quarterly reports
- Topic normalization
- Trend UI

---

## Success Metrics

After implementation, you'll have:

✅ Persistent file storage (Railway volume)  
✅ All analyses tracked in database  
✅ Gamma URLs stored and accessible  
✅ Better UI display with Rich formatting  
✅ Clear date-by-date progress logging  
✅ Descriptive file names with date ranges  
✅ Automated weekly email reports  
✅ Historical trend analysis capability  
✅ Quarterly/yearly report generation  
✅ Topic evolution tracking  

---

## Notes

- All database changes use SQLite (no external dependencies)
- SendGrid free tier sufficient for weekly emails
- Railway volume is one-time setup, no code changes
- Trend analysis builds on database foundation
- Can implement in phases as time permits


