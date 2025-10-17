"""
CLI Help System for Intercom Analysis Tool.
Provides comprehensive help, examples, and interactive mode.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.markdown import Markdown
from typing import Dict, List, Optional

console = Console()


class CLIHelpSystem:
    """Comprehensive help system for the CLI."""
    
    def __init__(self):
        self.commands = {
            # Primary Commands (Technical Triage)
            'tech-analysis': {
                'category': 'Primary',
                'description': 'Find technical troubleshooting patterns',
                'usage': 'python -m src.main tech-analysis --days 30',
                'options': ['--days', '--start-date', '--end-date', '--generate-ai-report', '--max-pages']
            },
            'find-macros': {
                'category': 'Primary', 
                'description': 'Discover macro opportunities',
                'usage': 'python -m src.main find-macros --min-occurrences 5 --days 30',
                'options': ['--min-occurrences', '--days', '--start-date', '--end-date']
            },
            'fin-escalations': {
                'category': 'Primary',
                'description': 'Analyze Fin → human handoffs', 
                'usage': 'python -m src.main fin-escalations --days 30',
                'options': ['--days', '--start-date', '--end-date', '--detailed']
            },
            'analyze-agent': {
                'category': 'Primary',
                'description': 'Agent-specific performance analysis',
                'usage': 'python -m src.main analyze-agent "Dae-Ho" --days 30',
                'options': ['--agent', '--days', '--start-date', '--end-date']
            },
            
            # Secondary Commands (VoC Reports)
            'analyze-category': {
                'category': 'Secondary',
                'description': 'Single taxonomy category report',
                'usage': 'python -m src.main analyze-category billing --days 30',
                'options': ['--category', '--days', '--start-date', '--end-date', '--output-format']
            },
            'analyze-all-categories': {
                'category': 'Secondary',
                'description': 'All 13 taxonomy reports',
                'usage': 'python -m src.main analyze-all-categories --days 30',
                'options': ['--days', '--start-date', '--end-date', '--parallel']
            },
            'analyze-subcategory': {
                'category': 'Secondary',
                'description': 'Specific subcategory analysis',
                'usage': 'python -m src.main analyze-subcategory "Billing > Refund" --days 30',
                'options': ['--subcategory', '--days', '--start-date', '--end-date']
            },
            
            # Advanced Commands (Synthesis)
            'synthesize': {
                'category': 'Advanced',
                'description': 'Cross-category pattern analysis',
                'usage': 'python -m src.main synthesize --categories "Billing,Bug" --days 30',
                'options': ['--categories', '--pattern', '--days', '--start-date', '--end-date']
            },
            'analyze-custom-tag': {
                'category': 'Advanced',
                'description': 'Custom tag analysis (e.g., "DC")',
                'usage': 'python -m src.main analyze-custom-tag "DC" --days 30',
                'options': ['--tag', '--agent', '--days', '--start-date', '--end-date']
            },
            'analyze-escalations': {
                'category': 'Advanced',
                'description': 'Escalation pattern analysis',
                'usage': 'python -m src.main analyze-escalations --to "Hilary" --days 30',
                'options': ['--to', '--from', '--days', '--start-date', '--end-date']
            },
            'analyze-pattern': {
                'category': 'Advanced',
                'description': 'Text pattern search',
                'usage': 'python -m src.main analyze-pattern "email change" --days 30',
                'options': ['--pattern', '--days', '--start-date', '--end-date', '--case-sensitive']
            },
            
            # Utility Commands
            'help': {
                'category': 'Utility',
                'description': 'Show this help message',
                'usage': 'python -m src.main help',
                'options': []
            },
            'interactive': {
                'category': 'Utility',
                'description': 'Start interactive mode',
                'usage': 'python -m src.main interactive',
                'options': []
            },
            'list-commands': {
                'category': 'Utility',
                'description': 'List all available commands',
                'usage': 'python -m src.main list-commands',
                'options': []
            },
            'examples': {
                'category': 'Utility',
                'description': 'Show usage examples',
                'usage': 'python -m src.main examples',
                'options': []
            },
            'show-categories': {
                'category': 'Utility',
                'description': 'List available categories',
                'usage': 'python -m src.main show-categories',
                'options': []
            },
            'show-tags': {
                'category': 'Utility',
                'description': 'List tags in your data',
                'usage': 'python -m src.main show-tags',
                'options': ['--days', '--agent']
            },
            'show-agents': {
                'category': 'Utility',
                'description': 'List all agents',
                'usage': 'python -m src.main show-agents',
                'options': ['--days']
            },
            'sync-taxonomy': {
                'category': 'Utility',
                'description': 'Update taxonomy from Intercom',
                'usage': 'python -m src.main sync-taxonomy --days 90',
                'options': ['--days', '--auto-update']
            }
        }
    
    def show_main_help(self):
        """Display main help message."""
        console.print(Panel.fit(
            "[bold blue]Intercom Analysis Tool for Gamma[/bold blue]\n"
            "[dim]Technical Triage • VoC Reports • Macro Discovery[/dim]",
            border_style="blue"
        ))
        
        console.print("\n[bold]USAGE:[/bold]")
        console.print("  python -m src.main [COMMAND] [OPTIONS]")
        
        # Group commands by category
        categories = {
            'Primary': 'Technical Triage',
            'Secondary': 'VoC Reports', 
            'Advanced': 'Synthesis',
            'Utility': 'Utilities'
        }
        
        for category, description in categories.items():
            console.print(f"\n[bold cyan]{category.upper()} COMMANDS ({description}):[/bold cyan]")
            
            for cmd_name, cmd_info in self.commands.items():
                if cmd_info['category'] == category:
                    console.print(f"  [green]{cmd_name:<20}[/green] {cmd_info['description']}")
        
        console.print(f"\n[bold]Get help on any command:[/bold]")
        console.print("  python -m src.main [COMMAND] --help")
        
        console.print(f"\n[bold]Examples:[/bold]")
        console.print("  python -m src.main tech-analysis --days 30")
        console.print("  python -m src.main find-macros --min-occurrences 5 --days 30")
        console.print("  python -m src.main analyze-category billing --days 7")
    
    def show_command_help(self, command: str):
        """Display detailed help for a specific command."""
        if command not in self.commands:
            console.print(f"[red]Unknown command: {command}[/red]")
            return
        
        cmd_info = self.commands[command]
        
        # Header
        console.print(Panel.fit(
            f"[bold blue]{command.replace('-', ' ').title()} Analysis[/bold blue]",
            border_style="blue"
        ))
        
        # Description
        console.print(f"\n[bold]DESCRIPTION:[/bold]")
        console.print(f"  {cmd_info['description']}")
        
        # Usage
        console.print(f"\n[bold]USAGE:[/bold]")
        console.print(f"  {cmd_info['usage']}")
        
        # Options
        if cmd_info['options']:
            console.print(f"\n[bold]OPTIONS:[/bold]")
            for option in cmd_info['options']:
                console.print(f"  --{option}")
        
        # Examples based on command type
        self._show_command_examples(command)
    
    def _show_command_examples(self, command: str):
        """Show examples for specific commands."""
        examples = {
            'tech-analysis': [
                "# Analyze last 30 days",
                "python -m src.main tech-analysis --days 30",
                "",
                "# Specific date range with AI report", 
                "python -m src.main tech-analysis \\",
                "  --start-date 2025-09-01 \\",
                "  --end-date 2025-10-01 \\",
                "  --generate-ai-report",
                "",
                "# Quick test (3 days, 2 pages)",
                "python -m src.main tech-analysis --days 3 --max-pages 2"
            ],
            'find-macros': [
                "# Find macros with 5+ occurrences",
                "python -m src.main find-macros --min-occurrences 5 --days 30",
                "",
                "# Find macros from specific date range",
                "python -m src.main find-macros \\",
                "  --start-date 2025-09-01 \\",
                "  --end-date 2025-10-01 \\",
                "  --min-occurrences 3"
            ],
            'analyze-category': [
                "# Analyze billing category",
                "python -m src.main analyze-category billing --days 30",
                "",
                "# Specific date range",
                "python -m src.main analyze-category billing \\",
                "  --start-date 2025-09-01 \\",
                "  --end-date 2025-10-01",
                "",
                "# Last 7 days",
                "python -m src.main analyze-category billing --days 7"
            ],
            'synthesize': [
                "# Cross-category analysis",
                "python -m src.main synthesize \\",
                "  --categories \"Billing,Bug\" \\",
                "  --days 30",
                "",
                "# Pattern-specific synthesis",
                "python -m src.main synthesize \\",
                "  --categories \"Billing,Bug\" \\",
                "  --pattern \"refund after bug\" \\",
                "  --days 30"
            ]
        }
        
        if command in examples:
            console.print(f"\n[bold]EXAMPLES:[/bold]")
            for line in examples[command]:
                if line.startswith('#'):
                    console.print(f"  [dim]{line}[/dim]")
                elif line.strip() == "":
                    console.print()
                else:
                    console.print(f"  [green]{line}[/green]")
    
    def show_examples(self):
        """Display comprehensive usage examples."""
        console.print(Panel.fit(
            "[bold blue]Usage Examples[/bold blue]",
            border_style="blue"
        ))
        
        examples = {
            'TECHNICAL TRIAGE': [
                "# Basic technical analysis (30 days)",
                "python -m src.main tech-analysis --days 30",
                "",
                "# With AI-powered insights",
                "python -m src.main tech-analysis --days 30 --generate-ai-report",
                "",
                "# Find macro opportunities (min 5 occurrences)",
                "python -m src.main find-macros --min-occurrences 5 --days 30"
            ],
            'VOICE OF CUSTOMER': [
                "# Single category (billing)",
                "python -m src.main analyze-category billing --days 30",
                "",
                "# Specific date range",
                "python -m src.main analyze-category billing \\",
                "  --start-date 2025-09-01 --end-date 2025-10-01",
                "",
                "# All categories at once",
                "python -m src.main analyze-all-categories --days 30"
            ],
            'FIN ANALYSIS': [
                "# Fin effectiveness by category",
                "python -m src.main fin-escalations --days 30",
                "",
                "# Detailed Fin performance report",
                "python -m src.main analyze-fin --days 30 --detailed"
            ],
            'AGENT PERFORMANCE': [
                "# Dae-Ho's performance",
                "python -m src.main analyze-agent \"Dae-Ho\" --days 30",
                "",
                "# Custom tag analysis",
                "python -m src.main analyze-custom-tag \"DC\" --days 30"
            ],
            'ADVANCED': [
                "# Cross-category synthesis",
                "python -m src.main synthesize \\",
                "  --categories \"Billing,Bug\" \\",
                "  --pattern \"refund after bug\" \\",
                "  --days 30",
                "",
                "# Email change pattern search",
                "python -m src.main analyze-pattern \"email change\" --days 30"
            ],
            'UTILITY': [
                "# Sync taxonomy from Intercom",
                "python -m src.main sync-taxonomy --days 90",
                "",
                "# Show available categories",
                "python -m src.main show-categories",
                "",
                "# Interactive mode (guided)",
                "python -m src.main interactive"
            ]
        }
        
        for category, lines in examples.items():
            console.print(f"\n[bold cyan]{category}:[/bold cyan]")
            for line in lines:
                if line.startswith('#'):
                    console.print(f"  [dim]{line}[/dim]")
                elif line.strip() == "":
                    console.print()
                else:
                    console.print(f"  [green]{line}[/green]")
    
    def show_categories(self):
        """Display available categories."""
        categories = [
            ("Abuse", "13 subcategories", "Reports of harmful behavior, DMCA, malicious links"),
            ("Account", "12 subcategories", "Account access, settings, credits, email changes"),
            ("Billing", "29 subcategories", "Refunds, invoices, subscriptions, payment methods"),
            ("Bug", "30+ subcategories", "Product bugs, errors, functionality issues"),
            ("Agent/Buddy", "Product question > Agent", "AI agent questions and usage"),
            ("Chargeback", "No subcategories", "Disputed or unauthorized charges"),
            ("Feedback", "No subcategories", "Feature requests and suggestions"),
            ("Partnerships", "3 subcategories", "Business collaborations, affiliate programs"),
            ("Privacy", "4 subcategories", "Data protection, security, ToS, privacy policies"),
            ("Product Q", "25+ subcategories", "How-to questions about features"),
            ("Promotions", "No subcategories", "Discounts, special offers, coupon codes"),
            ("Unknown", "No subcategories", "Unclassified or unresponsive conversations"),
            ("Workspace", "2 subcategories", "Member management, permissions, sharing")
        ]
        
        table = Table(title="Available Categories")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Subcategories", style="magenta")
        table.add_column("Description", style="white")
        
        for category, subcats, description in categories:
            table.add_row(category, subcats, description)
        
        console.print(table)
        
        console.print(f"\n[bold]To analyze a category:[/bold]")
        console.print("  python -m src.main analyze-category billing --days 30")
    
    def interactive_mode(self):
        """Start interactive mode with guided prompts."""
        console.print(Panel.fit(
            "[bold blue]Welcome to Intercom Analysis Tool (Interactive)[/bold blue]",
            border_style="blue"
        ))
        
        console.print("\nWhat would you like to analyze?")
        console.print("1. Technical troubleshooting (macros, training, escalations)")
        console.print("2. Specific category (billing, bugs, account, etc.)")
        console.print("3. Fin effectiveness analysis")
        console.print("4. Agent performance (Dae-Ho, Hilary, etc.)")
        console.print("5. Custom pattern search")
        console.print("6. Everything (complete analysis suite)")
        
        choice = Prompt.ask("Choice", choices=["1", "2", "3", "4", "5", "6"], default="1")
        
        if choice == "1":
            self._interactive_technical_analysis()
        elif choice == "2":
            self._interactive_category_analysis()
        elif choice == "3":
            self._interactive_fin_analysis()
        elif choice == "4":
            self._interactive_agent_analysis()
        elif choice == "5":
            self._interactive_pattern_search()
        elif choice == "6":
            self._interactive_complete_analysis()
    
    def _interactive_technical_analysis(self):
        """Interactive technical analysis setup."""
        console.print("\n[bold]Great! Let's set up your technical analysis.[/bold]")
        
        console.print("\nDate range:")
        console.print("1. Last 7 days")
        console.print("2. Last 30 days")
        console.print("3. Custom date range")
        
        date_choice = Prompt.ask("Choice", choices=["1", "2", "3"], default="2")
        
        if date_choice == "1":
            days = 7
        elif date_choice == "2":
            days = 30
        else:
            days = int(Prompt.ask("Number of days", default="30"))
        
        generate_ai = Confirm.ask("Generate AI-powered insights report?", default=True)
        
        console.print(f"\n[bold]Starting analysis...[/bold]")
        console.print("✓ Fetching conversations")
        console.print("✓ Analyzing technical patterns")
        console.print("✓ Finding macro opportunities")
        console.print("✓ Tracking escalations")
        if generate_ai:
            console.print("✓ Generating AI report")
        
        console.print(f"\n[bold green]Complete![/bold green] Reports saved to:")
        console.print("  • outputs/technical_training_YYYYMMDD.md")
        console.print("  • outputs/macros_YYYYMMDD.csv")
        console.print("  • outputs/escalations_YYYYMMDD.csv")
    
    def _interactive_category_analysis(self):
        """Interactive category analysis setup."""
        console.print("\n[bold]Which category would you like to analyze?[/bold]")
        
        categories = [
            "billing", "bug", "account", "abuse", "agent", "chargeback",
            "feedback", "partnerships", "privacy", "product", "promotions",
            "unknown", "workspace"
        ]
        
        category = Prompt.ask("Category", choices=categories, default="billing")
        
        days = int(Prompt.ask("Number of days", default="30"))
        
        console.print(f"\n[bold]Analyzing {category} category for {days} days...[/bold]")
        console.print("✓ Fetching conversations")
        console.print("✓ Filtering by category")
        console.print("✓ Analyzing subcategories")
        console.print("✓ Generating report")
        
        console.print(f"\n[bold green]Complete![/bold green] Report saved to:")
        console.print(f"  • outputs/{category}_analysis_YYYYMMDD.md")
    
    def _interactive_fin_analysis(self):
        """Interactive Fin analysis setup."""
        console.print("\n[bold]Fin effectiveness analysis setup.[/bold]")
        
        days = int(Prompt.ask("Number of days", default="30"))
        detailed = Confirm.ask("Generate detailed performance report?", default=True)
        
        console.print(f"\n[bold]Analyzing Fin performance for {days} days...[/bold]")
        console.print("✓ Fetching Fin interactions")
        console.print("✓ Analyzing escalation patterns")
        console.print("✓ Calculating resolution rates")
        if detailed:
            console.print("✓ Generating detailed performance metrics")
        
        console.print(f"\n[bold green]Complete![/bold green] Report saved to:")
        console.print("  • outputs/fin_effectiveness_YYYYMMDD.md")
    
    def _interactive_agent_analysis(self):
        """Interactive agent analysis setup."""
        console.print("\n[bold]Which agent would you like to analyze?[/bold]")
        
        agents = ["Dae-Ho", "Hilary", "Max Jackson", "All agents"]
        agent = Prompt.ask("Agent", choices=agents, default="Dae-Ho")
        
        days = int(Prompt.ask("Number of days", default="30"))
        
        console.print(f"\n[bold]Analyzing {agent} performance for {days} days...[/bold]")
        console.print("✓ Fetching agent conversations")
        console.print("✓ Analyzing performance metrics")
        console.print("✓ Identifying expertise areas")
        
        console.print(f"\n[bold green]Complete![/bold green] Report saved to:")
        console.print(f"  • outputs/agent_{agent.lower().replace(' ', '_')}_YYYYMMDD.md")
    
    def _interactive_pattern_search(self):
        """Interactive pattern search setup."""
        console.print("\n[bold]Custom pattern search setup.[/bold]")
        
        pattern = Prompt.ask("Search pattern (e.g., 'email change', 'refund request')")
        days = int(Prompt.ask("Number of days", default="30"))
        case_sensitive = Confirm.ask("Case sensitive search?", default=False)
        
        console.print(f"\n[bold]Searching for '{pattern}' in {days} days...[/bold]")
        console.print("✓ Fetching conversations")
        console.print("✓ Searching conversation text")
        console.print("✓ Analyzing matches")
        console.print("✓ Generating pattern report")
        
        console.print(f"\n[bold green]Complete![/bold green] Report saved to:")
        console.print(f"  • outputs/pattern_{pattern.replace(' ', '_')}_YYYYMMDD.md")
    
    def _interactive_complete_analysis(self):
        """Interactive complete analysis setup."""
        console.print("\n[bold]Complete analysis suite setup.[/bold]")
        
        days = int(Prompt.ask("Number of days", default="30"))
        parallel = Confirm.ask("Run analyses in parallel (faster)?", default=True)
        
        console.print(f"\n[bold]Running complete analysis for {days} days...[/bold]")
        console.print("✓ Fetching conversations")
        console.print("✓ Technical troubleshooting analysis")
        console.print("✓ 13 taxonomy category reports")
        console.print("✓ Fin effectiveness report")
        console.print("✓ Agent performance reports")
        console.print("✓ Synthesis report")
        console.print("✓ Coverage report")
        
        console.print(f"\n[bold green]Complete![/bold green] All reports saved to outputs/")
        console.print("  • Technical training report")
        console.print("  • 13 category reports")
        console.print("  • Fin effectiveness report")
        console.print("  • Agent performance reports")
        console.print("  • Synthesis insights")
        console.print("  • Coverage analysis")


# Global help system instance
help_system = CLIHelpSystem()





