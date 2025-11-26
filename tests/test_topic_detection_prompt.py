import pytest
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.config.taxonomy import TaxonomyManager

@pytest.mark.asyncio
async def test_prompt_categories_match_taxonomy():
    """
    Verify that the categories used in the LLM prompt match the taxonomy's Tier 1 categories.
    This ensures the prompt is always up-to-date with the single source of truth.
    """
    agent = TopicDetectionAgent()
    taxonomy = TaxonomyManager()
    
    # Get categories from taxonomy
    # TaxonomyManager.categories keys are the Tier 1 topic names
    taxonomy_categories = set(taxonomy.categories.keys())
    
    # The agent constructs the prompt dynamically using self.topics
    # self.topics is initialized from TaxonomyManager in __init__
    agent_topics = set(agent.topics.keys())
    
    # 1. Verify agent's internal topic list matches taxonomy exactly
    assert agent_topics == taxonomy_categories, \
        f"Agent topics {agent_topics} do not match Taxonomy {taxonomy_categories}"
    
    # 2. Verify the specific logic used for prompt construction
    # In _classify_with_llm_smart:
    # valid_categories = [t for t in self.topics.keys() if t != 'Unknown/unresponsive']
    
    prompt_categories = [t for t in agent.topics.keys() if t != 'Unknown/unresponsive']
    
    # In taxonomy, 'Unknown/unresponsive' might or might not be present depending on yaml
    # But we want to ensure the 'valid_categories' list covers all actual business categories
    expected_business_categories = [t for t in taxonomy.categories.keys() if t != 'Unknown/unresponsive']
    
    assert sorted(prompt_categories) == sorted(expected_business_categories)
    assert len(prompt_categories) == len(expected_business_categories)
    
    # Check for a few known categories to be sure
    known_categories = {'Billing', 'Bug', 'Product Question', 'Account'}
    assert known_categories.issubset(set(prompt_categories))

