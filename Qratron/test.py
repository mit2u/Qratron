from django.test import TestCase


class QaTest(TestCase):

    def test_qa(self):
        url = "/api/v1/ingest/"

        payload = { }
        payload = {'pdf_file' : open( 'Qratron/fixtures/resume.pdf' , 'rb' ),
            'questions': open( 'Qratron/fixtures/questions.json' , 'rb' )  }

        response = self.client.post(url , data = payload  )
        json_r = response.json()
        print(json_r  )

        self.assertEqual(response.status_code, 200)


