# Agent Coaching - Quick Reference Card

## 🎯 Most Common Commands

### Weekly Coaching Report (Recommended)
```bash
python src/main.py agent-coaching-report --vendor horatio
```
**Use for**: Monday morning coaching prep, identify this week's priorities

### Monthly Performance Review
```bash
python src/main.py agent-performance --agent boldr --time-period month --individual-breakdown --generate-gamma
```
**Use for**: Monthly leadership meetings, performance trends

### Quick Team Check
```bash
python src/main.py agent-performance --agent horatio --time-period week
```
**Use for**: Fast team-level summary without individual breakdown

---

## 📊 What You Get

### Coaching Report Shows:
- ✅ Individual agent FCR rankings
- ✅ Who needs coaching (specific subcategories)
- ✅ Who deserves praise (top performers)
- ✅ Team training priorities
- ✅ Week-over-week trend arrows
- ✅ Specific Intercom conversation examples

### Key Metrics:
- **FCR Rate**: First Contact Resolution (target: >85%)
- **Escalation Rate**: How often agent escalates (target: <10%)
- **Response Time**: Median first response (target: <1 hour)
- **Resolution Time**: Time to close ticket (target: <24 hours)

---

## 🎓 Coaching Priorities

### HIGH Priority (Red Flag)
- FCR <70% OR Escalation >20%
- **Action**: Immediate 1-on-1 coaching session

### MEDIUM Priority (Yellow Flag)
- Multiple weak categories (2+)
- **Action**: Focus training on weak subcategories

### LOW Priority (Green)
- Good performance across metrics
- **Action**: Maintain current approach, recognize achievements

---

## 📈 Performance Levels

### Excellent ⭐⭐⭐
- FCR ≥85%
- Escalation ≤10%
- **Action**: Share as best practice

### Good ⭐⭐
- FCR 75-84%
- Escalation 11-15%
- **Action**: Minor improvements

### Fair ⭐
- FCR 70-74%
- Escalation 16-20%
- **Action**: Targeted coaching

### Poor ❌
- FCR <70%
- Escalation >20%
- **Action**: Intensive coaching required

---

## 🔍 Reading the Output

### Individual Agent Table
```
│  3  │ Tom Anderson  │     65  │ 80.0%  │  9.0%  │ 1.5h │ MEDIUM │
```
**Means**:
- Rank #3 on team by FCR
- 65 conversations handled
- 80% FCR (good, not excellent)
- 9% escalation (acceptable)
- 1.5 hour response time (room for improvement)
- Medium coaching priority (some areas to improve)

### Weak Subcategories
```
Weak subcategories: Bug>Export, Bug>API, Account>Login
```
**Means**:
- Agent struggles with 3 specific areas
- These should be coaching focus
- Pair with agent who excels in these areas

### Team Training Needs
```
HIGH: Bug>Export
4 agents showing poor performance in this area
Affects: John, Lisa, Amy, David
```
**Means**:
- Common knowledge gap across team
- Plan team training session on Export feature troubleshooting
- Create documentation or guide
- Not just one agent's problem

---

## 💡 Coaching Workflow

### Step 1: Run Report (Monday AM)
```bash
python src/main.py agent-coaching-report --vendor horatio
```

### Step 2: Review Console (5 minutes)
- Check highlights (what's going well?)
- Check lowlights (what needs attention?)
- Identify high-priority coaching needs

### Step 3: Review JSON (10 minutes)
- Open `outputs/coaching_report_*.json`
- Drill into `performance_by_subcategory` for each agent
- Note specific Intercom conversation URLs for examples

### Step 4: Schedule Sessions
- **High priority**: 1-on-1 this week
- **Medium priority**: Group coaching or peer shadowing
- **Top performers**: Recognition in team meeting

### Step 5: Plan Training
- Identify subcategories affecting 2+ agents
- Schedule team training sessions
- Create/update documentation

### Step 6: Track Progress (Next Week)
- Run report again
- Check week-over-week changes
- Verify coaching had impact

---

## 🎨 Gamma Presentations

Add `--generate-gamma` to any command:

```bash
python src/main.py agent-coaching-report --vendor horatio --generate-gamma
```

**Generates slides with**:
- Team performance summary
- Top performers (with achievements)
- Coaching priorities (with focus areas)
- Team training needs
- Week-over-week trends

**Use for**:
- Leadership presentations
- Team meetings
- Stakeholder reviews
- Performance documentation

---

## 📁 Output Files

### Location
`outputs/` directory

### Files Created
- `coaching_report_horatio_YYYYMMDD_HHMMSS.json` - Detailed metrics
- `agent_performance_horatio_YYYYMMDD_HHMMSS.json` - Same data (different command)
- `gamma_url_*.txt` - Gamma presentation URL (if generated)

### Historical Data
`outputs/historical_data/` directory

- `agent_performance_horatio_YYYYMMDD.json` - Weekly snapshots
- Used for trending and week-over-week comparisons

---

## ⚡ Pro Tips

### 1. Focus on Subcategories
Generic "Bug" category too broad. Look at subcategories:
- `Bug>Export` vs `Bug>API` vs `Bug>Performance`
- Targeted coaching is more effective

### 2. Use Example Conversations
Each agent has:
- `best_example_url`: Show what they did well
- `needs_coaching_example_url`: Discuss improvement areas

### 3. Track Trends
Don't just look at current week:
- Week-over-week: Is coaching working?
- Month-over-month: Long-term improvement?

### 4. Compare Peers
If John struggles with Bug>Export but Maria excels:
- Pair them for shadowing
- Have Maria share her approach
- Leverage team strengths

### 5. Celebrate Wins
Use highlights for:
- Team Slack announcements
- Performance bonuses
- Peer recognition

---

## 🚨 Red Flags to Watch

### Agent Level
- FCR dropping week-over-week
- Escalation rate increasing
- Multiple weak subcategories appearing
- Reopen rate >15%

### Team Level
- 3+ agents below 70% FCR
- Team escalation rate >15%
- Common weak subcategory across 50%+ of team
- Lowlights increasing week-over-week

---

## 📞 Support

### Questions?
- See `INDIVIDUAL_AGENT_PERFORMANCE_GUIDE.md` for detailed docs
- See `AGENT_COACHING_IMPLEMENTATION_SUMMARY.md` for technical details
- Check test files for usage examples

### Issues?
- Enable debug logging: Set `LOG_LEVEL=DEBUG` in environment
- Check Intercom API permissions include admin read access
- Verify DuckDB file permissions
- Review linter output: `read_lints` on modified files

---

**Quick Reference Version**: 1.0  
**Last Updated**: October 24, 2025

