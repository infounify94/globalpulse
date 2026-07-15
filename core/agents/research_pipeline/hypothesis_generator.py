import os
import sys
import json
import logging
from typing import List, Dict, Any

# Ensure python can find the core module
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.research_pipeline.llm_provider import LLMProvider, GeminiProvider

class HypothesisGenerator:
    """
    The autonomous Research Agent.
    Reads ancient texts (or science papers) and generates mathematically testable hypotheses.
    """
    def __init__(self, llm_provider: LLMProvider = None, corpus_dir="data/datasets/wisdomlib"):
        self.llm = llm_provider or GeminiProvider()
        self.corpus_dir = os.path.join(BASE_DIR, corpus_dir)
        
        self.system_prompt = """
        You are an elite scientific Research Agent. Your job is to extract falsifiable hypotheses from ancient texts.
        You will be provided with a fragment of text. 
        Your task is to identify if the text suggests any correlation between a phenomenon (e.g. planetary alignment) and an outcome (e.g. victory, strength, affliction).
        
        You MUST output your response strictly as a JSON object matching this schema:
        {
            "hypothesis_name": "Short PascalCase name",
            "description": "What the text claims, and how it translates to a feature.",
            "python_logic": "def extract(doc):\n    return {'feature_name': 1}",
            "source_text_reference": "Snippet of the text that justifies this.",
            "confidence_score": float (0.0 to 1.0)
        }
        """

    def _load_corpus(self, text_id: str) -> List[Dict]:
        path = os.path.join(self.corpus_dir, f"{text_id}_corpus.jsonl")
        docs = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        docs.append(json.loads(line))
        return docs

    def generate_from_corpus(self, text_id: str) -> List[Dict[str, Any]]:
        """
        Reads a corpus and asks the LLM to generate hypotheses.
        """
        docs = self._load_corpus(text_id)
        if not docs:
            print(f"No documents found for {text_id} in {self.corpus_dir}")
            return []
            
        hypotheses = []
        for doc in docs:
            content = doc.get("content", "")
            if not content:
                continue
                
            print(f"Analyzing {doc.get('chapter_title', 'Unknown Chapter')}...")
            user_prompt = f"Extract a testable feature hypothesis from the following text:\n\n{content}"
            
            result = self.llm.generate_json(self.system_prompt, user_prompt)
            if result:
                # Attach metadata
                result['source_text_id'] = doc.get('text_id')
                result['source_url'] = doc.get('url')
                hypotheses.append(result)
                
        return hypotheses

if __name__ == "__main__":
    generator = HypothesisGenerator()
    # Test on the mocked BPHS corpus we just generated
    print("Testing HypothesisGenerator on BPHS corpus...")
    hyps = generator.generate_from_corpus("bphs")
    for h in hyps:
        print(json.dumps(h, indent=2))
