# Qratron API Guide

This document describes the consolidated API for PDF Q&A and presentation planning.

## Endpoints

## `GET /api/v1/health/`
Returns service status.

**Response**
```json
{
  "status": "ok",
  "service": "qratron"
}
```

## `POST /api/v1/ingest/`
Single upload + JSON file questions.

**Multipart fields**
- `pdf_file` *(required)*
- `questions` *(required JSON file: object or array)*

## `POST /api/v1/ingest/batch/`
Single upload + inline JSON questions.

**Multipart fields**
- `pdf_file` *(required)*
- `questions_json` *(required JSON string: object or array)*

**Example `questions_json` values**
```json
{"q1": "What is the goal?", "q2": "What risks are mentioned?"}
```
or
```json
["What is the goal?", "What risks are mentioned?"]
```

## `POST /api/v1/presentation/`
Generates a pptgen-style plan from PDF context.

**Multipart fields**
- `pdf_file` *(required)*
- `title` *(optional, default `Qratron Auto Deck`)*
- `topic` *(optional, default `Summarize this document`)*
- `max_slides` *(optional int, clamped to `3..15`)*

**Response**
```json
{
  "title": "Roadmap",
  "slide_count": 4,
  "slides": [
    {"title": "Problem", "bullets": ["...", "..."]}
  ],
  "markdown_preview": "# Roadmap\n\n## Slide 1: Problem\n- ..."
}
```

## Error behavior
- `400` for validation/JSON errors.
- `502` for upstream/service failures (LLM/API key/vector processing).

## Environment variables
- `QRATRON_PROVIDER` *(default `together`; set to `local` / `ollama` / `lmstudio` for local mode)*
- `TOGETHER_API_KEY` *(required by default remote mode)*
- `QRATRON_API_KEY_ENV` *(override which key env var is read in remote mode)*
- `QRATRON_LLM_BASE_URL` *(override remote model gateway URL)*
- `QRATRON_MODEL` *(override remote chat model identifier)*
- `QRATRON_EMBEDDING_MODEL` *(override remote embedding model identifier)*
- `QRATRON_LOCAL_BASE_URL` *(default `http://localhost:11434/v1`)*
- `QRATRON_LOCAL_MODEL` *(default `llama3.1`)*
- `QRATRON_LOCAL_EMBEDDING_MODEL` *(default `nomic-embed-text`)*
- `QRATRON_HF_SPACE_BASE_URL` *(required for `hf_space` provider, OpenAI-compatible `/v1` URL)*
- `QRATRON_HF_MODEL` *(optional Hugging Face chat model id override)*
- `QRATRON_HF_EMBEDDING_MODEL` *(optional Hugging Face embedding model id override)*
- `HF_TOKEN` *(optional Hugging Face token; defaults to `hf`)*

### Local mode example
```bash
export QRATRON_PROVIDER=local
export QRATRON_LOCAL_BASE_URL=http://localhost:11434/v1
export QRATRON_LOCAL_MODEL=llama3.1
python manage.py runserver
```


## Replit deployment quickstart
- Import repo into Replit.
- Ensure secrets are configured (`TOGETHER_API_KEY` for remote provider, or local provider vars).
- Run button starts Django on `0.0.0.0:$PORT`.
- Migrations are executed in Replit deployment run command.


### Hugging Face Space mode example
```bash
export QRATRON_PROVIDER=hf_space
export QRATRON_HF_SPACE_BASE_URL=https://your-space.hf.space/v1
export HF_TOKEN=hf_xxx
python manage.py runserver
```
