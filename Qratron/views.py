import json
import os
import tempfile

from rest_framework.response import Response
from rest_framework.views import APIView


class Ingest(APIView):

    def post(self, request):
        files = request.FILES
        pdf_file = files.get('pdf_file')
        questions_file =  files.get('questions')
        from langchain_community.document_loaders import PyPDFLoader
        with open('/tmp/ingest.pdf','w+b') as fp :
            bytesio_object = pdf_file.file
            fp.write( bytesio_object.getbuffer() )
            loader = PyPDFLoader( '/tmp/ingest.pdf' )
            docs = loader.load()
            print( len( docs ) )
        questions = json.load(questions_file.file)
        print(questions)

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI( base_url = "https://api.together.xyz/v1" , api_key = os.environ[ "TOGETHER_API_KEY" ] ,
            model = "google/gemma-2-9b-it" , )

        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        text_splitter = RecursiveCharacterTextSplitter( chunk_size = 1000 , chunk_overlap = 200 )
        splits = text_splitter.split_documents( docs )
        vectorstore = Chroma.from_documents( documents = splits , embedding = OpenAIEmbeddings() )

        retriever = vectorstore.as_retriever()
        from langchain.chains import create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain_core.prompts import ChatPromptTemplate

        system_prompt = ("You are an assistant for question-answering tasks. "
                         "Use the following pieces of retrieved context to answer "
                         "the question. If you don't know the answer, say that you "
                         "don't know. Use three sentences maximum and keep the "
                         "answer concise."
                         "\n\n"
                         "{context}")

        prompt = ChatPromptTemplate.from_messages( [ ("system" , system_prompt) , ("human" , "{input}") , ] )

        question_answer_chain = create_stuff_documents_chain( llm , prompt )
        rag_chain = create_retrieval_chain( retriever , question_answer_chain )
        results = {}
        for question in questions :
            results[question] = rag_chain.invoke( { "input" : questions[question] } )['answer']

        return Response(results,content_type = 'application/json')
