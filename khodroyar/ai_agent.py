import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import openai
import jdatetime
import pytz
from django.conf import settings
from .models import Conversation, Message
from .car_search import get_car_search_service
from .car_features_search import get_car_features_search_service


class KhodroyarAIAgent:
    """AI Agent for Khodroyar chatbot using Aval AI API with GPT-4.1"""
    car_search_service = get_car_search_service()
    car_features_search_service = get_car_features_search_service()

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
        
        # Define available functions for the AI agent
        self.available_functions = [
            {
                "type": "function",
                "function": {
                    "name": "search_car_features",
                    "description": "Search for car features and specifications by car name with similarity matching",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "car_name": {
                                "type": "string",
                                "description": "Name of the car to search for (can be partial or similar)"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "description": "Minimum similarity threshold (0.0 to 1.0, default 0.4)",
                                "default": 0.4
                            }
                        },
                        "required": ["car_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_cars_by_company",
                    "description": "Search for cars by company name with similarity matching",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "Name of the car company to search for"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "description": "Minimum similarity threshold (0.0 to 1.0, default 0.4)",
                                "default": 0.4
                            }
                        },
                        "required": ["company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_cars_by_feature",
                    "description": "Search for cars by specific features or characteristics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "feature_keyword": {
                                "type": "string",
                                "description": "Keyword to search for in car features, specs, advantages, or disadvantages"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "description": "Minimum similarity threshold (0.0 to 1.0, default 0.3)",
                                "default": 0.3
                            }
                        },
                        "required": ["feature_keyword"]
                    }
                }
            }
        ]
    
    def search_car_features(self, car_name: str, similarity_threshold: float = 0.4) -> Dict:
        """
        Function to search for car features by name
        
        Args:
            car_name: Name of the car to search for
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Dictionary with search results
        """
        try:
            results = self.car_features_search_service.search_car_by_name(car_name, similarity_threshold)
            
            if not results:
                return {
                    "success": False,
                    "message": f"هیچ خودرویی با نام '{car_name}' یافت نشد.",
                    "results": []
                }
            
            # Format results for better presentation
            formatted_results = []
            for car in results[:5]:  # Limit to top 5 results
                formatted_car = {
                    "شرکت": car['company'],
                    "نام خودرو": car['car_name'],
                    "نام کامل": car['full_name'],
                    "مشخصات فنی": car['technical_specs'][:200] + "..." if len(car['technical_specs']) > 200 else car['technical_specs'],
                    "مزایا": car['advantages'][:200] + "..." if len(car['advantages']) > 200 else car['advantages'],
                    "معایب": car['disadvantages'][:200] + "..." if len(car['disadvantages']) > 200 else car['disadvantages']
                }
                formatted_results.append(formatted_car)
            
            return {
                "success": True,
                "message": f"نتایج جستجو برای '{car_name}':",
                "results": formatted_results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"خطا در جستجوی خودرو: {str(e)}",
                "results": []
            }
    
    def search_cars_by_company(self, company_name: str, similarity_threshold: float = 0.4) -> Dict:
        """
        Function to search for cars by company
        
        Args:
            company_name: Name of the company to search for
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Dictionary with search results
        """
        try:
            results = self.car_features_search_service.search_cars_by_company(company_name, similarity_threshold)
            
            if not results:
                return {
                    "success": False,
                    "message": f"هیچ خودرویی از شرکت '{company_name}' یافت نشد.",
                    "results": []
                }
            
            # Format results for better presentation
            formatted_results = []
            for car in results[:10]:  # Limit to top 10 results
                formatted_car = {
                    "شرکت": car['company'],
                    "نام خودرو": car['car_name'],
                    "نام کامل": car['full_name'],
                    "مشخصات فنی": car['technical_specs'][:150] + "..." if len(car['technical_specs']) > 150 else car['technical_specs'],
                    "مزایا": car['advantages'][:150] + "..." if len(car['advantages']) > 150 else car['advantages'],
                    "معایب": car['disadvantages'][:150] + "..." if len(car['disadvantages']) > 150 else car['disadvantages']
                }
                formatted_results.append(formatted_car)
            
            return {
                "success": True,
                "message": f"خودروهای شرکت '{company_name}':",
                "results": formatted_results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"خطا در جستجوی شرکت: {str(e)}",
                "results": []
            }
    
    def search_cars_by_feature(self, feature_keyword: str, similarity_threshold: float = 0.3) -> Dict:
        """
        Function to search for cars by features
        
        Args:
            feature_keyword: Keyword to search for in features
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Dictionary with search results
        """
        try:
            results = self.car_features_search_service.search_cars_by_feature(feature_keyword, similarity_threshold)
            
            if not results:
                return {
                    "success": False,
                    "message": f"هیچ خودرویی با ویژگی '{feature_keyword}' یافت نشد.",
                    "results": []
                }
            
            # Format results for better presentation
            formatted_results = []
            for car in results[:8]:  # Limit to top 8 results
                formatted_car = {
                    "شرکت": car['company'],
                    "نام خودرو": car['car_name'],
                    "نام کامل": car['full_name'],
                    "مشخصات فنی": car['technical_specs'][:150] + "..." if len(car['technical_specs']) > 150 else car['technical_specs'],
                    "مزایا": car['advantages'][:150] + "..." if len(car['advantages']) > 150 else car['advantages'],
                    "معایب": car['disadvantages'][:150] + "..." if len(car['disadvantages']) > 150 else car['disadvantages']
                }
                formatted_results.append(formatted_car)
            
            return {
                "success": True,
                "message": f"خودروهای دارای ویژگی '{feature_keyword}':",
                "results": formatted_results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"خطا در جستجوی ویژگی: {str(e)}",
                "results": []
            }
    
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
    
    def _get_current_shamsi_date(self) -> str:
        """
        Get current date in Shamsi (Persian) format
        
        Returns:
            Current date in Persian format
        """
        try:
            # Get current datetime in Tehran timezone and convert to Shamsi
            tehran_tz = pytz.timezone('Asia/Tehran')
            current_datetime = datetime.now(tehran_tz)
            shamsi_datetime = jdatetime.datetime.fromgregorian(datetime=current_datetime)
            
            # Persian month names
            persian_months = {
                1: "فروردین",
                2: "اردیبهشت", 
                3: "خرداد",
                4: "تیر",
                5: "مرداد",
                6: "شهریور",
                7: "مهر",
                8: "آبان",
                9: "آذر",
                10: "دی",
                11: "بهمن",
                12: "اسفند"
            }
            
            # Convert numbers to Persian digits
            persian_digits = {
                '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
                '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
            }
            
            def to_persian_number(num):
                return ''.join(persian_digits[digit] for digit in str(num))
            
            # Format the date in Persian
            day_persian = to_persian_number(shamsi_datetime.day)
            month_name = persian_months[shamsi_datetime.month]
            year_persian = to_persian_number(shamsi_datetime.year)
            
            return f"{day_persian} {month_name} {year_persian}"
            
        except Exception as e:
            print(f"Error getting current date: {str(e)}")
            return "تاریخ نامشخص"
    
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
            
            # Try GPT-4.1 models in order of preference
            gpt4_models = [
                "gpt-4.1",      # Primary GPT-4.1 model
            ]
            
            response = None
            used_model = None
            
            for model in gpt4_models:
                try:
                    # First, try to get a response with function calling
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=self.available_functions,
                        tool_choice="auto",
                        max_tokens=16000,
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
            
            # Check if the AI wants to call a function
            if response.choices[0].message.tool_calls:
                # Handle function calls
                tool_calls = response.choices[0].message.tool_calls
                tool_results = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"AI requested function call: {function_name} with args: {function_args}")
                    
                    # Execute the appropriate function
                    if function_name == "search_car_features":
                        result = self.search_car_features(
                            car_name=function_args.get("car_name"),
                            similarity_threshold=function_args.get("similarity_threshold", 0.4)
                        )
                    elif function_name == "search_cars_by_company":
                        result = self.search_cars_by_company(
                            company_name=function_args.get("company_name"),
                            similarity_threshold=function_args.get("similarity_threshold", 0.4)
                        )
                    elif function_name == "search_cars_by_feature":
                        result = self.search_cars_by_feature(
                            feature_keyword=function_args.get("feature_keyword"),
                            similarity_threshold=function_args.get("similarity_threshold", 0.3)
                        )
                    else:
                        result = {"success": False, "message": f"Unknown function: {function_name}"}
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # Add function results to messages and get final response
                messages.append({
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                    "tool_calls": tool_calls
                })
                messages.extend(tool_results)
                
                # Get final response from AI
                final_response = self.client.chat.completions.create(
                    model=used_model,
                    messages=messages,
                    max_tokens=16000,
                    temperature=0.7,
                    stream=False
                )
                
                ai_response = final_response.choices[0].message.content.strip()
            else:
                # No function calls, return direct response
                ai_response = response.choices[0].message.content.strip()
            
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
        
        # Get current date
        current_date = self._get_current_shamsi_date()
        car_prices_info = self.car_search_service.get_car_prices_for_prompt()
        car_features_summary = self.car_features_search_service.get_car_features_summary()
        print(car_prices_info)
        base_prompt = f"""شما ربات خودرویار هستید، یک دستیار هوشمند برای کمک به کاربران در زمینه انتخاب خودرو صفر و دست دوم جهت خرید بر اساس بودجه . 

وظایف شما:
- پاسخ به سوالات مربوط به خودرو
- کمک در جستجو و مقایسه خودروها
- ارائه اطلاعات قیمت و مشخصات
- راهنمایی جهت بازدید خودرو
- جستجوی مشخصات فنی، مزایا و معایب خودروها

نکات مهم:
- همیشه به فارسی پاسخ دهید
- به هیچ عنوان به سوالات غیر مربوط به خودرو پاسخ ندهید
- همیشه ابتدا بپرسید که خودروی صفر یا دست دوم میخواهد
- اگر کاربر دنبال خودروی صفر بود بودجه کاربر را بپرسید تا خودرو مناسب بودجه پیشنهاد دهید
- اگر کاربر دنبال خودرو دست دوم بود مشخصات خودرویی که مد نظر دارد را بپرسید تا تخمین قیمت ارائه دهید
- از لحن دوستانه و حرفه‌ای استفاده کنید
- در صورت نیاز به اطلاعات بیشتر، سوال بپرسید
- جواب مفید و کوتاه باشد
- بعد اینکه خودرو بر اساس بودجه کاربر معرفی میکنی قیمت خودرو ها هم حتما ذکر کن
- قبل از ارائه قیمت خودروها، حتماً تاریخ فعلی را ذکر کنید
- شما در حال حاضر این امکان را ندارید که آگهی خودرو های دیوار دریافت کنید یا پیشنهاد دهید و از کاربر بخواید که مشخصات خوددرو برای شما توضیح دهد تا قیمت را ارزیابی کنید

قابلیت‌های جستجوی خودرو:
- جستجوی خودرو بر اساس نام (با تطبیق مشابهت)
- جستجوی خودرو بر اساس شرکت سازنده
- جستجوی خودرو بر اساس ویژگی‌های خاص (مثل توربو، هیبرید، و غیره)

اطلاعات قیمت خودروهای صفر:

{car_prices_info}

اطلاعات مشخصات و ویژگی‌های خودروهای صفر:

{car_features_summary}

فرمول محاسبه قیمت خودروهای دست دوم:
P=P0*(1-δA)*(1-δK)*(cond)*(Copt)*(Cbrand)*(Cmarket)
P0: قیمت خودرو صفر
δA:  نرخ استهلاک سالیانه (افت قیمت سال اول ۱۰ درصد، سال دوم تا چهارم هر سال ۵ درصد و بعد چهارسال هر سال ۲ درصد)   مثلا یک خودرو ی ۶ ساله 0.9*0.95*0.95*0.95*0.95*0.98 میشود
δK: نرخ استهلاک کیلومتری (۱ درصد به ازای هر ۱۰ هزارکیلومتر اضافه بر ۲۵ هزار کیلومتری سالیانه) 
Ccond: وضعیت سلامت خودرو. هر قطعه رنگ شدگی ۳ درصد کاهش و رنگ شدگی سقف و یا شاسی ۹ درصد کاهش  هر قطعه تعویض هم ۵ درصد کاهش و تعویض اتاق ۴۰ درصد کاهش. تعویض کاپوت هم ۹ درصد کاهش
Copt: آپشن های خودرو عددی بین 0.9 تا 1.1 معمولا 1
Cbrand: محبوبیت برند خودرو. خودرو های رایج مثل ایران خودرو و سایپا ۱ و برند های کم طرفدار مثل ام جی و جیلی و لیفان ۰.۹
Cmarket:  در اکثر موارد ۱ 

برای پاسخ به سوالات کاربر:
- اگر کاربر بودجه خود را اعلام کرد، از اطلاعات قیمت بالا برای پیدا کردن خودروهای مناسب استفاده کنید
- اگر کاربر قیمت خودروی خاصی را پرسید، از اطلاعات قیمت بالا برای پیدا کردن آن خودرو استفاده کنید
- همیشه قیمت‌ها را به صورت فارسی و خوانا ارائه دهید (مثلاً ۱ میلیارد و ۵۰۰ میلیون تومان)
- اگر کاربر قیمت خودرو دست دوم را پرسید حتما اطلاعات کامل مورد نیاز ( مثل سال، کیلومتر و وضعیت بدنه و شاسی و موتور خودرو) را بپرسید و از فرمول بالا استفاده کنید و فقط قیمت را به صورت بازه ای ۳ درصپ بالای عدد بدست آمده و ۳ درصد پایین عدد بدست آمده را به کاربر بگویید و بگویید بسته به تمیزی و سلامت ماشین در این بازه قرار میگیرد
- جزئیات فرمول محاسبه قیمت خودرو کارکرده را به کاربر توضیح ندهید و فقط بازه بدست آمده را اطلاع بدید

- قبل از ارائه هرگونه اطلاعات قیمت، حتماً تاریخ فعلی را ذکر کنید: {current_date}"""

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