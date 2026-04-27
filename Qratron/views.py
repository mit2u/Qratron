import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Qratron.services import (
    ServiceError,
    answer_questions,
    build_slide_plan,
    load_pdf_docs,
    normalize_questions,
    render_markdown_slides,
)


def _error(message: str, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


class Health(APIView):

    def get(self, request):
        return Response({"status": "ok", "service": "qratron"})


class Ingest(APIView):

    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        questions_file = request.FILES.get("questions")

        if not pdf_file or not questions_file:
            return _error("Both pdf_file and questions are required.")

        try:
            questions = normalize_questions(json.load(questions_file.file))
            docs = load_pdf_docs(pdf_file)
            results = answer_questions(docs=docs, questions=questions)
        except json.JSONDecodeError:
            return _error("questions file must contain valid JSON.")
        except ServiceError as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)

        return Response(results, content_type="application/json")


class IngestBatch(APIView):

    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            return _error("pdf_file is required.")

        questions_json = request.data.get("questions_json")
        if not questions_json:
            return _error("questions_json field is required and must be valid JSON.")

        try:
            questions = normalize_questions(json.loads(questions_json))
            docs = load_pdf_docs(pdf_file)
            results = answer_questions(docs=docs, questions=questions)
        except json.JSONDecodeError:
            return _error("questions_json is not valid JSON.")
        except ServiceError as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)

        return Response({"count": len(results), "results": results}, content_type="application/json")


class GeneratePresentation(APIView):

    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            return _error("pdf_file is required.")

        title = request.data.get("title", "Qratron Auto Deck")
        topic = request.data.get("topic", "Summarize this document")

        try:
            max_slides = int(request.data.get("max_slides", 6))
        except ValueError:
            return _error("max_slides must be an integer.")

        max_slides = min(max(max_slides, 3), 15)

        try:
            docs = load_pdf_docs(pdf_file)
            plan = build_slide_plan(docs=docs, topic=topic, max_slides=max_slides, title=title)
            markdown = render_markdown_slides(plan)
        except ServiceError as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "title": plan.get("title", title),
                "slide_count": len(plan.get("slides", [])),
                "slides": plan.get("slides", []),
                "markdown_preview": markdown,
            },
            content_type="application/json",
        )
