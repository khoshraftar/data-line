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
            # Calculate budget range: 10% under to 5% over (all in Tomans)
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
    
    def search_car_price_by_name(self, car_name: str, similarity_threshold: float = 0.6) -> List[Dict]:
        """
        Search for a specific car by name with fuzzy matching
        
        Args:
            car_name: Name of the car to search for
            similarity_threshold: Minimum similarity ratio (0.0 to 1.0)
            
        Returns:
            List of matching cars with similarity scores, sorted by similarity
        """
        try:
            if not car_name or not car_name.strip():
                return []
            
            # Normalize the search term
            search_term = car_name.strip().lower()
            
            matching_cars = []
            
            for car in self.cars_data:
                car_name_normalized = car['car_name'].lower()
                
                # Calculate similarity using SequenceMatcher
                similarity = SequenceMatcher(None, search_term, car_name_normalized).ratio()
                
                # Also check if search term is contained in car name
                contains_match = search_term in car_name_normalized or car_name_normalized in search_term
                
                # If similarity is above threshold or contains match, add to results
                if similarity >= similarity_threshold or contains_match:
                    matching_cars.append({
                        'car_name': car['car_name'],
                        'current_price': car['current_price'],
                        'price_formatted': self._format_price(car['current_price']),
                        'similarity': similarity,
                        'contains_match': contains_match
                    })
            
            # Sort by similarity (highest first) and then by contains_match
            matching_cars.sort(key=lambda x: (x['contains_match'], x['similarity']), reverse=True)
            
            # Remove similarity and contains_match from final results
            for car in matching_cars:
                car.pop('similarity', None)
                car.pop('contains_match', None)
            
            return matching_cars
            
        except Exception as e:
            print(f"Error searching car by name: {str(e)}")
            return []
    
    def _format_price(self, price: int) -> str:
        """
        Format price in a beautiful Persian format
        
        Args:
            price: Price in Tomans
            
        Returns:
            Beautifully formatted price string in Persian
        """
        # Format with commas for readability (price is already in Tomans)
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