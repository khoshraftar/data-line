import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import openai
import jdatetime
import pytz
from django.conf import settings
from .models import Conversation, Message
from .car_search import get_car_search_service
from .car_details_service import get_car_details_service

# Configure logging for function calls
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only output to stdout
    ]
)
logger = logging.getLogger('khodroyar_function_calls')


class KhodroyarAIAgent:
    """AI Agent for Khodroyar chatbot using Aval AI API with GPT-4.1"""
    car_search_service = get_car_search_service()
    car_details_service = get_car_details_service()

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
            
            # Define available functions
            functions = [
                {
                    "name": "calculate_used_car_price",
                    "description": "Calculate used car price based on age, kilometers, and damages",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_price": {
                                "type": "number",
                                "description": "Original car price in tomans"
                            },
                            "car_age": {
                                "type": "integer",
                                "description": "Car age in years"
                            },
                            "car_kilometers": {
                                "type": "integer",
                                "description": "Total kilometers driven"
                            },
                            "damages": {
                                "type": "array",
                                "description": "List of car damages",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["paint", "replacement", "body_replacement", "hood_replacement"],
                                            "description": "Type of damage"
                                        },
                                        "part": {
                                            "type": "string",
                                            "description": "Part name"
                                        },
                                        "severity": {
                                            "type": "string",
                                            "enum": ["minor", "major"],
                                            "description": "Severity for paint damage"
                                        }
                                    },
                                    "required": ["type"]
                                }
                            }
                        },
                        "required": ["base_price", "car_age", "car_kilometers", "damages"]
                    }
                },
                {
                    "name": "get_car_details",
                    "description": "Get detailed information about a specific car model, including technical specifications, pros and cons using similarity search from car details database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "car_name": {
                                "type": "string",
                                "description": "Full car name to search for (e.g., 'پژو 207', 'دنا پلاس', 'سورن پلاس', 'لاماری ایما')"
                            }
                        },
                        "required": ["car_name"]
                    }
                }
            ]
            
            # Prepare messages for AI
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Try GPT-4.1 models in order of preference
            gpt_models = [
                "gpt-4.1",      # Primary GPT-4.1 model
            ]
            
            response = None
            used_model = None
            
            for model in gpt_models:
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        functions=functions,
                        function_call="auto",
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
            
            # Check if function call was requested
            if response.choices[0].message.function_call:
                function_call = response.choices[0].message.function_call
                
                # Log function call attempt
                logger.info(f"Function call requested: {function_call.name}")
                logger.info(f"User message: {user_message}")
                logger.info(f"Conversation ID: {conversation.id}")
                
                if function_call.name == "calculate_used_car_price":
                    # Parse function arguments
                    function_args = json.loads(function_call.arguments)
                    
                    # Log function parameters
                    logger.info(f"Function parameters: {json.dumps(function_args, ensure_ascii=False, indent=2)}")
                    
                    try:
                        # Call the function
                        result = self.calculate_used_car_price(
                            base_price=function_args["base_price"],
                            car_age=function_args["car_age"],
                            car_kilometers=function_args["car_kilometers"],
                            damages=function_args["damages"]
                        )
                        
                    except Exception as func_error:
                        logger.error(f"Function execution failed: {str(func_error)}")
                        raise func_error
                    
                    # Add function result to messages
                    messages.append({
                        "role": "function",
                        "name": "calculate_used_car_price",
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
                    # Get final response from AI
                    final_response = self.client.chat.completions.create(
                        model=used_model,
                        messages=messages,
                        max_tokens=16000,
                        temperature=0.7,
                        stream=False
                    )
                    
                    ai_response = final_response.choices[0].message.content.strip()
                    
                elif function_call.name == "get_car_details":
                    # Parse function arguments
                    function_args = json.loads(function_call.arguments)
                    
                    # Log function parameters
                    logger.info(f"Function parameters: {json.dumps(function_args, ensure_ascii=False, indent=2)}")
                    
                    try:
                        # Call the function
                        result = self.car_details_service.get_car_details_and_pros_cons(
                            car_name=function_args["car_name"]
                        )
                        
                    except Exception as func_error:
                        logger.error(f"Function execution failed: {str(func_error)}")
                        raise func_error
                    
                    # Add function result to messages
                    messages.append({
                        "role": "function",
                        "name": "get_car_details",
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
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
                    # Unknown function call
                    logger.warning(f"Unknown function call requested: {function_call.name}")
                    ai_response = "متأسفانه تابع درخواستی پشتیبانی نمی‌شود."
            else:
                # No function call, get direct response
                logger.info("No function call requested - direct response generated")
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
        print(car_prices_info)
        base_prompt = f"""شما ربات خودرویار هستید، یک دستیار هوشمند برای کمک به کاربران در زمینه انتخاب خودرو صفر و دست دوم جهت خرید بر اساس بودجه . 

وظایف شما:
- پاسخ به سوالات مربوط به خودرو
- کمک در جستجو و مقایسه خودروها
- ارائه اطلاعات قیمت و مشخصات

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
- شما در حال حاضر این امکان را ندارید که آگهی خودرو های دیوار دریافت کنید یا پیشنهاد دهید و از کاربر بخواید که مشخصات خوددرو برای شما توضیح دهد تا قیمت را ارزیابی کنید
- خودرو های سایپا کم خرج تر از ایران خودرو هستند و برای مسافر کشی و اسنپ مناسب تر هستند
- در صورتی که از یک اسم چندین مدل خودرو وجود داشت مثل سورن از کاربر بپرسید که به دنبال کدام مدل هست
- اگر به خودرویی اشاره کرد که در لیست قیمت صفر نیست نزدیک ترین خودرو رو به کاربر نشون بده و بپرس که این خودرو مد نظرشه یا نه

اطلاعات قیمت خودروهای صفر:

{car_prices_info}

برای محاسبه قیمت خودروهای دست دوم:
- از تابع calculate_used_car_price استفاده کنید
- این تابع فرمول دقیق محاسبه قیمت خودروهای دست دوم را پیاده‌سازی کرده است
- ورودی‌های مورد نیاز: قیمت پایه (قیمت خودرو صفر)، سن خودرو (سال)، کیلومتر، لیست آسیب‌ها
- خروجی: قیمت نهایی

نحوه استفاده از تابع calculate_used_car_price:
1. قیمت پایه خودرو صفر را از لیست بالا پیدا کنید
2.  سن خودرو (سال) را مشخص کنید
3. کیلومتر خودرو را وارد کنید
4. لیست آسیب‌ها را به صورت زیر تعریف کنید:
   - رنگ شدگی: {{'type': 'paint', 'part': 'نام قطعه', 'severity': 'minor/major'}}
   - تعویض قطعه: {{'type': 'replacement', 'part': 'نام قطعه'}}
   - تعویض اتاق: {{'type': 'body_replacement', 'part': 'نام قطعه'}}
   - تعویض کاپوت: {{'type': 'hood_replacement', 'part': 'hood'}}
5. تابع قیمت نهایی را محاسبه می‌کند


فقط برای دریافت اطلاعات فنی و مشخصات خودرو (مشخصات فنی، مزایا و معایب):
- از تابع get_car_details استفاده کنید
- این تابع با جستجوی اطلاعات کامل خودرو را از پایگاه داده پیدا می‌کند
- ورودی مورد نیاز: نام کامل خودرو (مثل 'پژو 207 دنده‌ای هیدرولیک')
- خروجی: مشخصات فنی، مزایا، معایب و اطلاعات کامل خودرو

نحوه استفاده از تابع get_car_details:
1. نام کامل خودرو را وارد کنید (مثل 'پژو 207 دنده‌ای هیدرولیک')
2. تابع با جستجوی شباهت، بهترین تطبیق را پیدا می‌کند
3. اطلاعات برگشتی شامل: مشخصات فنی، مزایا، معایب و نام دقیق خودرو
4. اگر خروجی با خودرو مورد نظر تطبیق نداشت از اطلاعات استفاده نکن و از خودت جواب بده



برای پاسخ به سوالات کاربر:
- اگر کاربر بودجه خود را اعلام کرد، از اطلاعات قیمت بالا برای پیدا کردن خودروهای مناسب استفاده کنید
- اگر کاربر قیمت خودروی خاصی را پرسید، از اطلاعات قیمت بالا برای پیدا کردن آن خودرو استفاده کنید
- اگر کاربر درباره مشخصات، مزایا یا معایب خودروی خاصی سوال کرد، از تابع get_car_details استفاده کنید
- اگر صفر خودرو تولید نمیشد و قیمتش رو در لیست بالا نداشتی نزدیک ترین خودرو رو انتخاب کن و ۱۰ درصد کمتر در نظر بگیر به عنوان قیمت صفر خودرو مذکور
- همیشه قیمت‌ها را به صورت فارسی و خوانا ارائه دهید (مثلاً ۱ میلیارد و ۵۰۰ میلیون تومان)
- برای محاسبه قیمت خودروهای دست دوم، حتماً از تابع calculate_used_car_price استفاده کنید
- قیمت نهایی را به صورت بازه ۵ درصد بالاتر و ۵ درصد پایین‌تر ارائه دهید
- حین ارائه قیمت به کاربر تاریخ فعلی هم ذکر کن تاریخ فعلی:  {current_date} """ 

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
            gpt_models = ["gpt-4.1"]
            
            for model in gpt_models:
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

    def calculate_used_car_price(
        self,
        base_price: float,
        car_age: int,
        car_kilometers: int,
        damages: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate used car price based on the formula:
        P = P0 * (1-δA) * (1-δK) * Ccond
        
        Args:
            base_price: Original car price (P0)
            car_age: Car age in years
            car_kilometers: Total kilometers driven
            damages: List of damage dictionaries with keys:
                - type: 'paint', 'replacement', 'body_replacement', 'hood_replacement'
                - part: part name (for paint and replacement)
                - severity: 'minor', 'major' (for paint)
            
        Returns:
            Dictionary with calculated price and breakdown
        """
        try:
            # Log function entry with parameters
            logger.info(f"=== Starting calculate_used_car_price ===")
            logger.info(f"Input parameters: Base price: {base_price:,}, Age: {car_age}, Kilometers: {car_kilometers:,}")
            logger.info(f"Damages: {len(damages)} items")
            for i, damage in enumerate(damages):
                logger.info(f"  Damage {i+1}: {damage}")
            
            # Calculate annual depreciation (δA)
            annual_depreciation = self._calculate_annual_depreciation(car_age)
            
            # Calculate kilometer depreciation (δK)
            kilometer_depreciation = self._calculate_kilometer_depreciation(car_age, car_kilometers)
            
            # Calculate condition factor (Ccond)
            condition_factor = self._calculate_condition_factor(damages, car_age)
            
            # Apply the formula
            final_price = (
                base_price * 
                (1 - annual_depreciation) * 
                (1 - kilometer_depreciation) * 
                condition_factor
            )
            
            # Calculate price range (±5%)
            price_range_lower = final_price * 0.95
            price_range_upper = final_price * 1.05
            
            return {
                'base_price': base_price,
                'final_price': final_price,
                'price_range_lower': price_range_lower,
                'price_range_upper': price_range_upper,
                'annual_depreciation': annual_depreciation,
                'kilometer_depreciation': kilometer_depreciation,
                'condition_factor': condition_factor
            }
            
        except Exception as e:
            logger.error(f"Error in calculate_used_car_price: {str(e)}")
            print(f"Error calculating used car price: {str(e)}")
            return {
                'base_price': base_price,
                'final_price': base_price,
                'price_range_lower': base_price * 0.95,
                'price_range_upper': base_price * 1.05,
                'error': str(e)
            }
    
    def _calculate_annual_depreciation(self, car_age: int) -> float:
        """
        Calculate annual depreciation factor (δA)
        
        Args:
            car_age: Car age in years
            
        Returns:
            Annual depreciation factor
        """
        if car_age <= 0:
            return 0.0
        
        depreciation = 1.0
        
        for year in range(1, car_age + 1):
            if year == 1:
                # First year: 10% depreciation
                depreciation *= 0.9
            elif year <= 4:
                # Years 2-4: 5% depreciation each year
                depreciation *= 0.95
            else:
                # After 4 years: 2% depreciation each year
                depreciation *= 0.97
        
        return 1.0 - depreciation
    
    def _calculate_kilometer_depreciation(self, car_age: int, car_kilometers: int) -> float:
        """
        Calculate kilometer depreciation factor (δK)
        
        Args:
            car_age: Car age in years
            car_kilometers: Total kilometers driven
            
        Returns:
            Kilometer depreciation factor
        """
        # Standard annual kilometers: 25,000 km
        standard_annual_km = 25000
        expected_km = car_age * standard_annual_km
        
        if car_kilometers <= expected_km:
            return 0.0
        
        # Calculate excess kilometers
        excess_km = car_kilometers - expected_km
        
        # 1% depreciation for every 10,000 km excess
        depreciation = (excess_km / 10000) * 0.01
        
        return min(depreciation, 0.5)  # Cap at 50% depreciation
    
    def _calculate_condition_factor(self, damages: List[Dict], car_age: int) -> float:
        """
        Calculate condition factor (Ccond) based on damages
        
        Args:
            damages: List of damage dictionaries
            car_age: Car age in years
            
        Returns:
            Condition factor
        """
        condition_factor = 1.0
        
        for damage in damages:
            damage_type = damage.get('type', '')
            
            if damage_type == 'paint':
                part = damage.get('part', '')
                severity = damage.get('severity', 'minor')
                
                if part in ['roof', 'chassis'] or severity == 'major':
                    # Roof/chassis paint or major paint damage: 9% reduction
                    condition_factor *= 0.91
                else:
                    # Regular paint damage: 3% reduction
                    condition_factor *= 0.97
                    
            elif damage_type == 'replacement':
                # Part replacement: 5% reduction
                condition_factor *= 0.95
                
            elif damage_type == 'body_replacement':
                # Body replacement based on car age
                if car_age <= 10:
                    # Recent cars (≤10 years): 25% reduction
                    condition_factor *= 0.75
                elif car_age <= 15:
                    # Cars 10-15 years: 15% reduction
                    condition_factor *= 0.85
                else:
                    # Cars >15 years: 0% reduction
                    pass
                    
            elif damage_type == 'hood_replacement':
                # Hood replacement: 9% reduction
                condition_factor *= 0.91
        
        return condition_factor


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