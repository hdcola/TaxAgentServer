# 🚀 TaxAgentServer

**TaxAgentServer** is an AI-powered automatic tax filing assistant designed to simplify the entire tax return process.

Once users provide their personal and tax-related information through natural language, the system intelligently:

- Opens the relevant tax form webpages
- Auto-fills personal details and tax slip data
- Allows users to retrieve, review, and summarize all entered information
- Supports easy verification and adjustments via conversational commands

No complex forms, no manual data entry — just a fast, user-friendly, and reliable tax filing experience.

## ✨ Features

- **Automated Tax Filing:**  
  Automatically opens required web pages, fills in tax slip information based on user input, and handles form interactions intelligently.

- **Natural Language Interface:**  
  Users simply chat with the system — no complicated forms or technical steps. Provide slip types, box numbers, and amounts naturally through conversation.

- **AI-Driven Data Extraction:**  
  Automatically retrieves, validates, and summarizes the filled tax data for review, reducing human errors.

- **Interactive Review Mode:**  
  Offers a user-friendly, conversational interface for users to review, confirm, and edit their tax information before final submission.

- **Zero Guesswork, Zero Confusion:**  
  Streamlines the entire tax return process — no need for users to understand government forms or technical details. The system handles everything end-to-end.

- **Seamless Slip Management:**  
  Supports multiple slip types (T4, T4A, etc.) and dynamic box number matching, with intelligent auto-correction and validation.

- **Fast and Secure:**  
  Optimized for speed and accuracy while maintaining high standards of user data privacy and protection.


## 🛠️ Tech Stack

- **Python** — Core programming language
- **Playwright** — Browser automation for seamless web interaction
- **Google GenAI** — Natural language understanding and AI-driven processing
- **JWT Authentication** — Secure and stateless user authentication
- **FastAPI** — High-performance web framework for APIs
- **SQLite** — Lightweight database for storage
- **Docker** — Containerization for easy deployment and scaling

## 🚀 Installation

### 📦 Installation Requirements

1. **Clone the repository**:

```bash
git clone https://github.com/yourusername/fill-agent-server.git
```

2. **Initialize virtual environment and install dependencies**:

```bash
uv venv
uv sync
```

3. **Install Playwright browsers**:

```bash
playwright install
```

### ⚙️ Setup Environment Variables

Set your Google GenAI API key, JWT secret key, and UFile credentials:

```bash
GOOGLE_GENAI_USE_VERTEXAI="False"
GOOGLE_API_KEY=
JWT_SECRET_KEY=
UFILE_USERNAME=
UFILE_PASSWORD=
PLAYWRIGHT_PORT=3100
```

### 📖 Usage

#### 🖥️ Start Browser

```bash
uv run income_tax_agent/brower_server.py
```

> 📝 **Note**: After starting the browser, click the login button and select the **2024** tax year.

#### 💻 Development Web UI

```bash
uv run adk web
```

#### 🖥️ Command Line Interface (CLI)

```bash
uv run income_tax_agent
```

### 🛠️ Run Backend API Server

```bash
uv run main.py
```

---

## 🤝 Contributing

We welcome contributions and suggestions! Here's how you can help:

1. Fork this repository
2. Create a new branch
3. Commit your changes
4. Create a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**.

