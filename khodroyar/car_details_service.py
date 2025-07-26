import json
import os
from typing import List, Dict, Optional
from django.conf import settings
from difflib import SequenceMatcher


class CarDetailsService:
    """Service for searching car details and pros/cons based on similarity"""
    
    def __init__(self):
        """Initialize the car details service"""
        self.cars_details = self._load_cars_details()
    
    def _load_cars_details(self) -> List[Dict]:
        """
        Load car details from JSON file
        
        Returns:
            List of car detail dictionaries
        """
        try:
            # Get the path to the JSON file in the khodroyar/data directory
            json_file_path = os.path.join(settings.BASE_DIR, 'khodroyar', 'data', 'car_details.json')
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Extract cars from the data
            cars_details = data.get('cars', [])
            
            print(f"Loaded {len(cars_details)} cars with details")
            return cars_details
            
        except Exception as e:
            print(f"Error loading car details: {str(e)}")
            return []
    
    def search_car_details_by_name(self, car_name: str, threshold: float = 0.6) -> List[Dict]:
        """
        Search for car details using similarity matching on full car name
        
        Args:
            car_name: The car name to search for
            threshold: Minimum similarity threshold (0.0 to 1.0)
            
        Returns:
            List of matching car details with similarity scores
        """
        if not car_name or not self.cars_details:
            return []
        
        # Normalize the search term
        search_term = car_name.strip().lower()
        
        matches = []
        
        for car in self.cars_details:
            full_car_name = car.get('full_car_name', '').lower()
            car_name_field = car.get('car_name', '').lower()
            brand = car.get('brand', '').lower()
            
            # Calculate similarity scores for different fields
            full_name_similarity = SequenceMatcher(None, search_term, full_car_name).ratio()
            car_name_similarity = SequenceMatcher(None, search_term, car_name_field).ratio()
            brand_similarity = SequenceMatcher(None, search_term, brand).ratio()
            
            # Check for exact matches first
            if search_term in full_car_name or full_car_name in search_term:
                full_name_similarity = max(full_name_similarity, 0.9)
            
            if search_term in car_name_field or car_name_field in search_term:
                car_name_similarity = max(car_name_similarity, 0.9)
            
            if search_term in brand or brand in search_term:
                brand_similarity = max(brand_similarity, 0.9)
            
            # Use the highest similarity score
            max_similarity = max(full_name_similarity, car_name_similarity, brand_similarity)
            
            # Additional scoring for partial matches
            if any(word in full_car_name for word in search_term.split()):
                max_similarity = max(max_similarity, 0.7)
            
            if any(word in car_name_field for word in search_term.split()):
                max_similarity = max(max_similarity, 0.7)
            
            if max_similarity >= threshold:
                # Create a copy of the car data with similarity score
                car_with_score = car.copy()
                car_with_score['similarity_score'] = max_similarity
                matches.append(car_with_score)
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return matches
    
    def get_car_details_and_pros_cons(self, car_name: str) -> Dict:
        """
        Get car details, pros, and cons for a specific car
        
        Args:
            car_name: The full car name to search for
            
        Returns:
            Dictionary with car details, pros, and cons
        """
        matches = self.search_car_details_by_name(car_name, threshold=0.5)
        
        if not matches:
            return {
                'found': False,
                'message': f'اطلاعات خودرو "{car_name}" یافت نشد.',
                'suggestions': self._get_similar_car_names(car_name)
            }
        
        # Get the best match
        best_match = matches[0]
        
        return {
            'found': True,
            'car_name': best_match.get('full_car_name', ''),
            'brand': best_match.get('brand', ''),
            'technical_specs': best_match.get('technical_specs', ''),
            'advantages': best_match.get('advantages', ''),
            'disadvantages': best_match.get('disadvantages', ''),
            'similarity_score': best_match.get('similarity_score', 0),
            'all_matches': matches[:5] if len(matches) > 1 else []  # Include top 5 matches for reference
        }
    
    def _get_similar_car_names(self, car_name: str, limit: int = 5) -> List[str]:
        """
        Get similar car names for suggestions
        
        Args:
            car_name: The car name to find suggestions for
            limit: Maximum number of suggestions
            
        Returns:
            List of similar car names
        """
        matches = self.search_car_details_by_name(car_name, threshold=0.3)
        return [car.get('full_car_name', '') for car in matches[:limit]]


# Global car details service instance
_car_details_service = None

def get_car_details_service() -> CarDetailsService:
    """
    Get or create global car details service instance
    
    Returns:
        CarDetailsService instance
    """
    global _car_details_service
    if _car_details_service is None:
        _car_details_service = CarDetailsService()
    return _car_details_service 