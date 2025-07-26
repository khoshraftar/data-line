#!/usr/bin/env python3
"""
Test script to demonstrate function call logging
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khodroyar.settings')
django.setup()

from ai_agent import get_ai_agent
from .models import Conversation, Message

def test_function_call_logging():
    """Test function call logging"""
    
    print("=== Testing Function Call Logging ===")
    print("This will show detailed logs in stdout for function calls\n")
    
    # Get AI agent
    ai_agent = get_ai_agent()
    
    # Create a test conversation
    conversation = Conversation.objects.create(
        user_id="test_user_logging",
        title="Test Logging Conversation"
    )
    
    # Test message that should trigger function call
    test_message = "سلام، من دنبال یک خودروی پراید 3 ساله با 75000 کیلومتر هستم. قیمتش چقدر میشه؟"
    
    print(f"User Message: {test_message}")
    print("\n" + "="*50)
    print("LOGS WILL APPEAR BELOW:")
    print("="*50 + "\n")
    
    try:
        # Generate response (this will trigger function call and logging)
        response = ai_agent.generate_response(
            user_message=test_message,
            conversation=conversation,
            user_context=None
        )
        
        print("\n" + "="*50)
        print("FINAL RESPONSE:")
        print("="*50)
        print(response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    finally:
        # Clean up
        conversation.delete()

def test_direct_function_logging():
    """Test direct function call logging"""
    
    print("\n=== Testing Direct Function Call Logging ===")
    
    # Get AI agent
    ai_agent = get_ai_agent()
    
    # Test data
    base_price = 500000000  # 500 million tomans
    car_age = 3
    car_kilometers = 75000
    
    damages = [
        {
            'type': 'paint',
            'part': 'front_bumper',
            'severity': 'minor'
        },
        {
            'type': 'replacement',
            'part': 'headlight'
        }
    ]
    
    print(f"Calling calculate_used_car_price directly...")
    print("\n" + "="*50)
    print("LOGS WILL APPEAR BELOW:")
    print("="*50 + "\n")
    
    # Call function directly (this will trigger logging)
    result = ai_agent.calculate_used_car_price(
        base_price=base_price,
        car_age=car_age,
        car_kilometers=car_kilometers,
        damages=damages
    )
    
    print("\n" + "="*50)
    print("FUNCTION RESULT:")
    print("="*50)
    print(f"Base Price: {result['base_price']:,} tomans")
    print(f"Final Price: {result['final_price']:,.0f} tomans")
    print(f"Price Range: {result['price_range_lower']:,.0f} - {result['price_range_upper']:,.0f} tomans")

if __name__ == "__main__":
    print("Starting Function Call Logging Tests...")
    
    # Test direct function call logging
    test_direct_function_logging()
    
    # Test function call through AI
    test_function_call_logging()
    
    print("\n" + "="*50)
    print("ALL TESTS COMPLETED!")
    print("="*50) 