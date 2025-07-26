import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CarPriceScraper:
    def __init__(self):
        self.base_url = "https://www.hamrah-mechanic.com/carprice/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_page_content(self, url: str) -> BeautifulSoup:
        """Fetch and parse the webpage content"""
        try:
            logger.info(f"Fetching content from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching page: {e}")
            return None
    
    def clean_price(self, price_text: str) -> str:
        """Clean and extract price from text"""
        if not price_text:
            return ""
        
        # Remove extra whitespace and newlines
        price_text = re.sub(r'\s+', ' ', price_text.strip())
        
        # Extract price pattern (numbers followed by تومان)
        price_match = re.search(r'([\d,]+)\s*تومان', price_text)
        if price_match:
            return price_match.group(1).replace(',', '')
        
        return price_text
    
    def clean_car_name(self, car_name: str) -> str:
        """Clean car name text"""
        if not car_name:
            return ""
        
        # Remove extra whitespace and newlines
        car_name = re.sub(r'\s+', ' ', car_name.strip())
        
        # Remove common unwanted patterns
        car_name = re.sub(r'قیمت\s+محصولات\s+', '', car_name)
        car_name = re.sub(r'خرید\s+تضمینی\s+محصولات\s+', '', car_name)
        
        return car_name
    
    def extract_car_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract car data from the webpage"""
        cars_data = []
        
        # Find all car brand sections using the specific CSS class
        brand_sections = soup.find_all('div', class_='carsBrandPriceList_price-list__0BSbT')
        
        logger.info(f"Found {len(brand_sections)} brand sections")
        
        for section in brand_sections:
            # Get the brand name from the brand section
            brand_name_elem = section.find('div', class_='carsBrandPriceList_brand__name__Ohntn')
            if not brand_name_elem:
                continue
                
            brand_name = brand_name_elem.get_text(strip=True)
            brand_name = self.clean_car_name(brand_name)
            
            # Find the table within this section
            table = section.find('table', class_='carsBrandPriceList_price-table__Z04ZN')
            if not table:
                continue
            
            # Extract rows from the table
            rows = table.find_all('tr', class_='carsBrandPriceList_price-table__row__Ev8Ts')
            
            for row in rows:
                # Get car name and details
                car_name_cell = row.find('td', class_='carsBrandPriceList_price-table__right-content__nl31g')
                price_cell = row.find('td', class_='carsBrandPriceList_price-table__left-content__VRcOA')
                
                if not car_name_cell or not price_cell:
                    continue
                
                # Extract car name and type
                car_link = car_name_cell.find('a', class_='carsBrandPriceList_model__auHvZ')
                if car_link:
                    car_name_elem = car_link.find('div', class_='carsBrandPriceList_model__name__fYre5')
                    car_type_elem = car_link.find('div', class_='carsBrandPriceList_model__type__1L_I7')
                    
                    car_name = car_name_elem.get_text(strip=True) if car_name_elem else ""
                    car_type = car_type_elem.get_text(strip=True) if car_type_elem else ""
                    
                    # Combine car name and type
                    full_car_model = f"{car_name} {car_type}".strip()
                else:
                    full_car_model = car_name_cell.get_text(strip=True)
                
                # Extract price
                price_link = price_cell.find('a', class_='carsBrandPriceList_price__zz8Fs')
                if price_link:
                    price_number_elem = price_link.find('div', class_='carsBrandPriceList_price__number__APBu0')
                    price_unit_elem = price_link.find('div', class_='carsBrandPriceList_price__unit__Hjahg')
                    
                    price_number = price_number_elem.get_text(strip=True) if price_number_elem else ""
                    price_unit = price_unit_elem.get_text(strip=True) if price_unit_elem else ""
                    price_text = f"{price_number} {price_unit}".strip()
                    price = self.clean_price(price_text)
                else:
                    price_text = price_cell.get_text(strip=True)
                    price = self.clean_price(price_text)
                
                # Combine brand name with car model
                full_car_name = f"{brand_name} {full_car_model}" if brand_name else full_car_model
                
                # Create car data entry (removed scraped_at, url, and price_text)
                car_data = {
                    'brand': brand_name,
                    'car_name': full_car_model,
                    'full_car_name': full_car_name,
                    'price': price
                }
                
                cars_data.append(car_data)
                logger.info(f"Extracted: {full_car_name} - {price}")
        
        return cars_data
    
    def scrape_car_prices(self) -> List[Dict[str, Any]]:
        """Main method to scrape car prices"""
        logger.info("Starting car price scraping...")
        
        soup = self.get_page_content(self.base_url)
        if not soup:
            logger.error("Failed to fetch page content")
            return []
        
        cars_data = self.extract_car_data(soup)
        
        logger.info(f"Successfully scraped {len(cars_data)} car entries")
        return cars_data
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str = 'car_prices.json'):
        """Save scraped data to JSON file"""
        try:
            # Create the data directory path
            import os
            data_dir = '.'
            os.makedirs(data_dir, exist_ok=True)
            
            # Full path for the file
            file_path = os.path.join(data_dir, filename)
            
            output_data = {
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source_url': self.base_url,
                'total_cars': len(data),
                'cars': data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Data saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            return False

def main():
    """Main function to run the scraper"""
    scraper = CarPriceScraper()
    
    try:
        # Scrape car prices
        cars_data = scraper.scrape_car_prices()
        
        if cars_data:
            # Save to JSON file
            success = scraper.save_to_json(cars_data, 'car_prices.json')
            
            if success:
                print(f"\n✅ Successfully scraped {len(cars_data)} car prices!")
                print("📁 Data saved to 'khodroyar/data/car_prices.json'")
                
                # Print sample data
                print("\n📊 Sample data:")
                for i, car in enumerate(cars_data[:5]):
                    print(f"{i+1}. {car['full_car_name']} - {car['price']} تومان")
                
                if len(cars_data) > 5:
                    print(f"... and {len(cars_data) - 5} more cars")
            else:
                print("❌ Failed to save data to JSON file")
        else:
            print("❌ No car data found")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main() 