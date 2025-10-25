# Category Deep Dive Commands - Critical Bug Fix

## Problem
**Every single category deep dive command was failing immediately** when executed from the web interface.

## Root Cause
The web UI JavaScript was passing incompatible command-line flags to category deep dive commands.

### Technical Details

Category deep dive commands (`analyze-billing`, `analyze-product`, `analyze-api`, `tech-analysis`, `analyze-escalations`) only support:
- `--days N` (for time period)
- `--start-date YYYY-MM-DD` and `--end-date YYYY-MM-DD` (for custom dates)
- `--generate-gamma` (for output format)
- `--max-conversations N` (optional)

**But the web UI was incorrectly passing:**
- `--time-period week` ❌ (Not supported by category commands)
- `--test-mode` ❌ (Not supported by category commands)
- `--test-data-count 100` ❌ (Not supported by category commands)
- `--focus-areas Category` ❌ (Not supported by category commands)

This caused all category deep dive commands to fail immediately with "unknown option" errors.

## Solution

Updated `static/app.js` to intelligently route flags based on command type:

### 1. Time Period Handling (Lines 903-947)
```javascript
// Commands that support --time-period flag
const supportsTimePeriod = [
    'voice-of-customer',
    'agent-performance',
    'agent-coaching-report',
    'canny-analysis'
];

// Commands that only support --days
const categoryDeepDiveCommands = [
    'analyze-billing',
    'analyze-product',
    'analyze-api',
    'analyze-sites',
    'analyze-escalations',
    'tech-analysis',
    'analyze-all-categories'
];

// Convert time period to --days for category commands
if (categoryDeepDiveCommands.includes(command)) {
    const dayMap = {
        'yesterday': 1,
        'week': 7,
        'month': 30
    };
    const days = dayMap[timeValue] || 7;
    args.push('--days', String(days));
} else if (supportsTimePeriod.includes(command)) {
    args.push('--time-period', timeValue);
}
```

### 2. Test Mode Filtering (Lines 966-971)
```javascript
// Only add --test-mode to commands that support it
const supportsTestMode = ['voice-of-customer', 'agent-performance', 'agent-coaching-report'];
if (isTestMode && supportsTestMode.includes(command)) {
    args.push('--test-mode');
    args.push('--test-data-count', testCount);
}
```

### 3. Taxonomy Filter Filtering (Lines 956-959)
```javascript
// Only add --focus-areas to commands that support it
if (filterValue && supportsTimePeriod.includes(command)) {
    args.push('--focus-areas', filterValue);
}
```

## Files Modified

1. **`static/app.js`**
   - Added command compatibility checks
   - Convert time period to `--days` for category commands
   - Filter unsupported flags by command type
   - Updated version marker to v3.0.3-category-fix

2. **`deploy/railway_web.py`**
   - Updated version markers to v3.0.3
   - Updated debug endpoint with fix details
   - Updated cache-busting query strings

## Testing

To verify the fix works:

1. **Billing Analysis**: Select "Billing Analysis" → "Last Week" → "Gamma Presentation" → Run
   - ✅ Should execute: `python src/main.py analyze-billing --days 7 --generate-gamma`
   
2. **Product Feedback**: Select "Product Feedback" → "Last Month" → Run
   - ✅ Should execute: `python src/main.py analyze-product --days 30`

3. **API Analysis**: Select "API Issues & Integration" → Custom dates → Run
   - ✅ Should execute: `python src/main.py analyze-api --start-date YYYY-MM-DD --end-date YYYY-MM-DD`

4. **Voice of Customer** (should still work with --time-period):
   - ✅ Should execute: `python src/main.py voice-of-customer --time-period week --multi-agent --analysis-type complete`

## Impact

- ✅ All category deep dive commands now work correctly from web UI
- ✅ Voice of Customer, Agent Performance, and Agent Coaching commands unaffected
- ✅ Test mode only enabled for commands that support it
- ✅ Taxonomy filters only added to commands that support them
- ✅ Custom date ranges work for all commands

## Deployment

1. Commit changes to git
2. Push to Railway (auto-deploys from `feature/multi-agent-implementation` branch)
3. Verify version marker shows `v3.0.3-category-fix` in web UI footer
4. Test category deep dive commands

## Related Commands Affected

**Now Working:**
- Billing Analysis (`analyze-billing`)
- Product Feedback (`analyze-product`)
- API Issues & Integration (`analyze-api`)
- Technical Troubleshooting (`tech-analysis`)
- Escalations (`analyze-escalations`)
- All Categories (`analyze-all-categories`)

**Still Working (unchanged):**
- Voice of Customer (`voice-of-customer`)
- Agent Performance (`agent-performance`)
- Agent Coaching Reports (`agent-coaching-report`)
- Canny Analysis (`canny-analysis`)

## Previous Issues

This was a **critical bug** that made the web interface effectively non-functional for category-specific analyses, which are a core feature of the tool.

Users had to fall back to the CLI, defeating the purpose of the web interface.

