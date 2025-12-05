
import json
import os
from collections import Counter
import re

def analyze_languages(file_path):
    print(f"Analyzing {file_path}...")
    
    language_counts = Counter()
    non_english_samples = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            conversations = data.get('conversations', [])
            
            for conv in conversations:
                # Get language from browser settings if available
                contacts = conv.get('contacts', {}).get('contacts', [])
                lang = 'unknown'
                if contacts:
                    lang = contacts[0].get('browser_language', 'unknown')
                
                # Normalize simple codes
                if lang and len(lang) >= 2:
                    lang = lang[:2].lower()
                
                language_counts[lang] += 1
                
                # If non-english, capture sample text
                if lang not in ['en', 'unknown'] and lang not in non_english_samples:
                    subject = conv.get('source', {}).get('subject', '')
                    body = conv.get('source', {}).get('body', '')
                    # Clean HTML slightly for readability
                    text = re.sub(r'<[^>]+>', ' ', subject + " " + body)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if len(text) > 20:
                        non_english_samples[lang] = text[:200]
                        
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print("\nLanguage Distribution:")
    for lang, count in language_counts.most_common(15):
        print(f"  {lang}: {count}")
        
    print("\nSample Text from Non-English Languages:")
    for lang, text in non_english_samples.items():
        print(f"  [{lang}]: {text}")

# Find the target file
base_dir = "reference_data/Sample Mode Last Month 1000 tickets copy/"
target_file = None
for f in os.listdir(base_dir):
    if f.endswith('.json') and 'sample_mode' in f:
        target_file = os.path.join(base_dir, f)
        break

if target_file:
    analyze_languages(target_file)
else:
    print("Target file not found")








