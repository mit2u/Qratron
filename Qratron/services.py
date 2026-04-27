import json
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Iterable

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_QA_PROMPT = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer the question. "
    "If you don't know the answer, say that you don't know. "
    "Use three sentences maximum and keep the answer concise.\n\n{context}"
)

SLIDES_PROMPT = (
    "You are a presentation architect. Build a concise slide outline as JSON. "
    "Return a JSON object with exactly this shape: "
    "{'title': str, 'slides': [{'title': str, 'bullets': [str, ... up to 5]}]}. "
    "Use at most {max_slides} slides and do not include markdown fences. "
    "Topic hint: {topic}.\n\nContext:\n{context}"
)


class ServiceError(Exception):
    """Raised when service-level processing fails."""


@dataclass
class LLMConfig:
    provider: str = os.getenv("QRATRON_PROVIDER", "together")
    model: str = os.getenv("QRATRON_MODEL", "google/gemma-2-9b-it")
    base_url: str = os.getenv("QRATRON_LLM_BASE_URL", "https://api.together.xyz/v1")
    api_key_env: str = os.getenv("QRATRON_API_KEY_ENV", "TOGETHER_API_KEY")


def _is_local_provider(provider: str) -> bool:
    return provider.lower() in {"local", "ollama", "lmstudio"}


def _is_hf_space_provider(provider: str) -> bool:
    return provider.lower() in {"huggingface_space", "hf_space", "huggingface"}


def get_llm(config: LLMConfig | None = None) -> ChatOpenAI:
    config = config or LLMConfig()

    if _is_local_provider(config.provider):
        local_url = os.getenv("QRATRON_LOCAL_BASE_URL", "http://localhost:11434/v1")
        local_model = os.getenv("QRATRON_LOCAL_MODEL", "llama3.1")
        return ChatOpenAI(base_url=local_url, api_key="local", model=local_model)

    if _is_hf_space_provider(config.provider):
        hf_base_url = os.getenv("QRATRON_HF_SPACE_BASE_URL")
        if not hf_base_url:
            raise ServiceError("Missing QRATRON_HF_SPACE_BASE_URL for Hugging Face Spaces provider.")

        hf_model = os.getenv("QRATRON_HF_MODEL", config.model)
        hf_token = os.getenv("HF_TOKEN", "hf")
        return ChatOpenAI(base_url=hf_base_url, api_key=hf_token, model=hf_model)

    api_key = os.getenv(config.api_key_env)
    if not api_key:
        raise ServiceError(f"Missing API key environment variable: {config.api_key_env}")

    return ChatOpenAI(base_url=config.base_url, api_key=api_key, model=config.model)


def load_pdf_docs(pdf_file):
    from langchain_community.document_loaders import PyPDFLoader

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as fp:
        fp.write(pdf_file.file.getbuffer())
        path = fp.name

    try:
        docs = PyPDFLoader(path).load()
    finally:
        if os.path.exists(path):
            os.remove(path)

    return docs


def _build_retriever(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
    return vectorstore.as_retriever()


def normalize_questions(questions: dict | list) -> dict[str, str]:
    if isinstance(questions, dict):
        return {str(key): str(value) for key, value in questions.items() if str(value).strip()}

    if isinstance(questions, list):
        normalized = {}
        for index, question in enumerate(questions, start=1):
            text = str(question).strip()
            if text:
                normalized[f"q{index}"] = text
        return normalized

    raise ServiceError("Questions payload must be an object or an array of strings.")


def answer_questions(docs, questions: dict[str, str], system_prompt: str | None = None):
    retriever = _build_retriever(docs)
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt or DEFAULT_QA_PROMPT), ("human", "{input}")]
    )

    qa_chain = create_stuff_documents_chain(get_llm(), prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    results = {}
    for key, question in questions.items():
        raw = rag_chain.invoke({"input": question})
        context = raw.get("context", [])
        sources = sorted(
            {
                item.metadata.get("source")
                for item in context
                if getattr(item, "metadata", None) and item.metadata.get("source")
            }
        )
        results[key] = {
            "question": question,
            "answer": raw.get("answer", ""),
            "sources": sources,
        }
    return results


def _extract_json_fragment(text: str) -> str:
    candidate = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", candidate)
    if not match:
        raise ServiceError("Slide generator did not return valid JSON.")

    return match.group(0)


def parse_slides_json(text: str, fallback_title: str) -> dict:
    cleaned = _extract_json_fragment(text)
    parsed = json.loads(cleaned)
    slides = parsed.get("slides", [])

    safe_slides = []
    for slide in slides:
        title = str(slide.get("title", "Untitled")).strip()[:120]
        bullets = [str(b).strip()[:220] for b in slide.get("bullets", []) if str(b).strip()]
        safe_slides.append({"title": title or "Untitled", "bullets": bullets[:5]})

    return {"title": str(parsed.get("title") or fallback_title)[:120], "slides": safe_slides}


def build_slide_plan(docs, topic: str, max_slides: int, title: str):
    retriever = _build_retriever(docs)
    context_docs = retriever.invoke(topic)
    context_blob = "\n\n".join(doc.page_content for doc in context_docs[:12])
    prompt = SLIDES_PROMPT.format(max_slides=max_slides, topic=topic, context=context_blob)
    response = get_llm().invoke(prompt)
    return parse_slides_json(response.content, fallback_title=title)


def render_markdown_slides(plan: dict) -> str:
    lines = [f"# {plan.get('title', 'Auto Presentation')}", ""]
    slides: Iterable[dict] = plan.get("slides", [])
    for index, slide in enumerate(slides, start=1):
        lines.append(f"## Slide {index}: {slide.get('title', 'Untitled')}")
        for bullet in slide.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines)
