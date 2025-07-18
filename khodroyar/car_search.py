import json
import os
from typing import List, Dict
from django.conf import settings


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
            json_file_path = os.path.join(settings.BASE_DIR, 'khodroyar', 'data', 'iran_car_prices_combined.json')
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                cars_data = json.load(file)
            
            # Filter out cars with null prices
            valid_cars = [car for car in cars_data if car.get('current_price') is not None]
            
            print(f"Loaded {len(valid_cars)} cars with valid prices from {len(cars_data)} total cars")
            return valid_cars
            
        except Exception as e:
            print(f"Error loading car data: {str(e)}")
            return []
    
    def search_cars_by_budget(self, budget: int) -> List[Dict]:
        """
        Search for cars within budget range (5% over to 10% under budget)
        
        Args:
            budget: User's budget in Tomans
            
        Returns:
            List of cars within budget range, sorted by price
        """
        try:
            # Calculate budget range: 10% under to 5% over
            min_price = int(budget * 0.9)  # 10% under budget
            max_price = int(budget * 1.05)  # 5% over budget
            
            matching_cars = []
            
            for car in self.cars_data:
                price = car.get('current_price')
                if price is not None and min_price <= price <= max_price:
                    matching_cars.append({
                        'car_name': car['car_name'],
                        'current_price': price,
                        'price_formatted': self._format_price(price)
                    })
            
            # Sort by price (ascending)
            matching_cars.sort(key=lambda x: x['current_price'])
            
            return matching_cars
            
        except Exception as e:
            print(f"Error searching cars by budget: {str(e)}")
            return []
    
    def _format_price(self, price: int) -> str:
        """
        Format price in a readable format
        
        Args:
            price: Price in Tomans
            
        Returns:
            Formatted price string
        """
        if price >= 1000000000:  # 1 billion
            return f"{price // 1000000000} میلیارد تومان"
        elif price >= 1000000:  # 1 million
            return f"{price // 1000000} میلیون تومان"
        else:
            return f"{price:,} تومان"
    
    def get_all_cars(self) -> List[Dict]:
        """
        Get all available cars
        
        Returns:
            List of all cars with prices
        """
        return self.cars_data.copy()


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