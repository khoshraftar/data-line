import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import openai
from django.conf import settings
from .models import Conversation, Message
from .car_search import get_car_search_service


class KhodroyarAIAgent:
    """AI Agent for Khodroyar chatbot using Aval AI API with GPT-4.1"""
    
    def __init__(self):
        """Initialize the AI agent with Aval AI configuration"""
        self.base_url = settings.AVAL_AI_BASE_URL
        self.api_key = settings.AVAL_AI_API_KEY
        
        if not self.api_key:
            raise ValueError("AVAL_AI_API_KEY is not configured in environment variables")
        
        # Configure OpenAI client for Aval AI
        # Try different initialization approaches
        try:
            # First try with minimal configuration
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            print(f"Failed to initialize OpenAI client with base_url: {e}")
            # Fallback to standard OpenAI client
            self.client = openai.OpenAI(
                api_key=self.api_key
            )
            print("Using standard OpenAI client as fallback")
        
        # Initialize car search service
        self.car_search_service = get_car_search_service()
        
        # Define available functions for the AI
        self.available_functions = [
            {
                "type": "function",
                "function": {
                    "name": "search_cars_by_budget",
                    "description": "جستجوی خودروها بر اساس بودجه کاربر (۵٪ بالاتر تا ۱۰٪ پایین‌تر از بودجه)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "budget": {
                                "type": "integer",
                                "description": "بودجه کاربر به تومان"
                            }
                        },
                        "required": ["budget"]
                    }
                }
            }
        ]
    
    def get_conversation_history(self, conversation: Conversation, max_messages: int = 50) -> List[Dict]:
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
    
    def _call_function(self, function_name: str, arguments: Dict) -> str:
        """
        Call the specified function with given arguments
        
        Args:
            function_name: Name of the function to call
            arguments: Function arguments
            
        Returns:
            Function result as string
        """
        try:
            if function_name == "search_cars_by_budget":
                budget = arguments.get("budget")
                
                cars = self.car_search_service.search_cars_by_budget(budget)
                
                if not cars:
                    return f"متأسفانه هیچ خودرویی در محدوده بودجه {self.car_search_service._format_price(budget)} یافت نشد."
                
                result = f"با بودجه {self.car_search_service._format_price(budget)}، {len(cars)} خودرو پیدا شد:\n\n"
                
                for i, car in enumerate(cars[:10], 1):  # Show top 10 results
                    result += f"{i}. {car['car_name']} - {car['price_formatted']}\n"
                
                if len(cars) > 10:
                    result += f"\nو {len(cars) - 10} خودروی دیگر..."
                
                return result
                
            else:
                return f"تابع {function_name} شناخته نشد."
                
        except Exception as e:
            print(f"Error calling function {function_name}: {str(e)}")
            return f"خطا در اجرای تابع {function_name}: {str(e)}"
    
    def generate_response(
        self, 
        user_message: str, 
        conversation: Conversation,
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Generate AI response for user message using GPT-4.1 with function calling
        
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
            
            print(f"Calling Aval AI API with base_url: {self.base_url}")
            print(f"Messages to send: {messages}")
            
            # Try GPT-4.1 models in order of preference
            gpt4_models = [
                "gpt-4.1",  # Primary GPT-4.1 model
            ]
            
            response = None
            used_model = None
            
            for model in gpt4_models:
                try:
                    print(f"Trying model: {model}")
                    
                    # First call - check if function calling is needed
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=self.available_functions,
                        tool_choice="auto",
                        max_tokens=15000,
                        temperature=0.7,
                        stream=False
                    )
                    
                    used_model = model
                    print(f"Successfully used model: {model}")
                    break
                    
                except Exception as model_error:
                    print(f"Failed with {model}: {model_error}")
                    continue
            
            if response is None:
                raise Exception("All GPT models failed to respond")
            
            # Check if function calling is needed
            if response.choices[0].message.tool_calls:
                # Handle function calls
                tool_calls = response.choices[0].message.tool_calls
                function_results = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"Calling function: {function_name} with args: {function_args}")
                    
                    # Call the function
                    function_result = self._call_function(function_name, function_args)
                    function_results.append(function_result)
                
                # Add function results to messages and get final response
                messages.append(response.choices[0].message)
                
                for i, tool_call in enumerate(tool_calls):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_results[i]
                    })
                
                # Get final response from AI
                final_response = self.client.chat.completions.create(
                    model=used_model,
                    messages=messages,
                    max_tokens=15000,
                    temperature=0.7,
                    stream=False
                )
                
                ai_response = final_response.choices[0].message.content.strip()
                
            else:
                # No function calling needed
                ai_response = response.choices[0].message.content.strip()
            
            # Log the interaction for debugging
            self._log_interaction(conversation, user_message, ai_response, messages, used_model)
            
            return ai_response
            
        except Exception as e:
            error_msg = f"متأسفانه مشکلی در پردازش پیام شما پیش آمد. لطفاً دوباره تلاش کنید."
            print(f"AI Agent Error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return error_msg
    
    def _build_system_prompt(self, user_context: Optional[Dict] = None) -> str:
        """
        Build system prompt for the AI agent
        
        Args:
            user_context: User context information
            
        Returns:
            System prompt string
        """
        base_prompt = """شما ربات خودرویار هستید، یک دستیار هوشمند برای کمک به کاربران در زمینه انتخاب خودرو جهت خرید بر اساس بودجه . 

وظایف شما:
- پاسخ به سوالات مربوط به خودرو
- کمک در جستجو و مقایسه خودروها
- ارائه اطلاعات قیمت و مشخصات
- راهنمایی در خرید خودرو
- پاسخ به سوالات فنی خودرو

نکات مهم:
- همیشه ابتدا بودجه کاربر را بپرسید
- همیشه به فارسی پاسخ دهید
- از لحن دوستانه و حرفه‌ای استفاده کنید
- در صورت نیاز به اطلاعات بیشتر، سوال بپرسید
- جواب مفید و کوتاه باشد
- بعد اینکه خودرو بر اساس بودجه کاربر معرفی میکنی قیمت خودرو ها هم حتما ذکر کن

برای جستجوی خودرو بر اساس بودجه، از تابع search_cars_by_budget استفاده کنید:
- این تابع خودروهایی را که ۵٪ بالاتر تا ۱۰٪ پایین‌تر از بودجه کاربر هستند، برمی‌گرداند
- بودجه را به تومان دریافت کنید (مثلاً 500 میلیون تومان = 500000000 تومان)

اگر کاربر بودجه خود را اعلام کرد، حتماً از این تابع برای جستجوی خودرو استفاده کنید و نتایج را به صورت مفید و منظم ارائه دهید."""

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
        messages: List[Dict],
        used_model: str = None
    ):
        """
        Log AI interaction for debugging and monitoring
        
        Args:
            conversation: Conversation object
            user_message: Original user message
            ai_response: AI generated response
            messages: Full message history sent to AI
            used_model: The model that was successfully used
        """
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "conversation_id": conversation.conversation_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "message_count": len(messages),
                "user_id": conversation.user_auth.user_id,
                "used_model": used_model
            }
            
            # You can extend this to save to database or external logging service
            print(f"AI Interaction Log: {json.dumps(log_data, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"Error logging AI interaction: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test connection to Aval AI API with GPT-4.1
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try GPT-4.1 first, then fallback to other models
            gpt4_models = ["gpt-4.1", "gpt-4.1-turbo", "gpt-4", "gpt-3.5-turbo"]
            
            for model in gpt4_models:
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "سلام"}],
                        max_tokens=10
                    )
                    print(f"Connection test successful with model: {model}")
                    return True
                except Exception as e:
                    print(f"Connection test failed with {model}: {e}")
                    continue
            
            return False
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