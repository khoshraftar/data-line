import json
import os
from typing import List, Dict
from django.conf import settings
from difflib import SequenceMatcher


class CarSearchService:
    """Service for searching cars based on budget"""
    
    def __init__(self):
        """Initialize the car search service"""
        self.cars_data = self._load_cars_data()
    
    def _load_cars_data(self) -> List[Dict]:
        """
        Load car data from JSON file
        
        Returns:
            List of car dictionaries
        """
        try:
            # Get the path to the JSON file in the khodroyar/data directory
            json_file_path = os.path.join(settings.BASE_DIR, 'khodroyar', 'data', 'car_prices.json')
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Extract cars from the new format
            cars_data = data.get('cars', [])
            
            # Convert price strings to integers and add current_price field for compatibility
            for car in cars_data:
                if car.get('price'):
                    try:
                        car['current_price'] = int(car['price'])
                    except (ValueError, TypeError):
                        car['current_price'] = None
                else:
                    car['current_price'] = None
            
            # Filter out cars with null prices
            valid_cars = [car for car in cars_data if car.get('current_price') is not None]
            
            print(f"Loaded {len(valid_cars)} cars with valid prices from {len(cars_data)} total cars")
            return valid_cars
            
        except Exception as e:
            print(f"Error loading car data: {str(e)}")
            return []
    

    def get_car_prices_for_prompt(self) -> str:
        """
        Get formatted car prices for inclusion in AI prompt
        
        Returns:
            Formatted string with car prices
        """
        try:
            # Group cars by brand
            brands = {}
            for car in self.cars_data:
                brand = car.get('brand', 'سایر')
                if brand not in brands:
                    brands[brand] = []
                brands[brand].append(car)
            
            # Format the data
            result = "قیمت خودروهای صفر (به تومان):\n\n"
            
            for brand in sorted(brands.keys()):
                result += f"🏷️ {brand}:\n"
                cars = brands[brand]
                # Sort by price
                cars.sort(key=lambda x: x['current_price'])
                
                for car in cars:
                    price_formatted = self._format_price(car['current_price'])
                    result += f"  • {car['full_car_name']}: {price_formatted}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            print(f"Error formatting car prices for prompt: {str(e)}")
            return "اطلاعات قیمت خودرو در دسترس نیست."


# Global car search service instance
_car_search_service = None

def get_car_search_service() -> CarSearchService:
    """
    Get or create global car search service instance
    
    Returns:
        CarSearchService instance
    """
    global _car_search_service
    if _car_search_service is None:
        _car_search_service = CarSearchService()
    return _car_search_service 