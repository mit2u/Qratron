import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from Qratron.services import (
    LLMConfig,
    ServiceError,
    get_llm,
    normalize_questions,
    parse_slides_json,
    render_markdown_slides,
)


class QaApiTests(TestCase):

    def test_health(self):
        response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    @patch('Qratron.views.answer_questions')
    @patch('Qratron.views.load_pdf_docs')
    def test_ingest_batch(self, mock_load_pdf_docs, mock_answer_questions):
        mock_load_pdf_docs.return_value = ['doc']
        mock_answer_questions.return_value = {
            'q1': {'question': 'What?', 'answer': 'Answer', 'sources': ['/tmp/a.pdf']}
        }

        payload = {
            'pdf_file': SimpleUploadedFile('test.pdf', b'%PDF-test', content_type='application/pdf'),
            'questions_json': json.dumps({'q1': 'What?'}),
        }

        response = self.client.post('/api/v1/ingest/batch/', data=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 1)
        self.assertIn('q1', body['results'])

    def test_ingest_batch_rejects_bad_json(self):
        payload = {
            'pdf_file': SimpleUploadedFile('test.pdf', b'%PDF-test', content_type='application/pdf'),
            'questions_json': '{bad json}',
        }
        response = self.client.post('/api/v1/ingest/batch/', data=payload)
        self.assertEqual(response.status_code, 400)

    @patch('Qratron.views.build_slide_plan')
    @patch('Qratron.views.load_pdf_docs')
    def test_generate_presentation(self, mock_load_pdf_docs, mock_build_slide_plan):
        mock_load_pdf_docs.return_value = ['doc']
        mock_build_slide_plan.return_value = {
            'title': 'Demo deck',
            'slides': [{'title': 'One', 'bullets': ['A', 'B']}],
        }

        payload = {
            'pdf_file': SimpleUploadedFile('test.pdf', b'%PDF-test', content_type='application/pdf'),
            'title': 'Demo deck',
            'topic': 'Summarize',
            'max_slides': '5',
        }
        response = self.client.post('/api/v1/presentation/', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slide_count'], 1)


class SlideUtilityTests(TestCase):

    def test_parse_and_render_markdown(self):
        raw = json.dumps(
            {
                'title': 'Roadmap',
                'slides': [
                    {'title': 'Goal', 'bullets': ['Ship MVP', 'Measure usage']},
                    {'title': 'Plan', 'bullets': ['Week 1', 'Week 2']},
                ],
            }
        )
        plan = parse_slides_json(raw, fallback_title='Fallback')
        markdown = render_markdown_slides(plan)

        self.assertEqual(plan['title'], 'Roadmap')
        self.assertIn('# Roadmap', markdown)
        self.assertIn('## Slide 1: Goal', markdown)

    def test_parse_with_code_fence(self):
        raw = '```json\n{"title":"T","slides":[]}\n```'
        plan = parse_slides_json(raw, fallback_title='Fallback')
        self.assertEqual(plan['title'], 'T')

    def test_normalize_questions(self):
        self.assertEqual(normalize_questions(['A', 'B']), {'q1': 'A', 'q2': 'B'})
        with self.assertRaises(ServiceError):
            normalize_questions('bad')


class LLMConfigTests(TestCase):

    @patch('Qratron.services.ChatOpenAI')
    def test_get_llm_uses_local_provider_without_api_key(self, mock_chat):
        cfg = LLMConfig(provider='local')
        get_llm(cfg)
        kwargs = mock_chat.call_args.kwargs
        self.assertEqual(kwargs['base_url'], 'http://localhost:11434/v1')
        self.assertEqual(kwargs['api_key'], 'local')


    @patch('Qratron.services.ChatOpenAI')
    @patch.dict('os.environ', {'QRATRON_HF_SPACE_BASE_URL': 'https://demo-space.example.com/v1', 'HF_TOKEN': 'hf_test'})
    def test_get_llm_hf_space_provider(self, mock_chat):
        cfg = LLMConfig(provider='hf_space', model='meta-llama/Llama-3.1-8B-Instruct')
        get_llm(cfg)
        kwargs = mock_chat.call_args.kwargs
        self.assertEqual(kwargs['base_url'], 'https://demo-space.example.com/v1')
        self.assertEqual(kwargs['api_key'], 'hf_test')

    @patch.dict('os.environ', {}, clear=True)
    def test_get_llm_hf_space_missing_base_url(self):
        cfg = LLMConfig(provider='huggingface_space')
        with self.assertRaises(ServiceError):
            get_llm(cfg)

    @patch.dict('os.environ', {}, clear=True)
    def test_get_llm_missing_remote_api_key(self):
        cfg = LLMConfig(provider='together', api_key_env='TOGETHER_API_KEY')
        with self.assertRaises(ServiceError):
            get_llm(cfg)
