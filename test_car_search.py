#!/usr/bin/env python3
"""
Test script for the new car search by name functionality
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_line.settings')
django.setup()

from khodroyar.car_search import get_car_search_service

def test_car_search_by_name():
    """Test the car search by name functionality"""
    car_search_service = get_car_search_service()
    
    # Test cases with different variations
    test_cases = [
        "پژو 207",
        "دنا پلاس",
        "سورن",
        "کوییک",
        "شاهین",
        "پژو",
        "207",
        "دنا",
        "سایپا 151",
        "هایما",
        "چانگان",
        "کرولا",
        "مزدا",
        "هوندا",
        "کیا",
        "هیوندای"
    ]
    
    print("Testing car search by name functionality:")
    print("=" * 50)
    
    for test_name in test_cases:
        print(f"\nSearching for: '{test_name}'")
        results = car_search_service.search_car_price_by_name(test_name)
        
        if results:
            print(f"Found {len(results)} matching cars:")
            for i, car in enumerate(results[:5], 1):  # Show top 5 results
                print(f"  {i}. {car['car_name']} - {car['price_formatted']}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more")
        else:
            print("  No matches found")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_car_search_by_name() 