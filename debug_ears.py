import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
ASR_MODEL = "NCAIR1/NigerianAccentedEnglish"

def test_ears():
    print(f"🎧 Connecting to {ASR_MODEL} via Official Client...")
    client = InferenceClient(token=HF_API_KEY)
    
    
    filename = "temp_16k.wav"
    
    if not os.path.exists(filename):
        print(" No 'temp_16k.wav' found. Run the server and send a voice note first to generate it.")
        return

    try:
        with open(filename, "rb") as f:
            # The official client handles the API routing automatically
            result = client.automatic_speech_recognition(f, model=ASR_MODEL)
        
        print(" SUCCESS! Raw Output:")
        print(result)
        
    except Exception as e:
        print(f" Error: {e}")

if __name__ == "__main__":
    test_ears()