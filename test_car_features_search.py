#!/usr/bin/env python3
"""
Test script for car features search functionality
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_line.settings')
django.setup()

from khodroyar.car_features_search import get_car_features_search_service


def test_car_features_search():
    """Test the car features search functionality"""
    
    print("🚗 Testing Car Features Search Service")
    print("=" * 50)
    
    # Get the service
    service = get_car_features_search_service()
    
    # Test 1: Search by car name
    print("\n1. Testing search by car name:")
    print("-" * 30)
    
    test_cars = ["سورن", "دنا", "پژو 207", "هایما", "شاهین"]
    
    for car_name in test_cars:
        print(f"\nSearching for: {car_name}")
        results = service.search_car_by_name(car_name)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, car in enumerate(results[:3], 1):  # Show first 3 results
                print(f"  {i}. {car['full_name']}")
                if car['technical_specs']:
                    print(f"     مشخصات: {car['technical_specs'][:100]}...")
        else:
            print("  No results found")
    
    # Test 2: Search by company
    print("\n\n2. Testing search by company:")
    print("-" * 30)
    
    test_companies = ["ایرانخودرو", "سایپا", "مدیران‌خودرو"]
    
    for company in test_companies:
        print(f"\nSearching for company: {company}")
        results = service.search_cars_by_company(company)
        
        if results:
            print(f"Found {len(results)} cars:")
            for i, car in enumerate(results[:5], 1):  # Show first 5 results
                print(f"  {i}. {car['car_name']}")
        else:
            print("  No results found")
    
    # Test 3: Search by features
    print("\n\n3. Testing search by features:")
    print("-" * 30)
    
    test_features = ["توربو", "هیبرید", "اتوماتیک", "برقی"]
    
    for feature in test_features:
        print(f"\nSearching for feature: {feature}")
        results = service.search_cars_by_feature(feature)
        
        if results:
            print(f"Found {len(results)} cars with this feature:")
            for i, car in enumerate(results[:5], 1):  # Show first 5 results
                print(f"  {i}. {car['full_name']}")
        else:
            print("  No results found")
    
    # Test 4: Get all cars
    print("\n\n4. Testing get all cars:")
    print("-" * 30)
    
    all_cars = service.get_all_cars()
    print(f"Total cars in database: {len(all_cars)}")
    
    # Show some sample cars
    print("Sample cars:")
    for i, car in enumerate(all_cars[:5], 1):
        print(f"  {i}. {car['full_name']}")
    
    # Test 5: Get features summary
    print("\n\n5. Testing features summary:")
    print("-" * 30)
    
    summary = service.get_car_features_summary()
    print("Features summary (first 500 characters):")
    print(summary[:500] + "..." if len(summary) > 500 else summary)
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    test_car_features_search() 