from django.contrib import admin
from django.urls import path

from Qratron.views import GeneratePresentation, Health, Ingest, IngestBatch

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', Health.as_view()),
    path('api/v1/ingest/', Ingest.as_view()),
    path('api/v1/ingest/batch/', IngestBatch.as_view()),
    path('api/v1/presentation/', GeneratePresentation.as_view()),
]
