import os
import json
import asyncio
import time
import requests
import librosa
import soundfile as sf
from datetime import datetime
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from supabase import create_client, Client
from huggingface_hub import InferenceClient
from transformers import pipeline
from twilio.rest import Client as TwilioClient
from fpdf import FPDF
import edge_tts

load_dotenv()

app = FastAPI()

# --- CONFIGURATION ---
HF_API_KEY = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TW_SID = os.getenv("TWILIO_ACCOUNT_SID")
TW_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TW_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
OWNER_PHONE = os.getenv("OWNER_PHONE")
BASE_URL = os.getenv("BASE_URL", "https://huggingface.co/spaces/Archimedis/AkoweAje-Backend").rstrip("/")

if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- INITIALIZATION WITH ERROR LOGGING ---
def log_error(error_msg, context="General"):
    """Saves errors to Supabase so we don't lose them on restart."""
    print(f"❌ {context}: {error_msg}")
    try:
        if supabase:
            supabase.table("error_logs").insert({"error_message": str(error_msg), "context": context}).execute()
    except: pass

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    hf_client = InferenceClient(token=HF_API_KEY)
    twilio_client = TwilioClient(TW_SID, TW_TOKEN)
except Exception as e:
    print(f"⚠️ Critical Init Error: {e}")
    supabase = None # Prevent crashes if init fails

# --- LOCAL EARS ---
print("⏳ Loading Local ASR Model...")
try:
    asr_pipeline = pipeline("automatic-speech-recognition", model="NCAIR1/NigerianAccentedEnglish", token=HF_API_KEY)
    print("✅ ASR Ready!")
except Exception as e:
    log_error(e, "ASR Load")
    asr_pipeline = None

BRAIN_MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"
MARKET_PRICES = {"cement": 5500, "rice": 80000, "yam": 2500, "pepper": 15000}

# --- HELPER FUNCTIONS ---
def convert_audio_to_16k(input_path):
    try:
        # Fallback logic for reading audio is handled automatically by librosa/audioread
        y, sr = librosa.load(input_path, sr=16000)
        sf.write("temp_16k.wav", y, 16000)
        return "temp_16k.wav"
    except Exception as e:
        log_error(e, "Audio Conversion")
        return None

def transcribe_locally(file_path):
    if not asr_pipeline: return None
    try: return asr_pipeline(file_path).get("text", "")
    except Exception as e:
        log_error(e, "Transcribe")
        return None

def update_credit_score(user_phone):
    try:
        res = supabase.table("transactions").select("id", count="exact").eq("user_phone", user_phone).execute()
        count = res.count or 0
        new_score = min(800, 300 + (count * 10))
        supabase.table("users").upsert({"phone": user_phone, "credit_score": new_score}).execute()
        return new_score
    except: return 300

def generate_pdf_report(user_phone):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="AkoweAje Financial Report", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Generated for: {user_phone}", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=1, align='C')
        pdf.ln(10)

        # Fetch Data
        res = supabase.table("transactions").select("*").order("created_at", desc=True).limit(20).execute()
        
        # Simple Table
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 10, "Item", 1)
        pdf.cell(50, 10, "Amount", 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=10)
        for row in res.data:
            item = row.get('item', 'Unknown')
            amount = row.get('amount', 0)
            pdf.cell(100, 10, str(item)[:40], 1)
            pdf.cell(50, 10, f"N{amount:,}", 1)
            pdf.ln()

        filename = f"static/report_{int(datetime.now().timestamp())}.pdf"
        pdf.output(filename)
        return filename
    except Exception as e:
        log_error(e, "PDF Generation")
        return None

async def generate_voice_briefing(text):
    filename = f"static/briefing_{int(datetime.now().timestamp())}.mp3"
    try:
        communicate = edge_tts.Communicate(text, "en-NG-EzinneNeural")
        await communicate.save(filename)
        return filename
    except:
        try: # Fallback
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(filename)
            return filename
        except Exception as e:
            log_error(e, "TTS Generation")
            return None

# --- ROBUST BRAIN (WITH RETRY) ---
def extract_financial_data(text_input):
    system_prompt = """You are AkoweAje. Extract intent JSON. 
    Intents: SALE, DEBT, EXPENSE, GENERATE_REPORT, DAILY_BRIEF, QUERY_SCORE, GENERATE_AD.
    Example: "Sold rice 50k" -> {"intent": "SALE", "item": "rice", "amount": 50000}
    Example: "Write message to dangote" -> {"intent": "GENERATE_REMINDER", "customer": "dangote"}
    OUTPUT JSON ONLY."""
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text_input}]
    
    # Retry Logic for "Model Loading" errors
    for attempt in range(3):
        try:
            response = hf_client.chat_completion(model=BRAIN_MODEL_ID, messages=messages, max_tokens=200, temperature=0.1)
            raw = response.choices[0].message.content.strip()
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw[start:end+1])
        except Exception as e:
            print(f"⚠️ Brain Stumble (Attempt {attempt+1}): {e}")
            time.sleep(2) # Wait for model to load
            
    log_error("Brain failed after 3 attempts", "LLM Inference")
    return {"intent": "UNKNOWN"}

# --- PROCESSOR ---
async def process_message_task(sender_phone, body, media_url, media_type):
    final_text = body
    is_scan = False

    if media_url and media_type and media_type.startswith('audio/'):
        try:
            r = requests.get(media_url)
            with open("temp_voice.ogg", "wb") as f: f.write(r.content)
            wav = convert_audio_to_16k("temp_voice.ogg")
            if wav: final_text = transcribe_locally(wav) or final_text
        except Exception as e: log_error(e, "Audio Download")
    
    if not final_text: return
    
    data = extract_financial_data(final_text)
    intent = data.get("intent")
    reply = ""

    # ... [Keep your existing logic for SALE, REPORT, etc. here] ...
    # For brevity, I am summarizing the logic block:
    
    if intent == "SALE":
        item = data.get("item", "Item")
        amount = data.get("amount", 0)
        
        # Save to DB
        try:
            supabase.table("transactions").insert({"user_phone": sender_phone, "intent": "SALE", "item": item, "amount": amount}).execute()
            update_credit_score(sender_phone)
            reply = f"💰 Sale Recorded!\nItem: {item}\nAmount: ₦{amount:,}"
        except Exception as e:
            log_error(e, "DB Insert")
            reply = "⚠️ Error saving transaction."

    elif intent == "DAILY_BRIEF":
        summary = "Your daily summary is ready."
        mp3 = await generate_voice_briefing(summary)
        if mp3: reply = f"🎙️ Audio Briefing:\n{BASE_URL}/{mp3}"
        else: reply = summary

    elif intent == "GENERATE_REPORT":
        pdf = generate_pdf_report(sender_phone)
        if pdf: reply = f"📄 Report:\n{BASE_URL}/{pdf}"
        else: reply = "⚠️ Could not generate report."
        
    else:
        if intent == "UNKNOWN":
            reply = "I didn't understand that transaction. Try: 'Sold 5 bags of rice for 50k'."
        else:
            reply = f"Processed: {intent}"

    # Branding
    reply += "\n\n(Powered by Awarri)"

    try:
        twilio_client.messages.create(from_=TW_PHONE, to=sender_phone, body=reply)
    except Exception as e: log_error(e, "Twilio Send")

@app.get("/health")
def health_check():
    """Simple endpoint for UptimeRobot to ping"""
    return {"status": "alive", "timestamp": datetime.now()}

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    background_tasks.add_task(process_message_task, form.get('From'), form.get('Body'), form.get('MediaUrl0'), form.get('MediaContentType0'))
    return Response(content="<Response></Response>", media_type="application/xml")
