"""
Billing Analyzer for Intercom Analysis Tool.
Specialized analyzer for billing-related conversations including refunds, invoices, credits, and discounts.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

from src.analyzers.base_category_analyzer import BaseCategoryAnalyzer, AnalysisError
from src.config.prompts import PromptTemplates
from src.utils.time_utils import to_utc_datetime, ensure_date, calculate_time_delta_seconds

logger = logging.getLogger(__name__)


class BillingAnalyzer(BaseCategoryAnalyzer):
    """
    Specialized analyzer for billing and financial conversations.
    
    Focuses on:
    - Refund requests and processing
    - Invoice and payment issues
    - Subscription management
    - Credit and discount requests
    - Billing disputes and chargebacks
    """
    
    def __init__(self, **kwargs):
        """Initialize billing analyzer."""
        super().__init__(category_name="Billing", **kwargs)
        
        # Billing-specific patterns
        self.refund_patterns = [
            r'refund', r'money back', r'cancel.*subscription', r'return.*payment',
            r'reimburse', r'reverse.*charge', r'chargeback', r'dispute.*charge'
        ]
        
        self.invoice_patterns = [
            r'invoice', r'bill', r'receipt', r'payment.*confirmation',
            r'charge.*card', r'billing.*statement', r'payment.*history'
        ]
        
        self.subscription_patterns = [
            r'subscription', r'plan', r'upgrade', r'downgrade', r'renewal',
            r'cancel.*plan', r'change.*plan', r'billing.*cycle'
        ]
        
        self.credit_patterns = [
            r'credit', r'discount', r'promo.*code', r'coupon', r'special.*offer',
            r'free.*trial', r'extend.*trial', r'additional.*time'
        ]
        
        # Billing keywords for classification
        self.billing_keywords = {
            'refund': ['refund', 'money back', 'cancel', 'return', 'reimburse', 'chargeback'],
            'invoice': ['invoice', 'bill', 'receipt', 'payment', 'charge', 'billing'],
            'subscription': ['subscription', 'plan', 'upgrade', 'downgrade', 'renewal'],
            'credit': ['credit', 'discount', 'promo', 'coupon', 'offer', 'trial'],
            'dispute': ['dispute', 'fraud', 'unauthorized', 'chargeback', 'contest']
        }
        
        self.logger.info("Initialized BillingAnalyzer with specialized billing patterns")
    
    async def _perform_category_analysis(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform billing-specific analysis.
        
        Args:
            conversations: Filtered billing conversations
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            Billing-specific analysis results
        """
        self.logger.info(f"Performing billing analysis on {len(conversations)} conversations")
        
        try:
            # Classify conversations by billing type
            classified_conversations = self._classify_billing_conversations(conversations)
            
            # Analyze refund patterns
            refund_analysis = self._analyze_refund_patterns(classified_conversations['refund'])
            
            # Analyze invoice issues
            invoice_analysis = self._analyze_invoice_issues(classified_conversations['invoice'])
            
            # Analyze subscription management
            subscription_analysis = self._analyze_subscription_management(classified_conversations['subscription'])
            
            # Analyze credit and discount requests
            credit_analysis = self._analyze_credit_requests(classified_conversations['credit'])
            
            # Analyze billing disputes
            dispute_analysis = self._analyze_billing_disputes(classified_conversations['dispute'])
            
            # Calculate billing metrics
            billing_metrics = self._calculate_billing_metrics(conversations, classified_conversations)
            
            # Identify billing trends
            billing_trends = self._identify_billing_trends(conversations, start_date, end_date)
            
            # Find common billing issues
            common_issues = self._identify_common_billing_issues(conversations)
            
            # Analyze customer satisfaction with billing
            billing_satisfaction = self._analyze_billing_satisfaction(conversations)
            
            return {
                "analysis_type": "billing_analysis",
                "conversation_count": len(conversations),
                "classified_conversations": {
                    category: len(convs) for category, convs in classified_conversations.items()
                },
                "refund_analysis": refund_analysis,
                "invoice_analysis": invoice_analysis,
                "subscription_analysis": subscription_analysis,
                "credit_analysis": credit_analysis,
                "dispute_analysis": dispute_analysis,
                "billing_metrics": billing_metrics,
                "billing_trends": billing_trends,
                "common_issues": common_issues,
                "billing_satisfaction": billing_satisfaction
            }
            
        except Exception as e:
            self.logger.error(f"Billing analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to perform billing analysis: {e}") from e
    
    def _classify_billing_conversations(self, conversations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify conversations by billing type."""
        classified = {
            'refund': [],
            'invoice': [],
            'subscription': [],
            'credit': [],
            'dispute': [],
            'other': []
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            classified_into = False
            
            # Check each billing type
            for billing_type, keywords in self.billing_keywords.items():
                if any(keyword in text for keyword in keywords):
                    classified[billing_type].append(conv)
                    conv['billing_type'] = billing_type
                    classified_into = True
                    break
            
            if not classified_into:
                classified['other'].append(conv)
                conv['billing_type'] = 'other'
        
        self.logger.info(f"Classified conversations: {[(k, len(v)) for k, v in classified.items()]}")
        return classified
    
    def _analyze_refund_patterns(self, refund_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze refund request patterns."""
        if not refund_conversations:
            return {"total_refunds": 0, "refund_reasons": {}, "refund_trends": {}}
        
        refund_reasons = Counter()
        refund_amounts = []
        refund_resolution_times = []
        
        for conv in refund_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify refund reasons
            if 'too expensive' in text or 'expensive' in text:
                refund_reasons['Too Expensive'] += 1
            elif 'not working' in text or 'broken' in text:
                refund_reasons['Product Not Working'] += 1
            elif 'not needed' in text or 'no longer need' in text:
                refund_reasons['No Longer Needed'] += 1
            elif 'duplicate' in text or 'double charge' in text:
                refund_reasons['Duplicate Charge'] += 1
            elif 'trial' in text:
                refund_reasons['Trial Period'] += 1
            else:
                refund_reasons['Other'] += 1
            
            # Extract refund amounts (if mentioned)
            amount_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
            if amount_match:
                try:
                    refund_amounts.append(float(amount_match.group(1)))
                except ValueError:
                    pass
            
            # Calculate resolution time
            resolution_time = self._calculate_resolution_time(conv)
            if resolution_time:
                refund_resolution_times.append(resolution_time)
        
        # Calculate refund statistics
        total_refunds = len(refund_conversations)
        avg_refund_amount = sum(refund_amounts) / len(refund_amounts) if refund_amounts else 0
        avg_resolution_time = sum(refund_resolution_times) / len(refund_resolution_times) if refund_resolution_times else 0
        
        return {
            "total_refunds": total_refunds,
            "refund_reasons": dict(refund_reasons.most_common()),
            "average_refund_amount": avg_refund_amount,
            "average_resolution_time_hours": avg_resolution_time,
            "refund_amounts": refund_amounts,
            "resolution_times": refund_resolution_times
        }
    
    def _analyze_invoice_issues(self, invoice_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze invoice and payment issues."""
        if not invoice_conversations:
            return {"total_invoice_issues": 0, "issue_types": {}, "payment_methods": {}}
        
        issue_types = Counter()
        payment_methods = Counter()
        invoice_amounts = []
        
        for conv in invoice_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify issue types
            if 'not received' in text or 'missing' in text:
                issue_types['Invoice Not Received'] += 1
            elif 'wrong amount' in text or 'incorrect' in text:
                issue_types['Wrong Amount'] += 1
            elif 'payment failed' in text or 'declined' in text:
                issue_types['Payment Failed'] += 1
            elif 'duplicate' in text:
                issue_types['Duplicate Invoice'] += 1
            else:
                issue_types['Other'] += 1
            
            # Identify payment methods
            if 'credit card' in text or 'card' in text:
                payment_methods['Credit Card'] += 1
            elif 'paypal' in text:
                payment_methods['PayPal'] += 1
            elif 'bank' in text or 'wire' in text:
                payment_methods['Bank Transfer'] += 1
            else:
                payment_methods['Other'] += 1
            
            # Extract invoice amounts
            amount_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
            if amount_match:
                try:
                    invoice_amounts.append(float(amount_match.group(1)))
                except ValueError:
                    pass
        
        return {
            "total_invoice_issues": len(invoice_conversations),
            "issue_types": dict(issue_types.most_common()),
            "payment_methods": dict(payment_methods.most_common()),
            "average_invoice_amount": sum(invoice_amounts) / len(invoice_amounts) if invoice_amounts else 0,
            "invoice_amounts": invoice_amounts
        }
    
    def _analyze_subscription_management(self, subscription_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze subscription management issues."""
        if not subscription_conversations:
            return {"total_subscription_issues": 0, "management_actions": {}, "plan_changes": {}}
        
        management_actions = Counter()
        plan_changes = Counter()
        
        for conv in subscription_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify management actions
            if 'upgrade' in text:
                management_actions['Upgrade'] += 1
            elif 'downgrade' in text:
                management_actions['Downgrade'] += 1
            elif 'cancel' in text:
                management_actions['Cancel'] += 1
            elif 'renew' in text:
                management_actions['Renew'] += 1
            elif 'change' in text:
                management_actions['Change Plan'] += 1
            else:
                management_actions['Other'] += 1
            
            # Identify plan types
            if 'basic' in text or 'starter' in text:
                plan_changes['Basic/Starter'] += 1
            elif 'pro' in text or 'professional' in text:
                plan_changes['Pro/Professional'] += 1
            elif 'enterprise' in text or 'business' in text:
                plan_changes['Enterprise/Business'] += 1
            elif 'free' in text or 'trial' in text:
                plan_changes['Free/Trial'] += 1
        
        return {
            "total_subscription_issues": len(subscription_conversations),
            "management_actions": dict(management_actions.most_common()),
            "plan_changes": dict(plan_changes.most_common())
        }
    
    def _analyze_credit_requests(self, credit_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze credit and discount requests."""
        if not credit_conversations:
            return {"total_credit_requests": 0, "credit_types": {}, "discount_codes": {}}
        
        credit_types = Counter()
        discount_codes = []
        credit_amounts = []
        
        for conv in credit_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify credit types
            if 'discount' in text:
                credit_types['Discount'] += 1
            elif 'promo' in text or 'promotion' in text:
                credit_types['Promotion'] += 1
            elif 'coupon' in text:
                credit_types['Coupon'] += 1
            elif 'trial' in text:
                credit_types['Trial Extension'] += 1
            elif 'credit' in text:
                credit_types['Account Credit'] += 1
            else:
                credit_types['Other'] += 1
            
            # Extract discount codes
            code_match = re.search(r'[A-Z0-9]{4,}', text)
            if code_match:
                discount_codes.append(code_match.group())
            
            # Extract credit amounts
            amount_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
            if amount_match:
                try:
                    credit_amounts.append(float(amount_match.group(1)))
                except ValueError:
                    pass
        
        return {
            "total_credit_requests": len(credit_conversations),
            "credit_types": dict(credit_types.most_common()),
            "discount_codes": list(set(discount_codes)),
            "average_credit_amount": sum(credit_amounts) / len(credit_amounts) if credit_amounts else 0,
            "credit_amounts": credit_amounts
        }
    
    def _analyze_billing_disputes(self, dispute_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze billing disputes and chargebacks."""
        if not dispute_conversations:
            return {"total_disputes": 0, "dispute_reasons": {}, "resolution_outcomes": {}}
        
        dispute_reasons = Counter()
        resolution_outcomes = Counter()
        
        for conv in dispute_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify dispute reasons
            if 'fraud' in text or 'unauthorized' in text:
                dispute_reasons['Fraud/Unauthorized'] += 1
            elif 'duplicate' in text:
                dispute_reasons['Duplicate Charge'] += 1
            elif 'not received' in text:
                dispute_reasons['Service Not Received'] += 1
            elif 'cancelled' in text:
                dispute_reasons['Cancelled Service'] += 1
            else:
                dispute_reasons['Other'] += 1
            
            # Identify resolution outcomes
            state = conv.get('state', '').lower()
            if state == 'closed':
                resolution_outcomes['Resolved'] += 1
            elif state == 'open':
                resolution_outcomes['Open'] += 1
            else:
                resolution_outcomes['Other'] += 1
        
        return {
            "total_disputes": len(dispute_conversations),
            "dispute_reasons": dict(dispute_reasons.most_common()),
            "resolution_outcomes": dict(resolution_outcomes.most_common())
        }
    
    def _calculate_billing_metrics(self, conversations: List[Dict[str, Any]], classified: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate overall billing metrics."""
        total_conversations = len(conversations)
        
        # Calculate percentages
        refund_percentage = (len(classified['refund']) / total_conversations * 100) if total_conversations > 0 else 0
        invoice_percentage = (len(classified['invoice']) / total_conversations * 100) if total_conversations > 0 else 0
        subscription_percentage = (len(classified['subscription']) / total_conversations * 100) if total_conversations > 0 else 0
        credit_percentage = (len(classified['credit']) / total_conversations * 100) if total_conversations > 0 else 0
        dispute_percentage = (len(classified['dispute']) / total_conversations * 100) if total_conversations > 0 else 0
        
        # Calculate resolution rates
        resolved_conversations = sum(1 for conv in conversations if conv.get('state', '').lower() == 'closed')
        resolution_rate = (resolved_conversations / total_conversations) if total_conversations > 0 else 0
        
        return {
            "total_billing_conversations": total_conversations,
            "category_distribution": {
                "refund_percentage": refund_percentage,
                "invoice_percentage": invoice_percentage,
                "subscription_percentage": subscription_percentage,
                "credit_percentage": credit_percentage,
                "dispute_percentage": dispute_percentage
            },
            "overall_resolution_rate": resolution_rate,
            "resolved_conversations": resolved_conversations
        }
    
    def _identify_billing_trends(self, conversations: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Identify billing trends over time."""
        # Group conversations by date
        daily_counts = {}
        daily_types = {}
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                # Use helper to handle both datetime and numeric types
                dt = to_utc_datetime(created_at)
                if not dt:
                    continue
                
                date_key = dt.date().isoformat()
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                
                billing_type = conv.get('billing_type', 'other')
                if date_key not in daily_types:
                    daily_types[date_key] = Counter()
                daily_types[date_key][billing_type] += 1
        
        # Calculate trends
        dates = sorted(daily_counts.keys())
        if len(dates) < 2:
            return {"trend": "insufficient_data", "daily_counts": daily_counts}
        
        # Simple trend calculation
        first_half = sum(daily_counts[date] for date in dates[:len(dates)//2])
        second_half = sum(daily_counts[date] for date in dates[len(dates)//2:])
        
        if second_half > first_half * 1.1:
            trend = "increasing"
        elif second_half < first_half * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "daily_counts": daily_counts,
            "daily_types": {date: dict(types) for date, types in daily_types.items()},
            "total_days": len(dates),
            "average_daily": sum(daily_counts.values()) / len(daily_counts) if daily_counts else 0
        }
    
    def _identify_common_billing_issues(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common billing issues and patterns."""
        issue_patterns = Counter()
        issue_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify common issue patterns
            if 'refund' in text and 'too expensive' in text:
                issue_patterns['Refund - Too Expensive'] += 1
                if 'Refund - Too Expensive' not in issue_examples:
                    issue_examples['Refund - Too Expensive'] = text[:200] + "..."
            
            elif 'payment' in text and 'failed' in text:
                issue_patterns['Payment Failed'] += 1
                if 'Payment Failed' not in issue_examples:
                    issue_examples['Payment Failed'] = text[:200] + "..."
            
            elif 'invoice' in text and 'not received' in text:
                issue_patterns['Invoice Not Received'] += 1
                if 'Invoice Not Received' not in issue_examples:
                    issue_examples['Invoice Not Received'] = text[:200] + "..."
            
            elif 'subscription' in text and 'cancel' in text:
                issue_patterns['Subscription Cancellation'] += 1
                if 'Subscription Cancellation' not in issue_examples:
                    issue_examples['Subscription Cancellation'] = text[:200] + "..."
            
            elif 'discount' in text and 'code' in text:
                issue_patterns['Discount Code Issues'] += 1
                if 'Discount Code Issues' not in issue_examples:
                    issue_examples['Discount Code Issues'] = text[:200] + "..."
        
        # Format common issues
        common_issues = []
        for issue, count in issue_patterns.most_common(10):
            common_issues.append({
                "issue": issue,
                "count": count,
                "example": issue_examples.get(issue, "No example available")
            })
        
        return common_issues
    
    def _analyze_billing_satisfaction(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze customer satisfaction with billing interactions."""
        satisfaction_ratings = []
        satisfaction_keywords = {
            'positive': ['satisfied', 'happy', 'great', 'excellent', 'thank you', 'resolved'],
            'negative': ['frustrated', 'angry', 'disappointed', 'unhappy', 'terrible', 'awful'],
            'neutral': ['okay', 'fine', 'acceptable', 'average']
        }
        
        sentiment_counts = Counter()
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Check for explicit satisfaction ratings
            custom_attrs = conv.get('custom_attributes', {})
            rating = custom_attrs.get('satisfaction_rating') or custom_attrs.get('rating')
            if rating:
                try:
                    satisfaction_ratings.append(float(rating))
                except (ValueError, TypeError):
                    pass
            
            # Analyze sentiment from text
            positive_count = sum(1 for keyword in satisfaction_keywords['positive'] if keyword in text)
            negative_count = sum(1 for keyword in satisfaction_keywords['negative'] if keyword in text)
            neutral_count = sum(1 for keyword in satisfaction_keywords['neutral'] if keyword in text)
            
            if positive_count > negative_count and positive_count > neutral_count:
                sentiment_counts['positive'] += 1
            elif negative_count > positive_count and negative_count > neutral_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
        
        return {
            "explicit_ratings": {
                "count": len(satisfaction_ratings),
                "average": sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0
            },
            "sentiment_analysis": dict(sentiment_counts.most_common()),
            "total_analyzed": len(conversations)
        }
    
    def _calculate_resolution_time(self, conv: Dict[str, Any]) -> Optional[float]:
        """Calculate resolution time in hours."""
        created_at = conv.get('created_at')
        closed_at = conv.get('closed_at')
        
        if created_at and closed_at:
            try:
                # Use helper to calculate time delta in seconds
                delta_seconds = calculate_time_delta_seconds(created_at, closed_at)
                if delta_seconds is not None:
                    return delta_seconds / 3600  # Convert to hours
            except Exception as e:
                self.logger.warning(f"Error calculating resolution time: {e}")
                return None
        
        return None
    
    def _get_ai_analysis_prompt(self, data_summary: str) -> str:
        """Get AI analysis prompt for billing analysis."""
        return PromptTemplates.get_custom_analysis_prompt(
            custom_prompt="Analyze billing conversations focusing on refunds, invoices, subscriptions, credits, and billing disputes",
            start_date="",
            end_date="",
            intercom_data=data_summary
        )
