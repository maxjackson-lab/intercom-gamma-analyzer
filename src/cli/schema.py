"""
Canonical CLI command schema shared between CLI and Railway web server.
"""
from typing import Any, Dict, Optional, Tuple

DEFAULT_ALLOWED_MODULES = frozenset({'src.main', '-m'})

CANONICAL_COMMAND_MAPPINGS = {
    'sample_mode': {
        'command': 'python',
        'args': ['src/main.py', 'sample-mode'],
        'display_name': 'Sample Mode (Quick Data Check)',
        'description': 'Pull 25-100 real conversations with ultra-rich logging for schema validation',
        'allowed_flags': {
            '--count': {
                'type': 'integer',
                'default': 50,
                'min': 10,
                'max': 100,
                'description': 'Number of conversations to pull'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'default': 'week',
                'description': 'Time period for sampling'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date (YYYY-MM-DD)'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date (YYYY-MM-DD)'
            },
            '--save-to-file': {
                'type': 'boolean',
                'default': False,
                'description': 'Save raw JSON to outputs/'
            },
            '--test-llm': {
                'type': 'boolean',
                'default': False,
                'description': 'Run actual LLM sentiment test on diverse topics'
            },
            '--test-all-agents': {
                'type': 'boolean',
                'default': False,
                'description': 'Test ALL production agents (SubTopic, Example, Fin, Correlation, Quality, Churn, Confidence)'
            },
            '--show-agent-thinking': {
                'type': 'boolean',
                'default': False,
                'description': 'Show agent LLM prompts, responses, and reasoning (for prompt tuning)'
            },
            '--llm-topic-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Use LLM-first for topic detection (more accurate, costs ~$1 per 200 convs)'
            },
            '--schema-mode': {
                'type': 'enum',
                'values': ['quick', 'standard', 'deep', 'comprehensive'],
                'default': 'quick',
                'description': 'Analysis depth: quick(50/30s), standard(200/2m), deep(500/5m), comprehensive(1000/10m)'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model for LLM sentiment test (if --test-llm enabled)'
            },
            '--include-hierarchy': {
                'type': 'boolean',
                'default': True,
                'description': 'Show/hide topic hierarchy debugging section'
            },
            '--no-hierarchy': {
                'type': 'boolean',
                'default': False,
                'description': 'Alias: disable topic hierarchy debugging section (equivalent to --include-hierarchy False)'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--audit-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Run validation checks on all agent outputs'
            }
        },
        'estimated_duration': '30sec-10min (depends on --schema-mode)'
    },
    # Voice of Customer: Topic cards, synthesis, narrative-v2
    'voice_of_customer': {
        'command': 'python',
        'args': ['src/main.py', 'voice-of-customer'],
        'display_name': 'Voice of Customer Analysis',
        'description': (
            'Multi-agent Voice of Customer suite covering Hilary topic cards (TopicOrchestrator), '
            'Narrative V2 weekly story (TopicOrchestratorV2 + NarrativeFormatterAgent), '
            'synthesis-only deep dives, and complete dual-format runs.'
        ),
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--analysis-type': {
                'type': 'enum',
                'values': ['topic-based', 'synthesis', 'complete'],
                    'default': 'topic-based',
                'description': (
                    "Select workflow: 'topic-based' = Hilary card deck via TopicOrchestratorV2 (Voice of Customer V2), "
                    "'synthesis' = strategic insights only, 'complete' = topic-based + synthesis."
                )
            },
            '--multi-agent': {
                'type': 'boolean',
                'default': True,
                'description': 'Use multi-agent workflow'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory for files'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data for faster execution'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate detailed audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--llm-topic-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Use LLM-first for topic detection (more accurate, costs ~$1 per 200 convs)'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            },
            '--include-canny': {
                'type': 'boolean',
                'default': False,
                'description': 'Blend in Snowflake-backed Canny feedback (if SNOWFLAKE_* env vars are set)'
            },
            '--canny-board-id': {
                'type': 'string',
                'description': 'Specific Canny board ID for combined analysis'
            },
            '--enable-fallback': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable fallback to other AI model if primary fails'
            },
            '--include-trends': {
                'type': 'boolean',
                'default': False,
                'description': 'Include historical trend analysis'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation from results'
            },
            '--separate-agent-feedback': {
                'type': 'boolean',
                'default': True,
                'description': 'Separate feedback by agent type (Finn, Boldr, Horatio, etc.)'
            },
            '--digest-mode': {
                'type': 'boolean',
                'default': False,
                'description': (
                    'Digest narrative: tight executive summary + limited topic stories + constrained actions. '
                    'Recommended for quick LLM regression checks after prompt/model changes.'
                )
            },
            '--detail-level': {
                'type': 'enum',
                'values': ['standard', 'deep', 'comprehensive'],
                'default': 'standard',
                'description': 'Control report verbosity: standard (executive-ready), deep (adds reasoning + BPO detail), comprehensive (full traceability/logs).'
            },
            '--legacy-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Run legacy Hilary V1 multi-agent workflow (topic-based only)'
            },
            '--enable-correlation-analysis': {
                'type': 'boolean',
                'default': True,
                'description': 'Ensure Phase 4.5 CorrelationAgent runs (default: enabled)'
            },
            '--disable-correlation-analysis': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip Phase 4.5 CorrelationAgent for this run'
            },
            '--enable-quality-insights': {
                'type': 'boolean',
                'default': True,
                'description': 'Ensure Phase 4.5 QualityInsightsAgent runs (default: enabled)'
            },
            '--disable-quality-insights': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip Phase 4.5 QualityInsightsAgent for this run'
            },
            '--enable-churn-detection': {
                'type': 'boolean',
                'default': True,
                'description': 'Ensure Phase 4.5 ChurnRiskAgent runs (default: enabled)'
            },
            '--disable-churn-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip Phase 4.5 ChurnRiskAgent for this run'
            },
            '--enable-confidence-meta': {
                'type': 'boolean',
                'default': True,
                'description': 'Ensure Phase 4.5 ConfidenceMetaAgent runs (default: enabled)'
            },
            '--disable-confidence-meta': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip Phase 4.5 ConfidenceMetaAgent for this run'
            },
            '--enable-subtopic-detection': {
                'type': 'boolean',
                'default': True,
                'description': 'Run SubTopicDetectionAgent (Tier 2 taxonomy mapping)'
            },
            '--disable-subtopic-detection': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip SubTopicDetectionAgent to speed up runs'
            },
            '--enable-topic-sentiment': {
                'type': 'boolean',
                'default': True,
                'description': 'Generate TopicSentimentAgent insights'
            },
            '--disable-topic-sentiment': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip TopicSentimentAgent (no per-topic narratives)'
            },
            '--enable-topic-examples': {
                'type': 'boolean',
                'default': True,
                'description': 'Run ExampleExtractionAgent for quotes per topic'
            },
            '--disable-topic-examples': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip ExampleExtractionAgent'
            },
            '--enable-fin-analysis': {
                'type': 'boolean',
                'default': True,
                'description': 'Run FinPerformanceAgent (identify Fin performance)'
            },
            '--disable-fin-analysis': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip FinPerformanceAgent'
            },
            '--enable-bpo-analysis': {
                'type': 'boolean',
                'default': True,
                'description': 'Run BpoPerformanceAgent (Horatio/Boldr mapping)'
            },
            '--disable-bpo-analysis': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip BpoPerformanceAgent'
            },
            '--enable-trend-analysis': {
                'type': 'boolean',
                'default': True,
                'description': 'Run TrendAgent for historical comparisons'
            },
            '--disable-trend-analysis': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip TrendAgent even if enabled in config'
            }
        },
        'estimated_duration': '10-30 minutes'
    },
    'agent_performance': {
        'command': 'python',
        'args': ['src/main.py', 'agent-performance'],
        'display_name': 'Agent Performance Analysis',
        'description': 'Analyze individual agent and team performance',
        'allowed_flags': {
            '--agent': {
                'type': 'enum',
                'values': ['horatio', 'boldr', 'escalated'],
                'required': True,
                'description': 'Agent/vendor to analyze'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--individual-breakdown': {
                'type': 'boolean',
                'default': False,
                'description': 'Include per-agent metrics and taxonomy breakdown'
            },
            '--focus-categories': {
                'type': 'string',
                'description': 'Comma-separated categories to focus on (e.g., "Bug,API")'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Alias for focus categories (taxonomy filter)'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation output'
            },
            '--analyze-troubleshooting': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable AI-powered troubleshooting deep dive'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'agent_coaching': {
        'command': 'python',
        'args': ['src/main.py', 'agent-coaching-report'],
        'display_name': 'Agent Coaching Report',
        'description': 'Generate coaching priorities and development areas',
        'allowed_flags': {
            '--vendor': {
                'type': 'enum',
                'values': ['horatio', 'boldr'],
                'required': True,
                'description': 'Vendor to analyze'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'default': 'week',
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category (e.g., Billing, Bug, API)'
            },
            '--top-n': {
                'type': 'integer',
                'default': 5,
                'min': 1,
                'max': 20,
                'description': 'Number of top issues to highlight'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format (when output-format=gamma)'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory for files'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count (tiny, micro, small, medium, large, xlarge, xxlarge, or number)'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use (ChatGPT or Claude)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for custom range'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for custom range'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'category_billing': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-billing'],
        'display_name': 'Billing Analysis',
        'description': 'Multi-agent VoC narrative filtered to Billing (refunds, invoices, subscriptions)',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--days': {
                'type': 'integer',
                'default': 30,
                'description': 'Deprecated fallback for number of rolling days to analyze'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--max-pages': {
                'type': 'integer',
                'description': 'Maximum pages to fetch (testing)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_product': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-product'],
        'display_name': 'Product Feedback Analysis',
        'description': 'Multi-agent VoC narrative filtered to Feature Requests/Product questions',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--days': {
                'type': 'integer',
                'default': 30,
                'description': 'Deprecated fallback for number of days to analyze'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--max-pages': {
                'type': 'integer',
                'description': 'Maximum pages to fetch (testing)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_api': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-api'],
        'display_name': 'API Issues & Integration',
        'description': 'Multi-agent VoC narrative filtered to API/integration issues',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--days': {
                'type': 'integer',
                'default': 30,
                'description': 'Deprecated fallback for number of days to analyze'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--max-pages': {
                'type': 'integer',
                'description': 'Maximum pages to fetch (testing)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'category_escalations': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-escalations'],
        'display_name': 'Escalations Analysis',
        'description': 'Analyze escalation patterns and causes',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--days': {
                'type': 'integer',
                'default': 30,
                'description': 'Deprecated fallback for number of days to analyze'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--max-pages': {
                'type': 'integer',
                'description': 'Maximum pages to fetch (testing)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '3-10 minutes'
    },
    'tech_troubleshooting': {
        'command': 'python',
        'args': ['src/main.py', 'tech-analysis'],
        'display_name': 'Technical Troubleshooting Analysis',
        'description': (
            'Narrative V2 troubleshooting run (TopicOrchestrator + NarrativeFormatter) filtered to Bug/API taxonomy. '
            'Use the taxonomy dropdown to target any category (default: Bug).'
        ),
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--days': {
                'type': 'integer',
                'default': 30,
                'description': 'Deprecated fallback for number of days to analyze'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Primary taxonomy to analyze (e.g., Bug, API, Feedback)'
            },
            '--max-pages': {
                'type': 'integer',
                'description': 'Maximum pages to fetch (testing)'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '5-15 minutes'
    },
    'all_categories': {
        'command': 'python',
        'args': ['src/main.py', 'analyze-all-categories'],
        'display_name': 'All Categories Analysis',
        'description': 'Comprehensive analysis across all categories',
        'allowed_flags': {
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period for analysis'
            },
            '--periods-back': {
                'type': 'integer',
                'default': 1,
                'min': 1,
                'max': 12,
                'description': 'Number of periods to analyze'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format for results'
            },
            '--gamma-export': {
                'type': 'enum',
                'values': ['pdf', 'pptx'],
                'description': 'Gamma export format'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate audit trail'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--filter-category': {
                'type': 'string',
                'description': 'Filter by taxonomy category'
            },
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            }
        },
        'estimated_duration': '15-45 minutes'
    },
    'canny_analysis': {
        'command': 'python',
        'args': ['src/main.py', 'canny-analysis'],
        'display_name': 'Canny Feedback Analysis',
        'description': 'Analyze Canny feature requests and voting patterns',
        'allowed_flags': {
            '--start-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'Start date for analysis'
            },
            '--end-date': {
                'type': 'date',
                'format': 'YYYY-MM-DD',
                'description': 'End date for analysis'
            },
            '--time-period': {
                'type': 'enum',
                'values': ['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks'],
                'description': 'Time period shortcut (overrides start/end)'
            },
            '--board-id': {
                'type': 'string',
                'description': 'Specific Canny board ID'
            },
            '--ai-model': {
                'type': 'enum',
                'values': ['openai', 'claude'],
                'default': 'openai',
                'description': 'AI model to use'
            },
            '--enable-fallback': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable fallback to other AI model'
            },
            '--include-comments': {
                'type': 'boolean',
                'default': True,
                'description': 'Include post comments in analysis'
            },
            '--include-votes': {
                'type': 'boolean',
                'default': True,
                'description': 'Include voting patterns'
            },
            '--generate-gamma': {
                'type': 'boolean',
                'default': False,
                'description': 'Generate Gamma presentation'
            },
            '--output-format': {
                'type': 'enum',
                'values': ['markdown', 'json', 'excel', 'gamma'],
                'default': 'markdown',
                'description': 'Output format'
            },
            '--test-mode': {
                'type': 'boolean',
                'default': False,
                'description': 'Use test data'
            },
            '--test-data-count': {
                'type': 'string',
                'default': '100',
                'description': 'Test data count or preset'
            },
            '--verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable verbose logging'
            },
            '--audit-trail': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable audit trail'
            },
            '--output-dir': {
                'type': 'string',
                'default': 'outputs',
                'description': 'Output directory'
            }
        },
        'estimated_duration': '5-15 minutes'
    }
}

# Legacy aliases used by older web/CLI integrations
CANONICAL_COMMAND_MAPPINGS['agent_performance_team'] = CANONICAL_COMMAND_MAPPINGS['agent_performance']
CANONICAL_COMMAND_MAPPINGS['tech_analysis'] = CANONICAL_COMMAND_MAPPINGS['tech_troubleshooting']

def validate_command_request(analysis_type: str, flags: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate command request against canonical schema.
    
    Args:
        analysis_type: The analysis type key (e.g., 'voice_of_customer')
        flags: Dictionary of flag names and values
        
    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    if analysis_type not in CANONICAL_COMMAND_MAPPINGS:
        return False, f"Unknown analysis type: {analysis_type}"
    
    schema = CANONICAL_COMMAND_MAPPINGS[analysis_type]
    allowed_flags = schema['allowed_flags']
    
    # Check for unknown flags
    for flag_name in flags.keys():
        if flag_name not in allowed_flags:
            return False, f"Unknown flag '{flag_name}' for {analysis_type}"
    
    # Validate flag values
    for flag_name, flag_value in flags.items():
        flag_schema = allowed_flags[flag_name]
        
        if flag_schema['type'] == 'enum':
            if flag_value not in flag_schema['values']:
                return False, f"Invalid value '{flag_value}' for {flag_name}. Must be one of: {flag_schema['values']}"
        
        elif flag_schema['type'] == 'date':
            # Validate date format
            try:
                from datetime import datetime
                datetime.strptime(flag_value, '%Y-%m-%d')
            except ValueError:
                return False, f"Invalid date format for {flag_name}. Expected YYYY-MM-DD"
        
        elif flag_schema['type'] == 'integer':
            try:
                val = int(flag_value)
                if 'min' in flag_schema and val < flag_schema['min']:
                    return False, f"Value for {flag_name} must be at least {flag_schema['min']}"
                if 'max' in flag_schema and val > flag_schema['max']:
                    return False, f"Value for {flag_name} must be at most {flag_schema['max']}"
            except (ValueError, TypeError):
                return False, f"Invalid integer value for {flag_name}"
        
        elif flag_schema['type'] == 'boolean':
            if not isinstance(flag_value, bool):
                return False, f"Flag {flag_name} must be a boolean"
    
    # Check required flags
    for flag_name, flag_schema in allowed_flags.items():
        if flag_schema.get('required', False) and flag_name not in flags:
            return False, f"Missing required flag: {flag_name}"
    
    return True, None


def generate_executor_schema() -> Dict[str, Any]:
    """
    Auto-generate WebCommandExecutor schema from CANONICAL_COMMAND_MAPPINGS.
    
    This eliminates manual maintenance of the WebCommandExecutor whitelist,
    reducing the 4-layer contract (CLI → Schema → Executor → Frontend) to
    3 layers (CLI → Schema → Frontend).
    
    The generated schema has identical structure to the previous hardcoded version
    in WebCommandExecutor.COMMAND_SCHEMAS, ensuring backward compatibility.
    
    Returns:
        Dict with structure matching WebCommandExecutor.COMMAND_SCHEMAS:
        {
            'python': {
                'allowed_modules': {'src.main', '-m'},
                'allowed_flags': set of all flag names,
                'flag_schemas': dict of per-flag validation rules
            }
        }
    
    Example usage:
        COMMAND_SCHEMAS = generate_executor_schema()
    """
    def build_flag_schema(flag_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        flag_type = flag_def.get('type')
        if flag_type in (None, 'boolean'):
            return None
        
        requires_value = flag_def.get('requires_value')
        if requires_value is None:
            requires_value = True
        else:
            requires_value = bool(requires_value)
        
        if flag_type == 'enum':
            return {
                'type': 'enum',
                'values': flag_def.get('values', []),
                'requires_value': requires_value
            }
        if flag_type == 'integer':
            schema_entry: Dict[str, Any] = {'type': 'int', 'requires_value': requires_value}
            if 'min' in flag_def:
                schema_entry['min'] = flag_def['min']
            if 'max' in flag_def:
                schema_entry['max'] = flag_def['max']
            return schema_entry
        if flag_type == 'date':
            return {'type': 'date', 'requires_value': requires_value}
        if flag_type == 'string':
            return {'type': 'string', 'requires_value': requires_value}
        
        raise ValueError(f"Unsupported flag type '{flag_type}'")
    
    # Extract all unique flags from all commands
    all_flags: set = set()
    flag_schemas: Dict[str, Dict[str, Any]] = {}
    flag_origins: Dict[str, str] = {}
    
    for command_key, command_schema in CANONICAL_COMMAND_MAPPINGS.items():
        for flag_name, flag_def in command_schema['allowed_flags'].items():
            all_flags.add(flag_name)
            
            schema_entry = build_flag_schema(flag_def)
            if not schema_entry:
                continue
            
            if flag_name in flag_schemas and flag_schemas[flag_name] != schema_entry:
                origin = flag_origins[flag_name]
                raise ValueError(
                    f"Flag '{flag_name}' has conflicting schema definitions between "
                    f"'{origin}' and '{command_key}'"
                )
            
            flag_schemas[flag_name] = schema_entry
            flag_origins[flag_name] = command_key
    
    return {
        'python': {
            'allowed_modules': set(DEFAULT_ALLOWED_MODULES),
            'allowed_flags': all_flags,
            'flag_schemas': flag_schemas
        }
    }
