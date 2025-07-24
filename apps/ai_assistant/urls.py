from django.urls import path
from .views import AIAssistantView, AIContentGeneratorView

app_name = 'ai_assistant'

urlpatterns = [
    path('assistant/', AIAssistantView.as_view(), name='assistant'),
    path('generate/', AIContentGeneratorView.as_view(), name='generate_content'),
]