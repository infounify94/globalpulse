import os
import json
import logging
from core.agents.research_pipeline.llm_provider import GeminiProvider, OllamaProvider
from core.agents.research_pipeline.hypothesis_generator import HypothesisGenerator
from core.agents.research_pipeline.hypothesis_validator import HypothesisValidator
from core.agents.research_pipeline.auto_feature_generator import AutoFeatureGenerator
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# BPHS Chapter 3 Excerpt (Nature of Planets)
BPHS_TEXT = """
Chapter 3: Planetary Characters and Description.
1-2. O Lord! You have stated the names of the planets. Now please tell me about their characteristics. 
The Sun, Jupiter, and Mars are male. The Moon and Venus are female. Saturn and Mercury are neuter.
3-4. The Sun is malefic. The Moon is benefic. Mars is malefic. Mercury is benefic when associated with benefics, but malefic when associated with malefics. Jupiter and Venus are benefics. Saturn is malefic.
5. If Jupiter is in the same sign as the Sun, it is combust and loses its power.
6. The Moon is strong when waxing. It is weak when waning.
7. Venus and Jupiter are the gurus of demons and gods respectively.
"""

def main():
    # 1. Initialize Components
    print("Initializing Autonomous Research Pipeline...")
    try:
        llm = GeminiProvider()
        # Test connection
        llm.generate_json("Test", "Test")
    except Exception as e:
        print(f"Gemini API failed or unavailable: {e}. Falling back to Ollama...")
        llm = OllamaProvider()
    generator = HypothesisGenerator(llm_provider=llm)
    validator = HypothesisValidator()
    auto_coder = AutoFeatureGenerator()

    # Create a mock corpus from the text
    mock_corpus_dir = "data/datasets/wisdomlib"
    os.makedirs(mock_corpus_dir, exist_ok=True)
    corpus_file = os.path.join(mock_corpus_dir, "bphs_full_corpus.jsonl")
    with open(corpus_file, "w") as f:
        doc = {
            "text_id": "bphs_full",
            "chapter_title": "Chapter 3: Planetary Characters",
            "url": "local_text",
            "content": BPHS_TEXT,
            "source_type": "ancient_text",
            "hypothesis_valid": "pending"
        }
        f.write(json.dumps(doc) + "\n")

    # 2. Generate Hypothesis
    print("\n--- PHASE 1: HYPOTHESIS GENERATION ---")
    # We override the system prompt to explicitly request pandas dataframe usage if we want,
    # or just row-based logic
    generator.corpus_dir = mock_corpus_dir
    generator.system_prompt += (
        "\n\nCRITICAL: You MUST respond with exactly this JSON format. Do not change the keys.\n"
        "{\n"
        "  \"hypothesis_name\": \"is_jupiter_combust\",\n"
        "  \"description\": \"Jupiter is combust when in the same sign as the Sun.\",\n"
        "  \"python_logic\": \"def extract(doc):\\n    return {'is_jupiter_combust': 1 if doc.get('jupiter_sign') == doc.get('sun_sign') else 0}\",\n"
        "  \"confidence_score\": 0.9\n"
        "}\n"
    )
    
    hypotheses = generator.generate_from_corpus("bphs_full")
    if not hypotheses:
        print("No hypotheses generated.")
        return
        
    for idx, hyp in enumerate(hypotheses):
        print(f"\n--- Processing Hypothesis {idx+1}: {hyp.get('hypothesis_name')} ---")
        
        # 3. Validate Hypothesis
        print("Validating...")
        is_valid = validator.validate(hyp)
        if not is_valid:
            print("Hypothesis rejected by Validator. Skipping.")
            continue
            
        print("Hypothesis Approved!")
        
        # 4. Auto-Generate Feature
        print("Writing python logic to disk...")
        module_path = auto_coder.write_feature_module(hyp)
        print(f"Module written to: {module_path}")
        
        # 5. Execute on DataFrame
        print("Executing generated feature on sample data...")
        sample_data = pd.DataFrame([
            {"match_id": 1, "jupiter_sign": 5, "sun_sign": 5}, # Combust
            {"match_id": 2, "jupiter_sign": 2, "sun_sign": 8}  # Not combust
        ])
        
        try:
            result_df = auto_coder.load_and_execute(module_path, sample_data)
            print("\nSUCCESS! New Feature Dataframe:")
            print(result_df)
        except Exception as e:
            print(f"Auto-generated code failed to execute: {e}")

if __name__ == "__main__":
    main()
