"""
Voice of Customer analyzer for monthly executive reports.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.analyzers.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisRequest, VoiceOfCustomerResults
from src.config.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class VoiceAnalyzer(BaseAnalyzer):
    """Analyzer for Voice of Customer monthly executive reports."""
    
    async def analyze(self, request: AnalysisRequest) -> VoiceOfCustomerResults:
        """Perform Voice of Customer analysis."""
        start_time = datetime.now()
        self.logger.info(f"Starting Voice of Customer analysis for {request.month}/{request.year}")
        
        # Validate request
        if not request.month or not request.year:
            raise ValueError("Month and year are required for Voice of Customer analysis")
        
        # Fetch conversations
        conversations = await self.fetch_conversations(request)
        self.logger.info(f"Fetched {len(conversations)} conversations")
        
        if len(conversations) < 10:
            self.logger.warning(f"Low conversation count: {len(conversations)}. Analysis may be less reliable.")
        
        # Calculate metrics
        metrics = await self.calculate_metrics(conversations, request)
        
        # Generate AI insights
        ai_insights = await self.generate_ai_insights(conversations, metrics, request)
        
        # Extract customer quotes
        customer_quotes = await self.extract_customer_quotes(conversations, "positive")
        
        # Generate month-over-month comparison
        month_over_month = await self._generate_month_over_month_comparison(
            request.month, request.year, metrics
        )
        
        # Generate tier1 analysis
        tier1_analysis = await self._generate_tier1_analysis(
            metrics, request.tier1_countries or []
        )
        
        # Generate executive summary
        executive_summary = await self._generate_executive_summary(metrics, ai_insights)
        
        # Calculate analysis duration
        analysis_duration = self._calculate_analysis_duration(start_time)
        
        # Create results
        results = VoiceOfCustomerResults(
            request=request,
            analysis_date=datetime.now(),
            executive_summary=executive_summary,
            tier1_analysis=tier1_analysis,
            month_over_month_comparison=month_over_month,
            top_contact_reasons_analysis=ai_insights.get("top_contact_reasons_analysis", ""),
            billing_analysis=ai_insights.get("billing_analysis", ""),
            product_questions_analysis=ai_insights.get("product_questions_analysis", ""),
            account_questions_analysis=ai_insights.get("account_questions_analysis", ""),
            friction_points_analysis=ai_insights.get("friction_points_analysis", ""),
            customer_quotes=customer_quotes,
            total_conversations=metrics["volume"].total_conversations,
            ai_resolution_rate=metrics["volume"].ai_resolution_rate,
            median_response_time=self._format_time(metrics["efficiency"].median_first_response_seconds),
            median_handling_time=self._format_time(metrics["efficiency"].median_handling_time_seconds),
            median_resolution_time=self._format_time(metrics["efficiency"].median_resolution_time_seconds),
            overall_csat=metrics["satisfaction"].overall_csat or 0.0,
            analysis_duration_seconds=analysis_duration,
            tier1_countries=request.tier1_countries or []
        )
        
        self.logger.info(f"Voice of Customer analysis completed in {analysis_duration:.2f} seconds")
        return results
    
    async def _generate_month_over_month_comparison(
        self, 
        month: int, 
        year: int, 
        current_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate month-over-month comparison."""
        self.logger.info("Generating month-over-month comparison")
        
        # Calculate previous month
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year
        
        try:
            # Fetch previous month's conversations
            prev_start_date = datetime(prev_year, prev_month, 1)
            if prev_month == 12:
                prev_end_date = datetime(prev_year + 1, 1, 1)
            else:
                prev_end_date = datetime(prev_year, prev_month + 1, 1)
            
            prev_conversations = await self.intercom_service.fetch_conversations_by_date_range(
                prev_start_date, prev_end_date
            )
            
            # Calculate previous month's metrics
            prev_metrics = await self.calculate_metrics(prev_conversations, AnalysisRequest(
                mode="voice_of_customer",
                month=prev_month,
                year=prev_year
            ))
            
            # Calculate changes
            conversation_change = self._calculate_percentage_change(
                prev_metrics["volume"].total_conversations,
                current_metrics["volume"].total_conversations
            )
            
            csat_change = self._calculate_percentage_change(
                prev_metrics["satisfaction"].overall_csat,
                current_metrics["satisfaction"].overall_csat
            )
            
            response_time_change = self._calculate_percentage_change(
                prev_metrics["efficiency"].median_first_response_seconds,
                current_metrics["efficiency"].median_first_response_seconds
            )
            
            return {
                "previous_month": f"{prev_month}/{prev_year}",
                "conversation_change": conversation_change,
                "csat_change": csat_change,
                "response_time_change": response_time_change,
                "previous_metrics": {
                    "total_conversations": prev_metrics["volume"].total_conversations,
                    "overall_csat": prev_metrics["satisfaction"].overall_csat,
                    "median_response_time": prev_metrics["efficiency"].median_first_response_seconds
                }
            }
            
        except Exception as e:
            self.logger.warning(f"Could not generate month-over-month comparison: {e}")
            return {
                "previous_month": "N/A",
                "conversation_change": 0,
                "csat_change": 0,
                "response_time_change": 0,
                "error": "Previous month data not available"
            }
    
    async def _generate_tier1_analysis(
        self, 
        metrics: Dict[str, Any], 
        tier1_countries: List[str]
    ) -> Dict[str, Any]:
        """Generate tier1 country analysis."""
        self.logger.info("Generating tier1 country analysis")
        
        tier1_metrics = metrics["geographic"].tier1_metrics
        
        # Calculate tier1 performance
        tier1_total_conversations = sum(
            country_data["conversations"] 
            for country_data in tier1_metrics.values()
        )
        
        tier1_percentage = (
            tier1_total_conversations / metrics["volume"].total_conversations * 100
            if metrics["volume"].total_conversations > 0 else 0
        )
        
        # Top performing tier1 countries
        top_tier1_countries = sorted(
            tier1_metrics.items(),
            key=lambda x: x[1]["conversations"],
            reverse=True
        )[:5]
        
        # Tier1 satisfaction analysis
        tier1_satisfaction = {}
        for country in tier1_countries:
            if country in metrics["satisfaction"].csat_by_country:
                tier1_satisfaction[country] = metrics["satisfaction"].csat_by_country[country]
        
        return {
            "tier1_total_conversations": tier1_total_conversations,
            "tier1_percentage": round(tier1_percentage, 2),
            "top_tier1_countries": [
                {
                    "country": country,
                    "conversations": data["conversations"],
                    "percentage": data["percentage"]
                }
                for country, data in top_tier1_countries
            ],
            "tier1_satisfaction": tier1_satisfaction,
            "tier1_countries_analyzed": len(tier1_countries)
        }
    
    async def _generate_executive_summary(
        self, 
        metrics: Dict[str, Any], 
        ai_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary."""
        self.logger.info("Generating executive summary")
        
        # Key performance indicators
        kpis = {
            "total_conversations": metrics["volume"].total_conversations,
            "ai_resolution_rate": metrics["volume"].ai_resolution_rate,
            "overall_csat": metrics["satisfaction"].overall_csat,
            "median_response_time": metrics["efficiency"].median_first_response_seconds,
            "resolution_rate": metrics["efficiency"].resolution_rate
        }
        
        # Performance assessment
        performance_assessment = self._assess_performance(kpis)
        
        # Key insights
        key_insights = self._extract_key_insights(metrics, ai_insights)
        
        # Recommendations
        recommendations = self._generate_recommendations(metrics, performance_assessment)
        
        return {
            "kpis": kpis,
            "performance_assessment": performance_assessment,
            "key_insights": key_insights,
            "recommendations": recommendations,
            "analysis_confidence": self._calculate_confidence_score([], metrics)
        }
    
    def _assess_performance(self, kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall performance based on KPIs."""
        assessment = {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": [],
            "critical_issues": []
        }
        
        # CSAT assessment
        csat = kpis.get("overall_csat", 0)
        if csat >= 4.5:
            assessment["strengths"].append("Excellent customer satisfaction")
            assessment["overall_score"] += 25
        elif csat >= 4.0:
            assessment["strengths"].append("Good customer satisfaction")
            assessment["overall_score"] += 20
        elif csat >= 3.5:
            assessment["areas_for_improvement"].append("Customer satisfaction needs improvement")
            assessment["overall_score"] += 10
        else:
            assessment["critical_issues"].append("Low customer satisfaction")
            assessment["overall_score"] += 0
        
        # Response time assessment
        response_time = kpis.get("median_response_time", 0)
        if response_time and response_time <= 3600:  # 1 hour
            assessment["strengths"].append("Fast response times")
            assessment["overall_score"] += 25
        elif response_time and response_time <= 7200:  # 2 hours
            assessment["strengths"].append("Good response times")
            assessment["overall_score"] += 20
        elif response_time and response_time <= 14400:  # 4 hours
            assessment["areas_for_improvement"].append("Response times could be faster")
            assessment["overall_score"] += 10
        else:
            assessment["critical_issues"].append("Slow response times")
            assessment["overall_score"] += 0
        
        # AI resolution rate assessment
        ai_rate = kpis.get("ai_resolution_rate", 0)
        if ai_rate >= 70:
            assessment["strengths"].append("High AI resolution rate")
            assessment["overall_score"] += 25
        elif ai_rate >= 50:
            assessment["strengths"].append("Good AI resolution rate")
            assessment["overall_score"] += 20
        elif ai_rate >= 30:
            assessment["areas_for_improvement"].append("AI resolution rate could be higher")
            assessment["overall_score"] += 10
        else:
            assessment["critical_issues"].append("Low AI resolution rate")
            assessment["overall_score"] += 0
        
        # Resolution rate assessment
        resolution_rate = kpis.get("resolution_rate", 0)
        if resolution_rate >= 90:
            assessment["strengths"].append("High resolution rate")
            assessment["overall_score"] += 25
        elif resolution_rate >= 80:
            assessment["strengths"].append("Good resolution rate")
            assessment["overall_score"] += 20
        elif resolution_rate >= 70:
            assessment["areas_for_improvement"].append("Resolution rate could be higher")
            assessment["overall_score"] += 10
        else:
            assessment["critical_issues"].append("Low resolution rate")
            assessment["overall_score"] += 0
        
        return assessment
    
    def _extract_key_insights(self, metrics: Dict[str, Any], ai_insights: Dict[str, Any]) -> List[str]:
        """Extract key insights from metrics and AI analysis."""
        insights = []
        
        # Volume insights
        total_conversations = metrics["volume"].total_conversations
        if total_conversations > 1000:
            insights.append(f"High conversation volume ({total_conversations:,}) indicates strong customer engagement")
        elif total_conversations < 100:
            insights.append(f"Low conversation volume ({total_conversations}) may indicate underutilized support")
        
        # AI resolution insights
        ai_rate = metrics["volume"].ai_resolution_rate
        if ai_rate > 60:
            insights.append(f"Strong AI performance with {ai_rate}% resolution rate")
        elif ai_rate < 30:
            insights.append(f"AI resolution rate of {ai_rate}% has room for improvement")
        
        # Satisfaction insights
        csat = metrics["satisfaction"].overall_csat
        if csat and csat > 4.0:
            insights.append(f"Customer satisfaction at {csat} shows positive customer experience")
        elif csat and csat < 3.5:
            insights.append(f"Customer satisfaction at {csat} needs attention")
        
        # Channel insights
        channel_performance = metrics["channel"].channel_performance
        if channel_performance:
            top_channel = max(channel_performance.items(), key=lambda x: x[1]["volume"])
            insights.append(f"{top_channel[0]} is the primary support channel with {top_channel[1]['volume']} conversations")
        
        return insights
    
    def _generate_recommendations(self, metrics: Dict[str, Any], performance_assessment: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Based on performance assessment
        if performance_assessment["critical_issues"]:
            for issue in performance_assessment["critical_issues"]:
                if "satisfaction" in issue.lower():
                    recommendations.append("Implement immediate customer satisfaction improvement program")
                elif "response" in issue.lower():
                    recommendations.append("Optimize response time processes and agent allocation")
                elif "ai" in issue.lower():
                    recommendations.append("Enhance AI training and expand automated resolution capabilities")
                elif "resolution" in issue.lower():
                    recommendations.append("Review and improve resolution processes and agent training")
        
        # Based on metrics
        if metrics["friction"].escalation_patterns:
            recommendations.append("Address common escalation triggers to reduce friction")
        
        if metrics["topics"].billing_breakdown:
            recommendations.append("Improve billing process clarity and documentation")
        
        if metrics["efficiency"].median_handling_time_seconds and metrics["efficiency"].median_handling_time_seconds > 3600:
            recommendations.append("Optimize agent workflows to reduce handling time")
        
        return recommendations
    
    def _calculate_percentage_change(self, old_value: Optional[float], new_value: Optional[float]) -> float:
        """Calculate percentage change between two values."""
        if not old_value or not new_value or old_value == 0:
            return 0.0
        
        return round(((new_value - old_value) / old_value) * 100, 2)
    
    def _format_time(self, seconds: Optional[int]) -> str:
        """Format time in seconds to human-readable format."""
        if not seconds:
            return "N/A"
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

