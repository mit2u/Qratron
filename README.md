# Qratron

**Qratron** is a Django-based AI document assistant for PDF question answering and auto-generated slide decks.

## What's New in This Improved Fork

Inspired by the `pptgen` idea, this fork extends Qratron from plain PDF Q&A into a mini **document-to-insight pipeline**:

- PDF Retrieval-Augmented Q&A with source tracking
- Batch Q&A endpoint for multiple prompts in one request
- Automatic slide-outline generation (JSON + markdown preview) from uploaded PDFs
- Health endpoint for deployment checks

## API Endpoints

### 1) Health Check
`GET /api/v1/health/`

Returns service status.

### 2) Ingest + Q&A (file-based questions)
`POST /api/v1/ingest/`

Multipart form fields:
- `pdf_file`: PDF file
- `questions`: JSON file with key -> question mapping

### 3) Batch Ingest + Q&A (inline JSON)
`POST /api/v1/ingest/batch/`

Multipart form fields:
- `pdf_file`: PDF file
- `questions_json`: JSON string, e.g.

```json
{
  "q1": "What is the main objective?",
  "q2": "List key milestones"
}
```

### 4) Generate Presentation
`POST /api/v1/presentation/`

Multipart form fields:
- `pdf_file`: PDF file
- `title` (optional): presentation title (default: `Qratron Auto Deck`)
- `topic` (optional): guidance prompt for deck focus
- `max_slides` (optional): integer in range 3-15

Returns structured slide JSON and a markdown deck preview that can be passed into a PPT generator frontend/service.

## Getting Started

### Prerequisites

- Python 3.x
- `TOGETHER_API_KEY` environment variable

### Installation

```bash
git clone https://github.com/mit2u/Qratron.git
cd Qratron
pip install -r requirements.txt
```

### Run

```bash
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`


## Local model support (pptgen-style)

Qratron now supports **local OpenAI-compatible model backends** (for example Ollama or LM Studio), similar to local model workflows used in pptgen-style stacks.

Set:
- `QRATRON_PROVIDER=local`
- `QRATRON_LOCAL_BASE_URL=http://localhost:11434/v1`
- `QRATRON_LOCAL_MODEL=llama3.1`

When using local mode, Qratron does not require `TOGETHER_API_KEY` for the chat model client.

## Notes

- LLM and embeddings are currently configured for Together API + LangChain stack.
- If you run into embedding provider auth issues, set the appropriate OpenAI-compatible env vars for `OpenAIEmbeddings`.


## Documentation

- API reference: `docs/API.md`



## Hugging Face Spaces support

Qratron now supports **OpenAI-compatible Hugging Face Space endpoints**.

Set:
- `QRATRON_PROVIDER=hf_space` (or `huggingface_space`)
- `QRATRON_HF_SPACE_BASE_URL=https://<your-space-url>/v1`
- optional: `HF_TOKEN=<your_hf_token>`
- optional: `QRATRON_HF_MODEL=<model-id>`

This is useful when your Space exposes an OpenAI-compatible `/v1` API proxy.

## Deploy on Replit

This repo now includes Replit deployment files (`.replit` and `replit.nix`).

### Steps
1. Create a new Replit project by importing this repository.
2. In **Secrets**, set at least:
   - `TOGETHER_API_KEY` (for remote model mode) OR set local mode vars below.
   - optional: `QRATRON_PROVIDER=local`
   - optional: `QRATRON_LOCAL_BASE_URL=http://localhost:11434/v1`
   - optional: `QRATRON_LOCAL_MODEL=llama3.1`
3. Replit will install dependencies from `requirements.txt`.
4. Run the app. It binds to `0.0.0.0:$PORT` (default `3000`) and auto-runs migrations.

### Replit host/security notes
- `ALLOWED_HOSTS` defaults include `.replit.dev`.
- `CSRF_TRUSTED_ORIGINS` defaults include `https://*.replit.dev`.

