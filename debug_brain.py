import os
import json
import time
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")


# We try these in order. If one fails, we move to the next.
MODELS_TO_TRY = [
    "meta-llama/Meta-Llama-3-8B-Instruct",  
    "Qwen/Qwen2.5-7B-Instruct",             
    "google/gemma-2-9b-it",                 
    "HuggingFaceH4/zephyr-7b-beta"          
]

def test_brain():
    client = InferenceClient(token=HF_API_KEY)
    
    text_input = "I sell 50 bags of cement to Dangote for 200000 naira"
    
    messages = [
        {"role": "system", "content": "You are a financial extraction tool. Extract 'intent' (SALE/DEBT), 'item', 'amount', 'customer' into JSON. Return ONLY JSON."},
        {"role": "user", "content": text_input}
    ]

    print(" Starting Model Search...\n")

    for model_id in MODELS_TO_TRY:
        print(f" Trying Model: {model_id}...")
        try:
            response = client.chat_completion(
                model=model_id,
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )
            
            raw_content = response.choices[0].message.content
            print(f"✅ SUCCESS with {model_id}!")
            print("-" * 30)
            print(raw_content)
            print("-" * 30)
            
            print(f" WINNER: {model_id}")
            print("Update your main.py with this Model ID.")
            return

        except Exception as e:
            error_msg = str(e)
            if "loading" in error_msg:
                print(f"⏳ Model {model_id} is loading... (Skipping to next for speed)")
            elif "not supported" in error_msg:
                print(f"❌ Model {model_id} not supported/active.")
            else:
                print(f"❌ Error: {error_msg}")
            time.sleep(1) # Brief pause

    print(" All models failed. Check your Token permissions or Internet connection.")

if __name__ == "__main__":
    test_brain()