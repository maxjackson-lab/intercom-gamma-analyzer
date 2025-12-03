"""HTML template rendering utilities for the Railway web server."""

import time
from typing import Any, Dict, Optional


def render_timeline_html() -> str:
    """Return the timeline landing page HTML."""
    return """\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VoC Historical Insights - Timeline</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0;">📊 Voice of Customer - Historical Insights</h1>
            <a href="javascript:history.back()" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                ← Back to Main UI
            </a>
        </div>

        <!-- Historical Context Banner -->
        <div id="contextBanner" class="context-banner" style="display:none;"></div>

        <!-- Tab Navigation -->
        <div class="tab-navigation">
            <button class="tab-button active" onclick="switchTab('weekly')" data-type="weekly">Weekly</button>
            <button class="tab-button" onclick="switchTab('monthly')" data-type="monthly">Monthly</button>
            <button class="tab-button" onclick="switchTab('quarterly')" data-type="quarterly">Quarterly</button>
            </div>

        <!-- Timeline Container -->
        <div id="timelineContainer" class="timeline-container"></div>

        <!-- Trend Chart (shown when ≥4 weeks) -->
        <div id="trendChartSection" class="trend-chart-section" style="display:none;">
            <h3>Topic Volume Trends</h3>
            <canvas id="volumeTrendChart"></canvas>
                </div>
            </div>

    <script src="/static/timeline.js"></script>
</body>
</html>
    """


def render_chat_html_v2(app_version: str, git_commit: str, cache_bust: Optional[str] = None) -> str:
    """Return the chat interface HTML."""
    git_short = git_commit[:8] if git_commit != "unknown" else "unknown"
    APP_VERSION = app_version
    GIT_COMMIT = git_commit
    cache_bust_value = cache_bust or f"{app_version}-{git_short}-{int(time.time())}"
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intercom Analysis Tool v{APP_VERSION}</title>
    <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.2.1/ansi_up.min.js"></script>
    <link rel="stylesheet" href="/static/styles.css?v={cache_bust_value}">
    <!-- Cache busting for app.js -->
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0;">🤖 Intercom Analysis Tool - Chat Interface</h1>
            <div style="display: flex; gap: 10px;">
                <a href="/files" style="padding: 10px 20px; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                    📁 Browse Files
                </a>
            <a href="/history" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                📊 View Historical Analysis
            </a>
            </div>
        </div>

        <!-- Active Job Banner (hidden by default, shown by resumeActiveExecution) -->
        <div id="activeJobBanner" style="display: none; margin-bottom: 20px; padding: 15px 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-radius: 12px; border: 2px solid #fbbf24; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 700; font-size: 16px; color: #fff; margin-bottom: 5px;">
                        ⚡ Active Job Running
                    </div>
                    <div id="activeJobInfo" style="font-size: 13px; color: #fef3c7;"></div>
                </div>
                <button onclick="resumeFromBanner()" style="padding: 10px 20px; background: #fff; color: #d97706; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    👁️ View Progress
                </button>
            </div>
        </div>

        <!-- Simple Dropdown Form -->
        <div class="analysis-form">
            <h2>Configure Analysis</h2>

            <label>Analysis Type:</label>
            <select id="analysisType" onchange="updateAnalysisOptions()">
                <!-- Quick Diagnostic Tools - Always at Top -->
                <option value="sample-mode">🔬 Sample Mode / Schema Validation (Quick Debug + Data Structure Analysis)</option>
                <option disabled>──────────────────────────</option>

                <optgroup label="Voice of Customer">
                    <option value="voice-of-customer-hilary">VoC: Hilary Format (Topic Cards)</option>
                    <option value="voice-of-customer-narrative-v2" selected>VoC: Narrative V2 (Hilary Weekly Story)</option>
                    <option value="voice-of-customer-synthesis">VoC: Synthesis (Cross-cutting Insights)</option>
                    <option value="voice-of-customer-complete">VoC: Complete (Both Formats)</option>
                </optgroup>
                <optgroup label="Category Deep Dives (Narrative V2)">
                    <option value="analyze-billing">Billing Analysis</option>
                    <option value="analyze-product">Product Feedback</option>
                    <option value="analyze-api">API Issues & Integration</option>
                    <option value="analyze-escalations">Escalations</option>
                    <option value="tech-analysis">Technical Troubleshooting</option>
                </optgroup>
                <optgroup label="Combined Analysis">
                    <option value="analyze-all-categories">All Categories</option>
                </optgroup>
                <optgroup label="Agent Performance - Team Overview">
                    <option value="agent-performance-horatio-team">Horatio: Team Metrics</option>
                    <option value="agent-performance-boldr-team">Boldr: Team Metrics</option>
                    <option value="agent-performance-escalated">Escalated/Senior Staff Analysis</option>
                </optgroup>
                <optgroup label="Agent Performance - Individual Breakdown">
                    <option value="agent-performance-horatio-individual">Horatio: Individual Agents + Taxonomy</option>
                    <option value="agent-performance-boldr-individual">Boldr: Individual Agents + Taxonomy</option>
                </optgroup>
                <optgroup label="Agent Evaluation">
                    <option value="agent-eval-horatio">Horatio: Agent Evaluation</option>
                    <option value="agent-eval-boldr">Boldr: Agent Evaluation</option>
                    <option value="agent-eval-escalated">Escalated/Senior: Agent Evaluation</option>
                </optgroup>
                <optgroup label="Agent Coaching Reports">
                    <option value="agent-coaching-horatio">Horatio: Coaching & Development</option>
                    <option value="agent-coaching-boldr">Boldr: Coaching & Development</option>
                </optgroup>
                <optgroup label="Other Sources">
                    <option value="canny-analysis">Canny Feedback</option>
                </optgroup>
            </select>
            
            <!-- DL_MARKER_VISIBLE_TEST_20251128 -->
            <div style="background: red; color: white; padding: 10px; margin: 10px 0; font-weight: bold; text-align: center;">🚨 TEMPLATE UPDATE TEST - IF YOU SEE THIS, RAILWAY IS SERVING NEW CODE 🚨</div>
            <div id="detailLevelContainer" style="margin-top: 10px; padding: 12px; background: rgba(59, 130, 246, 0.12); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.45); display: none;">
                <!-- DL_MARKER_20251128 -->
                <label style="color: #93c5fd; font-size: 14px; display: block; margin-bottom: 6px;">Output Detail Level:</label>
                <select id="detailLevel" style="padding: 8px; background: #111827; border: 1px solid #3b82f6; border-radius: 4px; color: #e5e7eb; width: 100%;">
                    <option value="standard" selected>📊 Standard — headline fires & top topics</option>
                    <option value="deep">🔍 Deep — adds reasoning snippets & richer BPO detail</option>
                    <option value="comprehensive">🎯 Comprehensive — audit-ready narrative (thinking + traceability)</option>
                </select>
                <div id="detailLevelHelper" style="font-size: 11px; color: #93c5fd; margin-top: 6px; line-height: 1.5;">
                    Available for Voice of Customer workflows.
                </div>
            </div>

            <!-- Info Panel for Individual Breakdown -->
            <div id="individualBreakdownInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
                <div style="font-size: 12px; color: #3b82f6;">
                    <strong>📊 Individual Agent Breakdown Includes:</strong>
                    <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                        <li>Per-agent FCR, escalation, and response time metrics</li>
                        <li>Performance breakdown by taxonomy categories (Billing, Bug, API, etc.)</li>
                        <li>Performance breakdown by subcategories (Billing>Refund, Bug>Export, etc.)</li>
                        <li>Strong and weak areas for each agent</li>
                        <li>Agent rankings and comparisons</li>
                        <li>Example conversations (best and needs-coaching)</li>
                    </ul>
                </div>
            </div>

            <!-- Info Panel for Coaching Reports -->
            <div id="coachingReportInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.3);">
                <div style="font-size: 12px; color: #f59e0b;">
                    <strong>🎯 Coaching Report Includes:</strong>
                    <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                        <li>Coaching priority (high/medium/low) for each agent</li>
                        <li>Specific coaching focus areas (weak categories/subcategories)</li>
                        <li>Praise-worthy achievements to recognize</li>
                        <li>Top and bottom performers identification</li>
                        <li>Example conversations for coaching sessions</li>
                        <li>Team-wide coaching needs and training recommendations</li>
                    </ul>
                </div>
            </div>

            <!-- Info Panel for Team Overview -->
            <div id="teamOverviewInfo" style="display:none; margin-top: 15px; padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                <div style="font-size: 12px; color: #10b981;">
                    <strong>📈 Team Performance Overview Includes:</strong>
                    <ul style="margin: 8px 0; padding-left: 20px; line-height: 1.6;">
                        <li>Aggregated team FCR and escalation rates</li>
                        <li>Overall team strengths and weaknesses</li>
                        <li>Top categories handled</li>
                        <li>Team highlights and lowlights</li>
                        <li>No individual agent breakdown (use Individual Breakdown for that)</li>
                    </ul>
                </div>
            </div>

            <div id="agentPerformanceOptions" style="display:none; margin-top: 15px; padding: 15px; background: rgba(8, 47, 73, 0.8); border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.3); color: #e0f2fe;">
                <p style="margin: 0 0 10px 0; font-size: 13px;">
                    🎯 <strong>Taxonomy Filter Aware:</strong> When Agent Performance is selected, the "Filter by Taxonomy"
                    dropdown below maps directly to <code>--focus-categories</code>. Pick Billing, Bug, API, etc. to limit all
                    KPIs, trends, and QC examples to those categories only.
                </p>
                <div style="margin-top: 12px;">
                    <label style="display:flex;align-items:center;cursor:pointer;gap:8px;">
                        <input type="checkbox" id="agentPerformanceTroubleshootingToggle" style="width:18px;height:18px;cursor:pointer;">
                        <span style="font-weight:600; color:#7dd3fc;">🔧 Include troubleshooting deep dive</span>
                    </label>
                    <p style="margin:5px 0 0 26px; font-size: 12px; color: #bae6fd;">
                        Adds the <code>--analyze-troubleshooting</code> flag to surface diagnostic loops, low-signal tags,
                        and escalation chains. Recommended after major Fin or tooling changes.
                    </p>
                </div>
            </div>

            <label id="timePeriodLabel">Time Period:</label>
            <select id="timePeriod">
                <option value="yesterday">Yesterday (fast - ~1k conversations)</option>
                <option value="week" selected>Last Week (~7k conversations)</option>
                <option value="month">Last Month (full analysis)</option>
                <option value="custom">Custom Date Range...</option>
            </select>

            <!-- Sample Mode specific options (hidden by default) -->
            <div id="sampleModeOptions" style="display:none; background: rgba(16, 185, 129, 0.1); padding: 15px; border-radius: 8px; margin-top: 15px; border: 1px solid rgba(16, 185, 129, 0.3);">
                <div style="margin-bottom: 10px; color: #10b981; font-weight: bold;">
                    🔬 Sample Mode: Schema Validation & Quick Debug
                </div>
                <p style="margin: 10px 0; font-size: 14px; color: #d1d5db;">
                    Pulls <strong>real conversations</strong> with ultra-rich logging. Shows exactly what fields 
                    Intercom populates and debugs topic detection issues.
                </p>

                <label style="color: #e5e7eb; font-size: 14px; margin-top: 10px; display: block;">Analysis Depth:</label>
                <select id="sampleDetailLevel" style="margin-bottom: 15px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;">
                    <option value="standard">📊 Standard - Concise summary (default)</option>
                    <option value="deep">🔍 Deep - Adds reasoning for top topics</option>
                    <option value="comprehensive" selected>🎯 Comprehensive - Full agent thoughts & patterns</option>
                </select>

                <label for="sampleCount" style="color: #e5e7eb; font-size: 14px; display: block;">Sample Volume (10-100 conversations)</label>
                <input 
                    type="number" 
                    id="sampleCount" 
                    min="10" 
                    max="100" 
                    step="10" 
                    value="50"
                    style="margin-bottom: 10px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;"
                />
                <p style="margin: 5px 0 15px 0; font-size: 12px; color: #9ca3af;">
                    Controls the <code>--count</code> flag sent to the CLI (validated by Railway: min 10, max 100). 
                    Increase for more schema samples, decrease for faster iteration.
                </p>

                <label style="color: #e5e7eb; font-size: 14px; display: block;">Time Period:</label>
                <select id="sampleTimePeriod" style="margin-bottom: 15px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;">
                    <option value="day">Last 24 Hours</option>
                    <option value="week" selected>Last Week ⭐</option>
                    <option value="month">Last Month</option>
                </select>

                <label style="color: #e5e7eb; font-size: 14px; display: block;">AI Model:</label>
                <select id="sampleAiModel" style="margin-bottom: 15px; padding: 8px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb; width: 100%;">
                    <option value="openai" selected>🤖 OpenAI (GPT-4o-mini) - Fast & Balanced ⭐</option>
                    <option value="claude">🧠 Claude (Haiku 4.5) - More Accurate</option>
                </select>
                <p style="margin: -10px 0 15px 0; font-size: 12px; color: #9ca3af;">
                    Choose the AI model for LLM-powered analysis (sentiment, topic detection, agent tests)
                </p>

                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                        <input type="checkbox" id="includeHierarchy" checked style="margin-right: 8px; cursor: pointer;">
                        <span>Show Topic Hierarchy Debug Section</span>
                    </label>
                    <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                        Displays topic detection and hierarchy structure debugging information
                    </p>
                </div>

                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                        <input type="checkbox" id="testAllAgents" style="margin-right: 8px; cursor: pointer;">
                        <span>🧪 Test ALL Production Agents</span>
                    </label>
                    <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                        Tests 6 agents: SubTopic, Example, Fin, Correlation, Quality, Confidence (+30s runtime)
                    </p>
                </div>

                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                        <input type="checkbox" id="showAgentThinking" style="margin-right: 8px; cursor: pointer;">
                        <span>🧠 Show Agent Thinking</span>
                    </label>
                    <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                        Shows LLM prompts, responses, and agent reasoning - perfect for prompt tuning (+1 min runtime)
                    </p>
                </div>

                <div style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer; color: #e5e7eb; font-size: 14px;">
                        <input type="checkbox" id="llmTopicDetection" style="margin-right: 8px; cursor: pointer;">
                        <span>🤖 LLM-First Topic Detection</span>
                    </label>
                    <p style="margin: 5px 0 0 24px; font-size: 12px; color: #9ca3af;">
                        Uses LLM to classify every conversation (more accurate for edge cases, costs ~$1 per 200 convs)
                    </p>
                </div>

                <div style="margin-top: 10px; padding: 10px; background: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981; font-size: 13px; color: #e5e7eb;">
                    <strong style="color: #10b981;">💡 What You'll See:</strong>
                    <ul style="margin: 5px 0 0 20px; padding: 0; color: #d1d5db;">
                        <li><strong>Field Coverage:</strong> % of tickets with custom_attributes, tags, "Reason for contact"</li>
                        <li><strong>Tag Analysis:</strong> What custom tags exist and how often they're used</li>
                        <li><strong>Attribute Breakdown:</strong> All custom_attributes keys and sample values</li>
                        <li><strong>Topic Hierarchy:</strong> How conversations are assigned to categories (toggleable)</li>
                        <li><strong>Full Samples:</strong> Raw schema of real conversations with all fields</li>
                        <li><strong>LLM Sentiment Test:</strong> Actual sentiment generated by agents</li>
                    </ul>
                </div>
                <div style="margin-top: 10px; font-size: 12px; color: #9ca3af;">
                    <strong>Output:</strong> Terminal + JSON + Complete .log file (download from Files tab)
                </div>
            </div>

            <div id="customDateInputs" style="display:none; margin-top: 10px;">
                <label>Start Date: <input type="date" id="startDate"></label>
                <label>End Date: <input type="date" id="endDate"></label>
            </div>

            <label>Data Source:</label>
            <select id="dataSource">
                <option value="intercom" selected>Intercom Only</option>
                <option value="canny">Canny Only</option>
                <option value="both">Both Sources</option>
            </select>

            <label>Filter by Taxonomy (optional):</label>
            <select id="taxonomyFilter">
                <option value="" selected>All Categories</option>
                <option value="Billing">Billing – refunds, invoices, payments</option>
                <option value="Bug">Bug Reports – crashes, errors, broken flows</option>
                <option value="API">API &amp; Endpoint Issues</option>
                <option value="Product Question">Product Questions &amp; How-to</option>
                <option value="Account">Account Access &amp; Settings</option>
                <option value="Feedback">Feedback &amp; Feature Requests</option>
                <option value="Agent/Buddy">Agent/Buddy Interactions</option>
                <option value="Workspace">Workspace &amp; Team Management</option>
                <option value="Privacy">Privacy, GDPR &amp; Compliance</option>
                <option value="Chargeback">Chargeback / Dispute</option>
                <option value="Partnerships">Partnerships &amp; Integrations</option>
                <option value="Promotions">Promotions &amp; Discounts</option>
                <option value="Abuse">Abuse / DMCA / Malicious Content</option>
                <option value="Unknown">Unclassified / Triage Later</option>
            </select>

            <label>Output Format:</label>
            <select id="outputFormat">
                <option value="markdown" selected>Markdown Report</option>
                <option value="gamma">Gamma Presentation</option>
            </select>

            <label>AI Model:</label>
            <select id="aiModel">
                <option value="openai" selected>🤖 OpenAI (GPT-4o + GPT-4o-mini) - Fast & Reliable</option>
                <option value="claude">🧠 Claude (Sonnet 4.5 + Haiku 4.5) - Advanced Reasoning</option>
            </select>
            <div style="margin-top: 8px; font-size: 12px; color: #9ca3af; padding-left: 4px;">
                <strong>OpenAI:</strong> GPT-4o-mini for quick tasks, GPT-4o for complex analysis<br>
                <strong>Claude:</strong> Haiku 4.5 for quick tasks, Sonnet 4.5 for complex analysis
            </div>

            <!-- Test Mode Options -->
            <div style="margin-top: 20px; padding: 15px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 1px solid rgba(245, 158, 11, 0.3);">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="testMode" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 600; color: #f59e0b;">🧪 Test Mode (Use Mock Data)</span>
                </label>
                <div id="testModeOptions" style="display: none; margin-top: 12px; padding-left: 28px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px;">
                        Test Data Volume:
                        <select id="testDataCount" style="margin-left: 8px; padding: 4px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px; color: #e5e7eb;">
                            <option value="50">50 conversations (quick test)</option>
                            <option value="100" selected>100 conversations (1 hour)</option>
                            <option value="500">500 conversations (few hours)</option>
                            <option value="1000">1,000 conversations (~1 day)</option>
                            <option value="5000">5,000 conversations (~1 week) ⭐</option>
                            <option value="10000">10,000 conversations (2 weeks)</option>
                            <option value="20000">20,000 conversations (1 month)</option>
                        </select>
                    </label>
                    <label style="display: flex; align-items: center; margin-top: 8px; cursor: pointer;">
                        <input type="checkbox" id="verboseLogging" checked style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;">
                        <span style="font-size: 13px;">Verbose Logging (DEBUG level)</span>
                    </label>
                    <div style="font-size: 11px; color: #f59e0b; margin-top: 10px; line-height: 1.5;">
                        <strong>ℹ️ Test Mode Benefits:</strong><br>
                        • No API calls - runs instantly<br>
                        • Realistic data distribution (tiers, topics, languages)<br>
                        • DEBUG logs show agent decision-making<br>
                        • Perfect for testing changes before production
                    </div>
                </div>
            </div>

            <!-- Audit Trail Mode -->
            <div style="margin-top: 15px; padding: 15px; background: rgba(139, 92, 246, 0.1); border-radius: 8px; border: 1px solid rgba(139, 92, 246, 0.3);">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="auditMode" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 600; color: #a78bfa;">📋 Audit Trail Mode (Show Your Work)</span>
                </label>
                <div style="font-size: 11px; color: #a78bfa; margin-top: 10px; line-height: 1.5;">
                    <strong>ℹ️ Audit Trail Benefits:</strong><br>
                    • Narrates every step of analysis in plain language<br>
                    • Shows all decisions made and why<br>
                    • Documents data quality checks<br>
                    • Generates detailed report for data engineer review<br>
                    • Builds confidence in analysis methodology<br>
                    • Perfect for validation and debugging
                </div>
            </div>

            <!-- LLM-First Topic Detection (VOC only) -->
                <div id="llmTopicDetectionVocContainer" style="margin-top: 15px; padding: 15px; background: rgba(34, 197, 94, 0.1); border-radius: 8px; border: 1px solid rgba(34, 197, 94, 0.3); display: none;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="llmTopicDetectionVoc" checked style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-weight: 600; color: #22c55e;">🤖 LLM-First Topic Detection (ENABLED BY DEFAULT)</span>
                    </label>
                    <div style="font-size: 11px; color: #86efac; margin-top: 10px; line-height: 1.5;">
                        <strong>✅ Now Default for Maximum Accuracy:</strong><br>
                        • LLM classifies EVERY conversation (not just keywords)<br>
                        • Understands nuance: "confused annual with monthly" → Billing/Refund<br>
                        • Corrects mis-tagged SDK data automatically<br>
                        • Solves double-counting issues completely<br>
                        • Cost: ~$1 per 200 conversations (worth it for accuracy!)<br>
                        • Uncheck to revert to keyword-only mode
                </div>
            </div>

            <!-- Digest Mode Toggle -->
            <div id="digestModeContainer" style="margin-top: 15px; padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3); display: none;">
                <label style="display: flex; align-items: center; cursor: pointer;" title="Digest mode tightens Narrative V2 output for fast LLM regression sanity checks.">
                    <input type="checkbox" id="digestModeToggle" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 600; color: #60a5fa;">📄 Digest Mode (Executive Readout)</span>
                </label>
                <div style="font-size: 11px; color: #93c5fd; margin-top: 10px; line-height: 1.5;">
                    • Outputs executive summary, Tier-1 topic cards, prioritized actions<br>
                    • Hides legacy trend/churn blocks to keep narrative concise<br>
                    • Perfect for weekly proofs or leadership readouts<br>
                    • Recommended after LLM/prompt changes to sanity-check Narrative V2 regressions
                </div>
            </div>
            
            <!-- Detail Level Dropdown (visible for VoC modes) -->
            <div id="agentToggleContainer" style="margin-top: 15px; padding: 15px; background: rgba(107, 114, 128, 0.15); border-radius: 8px; border: 1px solid rgba(107, 114, 128, 0.4); display: none;">
                <div style="font-weight: 600; color: #e5e7eb; margin-bottom: 8px;">🧩 Agent Controls (per-run)</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px;">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentSubtopics" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">Sub-Topic Detection</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentTopicSentiment" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">Topic Sentiment</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentTopicExamples" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">Topic Examples</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentFinAnalysis" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">Fin Performance</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentBpoAnalysis" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">BPO Vendor Analysis</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="agentTrendAnalysis" checked style="width:18px;height:18px;">
                        <span style="color: #fbbf24;">Trend Analysis</span>
                    </label>
                </div>
                <p style="margin-top:10px;font-size:12px;color:#cbd5f5;">
                    Uncheck agents to save time/LLM spend for exploratory runs. Each toggle maps directly to CLI feature flags.
                </p>
            </div>
            
            <div id="insightFlagsContainer" style="margin-top: 15px; padding: 15px; background: rgba(249, 115, 22, 0.08); border-radius: 8px; border: 1px solid rgba(249, 115, 22, 0.3); display: none;">
                <div style="font-weight: 600; color: #fb923c; margin-bottom: 8px;">🧠 Phase 4.5 Insight Agents</div>
                <label style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
                    <input type="checkbox" id="correlationAgentToggle" checked style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="color: #fed7aa;">CorrelationAgent (Tier × CSAT × Escalation patterns)</span>
                </label>
                <label style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
                    <input type="checkbox" id="qualityInsightsToggle" checked style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="color: #fed7aa;">QualityInsightsAgent (FCR, reopen anomalies, exceptional convos)</span>
                </label>
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="confidenceMetaToggle" checked style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="color: #fed7aa;">ConfidenceMetaAgent (Data coverage & limitations)</span>
                </label>
                <div style="font-size: 11px; color: #fdba74; margin-top: 10px; line-height: 1.5;">
                    • Uncheck agents to reduce runtime / LLM cost for quick experiments.<br>
                    • Changes apply per-run only and are logged for audit traceability.
                </div>
            </div>
            
            <div id="legacyModeContainer" style="margin-top: 15px; padding: 15px; background: rgba(148, 163, 184, 0.12); border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.3); display: none;">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="legacyModeToggle" style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                    <span style="font-weight: 600; color: #cbd5f5;">🕰️ Legacy Hilary Mode (V1 Multi-Agent)</span>
                </label>
                <div style="font-size: 11px; color: #e2e8f0; margin-top: 10px; line-height: 1.5;">
                    • Replays the original Data → Category → Sentiment → Insight → Presentation stack.<br>
                    • Perfect for regression testing vs. TopicOrchestrator and validating historical decks.<br>
                    • Available for topic-based Hilary cards only (Intercom-only data; skips Canny).
                </div>
            </div>

            <button onclick="runAnalysis()" class="run-button">▶️ Run Analysis</button>
        </div>

        <!-- Old chat input and redundant analysisMode removed -->

        <div id="status"></div>

        <!-- Terminal output container -->
        <div class="terminal-container" id="terminalContainer">
            <div class="terminal-header">
                <div class="terminal-title">
                    <span class="spinner" id="executionSpinner" style="display:none;"></span>
                    <span id="terminalTitle">Command Execution</span>
                </div>
                <div class="terminal-controls">
                    <span class="status-badge" id="executionStatus" style="display:none;">Running</span>
                    <button class="btn-cancel" id="cancelButton" onclick="cancelExecution()" style="display:none;">Cancel</button>
                </div>
            </div>

            <!-- Active Job Tabs (Multi-job Support) -->
            <div id="jobTabsContainer" style="display: none; margin-bottom: 15px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #9ca3af; font-weight: 600;">ACTIVE JOBS</span>
                    <button id="startAnotherJobBtn" onclick="startAnotherJob()" style="padding: 4px 10px; background: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 4px; color: #22c55e; cursor: pointer; font-size: 11px; font-weight: 600;">
                        + New Job
                    </button>
                </div>
                <div id="jobTabs" style="display: flex; gap: 8px; flex-wrap: wrap; padding: 8px; background: rgba(17, 24, 39, 0.6); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
                    <!-- Job tabs will be dynamically populated -->
                </div>
            </div>

            <!-- Execution History Selector -->
            <div id="executionHistoryPanel" style="display: none; margin-bottom: 15px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <label style="font-weight: 600; color: #3b82f6; min-width: 140px;">📂 View Past Run:</label>
                    <select id="executionHistorySelect" onchange="loadHistoricalExecution()" style="flex: 1; padding: 8px; border-radius: 4px; border: 1px solid rgba(59, 130, 246, 0.5); background: rgba(17, 24, 39, 0.8); color: #e5e7eb; cursor: pointer;">
                        <option value="">-- Current Execution --</option>
                    </select>
                    <button onclick="refreshExecutionHistory()" style="padding: 8px 16px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.5); border-radius: 4px; color: #60a5fa; cursor: pointer; white-space: nowrap;">
                        🔄 Refresh List
                    </button>
                </div>
                <div style="font-size: 11px; color: #9ca3af;">
                    💡 Access output files from completed analysis runs
                </div>
            </div>

            <!-- Tab Navigation (ALWAYS VISIBLE - user can browse files anytime) -->
            <div class="tab-navigation" id="tabNavigation">
                <button class="tab-button" onclick="switchTab('terminal')" id="terminalTab">Terminal</button>
                <button class="tab-button" onclick="switchTab('summary')" id="summaryTab">Summary</button>
                <button class="tab-button active" onclick="switchTab('files')" id="filesTab">Files</button>
                <button class="tab-button" onclick="switchTab('gamma')" id="gammaTab">Gamma</button>
            </div>

            <!-- Tab Content -->
            <div class="tab-content">
                <div class="tab-pane" id="terminalTabContent">
                    <div class="terminal-output" id="terminalOutput"></div>
                </div>
                <div class="tab-pane" id="summaryTabContent">
                    <div id="analysisSummary" class="summary-container">
                        <h3>📊 Analysis Summary</h3>
                        <div class="summary-cards"></div>
                    </div>
                </div>
                <div class="tab-pane active" id="filesTabContent">
                    <div id="filesList" class="files-container">
                        <h3>📁 Available Output Files</h3>
                        <p style="color: #9ca3af; margin: 10px 0;">
                            All files from current and past analysis runs. Downloads available immediately.
                        </p>
                        <div id="filesContent" class="files-list">
                            <p style="color: #60a5fa;">Loading files...</p>
                        </div>
                    </div>
                </div>
                <div class="tab-pane" id="gammaTabContent">
                    <div id="gammaLinks" class="gamma-container">
                        <h3>📈 Gamma Presentations</h3>
                        <div class="gamma-links"></div>
                    </div>
                </div>
            </div>

            <div id="executionResults" style="padding: 15px; background: #2d2d2d; display: none;">
                <div id="downloadLinks"></div>
            </div>
        </div>


        <!-- Recent Jobs -->
        <div id="recentJobs" class="examples" style="display: none;">
            <h3>📋 Recent Jobs</h3>
            <div id="jobsList"></div>
        </div>

        <!-- Example queries removed - using simple dropdown form instead -->
    </div>

    <!-- Version marker for cache verification -->
    <div id="version-footer" style="position: fixed; bottom: 5px; right: 5px; background: rgba(0,0,0,0.7); color: #0f0; padding: 3px 8px; font-size: 10px; border-radius: 3px; font-family: monospace; z-index: 9999;">
        v{APP_VERSION}-{GIT_COMMIT[:8] if GIT_COMMIT != 'unknown' else 'unknown'}
    </div>

    <script src="/static/app.js?v={cache_bust_value}"></script>
    <script>
        // Robust cache busting: reload app.js if version in DOM doesn't match server
        (function() {{
            const serverVersion = "{cache_bust_value}";
            const scripts = document.getElementsByTagName('script');
            let appJsFound = false;
            
            for (let i = 0; i < scripts.length; i++) {{
                const src = scripts[i].src;
                if (src && src.includes('app.js')) {{
                    const url = new URL(src);
                    const loadedVersion = url.searchParams.get('v');
                    
                    if (loadedVersion !== serverVersion) {{
                        console.log('⚠️ app.js version mismatch. Reloading...', loadedVersion, 'vs', serverVersion);
                        const newScript = document.createElement('script');
                        newScript.src = '/static/app.js?v=' + serverVersion + '&t=' + new Date().getTime();
                        document.body.appendChild(newScript);
                    }}
                    appJsFound = true;
                    break;
                }}
            }}
        }})();
    </script>
    <script src="/static/file_browser.js?v={cache_bust_value}"></script>
</body>
</html>
    """


def render_files_html(cache_bust: Optional[str] = None) -> str:
    """Return the dedicated files browser HTML."""
    cache_bust_value = cache_bust or str(int(time.time()))
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Files</title>
    <link rel="stylesheet" href="/static/styles.css?v={cache_bust_value}">
</head>
<body style="background: #0a0a0a; color: #e5e7eb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px;">
    <div class="container" style="max-width: 960px; margin: 0 auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #60a5fa;">📁 Analysis Files</h1>
            <a href="/" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.3)';">
                ← Back to Main UI
            </a>
        </div>
        <div style="margin-bottom: 20px; padding: 15px; background: rgba(96, 165, 250, 0.1); border-radius: 8px; border: 1px solid rgba(96, 165, 250, 0.3);">
            <p style="margin: 0; color: #93c5fd; font-size: 14px;">
                Browse and download output files from current and historical runs. The list refreshes automatically every 30 seconds.
            </p>
        </div>
        <div id="filesContent" style="min-height: 200px;">
            <p style="color: #60a5fa;">Loading files...</p>
        </div>
    </div>
    <script src="/static/file_browser.js?v={cache_bust_value}"></script>
</body>
</html>
    """


def render_history_placeholder(historical_url: str) -> str:
    """Return guidance when the historical timeline UI is not configured."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Historical Analysis - Setup Required</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <h1>📊 Historical Analysis Timeline</h1>
        
        <div style="margin: 30px 0; padding: 20px; background: rgba(245, 158, 11, 0.1); border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.3);">
            <h3 style="color: #f59e0b; margin-top: 0;">⚠️ Setup Required</h3>
            <p style="color: #d1d5db; line-height: 1.8;">
                The Historical Analysis Timeline UI needs to be started separately or deployed as an additional service.
            </p>
            
            <h4 style="color: #e5e7eb; margin-top: 20px;">For Local Development:</h4>
            <pre style="background: #0a0a0a; padding: 15px; border-radius: 8px; overflow-x: auto;"><code style="color: #10b981;">python railway_web.py</code></pre>
            <p style="color: #9ca3af; font-size: 14px;">Then visit: <a href="{historical_url}" style="color: #667eea;">{historical_url}</a></p>
            
            <h4 style="color: #e5e7eb; margin-top: 20px;">For Production Deployment:</h4>
            <p style="color: #9ca3af; line-height: 1.8;">
                Set the <code style="background: #1a1a1a; padding: 2px 6px; border-radius: 4px; color: #f59e0b;">HISTORICAL_UI_URL</code>
                environment variable to point to your deployed historical timeline service URL.
            </p>
            
            <div style="margin-top: 30px;">
                <a href="/" style="padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    ← Back to Main Interface
                </a>
            </div>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: rgba(16, 185, 129, 0.1); border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">
            <h3 style="color: #10b981; margin-top: 0;">Need the timeline?</h3>
            <p style="color: #d1d5db; line-height: 1.8;">
                Deploy the historical UI service and set <code style="background: #1a1a1a; padding: 2px 6px; border-radius: 4px; color: #10b981;">HISTORICAL_UI_URL</code>
                to the externally accessible URL. This route will automatically redirect there when configured.
            </p>
        </div>
    </div>
</body>
</html>
    """


def render_snapshot_detail_html(snapshot: Dict[str, Any]) -> str:
    """Return the snapshot detail HTML view."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{snapshot.get('date_range_label', 'Snapshot')} - VoC Analysis</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <a href="/" style="color: #667eea; text-decoration: none; display: inline-block; margin-bottom: 20px;">← Back to Timeline</a>

        <h1>📊 {snapshot.get('date_range_label', 'Snapshot Details')}</h1>

        <div class="summary-container">
            <h3>Analysis Summary</h3>
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="card-title">Type</div>
                    <div class="card-value">{snapshot.get('analysis_type', 'Unknown').title()}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Total Conversations</div>
                    <div class="card-value">{snapshot.get('total_conversations', 0):,}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Created</div>
                    <div class="card-value">{snapshot.get('created_at', 'Unknown')}</div>
                </div>
            </div>

            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Key Insights</h4>
                <p style="color: #9ca3af; line-height: 1.6;">{snapshot.get('insights_summary', 'No summary available')}</p>
            </div>

            <div style="margin-top: 20px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Topic Volumes</h4>
                <div class="summary-cards">
                    {''.join([f'<div class="summary-card"><div class="card-title">{topic}</div><div class="card-value">{vol}</div></div>' for topic, vol in (snapshot.get('topic_volumes', {}) or {}).items()])}
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    """


def render_snapshot_comparison_html(
    current: Dict[str, Any],
    prior: Dict[str, Any],
    comparison: Dict[str, Any]
) -> str:
    """Return the snapshot comparison HTML view."""
    volume_changes_html = "<br>".join([
        f"{topic}: {change:+.1f}% ({abs_change:+d} conversations)"
        for topic, change, abs_change in comparison.get("volume_changes", [])
    ])
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparison - VoC Analysis</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <a href="/" style="color: #667eea; text-decoration: none; display: inline-block; margin-bottom: 20px;">← Back to Timeline</a>

        <h1>📊 Period Comparison</h1>

        <div class="summary-container">
            <h3>Comparing Periods</h3>
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="card-title">Current Period</div>
                    <div class="card-value">{current.get('date_range_label', 'Unknown')}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">Prior Period</div>
                    <div class="card-value">{prior.get('date_range_label', 'Unknown')}</div>
                </div>
            </div>

            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Volume Changes</h4>
                <p style="color: #9ca3af; line-height: 1.8;">{volume_changes_html or 'No significant changes'}</p>
            </div>

            <div style="margin-top: 20px; padding: 20px; background: #0a0a0a; border-radius: 12px;">
                <h4 style="color: #e5e7eb; margin-bottom: 12px;">Significant Changes</h4>
                <ul style="color: #9ca3af; line-height: 1.8;">
                    {''.join([f'<li>{change}</li>' for change in comparison.get('significant_changes', [])])}
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
    """
