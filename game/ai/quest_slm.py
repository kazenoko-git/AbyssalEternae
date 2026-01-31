import json
import requests
from typing import Dict, List, Any, Optional
from aurora_engine.core.logging import get_logger

class QuestSLM:
    """
    A specialized Small Language Model (SLM) wrapper.
    Supports multiple free providers:
    1. Groq (Llama 3 8B) - Recommended for speed and JSON following.
    2. Google Gemini (Flash) - Good context window.
    3. Hugging Face (Phi-3, Gemma, etc.) - widely available free inference.
    """
    
    def __init__(self, api_key: str, provider: str = "groq"):
        self.api_key = api_key
        self.provider = provider.lower()
        self.logger = get_logger()
        
        # Configuration for different providers
        self.configs = {
            "groq": {
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "model": "llama3-8b-8192",
                "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            },
            "gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
                "model": "gemini-1.5-flash",
                "headers": {"Content-Type": "application/json"}
            },
            "huggingface": {
                # We will try a list of models dynamically
                "headers": {"Authorization": f"Bearer {api_key}"}
            }
        }

    def _generate_groq(self, prompt: str) -> Optional[str]:
        """Generate content using Groq API (OpenAI compatible)."""
        config = self.configs["groq"]
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": "You are a quest generator. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"} # Groq supports JSON mode
        }
        
        try:
            response = requests.post(config["url"], json=payload, headers=config["headers"])
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"Groq generation failed: {e}")
            if 'response' in locals() and response.status_code != 200:
                self.logger.error(f"Response: {response.text}")
            return None

    def _generate_gemini(self, prompt: str) -> Optional[str]:
        """Generate content using Google Gemini API."""
        config = self.configs["gemini"]
        # Try a few model variants
        models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
        
        for model in models:
            url = f"{config['base_url']}/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            
            try:
                response = requests.post(url, json=payload, headers=config["headers"])
                if response.status_code == 200:
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                continue
        
        self.logger.error("All Gemini models failed.")
        return None

    def _generate_huggingface(self, prompt: str) -> Optional[str]:
        """Generate content using Hugging Face Inference API with fallback models."""
        config = self.configs["huggingface"]
        
        # List of models to try, starting with smaller/more likely to be free/available
        models_to_try = [
            "microsoft/Phi-3-mini-4k-instruct",
            "google/gemma-1.1-7b-it",
            "HuggingFaceH4/zephyr-7b-beta",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "google/flan-t5-large" # Last resort, might not output good JSON but usually up
        ]

        payload = {
            "inputs": f"<s>[INST] {prompt} [/INST]",
            "parameters": {"max_new_tokens": 2000, "return_full_text": False, "temperature": 0.7}
        }
        
        for model in models_to_try:
            url = f"https://api-inference.huggingface.co/models/{model}"
            try:
                self.logger.debug(f"Trying HF model: {model}")
                response = requests.post(url, json=payload, headers=config["headers"])
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0]["generated_text"]
                    elif isinstance(result, dict) and "generated_text" in result:
                        return result["generated_text"]
                elif response.status_code in [404, 410, 503]:
                    self.logger.warning(f"HF Model {model} unavailable ({response.status_code}).")
                    continue # Try next
                else:
                    self.logger.warning(f"HF Error {model}: {response.status_code}")
                    continue
                    
            except Exception as e:
                self.logger.error(f"HF Exception {model}: {e}")
                continue

        self.logger.error("All Hugging Face models failed.")
        return None

    def generate_quest_flow(self, theme: str, difficulty: int, npc_giver_context: Dict, world_context: Dict) -> Optional[Dict]:
        """Generates a multi-stage quest."""
        self.logger.info(f"Generating quest ({self.provider}) - Theme: {theme}")

        # Structure prompt based on difficulty
        if difficulty <= 3:
            structure = "Easy: 1 stage. Talk -> Action -> Reward."
        elif difficulty <= 7:
            structure = "Medium: 2-3 stages. Story slice. 1 combat."
        else:
            structure = "Hard: 4-6 stages. Character arc. Dungeon/Complex."

        prompt = f"""You are a Quest Designer AI. Generate a JSON quest.
Theme: {theme}
Difficulty: {difficulty}
NPC: {json.dumps(npc_giver_context)}
Context: {json.dumps(world_context)}
Structure: {structure}

Output JSON format:
{{
    "title": "String",
    "description": "String",
    "type": "String",
    "recommended_level": {difficulty * 2},
    "stages": [
        {{
            "stage_id": 1,
            "name": "String",
            "description": "String",
            "objectives": [{{"type": "KILL/FETCH/TALK", "target": "String", "count": 1}}],
            "start_dialogue": "String",
            "completion_dialogue": "String"
        }}
    ],
    "rewards": {{"xp": 100, "gold": 50, "items": ["String"]}}
}}
"""
        
        content = None
        if self.provider == "groq":
            content = self._generate_groq(prompt)
        elif self.provider == "gemini":
            content = self._generate_gemini(prompt)
        elif self.provider == "huggingface":
            content = self._generate_huggingface(prompt)
            
        if content:
            try:
                # Clean markdown
                content = content.replace("```json", "").replace("```", "").strip()
                # Sometimes HF models return the prompt + output. Try to find the JSON part.
                if "{" in content:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    content = content[start:end]
                
                return json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON Parse Error: {e}")
                self.logger.debug(f"Raw content: {content}")

        return None
