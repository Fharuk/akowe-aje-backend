import requests


url = "http://127.0.0.1:8000/webhook"

# We simulate a WhatsApp message coming from Twilio
payload = {
    "From": "whatsapp:+2348000000000",
    "Body": "I sell 50 bags of cement to Dangote for 200000 naira",
    
}

print("🚀 Sending test message to AkoweAje...")
try:
    response = requests.post(url, data=payload)
    print(f"✅ Response Status: {response.status_code}")
    print(f"📜 Response Body: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")