# 🚀 AI Job Search & Resume Improvement Agent

An intelligent multi-agent AI system that analyzes resumes, searches relevant jobs, matches skills with job requirements, suggests resume improvements, and generates interview questions automatically.

Built using **LangChain**, **CrewAI**, **Streamlit**, and free LLM providers like **Groq** and **Ollama**.

---

# ✨ Features

- 📄 Resume Analysis
- 🔍 AI-Powered Job Search
- 🎯 Skill Matching & Scoring
- 🧠 Resume Improvement Suggestions
- 🎤 Interview Question Generation
- 🌐 Streamlit Web Interface
- 📑 PDF Report Export
- ⚡ CLI Support
- 🤖 Multi-Agent Architecture
- ☁️ Cloud + Local LLM Support

---

# 🧠 AI Agents

| Agent | Responsibility |
|--------|----------------|
| **Resume Analyzer** | Extracts skills, strengths, experience, and missing keywords |
| **Job Finder** | Searches jobs and compares requirements with resume skills |
| **Recommendation Agent** | Suggests resume improvements and generates interview questions |

---

# 🛠️ Tech Stack

| Technology | Usage |
|------------|-------|
| **Python** | Backend development |
| **LangChain** | LLM orchestration |
| **CrewAI** | Multi-agent workflow |
| **Streamlit** | Web UI |
| **Groq** | Cloud LLM |
| **Ollama** | Local offline LLM |
| **ReportLab** | PDF export |

---

# 📁 Project Structure

```bash
AI-Job-Agent/
│
├── streamlit_app.py          # Streamlit web application
├── main.py                   # CLI entry point
├── requirements.txt
├── .env.example
│
├── src/
│   ├── agents/
│   │   └── crew_setup.py
│   │
│   ├── llm/
│   │   └── factory.py
│   │
│   ├── pipeline.py
│   │
│   ├── report/
│   │   └── pdf_export.py
│   │
│   ├── resume/
│   ├── jobs/
│   ├── matching/
│   └── tools/
│
└── sample_resume.txt
```

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/ai-job-agent.git

cd ai-job-agent
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Configure Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key

LLM_PROVIDER=groq
```

---

# 🤖 LLM Setup

# Option 1 — Groq (Recommended)

1. Create a free API key from:

https://console.groq.com/keys

2. Add the key to `.env`

```env
GROQ_API_KEY=your_api_key
```

---

# Option 2 — Ollama (Local LLM)

Install Ollama:

https://ollama.com

Pull the model:

```bash
ollama pull llama3.2
```

Set provider in `.env`

```env
LLM_PROVIDER=ollama
```

---

# ▶️ Running the Application

# 🌐 Streamlit Web Interface

```bash
streamlit run streamlit_app.py
```

or

```bash
python main.py ui
```

### Features Available in UI

- Upload resume
- Choose AI provider
- Quick analysis
- Full multi-agent workflow
- Download Markdown report
- Download PDF report

---

# 💻 CLI Usage

## Check LLM Providers

```bash
python main.py status
```

---

## Quick Resume Analysis

```bash
python main.py quick sample_resume.txt
```

Generate PDF report:

```bash
python main.py quick sample_resume.txt --pdf report.pdf
```

---

## Full Multi-Agent Workflow

```bash
python main.py run sample_resume.txt --provider groq
```

With PDF export:

```bash
python main.py run sample_resume.txt --provider groq --pdf report.pdf
```

---

## Use Local Ollama

```bash
python main.py quick sample_resume.txt --provider ollama
```

---

# 🧩 Individual Commands

## Analyze Resume

```bash
python main.py analyze sample_resume.txt
```

---

## Search Jobs

```bash
python main.py jobs "Python Developer"
```

---

## Match Resume with Jobs

```bash
python main.py jobs "Data Scientist" --resume sample_resume.txt
```

---

# 🔄 Workflow

1. Upload Resume
2. Resume Analyzer extracts skills and experience
3. Job Finder searches relevant jobs
4. Matching engine calculates compatibility score
5. Recommendation Agent suggests improvements
6. AI generates interview questions
7. Final report exported as PDF

---

# 📄 Sample Report Includes

- Resume Summary
- Extracted Skills
- Missing Keywords
- Resume Improvement Suggestions
- Job Recommendations
- Match Scores
- Interview Questions
- Final Career Recommendations

---

# 🚀 Future Improvements

- LinkedIn job integration
- ATS resume scoring
- AI cover letter generator
- Voice interview simulation
- Docker deployment
- User authentication
- Database integration
- Email notifications

---

# 🤝 Contributing

Contributions are welcome.

## Steps

```bash
# Fork repository

# Create feature branch
git checkout -b feature-name

# Commit changes
git commit -m "Added new feature"

# Push branch
git push origin feature-name

# Create pull request
```

---

# 📜 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

### Your Name

GitHub:
https://github.com/mohjunaid92



---

# ⭐ Support

If you found this project useful:

- Star the repository
- Share with others
- Contribute improvements

---

# 📚 Resources

- https://python.langchain.com/
- https://docs.crewai.com/
- https://streamlit.io/
- https://console.groq.com/
- https://ollama.com/

---
```
