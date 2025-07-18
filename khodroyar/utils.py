import jdatetime
from datetime import datetime
from .models import Payment


def to_shamsi_date(date_obj):
    """Convert datetime to Shamsi date format"""
    if not date_obj:
        return ""
    
    # Simple conversion - you might want to use a proper Persian date library
    return date_obj.strftime("%Y/%m/%d %H:%M")


def to_shamsi_date_short(date_obj):
    """
    Convert a datetime object to short Shamsi date format (YYYY/MM/DD)
    
    Args:
        date_obj: datetime object to convert
    
    Returns:
        str: Short Shamsi date string in YYYY/MM/DD format
    """
    if not date_obj:
        return ""
    
    jdate = jdatetime.datetime.fromgregorian(datetime=date_obj)
    return f"{jdate.year}/{jdate.month:02d}/{jdate.day:02d}" 


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
    if latest_payment.subscription_end and latest_payment.subscription_end < datetime.now():
        # Subscription has ended
        ended_message = f"""⏰ اشتراک شما به پایان رسیده است!

📅 اشتراک شما در تاریخ {to_shamsi_date(latest_payment.subscription_end)} منقضی شده است.

🔄 برای ادامه استفاده از خدمات خودرویار، لطفاً اشتراک خود را تمدید کنید:

💳 برای تمدید اشتراک، روی لینک زیر کلیک کنید:
https://data-lines.ir/khodroyar/pre-payment/

اگر سوالی دارید، با پشتیبانی تماس بگیرید."""
        
        return True, ended_message
    
    # Subscription is still active
    return False, None 