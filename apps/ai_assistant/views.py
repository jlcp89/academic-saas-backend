from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import openai
from django.conf import settings
from django.core.cache import cache
import hashlib

class AIAssistantView(APIView):
    """
    AI Teaching Assistant endpoint that uses OpenAI/Anthropic API
    to provide intelligent responses to student queries.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        message = request.data.get('message', '')
        context = request.data.get('context', 'general')
        
        if not message:
            return Response(
                {'error': 'Message is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check cache for similar questions
        cache_key = f"ai_response_{hashlib.md5(message.encode()).hexdigest()}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return Response({'response': cached_response})
        
        try:
            # Get user's enrolled courses for context
            user = request.user
            if hasattr(user, 'student'):
                enrolled_sections = user.student.enrollments.filter(
                    status='enrolled'
                ).select_related('section__subject')
                
                course_context = "Student is enrolled in: " + ", ".join([
                    f"{e.section.subject.name}" for e in enrolled_sections
                ])
            else:
                course_context = ""
            
            # Prepare the system prompt
            system_prompt = f"""You are an AI teaching assistant for an academic platform. 
            You help students understand course materials, explain concepts, and guide them 
            through assignments. Be encouraging, clear, and educational in your responses.
            
            {course_context}
            
            Context: {context}
            
            Important guidelines:
            - Never directly give answers to assignments or exams
            - Guide students to find answers themselves
            - Explain concepts clearly with examples
            - Be supportive and encouraging
            - If asked about specific course policies, suggest checking with the professor
            """
            
            # Call OpenAI API (or Anthropic)
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            completion = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = completion.choices[0].message.content
            
            # Cache the response for 1 hour
            cache.set(cache_key, ai_response, 3600)
            
            # Log the interaction for analytics
            self._log_interaction(user, message, ai_response)
            
            return Response({'response': ai_response})
            
        except Exception as e:
            return Response(
                {'error': 'Failed to generate response', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _log_interaction(self, user, question, response):
        """Log AI interactions for improvement and analytics"""
        # This could save to a model for later analysis
        pass


class AIContentGeneratorView(APIView):
    """
    Generate educational content like quizzes, flashcards, and summaries
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        content_type = request.data.get('type')  # quiz, flashcard, summary
        source_text = request.data.get('source_text')
        subject = request.data.get('subject')
        difficulty = request.data.get('difficulty', 'medium')
        
        if not all([content_type, source_text]):
            return Response(
                {'error': 'Type and source text are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompts = {
                'quiz': f"""Create a {difficulty} difficulty quiz with 5 multiple choice questions 
                based on this content. Include correct answers and explanations.
                Format as JSON with structure: 
                {{"questions": [{{"question": "", "options": [], "correct": 0, "explanation": ""}}]}}
                
                Content: {source_text}""",
                
                'flashcard': f"""Create 10 flashcards from this content. 
                Format as JSON: {{"cards": [{{"front": "", "back": ""}}]}}
                
                Content: {source_text}""",
                
                'summary': f"""Create a concise summary of this content in bullet points.
                Highlight key concepts and important details.
                
                Content: {source_text}"""
            }
            
            prompt = prompts.get(content_type, '')
            if not prompt:
                return Response(
                    {'error': 'Invalid content type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            completion = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an educational content creator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            generated_content = completion.choices[0].message.content
            
            return Response({
                'type': content_type,
                'content': generated_content,
                'subject': subject
            })
            
        except Exception as e:
            return Response(
                {'error': 'Failed to generate content', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )