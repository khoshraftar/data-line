import jdatetime
from datetime import datetime
from .models import Payment
from django.utils import timezone
import pytz

def get_tehran_timezone():
    """Get Tehran timezone object"""
    return pytz.timezone('Asia/Tehran')

def convert_to_tehran_timezone(datetime_obj):
    """
    Convert a datetime object to Tehran timezone
    
    Args:
        datetime_obj: datetime object (can be naive or timezone-aware)
        
    Returns:
        datetime object in Tehran timezone
    """
    if datetime_obj is None:
        return None
    
    tehran_tz = get_tehran_timezone()
    
    # If datetime is naive, assume it's in UTC
    if timezone.is_naive(datetime_obj):
        datetime_obj = timezone.make_aware(datetime_obj, pytz.UTC)
    
    # Convert to Tehran timezone
    return datetime_obj.astimezone(tehran_tz)

def to_shamsi_date(date_obj):
    """Convert datetime to Shamsi date format in Tehran timezone"""
    if not date_obj:
        return ""
    
    # Convert to Tehran timezone first
    tehran_datetime = convert_to_tehran_timezone(date_obj)
    
    # Convert to Shamsi
    jdate = jdatetime.datetime.fromgregorian(datetime=tehran_datetime)
    
    # Persian month names
    persian_months = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
    }
    
    # Convert numbers to Persian digits
    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    
    def to_persian_number(num):
        return ''.join(persian_digits[digit] for digit in str(num))
    
    # Format the date in Persian
    day_persian = to_persian_number(jdate.day)
    month_name = persian_months[jdate.month]
    year_persian = to_persian_number(jdate.year)
    hour_persian = to_persian_number(tehran_datetime.hour)
    minute_persian = to_persian_number(tehran_datetime.minute)
    
    return f"{day_persian} {month_name} {year_persian} - {hour_persian}:{minute_persian}"

def to_shamsi_date_short(date_obj):
    """
    Convert a datetime object to short Shamsi date format (YYYY/MM/DD) in Tehran timezone
    
    Args:
        date_obj: datetime object to convert
    
    Returns:
        str: Short Shamsi date string in YYYY/MM/DD format
    """
    if not date_obj:
        return ""
    
    # Convert to Tehran timezone first
    tehran_datetime = convert_to_tehran_timezone(date_obj)
    
    jdate = jdatetime.datetime.fromgregorian(datetime=tehran_datetime)
    return f"{jdate.year}/{jdate.month:02d}/{jdate.day:02d}"

def to_shamsi_datetime_full(date_obj):
    """
    Convert datetime to full Shamsi datetime format in Tehran timezone
    
    Args:
        date_obj: datetime object to convert
    
    Returns:
        str: Full Shamsi datetime string with Persian formatting
    """
    if not date_obj:
        return ""
    
    # Convert to Tehran timezone first
    tehran_datetime = convert_to_tehran_timezone(date_obj)
    
    # Convert to Shamsi
    jdate = jdatetime.datetime.fromgregorian(datetime=tehran_datetime)
    
    # Persian month names
    persian_months = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
    }
    
    # Convert numbers to Persian digits
    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    
    def to_persian_number(num):
        return ''.join(persian_digits[digit] for digit in str(num))
    
    # Format the datetime in Persian
    day_persian = to_persian_number(jdate.day)
    month_name = persian_months[jdate.month]
    year_persian = to_persian_number(jdate.year)
    hour_persian = to_persian_number(tehran_datetime.hour)
    minute_persian = to_persian_number(tehran_datetime.minute)
    
    return f"{day_persian} {month_name} {year_persian} ساعت {hour_persian}:{minute_persian}"

def get_current_tehran_datetime():
    """
    Get current datetime in Tehran timezone
    
    Returns:
        datetime object in Tehran timezone
    """
    return convert_to_tehran_timezone(timezone.now())

def format_amount_in_toman(amount_rials):
    """
    Format amount from Rials to Tomans with Persian formatting
    
    Args:
        amount_rials: Amount in Rials (integer)
    
    Returns:
        str: Formatted amount in Tomans with Persian digits
    """
    if amount_rials is None:
        return "۰ تومان"
    
    # Convert Rials to Tomans (divide by 10)
    amount_toman = amount_rials // 10
    
    # Convert numbers to Persian digits
    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    
    def to_persian_number(num):
        return ''.join(persian_digits[digit] for digit in str(num))
    
    # Format with thousands separator
    formatted_amount = f"{amount_toman:,}"
    
    # Convert to Persian digits
    persian_amount = ''.join(
        persian_digits.get(char, char) for char in formatted_amount
    )
    
    return f"{persian_amount} تومان"


def check_subscription_status(user_auth):
    """
    Check if user's subscription has ended and return appropriate message
    
    Args:
        user_auth: UserAuth object
        
    Returns:
        tuple: (has_ended, message) where has_ended is boolean and message is string or None
    """
    if not user_auth:
        return False, None
    
    # Get the most recent completed payment
    latest_payment = Payment.objects.filter(
        user_auth=user_auth,
        status='completed'
    ).order_by('-created_at').first()
    
    if not latest_payment:
        # No payment found - treat as no subscription
        return True, """🔒 شما هنوز اشتراک خودرویار ندارید!
💳 برای استفاده از خدمات خودرویار، لطفاً اشتراک تهیه کنید:
"""
    
    # Check if subscription has ended
    if latest_payment.subscription_end and latest_payment.subscription_end < timezone.now():
        # Subscription has ended
        ended_message = f"""⏰ اشتراک شما به پایان رسیده است!
📅 اشتراک شما در تاریخ {to_shamsi_date(latest_payment.subscription_end)} منقضی شده است.
🔄 برای ادامه استفاده از خدمات خودرویار، لطفاً اشتراک خود را تمدید کنید:
"""
        
        return True, ended_message
    
    # Subscription is still active
    return False, None 