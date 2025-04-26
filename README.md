# TaxAgentServer

An AI-driven automatic tax filing checker. Once users provide personal and tax-related information using natural language, the AI automatically opens the relevant tax form webpages, fills in personal details and tax data, and allows users to retrieve or summarize the provided information using natural language commands for easy verification.

## Features

- Automatically open webpages and fill tax information
- Natural language input and control
- Intelligent retrieval and summarization of filled data
- User-friendly interactive review interface

## Tech Stack

- Python
- Playwright
- Google GenAI
- JWT Authentication
- FastAPI
- SQLite
- Docker

## Installation 

### Installation requirements

1. Clone repository:

```bash
git clone https://github.com/yourusername/fill-agent-server.git
```

2. Init virtual environment and install dependencies:

```bash
uv venv
uv sync
```

3. Install Playwright browsers:

```bash
playwright install
```

### Setup environment Variables

Set Google GenAI API key and JWT secret key.

```bash
GOOGLE_GENAI_USE_VERTEXAI="False"
GOOGLE_API_KEY=
JWT_SECRET_KEY=
UFILE_USERNAME=
UFILE_PASSWORD=
PLAYWRIGHT_PORT=3100
```

### Usage

#### Satart browser

```bash
uv run income_tax_agent/brower_server.py
```

You should click login button and select 2024 tax year.

#### Usage

##### Using in development web UI

```bash
uv run adk web
```

##### Using in CLI

```bash
uv run income_tax_agent
```

### Run backend API server

```bash
uv run main.py
```


## Contributing

Contributions and suggestions are welcome:

1. Fork this repository
2. Create a new branch
3. Commit your changes
4. Create a Pull Request

## License

This project is licensed under the MIT License.

