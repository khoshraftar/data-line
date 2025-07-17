import jdatetime
from datetime import datetime


def to_shamsi_date(date_obj, include_time=False):
    """
    Convert a datetime object to Shamsi (Persian) date format
    
    Args:
        date_obj: datetime object to convert
        include_time: whether to include time in the output
    
    Returns:
        str: Formatted Shamsi date string
    """
    if not date_obj:
        return ""
    
    # Convert to jdatetime
    jdate = jdatetime.datetime.fromgregorian(datetime=date_obj)
    
    # Persian month names
    persian_months = {
        1: 'فروردین',
        2: 'اردیبهشت', 
        3: 'خرداد',
        4: 'تیر',
        5: 'مرداد',
        6: 'شهریور',
        7: 'مهر',
        8: 'آبان',
        9: 'آذر',
        10: 'دی',
        11: 'بهمن',
        12: 'اسفند'
    }
    
    month_name = persian_months.get(jdate.month, str(jdate.month))
    
    if include_time:
        return f"{jdate.day} {month_name} {jdate.year} - {jdate.hour:02d}:{jdate.minute:02d}"
    else:
        return f"{jdate.day} {month_name} {jdate.year}"


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