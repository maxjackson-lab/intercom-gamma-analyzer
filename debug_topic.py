
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.getcwd())

from src.agents.topic_detection_agent import TopicDetectionAgent

def debug_normalization():
    logging.basicConfig(level=logging.INFO)
    agent = TopicDetectionAgent()
    
    test_str = "How do I invite teammates?"
    print(f"\nTesting: '{test_str}'")
    result = agent._normalize_llm_topic(test_str)
    print(f"Result: '{result}'")
    
    test_str_2 = "Technical question about API limits"
    print(f"\nTesting: '{test_str_2}'")
    result_2 = agent._normalize_llm_topic(test_str_2)
    print(f"Result: '{result_2}'")

if __name__ == "__main__":
    debug_normalization()




