"""
CategoryAgent: Specialized in taxonomy-based category classification.

Responsibilities:
- Apply taxonomy classification to conversations
- Drill down into subcategories
- Identify specific issues within categories
- Maintain confidence scores for classifications
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.services.category_filters import CategoryFilters
from src.config.taxonomy import taxonomy_manager
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class CategoryAgent(BaseAgent):
    """Agent specialized in category classification"""
    
    def __init__(self):
        super().__init__(
            name="CategoryAgent",
            model="gpt-4o",  # Needs reasoning for accurate categorization
            temperature=0.3  # Moderate temperature for classification
        )
        self.category_filters = CategoryFilters()
        self.openai_client = OpenAIClient()
    
    def get_agent_specific_instructions(self) -> str:
        """Category agent specific instructions"""
        return """
CATEGORY AGENT SPECIFIC RULES:

1. Only classify using the provided taxonomy categories - NEVER invent new categories
2. State confidence levels: "HIGH/MEDIUM/LOW confidence" for each classification
3. Use "I cannot verify this classification" for uncertain cases
4. Never invent patterns or trends not supported by the conversation data
5. Drill down to specific subcategories when possible (not just top-level)

Classification Requirements:
- Provide both primary category and subcategory
- Include confidence score (0-1) for each classification
- Quote exact conversation text supporting the classification
- Identify specific issues within categories (e.g., "Email change failures" not just "Account issues")
- Flag conversations that don't fit existing taxonomy

Output Format:
{
    "conversation_id": "...",
    "primary_category": "...",
    "subcategory": "...",
    "confidence": 0.95,
    "supporting_quote": "...",
    "specific_issue": "..."
}
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe the category classification task"""
        conversations_count = len(context.conversations) if context.conversations else 0
        return f"""
Classify {conversations_count} conversations using the provided taxonomy.

For EACH conversation:
1. Identify the primary category from the taxonomy
2. Drill down to the most specific subcategory
3. Identify the specific issue (e.g., "Password reset failures" not just "Account issues")
4. Provide confidence score
5. Quote supporting text from the conversation

Taxonomy categories available:
{self._format_taxonomy()}
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format conversations for classification"""
        if not context.conversations:
            return "No conversations provided"
        
        # Sample first 3 conversations for prompt (full processing happens in code)
        sample = context.conversations[:3]
        return f"""
Total conversations to classify: {len(context.conversations)}

Sample conversations (showing first 3):
{json.dumps(sample, indent=2, default=str)}

Process ALL {len(context.conversations)} conversations using this classification approach.
"""
    
    def _format_taxonomy(self) -> str:
        """Format taxonomy for prompt"""
        categories = taxonomy_manager.get_all_categories()
        formatted = []
        
        for cat_name, cat_data in list(categories.items())[:13]:  # All 13 main categories
            subcats = cat_data.get('subcategories', [])
            formatted.append(f"- {cat_name}: {', '.join(subcats[:5])}{'...' if len(subcats) > 5 else ''}")
        
        return '\n'.join(formatted)
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that we have conversations to classify"""
        if not context.conversations:
            raise ValueError("No conversations provided for classification")
        
        if not isinstance(context.conversations, list):
            raise ValueError("Conversations must be a list")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate classification results"""
        if not result.get('classifications'):
            self.logger.warning("No classifications produced")
            return True
        
        classifications = result['classifications']
        
        # Check that all classifications have required fields
        required_fields = ['conversation_id', 'primary_category', 'confidence']
        for classification in classifications[:10]:  # Sample first 10
            for field in required_fields:
                if field not in classification:
                    self.logger.warning(f"Missing field '{field}' in classification")
        
        return True
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute category classification.
        
        Args:
            context: AgentContext with conversations from DataAgent
            
        Returns:
            AgentResult with category classifications
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self.validate_input(context)
            
            conversations = context.conversations
            self.logger.info(f"CategoryAgent: Classifying {len(conversations)} conversations")
            
            # Use CategoryFilters for initial classification
            classifications = []
            category_distribution = {}
            
            for conv in conversations:
                # Use existing category filters
                category = self.category_filters.get_primary_category(conv)
                subcategories = self.category_filters.get_subcategories(conv, category)
                
                # Calculate confidence based on keyword matches
                confidence = self._calculate_classification_confidence(conv, category)
                
                classification = {
                    'conversation_id': conv.get('id', 'unknown'),
                    'primary_category': category,
                    'subcategories': subcategories,
                    'confidence': confidence,
                    'confidence_level': 'HIGH' if confidence > 0.8 else 'MEDIUM' if confidence > 0.6 else 'LOW'
                }
                
                classifications.append(classification)
                
                # Track distribution
                category_distribution[category] = category_distribution.get(category, 0) + 1
            
            # Prepare result
            result_data = {
                'classifications': classifications,
                'category_distribution': category_distribution,
                'total_classified': len(classifications),
                'high_confidence_count': sum(1 for c in classifications if c['confidence'] > 0.8),
                'low_confidence_count': sum(1 for c in classifications if c['confidence'] < 0.6)
            }
            
            # Validate output
            self.validate_output(result_data)
            
            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)
            
            # Identify limitations
            limitations = []
            if result_data['low_confidence_count'] > len(classifications) * 0.2:
                limitations.append(f"{result_data['low_confidence_count']} classifications have low confidence (<0.6)")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Build result
            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=limitations,
                sources=["Taxonomy YAML", "Category keyword matching"],
                execution_time=execution_time,
                token_count=0  # Using rule-based classification, not LLM
            )
            
            self.logger.info(f"CategoryAgent: Completed in {execution_time:.2f}s, "
                           f"classified {len(classifications)} conversations, "
                           f"confidence: {confidence:.2f}")
            
            return agent_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"CategoryAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                limitations=["Category classification failed"],
                sources=[],
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _calculate_classification_confidence(self, conversation: Dict, category: str) -> float:
        """Calculate confidence for a classification based on keyword matches"""
        # Get category keywords from taxonomy
        taxonomy = taxonomy_manager.get_category(category)
        if not taxonomy or 'keywords' not in taxonomy:
            return 0.5  # Medium confidence if no keywords defined
        
        keywords = taxonomy['keywords']
        conv_text = str(conversation).lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword.lower() in conv_text)
        
        if matches >= 3:
            return 0.95  # High confidence
        elif matches >= 2:
            return 0.75  # Medium-high confidence
        elif matches >= 1:
            return 0.6   # Medium confidence
        else:
            return 0.4   # Low confidence

