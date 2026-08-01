# 🚀 Automation Prompt Builder

> Build production-ready AI automation prompts from simple natural language.

Automation Prompt Builder is an AI-powered application that transforms user requirements into structured, optimized prompts for autonomous AI agents, workflow automation platforms, LLM applications, and enterprise AI systems.

Instead of manually engineering prompts, users simply describe what they want to automate, and the system generates optimized prompts following prompt engineering best practices.

---

# ✨ Features

- AI-powered prompt generation
- Production-ready prompt templates
- Multiple automation categories
- Structured prompt formatting
- Variable extraction
- Prompt optimization
- Validation engine
- Prompt preview
- Export prompts
- Copy with one click
- Prompt versioning
- Fast generation
- Responsive UI
- REST API
- OpenAPI documentation

---

# 🏗 Architecture

```
                    ┌───────────────────────┐
                    │      Web Client       │
                    └──────────┬────────────┘
                               │
                         REST API
                               │
                    ┌──────────▼────────────┐
                    │      FastAPI API      │
                    └──────────┬────────────┘
                               │
        ┌──────────────────────┼───────────────────────┐
        │                      │                       │
        ▼                      ▼                       ▼
 Prompt Generator      Validation Engine      Template Engine
        │                      │                       │
        └──────────────┬───────┴──────────────┬────────┘
                       ▼
               Prompt Optimizer
                       │
                       ▼
                 Database Layer
                       │
                       ▼
                 PostgreSQL
```

---

# 📂 Project Structure

```
automation-prompt-builder/

├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── prompts/
│   ├── validators/
│   ├── utils/
│   └── main.py
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── lib/
│   └── assets/
│
├── docs/
├── tests/
├── docker/
├── scripts/
├── alembic/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── package.json
├── README.md
└── .env.example
```

---

# ⚙ Tech Stack

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- PostgreSQL
- Redis
- Celery

## Frontend

- React
- TypeScript
- Tailwind CSS
- Vite
- React Query
- Axios

## AI

- OpenAI
- Anthropic
- Gemini
- DeepSeek
- OpenRouter

## DevOps

- Docker
- Docker Compose
- GitHub Actions
- Railway
- Render
- Vercel

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/yourusername/automation-prompt-builder.git

cd automation-prompt-builder
```

---

## Backend

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Linux

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run server

```bash
uvicorn app.main:app --reload
```

---

## Frontend

Install packages

```bash
npm install
```

Start

```bash
npm run dev
```

---

## Docker

```bash
docker compose up --build
```

---

# 📌 API Endpoints

## Prompt Generation

```
POST /api/v1/prompts/generate
```

## Prompt Validation

```
POST /api/v1/prompts/validate
```

## Optimize Prompt

```
POST /api/v1/prompts/optimize
```

## Templates

```
GET /api/v1/templates
```

## Export Prompt

```
POST /api/v1/prompts/export
```

---

# 🧠 Supported Automation Types

- AI Agents
- Workflow Automation
- Customer Support
- Email Automation
- Marketing
- LinkedIn Content
- YouTube Automation
- Data Analysis
- Code Generation
- Documentation
- Research
- Sales
- Recruiting
- Project Management
- Custom Workflows

---

# 📊 Prompt Pipeline

```
User Input

      │

      ▼

Intent Detection

      │

      ▼

Requirement Extraction

      │

      ▼

Template Selection

      │

      ▼

Prompt Construction

      │

      ▼

Optimization

      │

      ▼

Validation

      │

      ▼

Final Prompt
```

---

# 🔒 Validation

Every generated prompt is validated for

- Structure
- Completeness
- Variable consistency
- Missing context
- Prompt quality
- AI compatibility
- Formatting

---

# 📈 Performance

- Fast prompt generation
- Async processing
- Redis caching
- Background workers
- Optimized database queries
- Low latency API

---

# 🧪 Testing

Run tests

```bash
pytest
```

Coverage

```bash
pytest --cov=app
```

---

# 📖 Documentation

Interactive API

```
/docs
```

ReDoc

```
/redoc
```

OpenAPI

```
/openapi.json
```

---

# 🌍 Environment Variables

```env
DATABASE_URL=

REDIS_URL=

OPENAI_API_KEY=

ANTHROPIC_API_KEY=

GOOGLE_API_KEY=

OPENROUTER_API_KEY=

SECRET_KEY=
```

---

# 🤝 Contributing

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature/new-feature
```

3. Commit changes

```bash
git commit -m "Add feature"
```

4. Push

```bash
git push origin feature/new-feature
```

5. Open Pull Request

---

# 🛣 Roadmap

- Prompt Marketplace
- Team Collaboration
- AI Evaluation
- Workflow Export
- Multi-language Prompts
- Prompt Analytics
- Prompt History
- AI Agent Templates
- Plugin Support
- Enterprise Dashboard

---

# 📄 License

MIT License

---

# ⭐ Support

If you find this project useful, consider giving it a ⭐ on GitHub.

---

Built with ❤️ using FastAPI, React, PostgreSQL, and Modern AI Models.
