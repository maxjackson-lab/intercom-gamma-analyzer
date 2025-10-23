"""
Orchestrator service for coordinating multiple analysis components.

This service acts as the central coordinator for all analysis operations,
managing the execution of different analyzers and combining their results.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.chunked_fetcher import ChunkedFetcher
from src.services.data_preprocessor import DataPreprocessor
from src.services.category_filters import CategoryFilters
from src.services.synthesis_engine import SynthesisEngine
from src.services.gamma_generator import GammaGenerator
from src.services.fin_escalation_analyzer import FinEscalationAnalyzer
from src.services.technical_pattern_detector import TechnicalPatternDetector
from src.services.macro_opportunity_finder import MacroOpportunityFinder
from src.services.story_driven_orchestrator import StoryDrivenOrchestrator

from src.analyzers.billing_analyzer import BillingAnalyzer
from src.analyzers.product_analyzer import ProductAnalyzer
from src.analyzers.sites_analyzer import SitesAnalyzer
from src.analyzers.api_analyzer import ApiAnalyzer

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """
    Orchestrates the execution of multiple analysis components.
    
    This service:
    - Coordinates data fetching and preprocessing
    - Manages parallel execution of category analyzers
    - Handles result synthesis and deduplication
    - Generates comprehensive reports
    - Manages error handling and recovery
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize core services
        self.chunked_fetcher = ChunkedFetcher()
        self.data_preprocessor = DataPreprocessor()
        self.category_filters = CategoryFilters()
        self.synthesis_engine = SynthesisEngine()
        self.gamma_generator = GammaGenerator()
        self.fin_escalation_analyzer = FinEscalationAnalyzer()
        self.technical_pattern_detector = TechnicalPatternDetector()
        self.macro_opportunity_finder = MacroOpportunityFinder()
        
        # Initialize category analyzers
        self.category_analyzers = {
            'billing': BillingAnalyzer(),
            'product': ProductAnalyzer(),
            'sites': SitesAnalyzer(),
            'api': ApiAnalyzer()
        }
        
        # Initialize story-driven orchestrator
        self.story_driven_orchestrator = StoryDrivenOrchestrator()
        
        self.logger.info("AnalysisOrchestrator initialized")

    async def run_comprehensive_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a comprehensive analysis across all categories and components.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            options: Analysis options and configuration
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        self.logger.info(f"Starting comprehensive analysis from {start_date} to {end_date}")
        
        if options is None:
            options = {}
        
        try:
            # Step 1: Fetch and preprocess data
            self.logger.info("Step 1: Fetching and preprocessing data")
            conversations = await self._fetch_and_preprocess_data(start_date, end_date, options)
            
            if not conversations:
                return {
                    'error': 'No conversations found for the specified date range',
                    'summary': {}
                }
            
            # Step 1.5: Validate data completeness and quality
            self.logger.info("Step 1.5: Validating data completeness and quality")
            validation_results = await self._validate_data_completeness(
                conversations,
                options.get('max_conversations', 1000),
                start_date,
                end_date
            )
            
            # Log validation warnings
            for warning in validation_results['warnings']:
                self.logger.warning(f"Data validation: {warning}")
            
            if not validation_results['passed']:
                self.logger.warning(f"Data validation failed with quality score: {validation_results['data_quality_score']:.2f}")
            
            # Step 2: Run category-specific analyses in parallel
            self.logger.info("Step 2: Running category-specific analyses")
            category_results = await self._run_category_analyses(conversations, start_date, end_date, options)
            
            # Step 3: Run specialized analyses
            self.logger.info("Step 3: Running specialized analyses")
            specialized_results = await self._run_specialized_analyses(conversations, start_date, end_date, options)
            
            # Step 4: Synthesize results
            self.logger.info("Step 4: Synthesizing results")
            synthesis_results = await self.synthesis_engine.synthesize_category_results(
                category_results, start_date, end_date, options
            )
            
            # Step 5: Generate comprehensive report
            self.logger.info("Step 5: Generating comprehensive report")
            comprehensive_report = await self._generate_comprehensive_report(
                conversations, category_results, specialized_results, synthesis_results, start_date, end_date, options
            )
            
            # Step 6: Generate Gamma presentation if requested
            gamma_presentation = None
            if options.get('generate_gamma_presentation', False):
                self.logger.info("Step 6: Generating Gamma presentation")
                gamma_presentation = await self._generate_gamma_presentation(
                    comprehensive_report, start_date, end_date, options
                )
            
            results = {
                'analysis_metadata': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'total_conversations': len(conversations),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'options': options
                },
                'validation': validation_results,
                'conversations': conversations,
                'category_results': category_results,
                'specialized_results': specialized_results,
                'synthesis_results': synthesis_results,
                'comprehensive_report': comprehensive_report,
                'gamma_presentation': gamma_presentation
            }
            
            self.logger.info("Comprehensive analysis completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Comprehensive analysis failed: {e}")
            return {
                'error': f'Analysis failed: {str(e)}',
                'summary': {}
            }

    async def run_category_analysis(
        self,
        category: str,
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run analysis for a specific category.
        
        Args:
            category: Category to analyze
            start_date: Start date for analysis
            end_date: End date for analysis
            options: Analysis options and configuration
            
        Returns:
            Dictionary containing category analysis results
        """
        self.logger.info(f"Running analysis for category: {category}")
        
        if options is None:
            options = {}
        
        try:
            # Fetch and preprocess data
            conversations = await self._fetch_and_preprocess_data(start_date, end_date, options)
            
            if not conversations:
                return {
                    'error': f'No conversations found for category {category}',
                    'summary': {}
                }
            
            # Run category-specific analysis
            if category in self.category_analyzers:
                analyzer = self.category_analyzers[category]
                results = await analyzer.analyze_category(conversations, start_date, end_date, options)
                
                # Add metadata
                results['analysis_metadata'] = {
                    'category': category,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'total_conversations': len(conversations),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'options': options
                }
                
                return results
            else:
                return {
                    'error': f'Unknown category: {category}',
                    'available_categories': list(self.category_analyzers.keys())
                }
                
        except Exception as e:
            self.logger.error(f"Category analysis failed for {category}: {e}")
            return {
                'error': f'Category analysis failed: {str(e)}',
                'summary': {}
            }

    async def run_specialized_analysis(
        self,
        analysis_type: str,
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a specialized analysis (Fin escalations, technical patterns, etc.).
        
        Args:
            analysis_type: Type of specialized analysis
            start_date: Start date for analysis
            end_date: End date for analysis
            options: Analysis options and configuration
            
        Returns:
            Dictionary containing specialized analysis results
        """
        self.logger.info(f"Running specialized analysis: {analysis_type}")
        
        if options is None:
            options = {}
        
        try:
            # Fetch and preprocess data
            conversations = await self._fetch_and_preprocess_data(start_date, end_date, options)
            
            if not conversations:
                return {
                    'error': f'No conversations found for {analysis_type} analysis',
                    'summary': {}
                }
            
            # Run specialized analysis
            if analysis_type == 'fin_escalations':
                results = self.fin_escalation_analyzer.analyze_fin_escalations(conversations)
            elif analysis_type == 'technical_patterns':
                results = self.technical_pattern_detector.detect_technical_patterns(conversations)
            elif analysis_type == 'macro_opportunities':
                results = self.macro_opportunity_finder.find_macro_opportunities(conversations)
            else:
                return {
                    'error': f'Unknown analysis type: {analysis_type}',
                    'available_types': ['fin_escalations', 'technical_patterns', 'macro_opportunities']
                }
            
            # Add metadata
            results['analysis_metadata'] = {
                'analysis_type': analysis_type,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_conversations': len(conversations),
                'analysis_timestamp': datetime.now().isoformat(),
                'options': options
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Specialized analysis failed for {analysis_type}: {e}")
            return {
                'error': f'Specialized analysis failed: {str(e)}',
                'summary': {}
            }
    
    async def run_story_driven_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a story-driven analysis focused on customer experience narratives.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            options: Analysis options and configuration
            
        Returns:
            Dictionary containing story-driven analysis results
        """
        self.logger.info(f"Starting story-driven analysis from {start_date} to {end_date}")
        
        if options is None:
            options = {}
        
        try:
            # Fetch conversations
            conversations = await self._fetch_and_preprocess_data(start_date, end_date, options)
            
            if not conversations:
                return {
                    'error': 'No conversations found for the specified date range',
                    'summary': {}
                }
            
            # Fetch Canny posts if available
            canny_posts = []
            if options.get('include_canny_data', True):
                try:
                    from services.canny_client import CannyClient
                    canny_client = CannyClient()
                    canny_posts = await canny_client.get_posts(
                        start_date=start_date,
                        end_date=end_date,
                        limit=options.get('canny_limit', 100)
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to fetch Canny data: {e}")
                    canny_posts = []
            
            # Run story-driven analysis
            story_results = await self.story_driven_orchestrator.run_story_driven_analysis(
                conversations=conversations,
                canny_posts=canny_posts,
                start_date=start_date,
                end_date=end_date,
                options=options
            )
            
            # Add metadata
            story_results['analysis_metadata'].update({
                'orchestrator_version': 'enhanced_with_story_driven',
                'analysis_type': 'story_driven_customer_experience',
                'total_conversations': len(conversations),
                'total_canny_posts': len(canny_posts)
            })
            
            self.logger.info("Story-driven analysis completed successfully")
            return story_results
            
        except Exception as e:
            self.logger.error(f"Story-driven analysis failed: {e}")
            return {
                'error': f'Story-driven analysis failed: {str(e)}',
                'summary': {}
            }

    async def _fetch_and_preprocess_data(
        self,
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch and preprocess conversation data."""
        try:
            # Fetch conversations
            max_conversations = options.get('max_conversations', 1000)
            conversations = await self.chunked_fetcher.fetch_with_conversation_limit(
                start_date, end_date, max_conversations
            )
            
            if not conversations:
                self.logger.warning("No conversations fetched")
                return []
            
            # Preprocess conversations
            preprocessed_conversations, _ = self.data_preprocessor.preprocess_conversations(
                conversations, options
            )
            
            self.logger.info(f"Fetched and preprocessed {len(preprocessed_conversations)} conversations")
            return preprocessed_conversations
            
        except Exception as e:
            self.logger.error(f"Data fetching and preprocessing failed: {e}")
            raise

    async def _run_category_analyses(
        self,
        conversations: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Run category analyses in parallel."""
        category_results = {}
        
        # Create tasks for parallel execution
        tasks = []
        for category, analyzer in self.category_analyzers.items():
            # Skip preprocessing since conversations are already preprocessed
            analysis_options = {**options, 'skip_preprocessing': True}
            task = asyncio.create_task(
                analyzer.analyze_category(conversations, start_date, end_date, analysis_options)
            )
            tasks.append((category, task))
        
        # Wait for all tasks to complete
        for category, task in tasks:
            try:
                result = await task
                category_results[category] = result
                self.logger.info(f"Category analysis completed for {category}")
            except Exception as e:
                self.logger.error(f"Category analysis failed for {category}: {e}")
                category_results[category] = {
                    'error': f'Analysis failed: {str(e)}',
                    'category': category
                }
        
        return category_results

    async def _run_specialized_analyses(
        self,
        conversations: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Run specialized analyses in parallel."""
        specialized_results = {}
        
        # Create tasks for parallel execution
        tasks = []
        
        # Fin escalation analysis
        if options.get('include_fin_analysis', True):
            task = asyncio.create_task(
                self._run_fin_escalation_analysis(conversations)
            )
            tasks.append(('fin_escalations', task))
        
        # Technical pattern analysis
        if options.get('include_technical_analysis', True):
            task = asyncio.create_task(
                self._run_technical_pattern_analysis(conversations)
            )
            tasks.append(('technical_patterns', task))
        
        # Macro opportunity analysis
        if options.get('include_macro_analysis', True):
            task = asyncio.create_task(
                self._run_macro_opportunity_analysis(conversations)
            )
            tasks.append(('macro_opportunities', task))
        
        # Wait for all tasks to complete
        for analysis_type, task in tasks:
            try:
                result = await task
                specialized_results[analysis_type] = result
                self.logger.info(f"Specialized analysis completed for {analysis_type}")
            except Exception as e:
                self.logger.error(f"Specialized analysis failed for {analysis_type}: {e}")
                specialized_results[analysis_type] = {
                    'error': f'Analysis failed: {str(e)}',
                    'analysis_type': analysis_type
                }
        
        return specialized_results

    async def _run_fin_escalation_analysis(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run Fin escalation analysis."""
        try:
            return self.fin_escalation_analyzer.analyze_fin_escalations(conversations)
        except Exception as e:
            self.logger.error(f"Fin escalation analysis failed: {e}")
            return {'error': f'Fin escalation analysis failed: {str(e)}'}

    async def _run_technical_pattern_analysis(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run technical pattern analysis."""
        try:
            return self.technical_pattern_detector.detect_technical_patterns(conversations)
        except Exception as e:
            self.logger.error(f"Technical pattern analysis failed: {e}")
            return {'error': f'Technical pattern analysis failed: {str(e)}'}

    async def _run_macro_opportunity_analysis(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run macro opportunity analysis."""
        try:
            return self.macro_opportunity_finder.find_macro_opportunities(conversations)
        except Exception as e:
            self.logger.error(f"Macro opportunity analysis failed: {e}")
            return {'error': f'Macro opportunity analysis failed: {str(e)}'}

    async def _generate_comprehensive_report(
        self,
        conversations: List[Dict[str, Any]],
        category_results: Dict[str, Dict[str, Any]],
        specialized_results: Dict[str, Dict[str, Any]],
        synthesis_results: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a comprehensive report combining all analysis results."""
        report = {
            'conversations': conversations,  # Include conversations for Gamma
            'category_results': category_results,  # Include category results for Gamma
            'executive_summary': synthesis_results.get('executive_summary', {}),
            'key_findings': self._extract_key_findings(category_results, specialized_results, synthesis_results),
            'category_insights': self._extract_category_insights(category_results),
            'specialized_insights': self._extract_specialized_insights(specialized_results),
            'cross_category_insights': synthesis_results.get('cross_category_patterns', {}),
            'recommendations': synthesis_results.get('actionable_insights', []),
            'priority_actions': synthesis_results.get('priority_areas', {}),
            'metrics_summary': self._generate_metrics_summary(category_results, specialized_results),
            'data_quality_assessment': self._assess_data_quality(conversations),
            'analysis_limitations': self._identify_analysis_limitations(conversations, options)
        }
        
        return report

    async def _generate_gamma_presentation(
        self,
        comprehensive_report: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a Gamma presentation from the comprehensive report."""
        try:
            # Get Gamma options
            style = options.get('gamma_style', 'executive')
            export_format = options.get('gamma_export')
            export_docs = options.get('export_docs', False)
            
            # Prepare analysis results for Gamma generation
            analysis_results = {
                'conversations': comprehensive_report.get('conversations', []),
                'category_results': comprehensive_report.get('category_results', {}),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'synthesis_results': comprehensive_report.get('synthesis_results', {}),
                'specialized_results': comprehensive_report.get('specialized_results', {})
            }
            
            # Generate Gamma presentation
            gamma_result = await self.gamma_generator.generate_from_analysis(
                analysis_results=analysis_results,
                style=style,
                export_format=export_format
            )
            
            # Generate Google Docs export if requested
            if export_docs:
                from services.google_docs_exporter import GoogleDocsExporter
                from pathlib import Path
                
                docs_exporter = GoogleDocsExporter()
                output_dir = Path(options.get('output_directory', 'outputs'))
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                docs_filename = f"comprehensive_analysis_{style}_{timestamp}.md"
                docs_path = output_dir / docs_filename
                
                docs_exporter.export_to_markdown(
                    analysis_results=analysis_results,
                    output_path=docs_path,
                    style=style
                )
                
                gamma_result['google_docs_export'] = str(docs_path)
            
            return gamma_result
            
        except Exception as e:
            self.logger.error(f"Gamma presentation generation failed: {e}", exc_info=True)
            return {'error': f'Gamma presentation generation failed: {str(e)}'}

    def _extract_key_findings(
        self,
        category_results: Dict[str, Dict[str, Any]],
        specialized_results: Dict[str, Dict[str, Any]],
        synthesis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract key findings from all analysis results."""
        findings = []
        
        # Extract findings from category results
        for category, results in category_results.items():
            if 'error' not in results:
                data_summary = results.get('data_summary', {})
                analysis_results = results.get('analysis_results', {})
                
                # Volume findings
                volume = data_summary.get('filtered_conversations', 0)
                if volume > 0:
                    findings.append({
                        'type': 'volume',
                        'category': category,
                        'finding': f"{category} category has {volume} conversations",
                        'priority': 'high' if volume > 100 else 'medium'
                    })
                
                # Escalation findings
                escalation_rate = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
                if escalation_rate > 30:
                    findings.append({
                        'type': 'escalation',
                        'category': category,
                        'finding': f"{category} category has high escalation rate: {escalation_rate:.1f}%",
                        'priority': 'high'
                    })
        
        # Extract findings from specialized results
        for analysis_type, results in specialized_results.items():
            if 'error' not in results:
                if analysis_type == 'fin_escalations':
                    escalation_rate = results.get('escalation_analysis', {}).get('escalation_rate', 0)
                    if escalation_rate > 0:
                        findings.append({
                            'type': 'fin_escalation',
                            'category': 'fin',
                            'finding': f"Fin escalation rate: {escalation_rate:.1f}%",
                            'priority': 'high' if escalation_rate > 20 else 'medium'
                        })
        
        return findings

    def _extract_category_insights(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights from category analysis results."""
        insights = {}
        
        for category, results in category_results.items():
            if 'error' not in results:
                insights[category] = {
                    'summary': results.get('data_summary', {}),
                    'analysis': results.get('analysis_results', {}),
                    'ai_insights': results.get('ai_insights', ''),
                    'key_metrics': self._extract_category_metrics(results)
                }
        
        return insights

    def _extract_specialized_insights(self, specialized_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights from specialized analysis results."""
        insights = {}
        
        for analysis_type, results in specialized_results.items():
            if 'error' not in results:
                insights[analysis_type] = {
                    'summary': results.get('summary', {}),
                    'analysis': results,
                    'key_metrics': self._extract_specialized_metrics(results)
                }
        
        return insights

    def _extract_category_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from category analysis results."""
        metrics = {}
        
        data_summary = results.get('data_summary', {})
        analysis_results = results.get('analysis_results', {})
        
        metrics['conversation_count'] = data_summary.get('filtered_conversations', 0)
        metrics['escalation_rate'] = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
        metrics['success_rate'] = analysis_results.get('success_analysis', {}).get('success_rate', 0)
        metrics['failure_rate'] = analysis_results.get('failure_analysis', {}).get('failure_rate', 0)
        
        return metrics

    def _extract_specialized_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from specialized analysis results."""
        metrics = {}
        
        if 'escalation_analysis' in results:
            metrics['escalation_rate'] = results['escalation_analysis'].get('escalation_rate', 0)
            metrics['success_rate'] = results['escalation_analysis'].get('success_rate', 0)
            metrics['failure_rate'] = results['escalation_analysis'].get('failure_rate', 0)
        
        if 'technical_patterns' in results:
            metrics['pattern_count'] = len(results['technical_patterns'])
            metrics['complexity_score'] = results.get('complexity_score', 0)
        
        if 'macro_opportunities' in results:
            metrics['opportunity_count'] = len(results.get('macro_opportunities', []))
            metrics['potential_savings'] = results.get('potential_savings', 0)
        
        return metrics

    def _generate_metrics_summary(
        self,
        category_results: Dict[str, Dict[str, Any]],
        specialized_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a summary of all metrics."""
        summary = {
            'total_conversations': 0,
            'category_metrics': {},
            'specialized_metrics': {},
            'overall_escalation_rate': 0,
            'overall_success_rate': 0
        }
        
        # Aggregate category metrics
        total_conversations = 0
        total_escalations = 0
        total_successes = 0
        
        for category, results in category_results.items():
            if 'error' not in results:
                metrics = self._extract_category_metrics(results)
                summary['category_metrics'][category] = metrics
                
                total_conversations += metrics.get('conversation_count', 0)
                total_escalations += metrics.get('escalation_rate', 0) * metrics.get('conversation_count', 0) / 100
                total_successes += metrics.get('success_rate', 0) * metrics.get('conversation_count', 0) / 100
        
        # Aggregate specialized metrics
        for analysis_type, results in specialized_results.items():
            if 'error' not in results:
                metrics = self._extract_specialized_metrics(results)
                summary['specialized_metrics'][analysis_type] = metrics
        
        # Calculate overall rates
        summary['total_conversations'] = total_conversations
        if total_conversations > 0:
            summary['overall_escalation_rate'] = (total_escalations / total_conversations) * 100
            summary['overall_success_rate'] = (total_successes / total_conversations) * 100
        
        return summary

    def _assess_data_quality(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the quality of the conversation data."""
        if not conversations:
            return {'quality_score': 0, 'issues': ['No conversations available']}
        
        issues = []
        quality_score = 100
        
        # Check for missing data
        missing_data_count = 0
        for conv in conversations:
            if not conv.get('id'):
                missing_data_count += 1
            if not conv.get('conversation_parts'):
                missing_data_count += 1
        
        if missing_data_count > 0:
            missing_percentage = (missing_data_count / len(conversations)) * 100
            issues.append(f"{missing_percentage:.1f}% of conversations have missing data")
            quality_score -= missing_percentage
        
        # Check for empty conversations
        empty_conversations = 0
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            if len(text.strip()) < 10:
                empty_conversations += 1
        
        if empty_conversations > 0:
            empty_percentage = (empty_conversations / len(conversations)) * 100
            issues.append(f"{empty_percentage:.1f}% of conversations are empty or very short")
            quality_score -= empty_percentage
        
        return {
            'quality_score': max(0, quality_score),
            'issues': issues,
            'total_conversations': len(conversations),
            'missing_data_count': missing_data_count,
            'empty_conversations': empty_conversations
        }

    def _identify_analysis_limitations(
        self,
        conversations: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> List[str]:
        """Identify limitations of the current analysis."""
        limitations = []
        
        # Data limitations
        if len(conversations) < 100:
            limitations.append("Limited data sample may affect statistical significance")
        
        # Time range limitations
        if options.get('max_conversations', 1000) < len(conversations):
            limitations.append("Analysis limited by maximum conversation count")
        
        # Analysis limitations
        limitations.append("Analysis based on text patterns and may miss context")
        limitations.append("Sentiment analysis is simplified and may not capture nuances")
        limitations.append("Escalation detection relies on keyword matching")
        
        return limitations

    def _extract_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """Extract text content from a conversation."""
        text_parts = []
        
        # Extract from conversation parts
        conversation_parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        for part in conversation_parts:
            if part.get('body'):
                text_parts.append(part['body'])
        
        # Extract from source
        source = conversation.get('source', {})
        if source.get('body'):
            text_parts.append(source['body'])
        
        return ' '.join(text_parts)

    async def _validate_data_completeness(
        self,
        conversations: List[Dict],
        max_conversations: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Validate data completeness and quality."""
        
        validation_results = {
            'passed': True,
            'warnings': [],
            'completeness_ratio': 0.0,
            'category_distribution': {},
            'data_quality_score': 0.0
        }
        
        # Check 1: Data completeness
        actual_count = len(conversations)
        completeness_ratio = actual_count / max_conversations if max_conversations > 0 else 0
        validation_results['completeness_ratio'] = completeness_ratio
        
        if completeness_ratio < 0.8:
            validation_results['warnings'].append(
                f"Only retrieved {actual_count}/{max_conversations} conversations ({completeness_ratio:.1%})"
            )
            validation_results['passed'] = False
        
        # Check 2: Category distribution
        category_counts = {}
        for conv in conversations:
            tags = conv.get('tags', {}).get('tags', [])
            for tag in tags:
                tag_name = tag.get('name', '')
                category_counts[tag_name] = category_counts.get(tag_name, 0) + 1
        
        if category_counts:
            max_category_pct = max(category_counts.values()) / actual_count
            if max_category_pct > 0.8:
                validation_results['warnings'].append(
                    f"Single category dominates dataset ({max_category_pct:.1%})"
                )
        
        validation_results['category_distribution'] = category_counts
        
        # Check 3: Date range coverage
        if conversations:
            dates = []
            for c in conversations:
                if c.get('created_at'):
                    try:
                        # Handle different date formats
                        date_str = c['created_at'].replace('Z', '+00:00')
                        dates.append(datetime.fromisoformat(date_str))
                    except (ValueError, TypeError):
                        continue
            
            if dates:
                date_range_days = (max(dates) - min(dates)).days
                expected_days = (end_date - start_date).days
                
                if date_range_days < expected_days * 0.5:
                    validation_results['warnings'].append(
                        f"Date range coverage only {date_range_days}/{expected_days} days"
                    )
        
        # Calculate quality score
        quality_factors = [
            completeness_ratio >= 0.8,
            len(validation_results['warnings']) == 0,
            len(category_counts) >= 2  # Reduced from 3 to 2 for smaller datasets
        ]
        validation_results['data_quality_score'] = sum(quality_factors) / len(quality_factors)
        
        return validation_results
