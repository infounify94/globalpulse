import abc
import os
import json
import requests
from typing import Dict, Any

class LLMProvider(abc.ABC):
    """
    Abstract interface for LLM calls so we can swap between Gemini, Ollama, Claude, etc.
    """
    @abc.abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Sends the prompts to the LLM and guarantees a JSON response parsed into a dict.
        """
        pass

class GeminiProvider(LLMProvider):
    """
    LLM provider using Google's Gemini REST API (bypassing google-generativeai SDK).
    """
    def __init__(self, api_key=None, model_name="gemini-3.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self._available = bool(self.api_key)
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        if not self._available:
            print("Warning: GEMINI_API_KEY not set. Please provide a key to use Gemini.")

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self._available:
            raise ValueError("Gemini API key is required but not provided.")
            
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        import time
        response = None
        for attempt in range(3):
            response = requests.post(self.url, json=payload, headers={'Content-Type': 'application/json'})
            if response.status_code in [503, 429]:
                print(f"Gemini API busy (Status {response.status_code}). Retrying in 2 seconds...")
                time.sleep(2)
                continue
            break
            
        if response is not None:
            response.raise_for_status()
            data = response.json()
        else:
            return {}
        try:
            if 'candidates' not in data:
                print(f"Gemini Error Response: {data}")
                return {}
                
            text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean markdown code blocks if the model wrapped the JSON
            if text.strip().startswith("```"):
                lines = text.strip().split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = '\n'.join(lines)
                
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Failed to extract/decode JSON from Gemini response: {e}")
            return {}

class OllamaProvider(LLMProvider):
    """
    Local, open-source LLM provider via Ollama.
    Assumes Ollama is running locally at http://localhost:11434
    """
    def __init__(self, model_name="llama3.2"):
        self.model_name = model_name
        self.url = "http://localhost:11434/api/generate"

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}\n\nRespond strictly with valid JSON."
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            response = requests.post(self.url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            raw_text = data.get('response', '{}')
            
            # Clean markdown code blocks if the model wrapped the JSON
            if raw_text.strip().startswith("```"):
                lines = raw_text.strip().split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = '\n'.join(lines)
            
            print(f"DEBUG Ollama Raw: {raw_text}")
            return json.loads(raw_text)
        except requests.exceptions.RequestException as e:
            print(f"Ollama connection failed (Is Ollama running?): {e}")
            return {}
        except json.JSONDecodeError:
            print("Failed to decode JSON from Ollama.")
            return {}
