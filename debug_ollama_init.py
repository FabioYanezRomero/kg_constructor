import sys
from kg_constructor.clients.ollama_client import OllamaOpenAILanguageModel

def test_init():
    model = OllamaOpenAILanguageModel(
        model_id="gemma3:12b",
        api_key="ollama",
        base_url="http://localhost:11434/v1",
        timeout=30
    )
    print(f"Model ID: {model.model_id}")
    print(f"Base URL: {model.base_url}")
    print(f"API Key: {model.api_key}")
    
    if model.model_id == "gemma3:12b" and "localhost" in model.base_url:
        print("SUCCESS: Initialization correct")
    else:
        print("FAILURE: Initialization incorrect")

if __name__ == "__main__":
    test_init()
