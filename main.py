import os
import json
import asyncio
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

#  CONFIGURATION 
HF_API_KEY = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TW_SID = os.getenv("TWILIO_ACCOUNT_SID")
TW_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TW_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/") # Strip trailing slash automatically
OWNER_PHONE = os.getenv("OWNER_PHONE")

# Mount Static Folder
if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Clients
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    hf_client = InferenceClient(token=HF_API_KEY)
    twilio_client = TwilioClient(TW_SID, TW_TOKEN)
except Exception as e: print(f"⚠️ Init Error: {e}")

#  2. LOCAL EARS (ASR) 
print("⏳ Loading Local ASR Model...")
try:
    asr_pipeline = pipeline("automatic-speech-recognition", model="NCAIR1/NigerianAccentedEnglish", token=HF_API_KEY)
    print("✅ ASR Ready!")
except: asr_pipeline = None

BRAIN_MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"

#  [FEATURE 4] MARKET WATCHDOG DATA 
MARKET_PRICES = {
    "cement": 5500,
    "rice": 80000,
    "yam": 2500,
    "pepper": 15000
}

#  3. HELPER FUNCTIONS 

def convert_audio_to_16k(input_path):
    try:
        y, sr = librosa.load(input_path, sr=16000)
        sf.write("temp_16k.wav", y, 16000)
        return "temp_16k.wav"
    except: return None

def transcribe_locally(file_path):
    if not asr_pipeline: return None
    try: return asr_pipeline(file_path).get("text", "")
    except: return None

#  [FEATURE 2] CREDIT SCORE CALCULATOR 
def update_credit_score(user_phone):
    try:
        # Simple Algorithm: Base 300 + (10 points per transaction cap 800)
        res = supabase.table("transactions").select("id", count="exact").eq("user_phone", user_phone).execute()
        count = res.count or 0
        new_score = min(800, 300 + (count * 10))
        # Upsert user and score (Requires 'users' table in DB)
        supabase.table("users").upsert({"phone": user_phone, "credit_score": new_score}).execute()
        return new_score
    except: return 300

#  [FEATURE 1] RECEIPT SCANNER (SIMULATED) 
def simulate_receipt_scan():
    return "I bought 30 cartons of Indomie for 150,000 naira."

#  PDF GENERATOR (CRASH PROOF) 
def generate_pdf_report(user_phone):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="AkoweAje Financial Report", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Generated for: {user_phone}", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=1, align='C')
    pdf.ln(10)

    score = update_credit_score(user_phone)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"Akowe Credit Score: {score}/800", ln=1)
    pdf.ln(5)

    res = supabase.table("transactions").select("*").order("created_at", desc=True).limit(20).execute()
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, "Date", 1)
    pdf.cell(25, 10, "Type", 1)
    pdf.cell(75, 10, "Item", 1)
    pdf.cell(35, 10, "Amount", 1)
    pdf.cell(25, 10, "Profit", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    total_sales = 0
    for row in res.data:
        # Safe Extraction
        date_str = row.get('created_at', '')[:10]
        intent = row.get('intent') or 'UNK'
        item = row.get('item') or 'Unknown'
        amount = row.get('amount') or 0
        profit = row.get('profit') or 0
        
        pdf.cell(30, 10, date_str, 1)
        pdf.cell(25, 10, intent[:10], 1)
        pdf.cell(75, 10, item[:35], 1)
        pdf.cell(35, 10, f"N{amount:,}", 1)
        pdf.cell(25, 10, f"N{profit:,}", 1)
        pdf.ln()
        
        if intent == 'SALE': total_sales += amount

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Total Revenue: N{total_sales:,.2f}", ln=1)

    filename = f"static/report_{int(datetime.now().timestamp())}.pdf"
    pdf.output(filename)
    return filename

#  VOICE BRIEFING 
async def generate_voice_briefing(text):
    filename = f"static/briefing_{int(datetime.now().timestamp())}.mp3"
    communicate = edge_tts.Communicate(text, "en-NG-EzinneNeural") 
    await communicate.save(filename)
    return filename

#  OMNI-BRAIN 
def extract_financial_data(text_input):
    system_prompt = """You are AkoweAje, an advanced AI Accountant. Analyze text -> return JSON.
    INTENTS: 'SALE', 'DEBT', 'GENERATE_REPORT', 'GENERATE_REMINDER', 'DAILY_BRIEF', 'GENERATE_AD', 'QUERY_SCORE'.
    
    EXAMPLES:
    Input: "I sell 50 bags of cement to Dangote for 200k. I buy am 150k."
    JSON: {"intent": "SALE", "item": "50 bags of cement", "amount": 200000, "cost_price": 150000, "customer": "Dangote"}
    
    Input: "What is my score" -> JSON: {"intent": "QUERY_SCORE"}
    Input: "{text_input}" -> JSON:"""
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text_input}]
    try:
        response = hf_client.chat_completion(model=BRAIN_MODEL_ID, messages=messages, max_tokens=250, temperature=0.1)
        clean_json = response.choices[0].message.content.strip()
        if "{" in clean_json:
            clean_json = clean_json[clean_json.find("{"):clean_json.rfind("}")+1]
            return json.loads(clean_json)
    except: pass
    return {"intent": "UNKNOWN"}

#  MAIN PROCESSOR  
async def process_message_task(sender_phone, body, media_url, media_type):
    final_text = body
    is_image_scan = False

    # [FEATURE 1] Receipt Scanning
    if media_url and media_type and media_type.startswith('image/'):
        print("📷 Image received. Simulating scan...")
        final_text = simulate_receipt_scan()
        is_image_scan = True

    # Audio Handling
    elif media_url and media_type and media_type.startswith('audio/'):
        try:
            r = requests.get(media_url, headers={'User-Agent': 'Mozilla/5.0'})
            with open("temp_voice.ogg", "wb") as f: f.write(r.content)
            wav = convert_audio_to_16k("temp_voice.ogg")
            if wav: final_text = transcribe_locally(wav) or final_text
        except: pass

    if not final_text: return
    print(f"📝 Analyzing: {final_text}")
    
    data = extract_financial_data(final_text)
    intent = data.get("intent")
    reply_msg = ""
    
    # [FEATURE 5] Anti-Theft
    if intent in ["SALE", "DEBT"] and OWNER_PHONE and sender_phone != OWNER_PHONE:
        alert_msg = f"🚨 SECURITY ALERT: Apprentice ({sender_phone}) just logged: {final_text}"
        try: twilio_client.messages.create(from_=TW_PHONE, to=OWNER_PHONE, body=alert_msg)
        except: pass

    if intent == "SALE":
        # Ensure strict integer conversion to avoid NoneType Errors 
        amount = int(data.get('amount') or 0)
        cost_price = int(data.get('cost_price') or 0)
        item = data.get('item') or "Unknown Item"
        
        # Profit Squeeze
        profit_msg = ""
        profit = 0
        if cost_price > 0 and amount > 0:
            profit = amount - cost_price
            margin = (profit / amount) * 100
            profit_msg = f"\n📈 Profit: ₦{profit:,.0f} ({margin:.1f}%)"
        
        # [FEATURE 4] Market Watchdog
        watchdog_msg = ""
        if amount > 0:
            for key, mkt_price in MARKET_PRICES.items():
                if key in item.lower():
                    # Naive check: if selling total is less than 1 unit price, warn
                    if amount < mkt_price:
                        watchdog_msg = f"\n⚠️ Market Alert: You are selling {key} cheap! Market price is N{mkt_price}."

        try:
            supabase.table("transactions").insert({
                "user_phone": sender_phone, "raw_text": final_text, "intent": "SALE",
                "item": item, "amount": amount,
                "cost_price": cost_price, "profit": profit
            }).execute()
        except Exception as e:
            print(f"DB Error: {e}")

        prefix = "📷 Receipt Scanned &" if is_image_scan else "💰"
        reply_msg = f"{prefix} Sale Recorded!\nItem: {item}\nAmount: ₦{amount:,.0f}{profit_msg}{watchdog_msg}"
        
        update_credit_score(sender_phone)

    elif intent == "GENERATE_AD":
        reply_msg = f"🚨 FRESH STOCK ALERT! 🚨\nJust landed: {data.get('item')}! Best quality, best price. Hurry before it finishes! 🏃🏾‍♂️💨"

    elif intent == "QUERY_SCORE":
        score = update_credit_score(sender_phone)
        reply_msg = f"🏆 Your current Akowe Credit Score is: {score}/800.\nKeep recording daily to increase it!"

    elif intent == "GENERATE_REMINDER":
        customer = data.get('customer', 'Customer')
        reply_msg = f"📝 Draft Message:\n\n'Hello {customer}, gentle reminder about the outstanding payment. Please let me know when to expect it. Thanks!'"

    elif intent == "GENERATE_REPORT":
        pdf_path = generate_pdf_report(sender_phone)
        reply_msg = f"📄 Official Financial Report & Credit Score:\n{BASE_URL}/{pdf_path}"

    elif intent == "DAILY_BRIEF":
        summary = "Good evening. You had a busy day. Your credit score is rising. Check your report for details."
        mp3_path = await generate_voice_briefing(summary)
        reply_msg = f"🎙️ Daily Voice Briefing:\n{BASE_URL}/{mp3_path}"
        
    else:
        reply_msg = f"I heard: '{final_text}'\nBut didn't understand. Try again."

    # SEND REPLY (Link Mode)
    try:
        twilio_client.messages.create(from_=TW_PHONE, to=sender_phone, body=reply_msg)
        print("✅ Message Sent!")
    except Exception as e: print(f"❌ Twilio Error: {e}")

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    # Safely get ContentType
    media_type = form.get('MediaContentType0', '')
    background_tasks.add_task(process_message_task, form.get('From'), form.get('Body'), form.get('MediaUrl0'), media_type)
    return Response(content="<Response></Response>", media_type="application/xml")