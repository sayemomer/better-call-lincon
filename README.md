# 🇨🇦 AI Immigration Lawyer Agent

> An AI-powered co-pilot that helps users navigate the Canadian immigration journey — from Student → Work Permit → PR → Citizenship.

Built for **ConUHacks Hackathon 2026** 💙

---

## 🌍 Problem

Canadian immigration is complex:

* Constant IRCC policy changes
* CRS scoring confusion
* Missed deadlines
* Application form errors
* No personalized, continuous guidance

Applicants often risk refusals due to small mistakes or outdated information.

---

## 💡 Our Solution

**AI Immigration Lawyer Agent** acts as an intelligent assistant that:

* Calculates CRS scores
* Tracks deadlines & compliance
* Monitors immigration policy updates
* Assists with document uploads & form understanding
* Generates personalized pathway recommendations
* Provides explainable AI insights (no black-box outputs)

⚠️ The system does **not** provide legal advice and does not submit applications to IRCC.

---
## 📸 Screenshots

### First Page
<img width="1468" height="798" alt="Screenshot 2026-01-25 at 8 42 56 AM" src="https://github.com/user-attachments/assets/725f9917-ae78-4936-a9d2-5382acfc6a08" />

### Dashboard
<img width="1078" height="644" alt="Screenshot 2026-01-25 at 9 32 08 AM" src="https://github.com/user-attachments/assets/58fa17a7-c389-4de4-bf62-14048f496b48" />

### Chat With AI
<img width="1052" height="648" alt="Screenshot 2026-01-25 at 9 32 47 AM" src="https://github.com/user-attachments/assets/7525691e-f595-4406-9590-4a2261ed9c84" />

<img width="1043" height="644" alt="Screenshot 2026-01-25 at 9 33 04 AM" src="https://github.com/user-attachments/assets/02472b2b-5fb0-45a0-ad80-55ddc82cb4e7" />

### About Us

<img width="1466" height="794" alt="Screenshot 2026-01-25 at 9 33 59 AM" src="https://github.com/user-attachments/assets/289567f3-1c57-4076-b762-0a69ca95e87e" />

---
## 🏗️ Architecture Overview

### 🔹 Backend

* **FastAPI** – High-performance REST APIs
* **MongoDB** – Flexible document storage
* **CrewAI** – Multi-agent orchestration
* **Gemini API** – AI reasoning & recommendations
* **Landing AI OCR** – Document text extraction

### 🔹 Frontend

* **React (Vite)** – Modern responsive UI

---

## 🧠 AI Agent System

We use **CrewAI** to orchestrate specialized agents:

* Eligibility Agent → CRS scoring & gap analysis
* Policy Monitoring Agent → Tracks IRCC updates
* Recommendation Agent → Pathway planning
* Form Assistant Agent → Explains application forms
* Compliance Agent → Deadline tracking & alerts

All AI outputs include explanations for transparency.

---

## 🔌 Core Features

### 🔐 Authentication & Profiles

* User registration/login
* Structured immigration profile storage

### 📊 CRS & Eligibility

* Express Entry CRS score computation
* Gap analysis
* Program eligibility summary

### ⏰ Deadline Tracking

* Study permit expiry
* PGWP deadlines
* PR timelines
* Smart alerting

### 📰 Policy Monitoring

* IRCC update ingestion
* Personalized policy relevance matching

### 📄 Document & Form Assistance

* OCR document extraction (Landing AI)
* Form explanation
* AI-assisted prefill suggestions

---

## 🗂️ Project Structure

```
/backend
    ├── app/
    ├── agents/
    ├── api/
    ├── models/
    ├── services/

frontend/
    ├── src/
    ├── components/
    ├── pages/
```

---

## ⚙️ Installation

### Backend

```bash
create a virtual environment and activate it
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🔐 Environment Variables

Create a `.env` file:

```
MONGODB_URI=
GEMINI_API_KEY=
LANDING_AI_API_KEY=
JWT_SECRET=
```

---

## 🧪 Example API Endpoints

* `POST /auth/register`
* `POST /eligibility/crs`
* `GET /deadlines`
* `POST /documents/upload`
* `POST /recommendations/pathways`

---

## 🛡️ Security & Ethics

* JWT-based authentication
* Secure document storage
* Explainable AI outputs
* No deterministic immigration guarantees
* No legal advice

---

## 🎯 Hackathon Context

This project was built during **ConUHacks 2026**.

Huge thanks to:

* 💙 **ConUHacks team** for organizing an amazing event
* 🤖 **Gemini API** for providing free AI access during development

We genuinely appreciate the support that made this possible.

---

## 🚀 Future Improvements

* Real-time IRCC policy crawler
* Advanced CRS simulation engine
* Multi-language support
* Timeline prediction modeling
* Admin dashboard for policy management

---

## 🤝 Sponsorship & Support

We are actively looking for:

* 🚀 Sponsorship
* ☁️ Cloud credits
* 🤖 AI API partnerships
* 💼 Immigration tech collaborators

If you're interested in supporting or collaborating:

📩 Open an issue
📧 Contact us directly

Omer Sayem: https://www.linkedin.com/in/omer-sayem/

Mahdieh Shekarian: https://www.linkedin.com/in/mahdieh-shekarian/

Sharifa Akter: https://www.linkedin.com/in/aktersharifa/

⭐ Or simply star the repo to show support

---

## 📄 License

MIT License


