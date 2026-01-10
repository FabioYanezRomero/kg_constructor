import requests
import json
import time

def test_ollama():
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "gemma3:12b",
        "prompt": "Say hello in one word.",
        "stream": False
    }
    
    print(f"Testing Ollama at {url}...")
    start_time = time.time()
    try:
        response = requests.post(url, json=data, timeout=30)
        elapsed = time.time() - start_time
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json().get('response')}")
        print(f"Time Taken: {elapsed:.2f}s")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ollama()
