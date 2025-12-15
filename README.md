# akowe-aje-backend

# 🦅 AkoweAje
### The AI Financial Platform for the Informal Economy
**(Powered by Awarri & Llama-3)**

---

### 🚀 Quick Access Ecosystem
| Component | Status | Link |
| :--- | :--- | :--- |
| **📊 Live Dashboard** | **Active** | [View Real-Time Ledger](https://akowe-aje-dashboard-nb83qwd94tzkhqmasvfbkg.streamlit.app) |
| **🧠 Backend API** | **Running** | [Hugging Face Space](https://huggingface.co/spaces/Archimedis/AkoweAje-Backend) |
| **📂 Source Code** | **Public** | [GitHub Repository](https://github.com/Fharuk/akowe-aje-backend) |

---

## 📖 The Problem
Nigeria’s informal sector accounts for **65% of GDP**, yet millions of traders remain unbanked. They operate in cash and oral agreements, making them invisible to formal financial institutions. Existing tools require high literacy and manual data entry, excluding the very people who need them most.

## 💡 The Solution: AkoweAje
**AkoweAje** (The AI Scribe for Wealth) is a voice-first financial identity platform built on **WhatsApp**. It allows illiterate and semi-literate traders to:
1.  **Keep Professional Books** by simply sending voice notes in Pidgin or local accents.
2.  **Track Profits** instantly with every sale.
3.  **Build a Credit Score** (The "Akowe Score") based on verifiable transaction history.
4.  **Receive Daily Audio Briefings** in their local accent.

---

## ⚙️ Technical Architecture (The Hybrid Engine)

We utilize a novel **Hybrid Inference Architecture** to balance cost, privacy, and accuracy.

### 1. Local "Ears" (Edge Inference) 🇳🇬
We do **not** use generic cloud APIs for speech recognition. Instead, we deploy the **N-ATLaS (NCAIR1/NigerianAccentedEnglish)** model directly inside our Docker container.
* **Why?** To accurately transcribe heavy Nigerian accents and market lingo that Western models miss.
* **Tech:** `transformers` pipeline running on CPU.

### 2. Cloud "Brain" (Reasoning) 🧠
We offload complex intent extraction to **Meta Llama-3-8B-Instruct**.
* **Role:** It analyzes the text to distinguish between `SALES`, `DEBTS`, `EXPENSES`, and `AD REQUESTS`.
* **Tech:** Hugging Face Inference API.

### 3. Agentic Workflows 🤖
The system is not just a passive ledger; it acts as an agent:
* **The Hype Man:** Generates creative ad copy for WhatsApp Status.
* **The Debtor Chaser:** Drafts polite debt recovery messages.
* **The Auditor:** Generates professional PDF financial reports using `FPDF`.
* **The Narrator:** Uses **Edge-TTS** with a dual-engine fallback (Nigerian Accent $\to$ US Accent) to read summaries back to the user.

---

## ✨ Key Features

* **🗣️ Voice-to-Ledger:** Records sales via voice notes ("I sell 5 bags of rice for 200k").
* **📈 Profit Squeeze:** Automatically calculates profit margins based on cost price.
* **🦅 Market Watchdog:** Warns users if they are selling below the market rate for items like Rice, Cement, or Yam.
* **📷 Receipt Scanner:** Uses computer vision to log inventory from photos of physical receipts.
* **🏆 Akowe Credit Score:** A gamified scoring system (300-800) that increases with consistent record-keeping.
* **🎙️ Resilient Audio Briefing:** Daily voice summaries that work even if specific TTS servers go down (Auto-Fallback).

---

## 🛠️ Installation & Setup

### Prerequisites
* Python 3.10+
* Docker
* Supabase Account
* Twilio Account (WhatsApp Sandbox)
* Hugging Face Token


## 1. Create a .env file:
HF_API_KEY=hf_xxxx
SUPABASE_URL=[https://your-project.supabase.co](https://your-project.supabase.co)
SUPABASE_KEY=your-anon-key
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
OWNER_PHONE=whatsapp:+23480xxxx

### 2. Run Locally (Docker)
docker build -t akoweaje .
docker run -p 7860:7860 --env-file .env akoweaje

### 📝 Usage Guide (WhatsApp Commands)
Intent,Example Command (Voice or Text)
Log Sale,"""I sell 20 cartons of Indomie for 100k. Cost price was 80k."""
Check Score,"""What is my credit score?"""
Marketing,"""Write advert for fresh pepper."""
Debt Reminder,"""Write message to Dangote to pay me."""
Report,"""Generate report"" (Returns PDF)"
Briefing,"""Give me daily brief"" (Returns Audio)"

# 🤝 Acknowledgements
Awarri & NCAIR: For the N-ATLaS model that makes local accent recognition possible.

Meta AI: For the Llama-3 model powering the reasoning engine.

Supabase: For the real-time database infrastructure.

Streamlit: For the live visualization dashboard.

### 4. Clone the Repo
```bash
git clone [https://github.com/Fharuk/akowe-aje-backend.git](https://github.com/Fharuk/akowe-aje-backend.git)
cd akowe-aje-backend

