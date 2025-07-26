import csv
import os
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from django.conf import settings


class CarFeaturesSearchService:
    """Service for searching car features from CSV file with similarity matching"""
    
    def __init__(self):
        """Initialize the car features search service"""
        self.csv_file_path = os.path.join(settings.BASE_DIR, 'khodroyar', 'data', 'خودروی صفر.csv')
        self.cars_data = self._load_cars_data()
    
    def _load_cars_data(self) -> List[Dict]:
        """
        Load car data from CSV file
        
        Returns:
            List of car dictionaries
        """
        try:
            cars_data = []
            
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                # Read CSV with pipe delimiter
                csv_reader = csv.DictReader(file, delimiter='|')
                
                for row in csv_reader:
                    car_data = {
                        'company': row.get('شرکت', '').strip(),
                        'car_name': row.get('نام ماشین', '').strip(),
                        'technical_specs': row.get('مشخصات فنی', '').strip(),
                        'advantages': row.get('مزایا', '').strip(),
                        'disadvantages': row.get('معایب', '').strip(),
                        'full_name': f"{row.get('شرکت', '').strip()} {row.get('نام ماشین', '').strip()}".strip()
                    }
                    cars_data.append(car_data)
            
            print(f"Loaded {len(cars_data)} cars from CSV file")
            return cars_data
            
        except Exception as e:
            print(f"Error loading car features data: {str(e)}")
            return []
    
    def search_car_by_name(self, car_name: str, similarity_threshold: float = 0.4) -> List[Dict]:
        """
        Search for a car by name with similarity matching
        
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
                # Check multiple fields for similarity
                car_name_normalized = car['car_name'].lower()
                full_name_normalized = car['full_name'].lower()
                company_normalized = car['company'].lower()
                
                # Calculate similarity for different fields
                name_similarity = SequenceMatcher(None, search_term, car_name_normalized).ratio()
                full_name_similarity = SequenceMatcher(None, search_term, full_name_normalized).ratio()
                company_similarity = SequenceMatcher(None, search_term, company_normalized).ratio()
                
                # Take the highest similarity score
                max_similarity = max(name_similarity, full_name_similarity, company_similarity)
                
                # Check if search term is contained in any field
                contains_match = (
                    search_term in car_name_normalized or 
                    search_term in full_name_normalized or 
                    search_term in company_normalized or
                    car_name_normalized in search_term or
                    company_normalized in search_term
                )
                
                # If similarity is above threshold or contains match, add to results
                if max_similarity >= similarity_threshold or contains_match:
                    matching_cars.append({
                        'company': car['company'],
                        'car_name': car['car_name'],
                        'full_name': car['full_name'],
                        'technical_specs': car['technical_specs'],
                        'advantages': car['advantages'],
                        'disadvantages': car['disadvantages'],
                        'similarity': max_similarity,
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
    
    def search_cars_by_company(self, company_name: str, similarity_threshold: float = 0.4) -> List[Dict]:
        """
        Search for cars by company name with similarity matching
        
        Args:
            company_name: Name of the company to search for
            similarity_threshold: Minimum similarity ratio (0.0 to 1.0)
            
        Returns:
            List of matching cars from the company
        """
        try:
            if not company_name or not company_name.strip():
                return []
            
            # Normalize the search term
            search_term = company_name.strip().lower()
            
            matching_cars = []
            
            for car in self.cars_data:
                company_normalized = car['company'].lower()
                
                # Calculate similarity
                similarity = SequenceMatcher(None, search_term, company_normalized).ratio()
                
                # Check if search term is contained in company name
                contains_match = search_term in company_normalized or company_normalized in search_term
                
                # If similarity is above threshold or contains match, add to results
                if similarity >= similarity_threshold or contains_match:
                    matching_cars.append({
                        'company': car['company'],
                        'car_name': car['car_name'],
                        'full_name': car['full_name'],
                        'technical_specs': car['technical_specs'],
                        'advantages': car['advantages'],
                        'disadvantages': car['disadvantages']
                    })
            
            return matching_cars
            
        except Exception as e:
            print(f"Error searching cars by company: {str(e)}")
            return []
    
    def search_cars_by_feature(self, feature_keyword: str, similarity_threshold: float = 0.3) -> List[Dict]:
        """
        Search for cars by features in technical specs, advantages, or disadvantages
        
        Args:
            feature_keyword: Keyword to search for in car features
            similarity_threshold: Minimum similarity ratio (0.0 to 1.0)
            
        Returns:
            List of cars matching the feature criteria
        """
        try:
            if not feature_keyword or not feature_keyword.strip():
                return []
            
            # Normalize the search term
            search_term = feature_keyword.strip().lower()
            
            matching_cars = []
            
            for car in self.cars_data:
                # Check in technical specs, advantages, and disadvantages
                tech_specs = car['technical_specs'].lower()
                advantages = car['advantages'].lower()
                disadvantages = car['disadvantages'].lower()
                
                # Calculate similarity for each field
                tech_similarity = SequenceMatcher(None, search_term, tech_specs).ratio()
                adv_similarity = SequenceMatcher(None, search_term, advantages).ratio()
                dis_similarity = SequenceMatcher(None, search_term, disadvantages).ratio()
                
                # Take the highest similarity score
                max_similarity = max(tech_similarity, adv_similarity, dis_similarity)
                
                # Check if search term is contained in any field
                contains_match = (
                    search_term in tech_specs or 
                    search_term in advantages or 
                    search_term in disadvantages
                )
                
                # If similarity is above threshold or contains match, add to results
                if max_similarity >= similarity_threshold or contains_match:
                    matching_cars.append({
                        'company': car['company'],
                        'car_name': car['car_name'],
                        'full_name': car['full_name'],
                        'technical_specs': car['technical_specs'],
                        'advantages': car['advantages'],
                        'disadvantages': car['disadvantages'],
                        'match_score': max_similarity
                    })
            
            # Sort by match score (highest first)
            matching_cars.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Remove match_score from final results
            for car in matching_cars:
                car.pop('match_score', None)
            
            return matching_cars
            
        except Exception as e:
            print(f"Error searching cars by feature: {str(e)}")
            return []
    
    def get_all_cars(self) -> List[Dict]:
        """
        Get all available cars from the CSV
        
        Returns:
            List of all cars with their features
        """
        return self.cars_data.copy()
    
    def get_car_features_summary(self) -> str:
        """
        Get a summary of available car features for inclusion in AI prompt
        
        Returns:
            Formatted string with car features summary
        """
        try:
            # Group cars by company
            companies = {}
            for car in self.cars_data:
                company = car['company']
                if company not in companies:
                    companies[company] = []
                companies[company].append(car)
            
            # Format the data
            result = "مشخصات و ویژگی‌های خودروهای صفر:\n\n"
            
            for company in sorted(companies.keys()):
                result += f"🏭 {company}:\n"
                cars = companies[company]
                
                for car in cars:
                    result += f"  🚗 {car['car_name']}\n"
                    if car['technical_specs']:
                        result += f"    📋 مشخصات فنی: {car['technical_specs'][:100]}...\n"
                    if car['advantages']:
                        result += f"    ✅ مزایا: {car['advantages'][:100]}...\n"
                    if car['disadvantages']:
                        result += f"    ❌ معایب: {car['disadvantages'][:100]}...\n"
                    result += "\n"
            
            return result
            
        except Exception as e:
            print(f"Error formatting car features summary: {str(e)}")
            return "اطلاعات مشخصات خودرو در دسترس نیست."


# Global car features search service instance
_car_features_search_service = None

def get_car_features_search_service() -> CarFeaturesSearchService:
    """
    Get or create global car features search service instance
    
    Returns:
        CarFeaturesSearchService instance
    """
    global _car_features_search_service
    if _car_features_search_service is None:
        _car_features_search_service = CarFeaturesSearchService()
    return _car_features_search_service 