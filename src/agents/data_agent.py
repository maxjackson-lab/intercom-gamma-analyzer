"""
DataAgent: Specialized in data fetching, validation, and preprocessing.

Responsibilities:
- Fetch conversations from Intercom API
- Validate data completeness and quality
- Preprocess and clean conversation data
- Extract metadata (dates, categories, sentiment indicators)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.elt_pipeline import ELTPipeline
from src.services.data_preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)


class DataAgent(BaseAgent):
    """Agent specialized in data collection and validation"""
    
    def __init__(self):
        super().__init__(
            name="DataAgent",
            model="gpt-4o-mini",  # Cost-effective for data validation
            temperature=0.1  # Low temperature for factual accuracy
        )
        self.pipeline = ELTPipeline()
        self.preprocessor = DataPreprocessor()
    
    def get_agent_specific_instructions(self) -> str:
        """Data agent specific instructions"""
        return """
DATA AGENT SPECIFIC RULES:

1. Only use data from Intercom API responses - never invent conversation content
2. Flag any missing or incomplete data with "DATA INCOMPLETE: [description]"
3. Never invent conversation IDs, timestamps, or user information
4. If API returns empty results, state: "No conversations found for specified criteria"
5. Validate all data fields before processing
6. Report data quality score based on completeness

Quality Metrics to Track:
- Total conversations fetched
- Missing fields count
- Invalid timestamps count
- Duplicate conversations count
- Overall data quality score (0-1)
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the data collection task"""
        return f"""
Fetch and validate conversation data from Intercom for the period:
{context.start_date.strftime('%Y-%m-%d')} to {context.end_date.strftime('%Y-%m-%d')}

Ensure all conversations have:
- Valid conversation IDs
- Complete timestamps
- Message content
- User information
- Tags and metadata

Report any data quality issues found.
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format context for prompt"""
        return f"""
Analysis ID: {context.analysis_id}
Analysis Type: {context.analysis_type}
Date Range: {context.start_date} to {context.end_date}
"""
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that we have necessary information to fetch data"""
        if not context.start_date or not context.end_date:
            raise ValueError("Start date and end date are required")
        
        if context.end_date < context.start_date:
            raise ValueError("End date must be after start date")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate that fetched data meets quality standards"""
        if not result.get('conversations'):
            self.logger.warning("No conversations fetched")
            return True  # Empty result is valid, just flag it
        
        conversations = result['conversations']
        
        # Check for required fields
        required_fields = ['id', 'created_at', 'conversation_parts']
        missing_fields = 0
        
        for conv in conversations[:10]:  # Sample first 10
            for field in required_fields:
                if field not in conv:
                    missing_fields += 1
        
        if missing_fields > 0:
            self.logger.warning(f"Missing fields in {missing_fields} conversation samples")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute data collection and validation.
        
        Args:
            context: AgentContext with date range and parameters
            
        Returns:
            AgentResult with fetched and validated conversations
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            self.logger.info(f"DataAgent: Fetching data from {context.start_date} to {context.end_date}")
            
            # Fetch data using ELT pipeline
            stats = await self.pipeline.extract_and_load(
                context.start_date,
                context.end_date
            )
            
            # Get conversations for preprocessing
            conversations = []
            if stats['conversations_count'] > 0:
                # Fetch conversations from storage for preprocessing
                from src.services.duckdb_storage import DuckDBStorage
                storage = DuckDBStorage()
                
                conversations = storage.get_conversations_by_date_range(
                    context.start_date,
                    context.end_date
                )
            
            # Prepare result
            result_data = {
                'conversations': conversations,
                'stats': stats,
                'data_quality_score': self._calculate_quality_score(conversations),
                'missing_fields': self._find_missing_fields(conversations),
                'date_range': {
                    'start': context.start_date.isoformat(),
                    'end': context.end_date.isoformat()
                }
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=self._identify_limitations(result_data),
                sources=["Intercom API", "DuckDB Storage"],
                execution_time=execution_time,
                token_count=0  # DataAgent doesn't use LLM
            )
            
            self.logger.info(f"DataAgent: Completed in {execution_time:.2f}s, "
                           f"fetched {len(conversations)} conversations, "
                           f"confidence: {confidence:.2f}")
            
            return agent_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"DataAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=["Data fetch failed"],
                sources=[],
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _calculate_quality_score(self, conversations: List[Dict]) -> float:
        """Calculate data quality score (0-1)"""
        if not conversations:
            return 0.0
        
        required_fields = ['id', 'created_at', 'conversation_parts']
        total_score = 0.0
        
        for conv in conversations:
            field_score = sum(1 for field in required_fields if field in conv and conv[field])
            total_score += field_score / len(required_fields)
        
        return total_score / len(conversations) if conversations else 0.0
    
    def _find_missing_fields(self, conversations: List[Dict]) -> List[str]:
        """Identify commonly missing fields"""
        if not conversations:
            return []
        
        required_fields = ['id', 'created_at', 'conversation_parts', 'tags', 'user']
        missing = set()
        
        for conv in conversations[:50]:  # Sample first 50
            for field in required_fields:
                if field not in conv or not conv[field]:
                    missing.add(field)
        
        return list(missing)
    
    def _identify_limitations(self, result: Dict[str, Any]) -> List[str]:
        """Identify limitations in the fetched data"""
        limitations = []
        
        if result['data_quality_score'] < 0.9:
            limitations.append(f"Data quality score: {result['data_quality_score']:.2f} - some fields missing")
        
        if result['missing_fields']:
            limitations.append(f"Missing fields: {', '.join(result['missing_fields'])}")
        
        if result['stats']['conversations_count'] == 0:
            limitations.append("No conversations found for specified date range")
        
        return limitations

