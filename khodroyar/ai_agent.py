import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import openai
from django.conf import settings
from .models import Conversation, Message


class KhodroyarAIAgent:
    """AI Agent for Khodroyar chatbot using Aval AI API"""
    
    def __init__(self):
        """Initialize the AI agent with Aval AI configuration"""
        self.base_url = settings.AVAL_AI_BASE_URL
        self.api_key = settings.AVAL_AI_API_KEY
        
        if not self.api_key:
            raise ValueError("AVAL_AI_API_KEY is not configured in environment variables")
        
        # Configure OpenAI client for Aval AI
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def get_conversation_history(self, conversation: Conversation, max_messages: int = 10) -> List[Dict]:
        """
        Get conversation history for context
        
        Args:
            conversation: Conversation object
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of message dictionaries for AI context
        """
        messages = conversation.messages.order_by('-created_at')[:max_messages]
        history = []
        
        for message in reversed(messages):  # Reverse to get chronological order
            role = "user" if message.message_type == "user" else "assistant"
            history.append({
                "role": role,
                "content": message.content
            })
        
        return history
    
    def generate_response(
        self, 
        user_message: str, 
        conversation: Conversation,
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Generate AI response for user message
        
        Args:
            user_message: The user's message
            conversation: Conversation object for context
            user_context: Additional user context (subscription info, etc.)
            
        Returns:
            Generated AI response
        """
        try:
            # Get conversation history
            conversation_history = self.get_conversation_history(conversation)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(user_context)
            
            # Prepare messages for AI
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Call Aval AI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # You can change this based on available models
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=False
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Log the interaction for debugging
            self._log_interaction(conversation, user_message, ai_response, messages)
            
            return ai_response
            
        except Exception as e:
            error_msg = f"متأسفانه مشکلی در پردازش پیام شما پیش آمد. لطفاً دوباره تلاش کنید."
            print(f"AI Agent Error: {str(e)}")
            return error_msg
    
    def _build_system_prompt(self, user_context: Optional[Dict] = None) -> str:
        """
        Build system prompt for the AI agent
        
        Args:
            user_context: User context information
            
        Returns:
            System prompt string
        """
        base_prompt = """شما ربات خودرویار هستید، یک دستیار هوشمند برای کمک به کاربران در زمینه خودرو. 

وظایف شما:
- پاسخ به سوالات مربوط به خودرو
- کمک در جستجو و مقایسه خودروها
- ارائه اطلاعات قیمت و مشخصات
- راهنمایی در خرید خودرو
- پاسخ به سوالات فنی خودرو

نکات مهم:
- همیشه به فارسی پاسخ دهید
- پاسخ‌های مفید و دقیق ارائه دهید
- اگر اطلاعات کافی ندارید، صادقانه بگویید
- از لحن دوستانه و حرفه‌ای استفاده کنید
- در صورت نیاز به اطلاعات بیشتر، سوال بپرسید"""

        # Add user context if available
        if user_context:
            context_info = []
            if user_context.get('subscription_end'):
                context_info.append(f"اشتراک کاربر تا {user_context['subscription_end']} فعال است")
            if user_context.get('plan_name'):
                context_info.append(f"نوع اشتراک: {user_context['plan_name']}")
            
            if context_info:
                base_prompt += f"\n\nاطلاعات کاربر:\n" + "\n".join(context_info)
        
        return base_prompt
    
    def _log_interaction(
        self, 
        conversation: Conversation, 
        user_message: str, 
        ai_response: str, 
        messages: List[Dict]
    ):
        """
        Log AI interaction for debugging and monitoring
        
        Args:
            conversation: Conversation object
            user_message: Original user message
            ai_response: AI generated response
            messages: Full message history sent to AI
        """
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "conversation_id": conversation.conversation_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "message_count": len(messages),
                "user_id": conversation.user_auth.user_id
            }
            
            # You can extend this to save to database or external logging service
            print(f"AI Interaction Log: {json.dumps(log_data, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"Error logging AI interaction: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test connection to Aval AI API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "سلام"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            print(f"AI API Connection Test Failed: {str(e)}")
            return False


# Global AI agent instance
_ai_agent = None

def get_ai_agent() -> KhodroyarAIAgent:
    """
    Get or create global AI agent instance
    
    Returns:
        KhodroyarAIAgent instance
    """
    global _ai_agent
    if _ai_agent is None:
        _ai_agent = KhodroyarAIAgent()
    return _ai_agent 