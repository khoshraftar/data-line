#!/usr/bin/env python3
"""
Standalone car price calculator utility
"""

from typing import List, Dict

class CarPriceCalculator:
    """Standalone calculator for used car prices"""
    
    @staticmethod
    def calculate_used_car_price(
        base_price: float,
        car_age: int,
        car_kilometers: int,
        damages: List[Dict],
        brand_popularity: float = 1.0,
        options_factor: float = 1.0,
        market_factor: float = 1.0
    ) -> Dict[str, float]:
        """
        Calculate used car price based on the formula:
        P = P0 * (1-δA) * (1-δK) * Ccond * Copt * Cbrand * Cmarket
        
        Args:
            base_price: Original car price (P0)
            car_age: Car age in years
            car_kilometers: Total kilometers driven
            damages: List of damage dictionaries with keys:
                - type: 'paint', 'replacement', 'body_replacement', 'hood_replacement'
                - part: part name (for paint and replacement)
                - severity: 'minor', 'major' (for paint)
            brand_popularity: Brand popularity factor (1.0 for popular brands, 0.9 for less popular)
            options_factor: Options factor (0.9 to 1.1, default 1.0)
            market_factor: Market factor (usually 1.0)
            
        Returns:
            Dictionary with calculated price and breakdown
        """
        try:
            # Calculate annual depreciation (δA)
            annual_depreciation = CarPriceCalculator._calculate_annual_depreciation(car_age)
            
            # Calculate kilometer depreciation (δK)
            kilometer_depreciation = CarPriceCalculator._calculate_kilometer_depreciation(car_age, car_kilometers)
            
            # Calculate condition factor (Ccond)
            condition_factor = CarPriceCalculator._calculate_condition_factor(damages, car_age)
            
            # Apply the formula
            final_price = (
                base_price * 
                (1 - annual_depreciation) * 
                (1 - kilometer_depreciation) * 
                condition_factor * 
                options_factor * 
                brand_popularity * 
                market_factor
            )
            
            # Calculate price range (±5%)
            price_range_lower = final_price * 0.95
            price_range_upper = final_price * 1.05
            
            return {
                'base_price': base_price,
                'final_price': final_price,
                'price_range_lower': price_range_lower,
                'price_range_upper': price_range_upper,
                'annual_depreciation': annual_depreciation,
                'kilometer_depreciation': kilometer_depreciation,
                'condition_factor': condition_factor,
                'options_factor': options_factor,
                'brand_popularity': brand_popularity,
                'market_factor': market_factor
            }
            
        except Exception as e:
            print(f"Error calculating used car price: {str(e)}")
            return {
                'base_price': base_price,
                'final_price': base_price,
                'price_range_lower': base_price * 0.95,
                'price_range_upper': base_price * 1.05,
                'error': str(e)
            }
    
    @staticmethod
    def _calculate_annual_depreciation(car_age: int) -> float:
        """
        Calculate annual depreciation factor (δA)
        
        Args:
            car_age: Car age in years
            
        Returns:
            Annual depreciation factor
        """
        if car_age <= 0:
            return 0.0
        
        depreciation = 1.0
        
        for year in range(1, car_age + 1):
            if year == 1:
                # First year: 10% depreciation
                depreciation *= 0.9
            elif year <= 4:
                # Years 2-4: 5% depreciation each year
                depreciation *= 0.95
            else:
                # After 4 years: 2% depreciation each year
                depreciation *= 0.98
        
        return 1.0 - depreciation
    
    @staticmethod
    def _calculate_kilometer_depreciation(car_age: int, car_kilometers: int) -> float:
        """
        Calculate kilometer depreciation factor (δK)
        
        Args:
            car_age: Car age in years
            car_kilometers: Total kilometers driven
            
        Returns:
            Kilometer depreciation factor
        """
        # Standard annual kilometers: 25,000 km
        standard_annual_km = 25000
        expected_km = car_age * standard_annual_km
        
        if car_kilometers <= expected_km:
            return 0.0
        
        # Calculate excess kilometers
        excess_km = car_kilometers - expected_km
        
        # 1% depreciation for every 10,000 km excess
        depreciation = (excess_km / 10000) * 0.01
        
        return min(depreciation, 0.5)  # Cap at 50% depreciation
    
    @staticmethod
    def _calculate_condition_factor(damages: List[Dict], car_age: int) -> float:
        """
        Calculate condition factor (Ccond) based on damages
        
        Args:
            damages: List of damage dictionaries
            car_age: Car age in years
            
        Returns:
            Condition factor
        """
        condition_factor = 1.0
        
        for damage in damages:
            damage_type = damage.get('type', '')
            
            if damage_type == 'paint':
                part = damage.get('part', '')
                severity = damage.get('severity', 'minor')
                
                if part in ['roof', 'chassis'] or severity == 'major':
                    # Roof/chassis paint or major paint damage: 9% reduction
                    condition_factor *= 0.91
                else:
                    # Regular paint damage: 3% reduction
                    condition_factor *= 0.97
                    
            elif damage_type == 'replacement':
                # Part replacement: 5% reduction
                condition_factor *= 0.95
                
            elif damage_type == 'body_replacement':
                # Body replacement based on car age
                if car_age <= 10:
                    # Recent cars (≤10 years): 25% reduction
                    condition_factor *= 0.75
                elif car_age <= 15:
                    # Cars 10-15 years: 15% reduction
                    condition_factor *= 0.85
                else:
                    # Cars >15 years: 0% reduction
                    pass
                    
            elif damage_type == 'hood_replacement':
                # Hood replacement: 9% reduction
                condition_factor *= 0.91
        
        return condition_factor
    
    @staticmethod
    def format_price_range(result: Dict[str, float]) -> str:
        """
        Format price range in Persian/Farsi format
        
        Args:
            result: Result dictionary from calculate_used_car_price
            
        Returns:
            Formatted price range string
        """
        lower = result['price_range_lower']
        upper = result['price_range_upper']
        
        def format_price(price):
            if price >= 1_000_000_000:  # 1 billion
                billions = int(price // 1_000_000_000)
                millions = int((price % 1_000_000_000) // 1_000_000)
                if millions > 0:
                    return f"{billions} میلیارد و {millions} میلیون تومان"
                else:
                    return f"{billions} میلیارد تومان"
            else:
                millions = int(price // 1_000_000)
                return f"{millions} میلیون تومان"
        
        return f"{format_price(lower)} تا {format_price(upper)}"


def main():
    """Example usage of the standalone calculator"""
    
    # Example 1: Basic calculation
    print("=== Example 1: 3-year-old car with minor damages ===")
    
    base_price = 500000000  # 500 million tomans
    car_age = 3
    car_kilometers = 75000  # 75,000 km
    
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
    
    result = CarPriceCalculator.calculate_used_car_price(
        base_price=base_price,
        car_age=car_age,
        car_kilometers=car_kilometers,
        damages=damages
    )
    
    print(f"Base Price: {result['base_price']:,} tomans")
    print(f"Final Price: {result['final_price']:,.0f} tomans")
    print(f"Price Range: {CarPriceCalculator.format_price_range(result)}")
    print(f"Annual Depreciation: {result['annual_depreciation']:.2%}")
    print(f"Kilometer Depreciation: {result['kilometer_depreciation']:.2%}")
    print(f"Condition Factor: {result['condition_factor']:.3f}")
    print()


if __name__ == "__main__":
    main() 