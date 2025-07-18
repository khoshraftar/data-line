#!/usr/bin/env python3
"""
Working Car Price Scraper for Iran Jib Website
Based on successful debug findings
Now supports multiple URLs and data combination
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv
import logging
import re
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkingCarPriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
        })
    
    def convert_persian_numbers(self, text):
        """Convert Persian numbers to English numbers"""
        if not text:
            return text
        
        persian_to_english = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
        }
        
        for persian, english in persian_to_english.items():
            text = text.replace(persian, english)
        
        return text
    
    def clean_price(self, price_text):
        """Clean and standardize price text"""
        if not price_text:
            return None
        
        # Convert Persian numbers to English
        price_text = self.convert_persian_numbers(price_text.strip())
        
        # Remove non-numeric characters except commas
        price_text = re.sub(r'[^\d,]', '', price_text)
        
        # Remove commas and convert to integer
        try:
            price_numeric = int(price_text.replace(',', ''))
            return price_numeric
        except ValueError:
            return None
    
    def scrape_car_prices(self, url, source_name=None):
        """Main method to scrape car prices from a single URL"""
        logger.info(f"Starting to scrape car prices from: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables")
            
            cars_data = []
            
            if len(tables) >= 2:
                # Use the second table (index 1) which contains car data
                table = tables[1]
                rows = table.find_all('tr')
                logger.info(f"Processing {len(rows)} rows in table 2")
                
                for row in rows:
                    # Skip expandable rows (chart rows)
                    if 'expand' in row.get('class', []):
                        continue
                    
                    cells = row.find_all('td')
                    
                    if len(cells) >= 3:
                        car_data = {}
                        
                        # Add source information
                        if source_name:
                            car_data['source'] = source_name
                            car_data['source_url'] = url
                        
                        # First cell with entryrtl class contains car name
                        first_cell = cells[0]
                        if first_cell.get('class') and 'entryrtl' in first_cell.get('class'):
                            car_link = first_cell.find('a')
                            if car_link:
                                car_name = car_link.get_text(strip=True)
                                car_data['car_name'] = car_name
                                
                                # Get car URL if available
                                car_url = car_link.get('href')
                                if car_url and car_url != '#':
                                    car_data['car_url'] = car_url
                        
                        # Second cell contains current price
                        if len(cells) > 1:
                            current_price_text = cells[1].get_text(strip=True)
                            if current_price_text:
                                current_price_numeric = self.clean_price(current_price_text)
                                car_data['current_price'] = current_price_text
                                car_data['current_price_numeric'] = current_price_numeric
                        
                        # Third cell contains previous price
                        if len(cells) > 2:
                            previous_price_text = cells[2].get_text(strip=True)
                            if previous_price_text:
                                previous_price_numeric = self.clean_price(previous_price_text)
                                car_data['previous_price'] = previous_price_text
                                car_data['previous_price_numeric'] = previous_price_numeric
                        
                        # Fourth cell contains change percentage
                        if len(cells) > 3:
                            change_text = cells[3].get_text(strip=True)
                            if change_text:
                                # Extract percentage from text like "(۰.۰۰%)۰"
                                percentage_match = re.search(r'\(([^)]+)\)', change_text)
                                if percentage_match:
                                    car_data['change_percentage'] = percentage_match.group(1)
                                else:
                                    car_data['change_percentage'] = change_text
                        
                        # Only add if we have a car name
                        if car_data.get('car_name'):
                            cars_data.append(car_data)
            
            logger.info(f"Found {len(cars_data)} car entries from {url}")
            return cars_data
            
        except Exception as e:
            logger.error(f"Error scraping data from {url}: {e}")
            return []
    
    def scrape_multiple_urls(self, urls_with_names):
        """Scrape car prices from multiple URLs and combine the data"""
        all_cars_data = []
        
        for url, source_name in urls_with_names:
            logger.info(f"Scraping from source: {source_name}")
            cars_data = self.scrape_car_prices(url, source_name)
            all_cars_data.extend(cars_data)
            
            # Add a small delay between requests to be respectful
            import time
            time.sleep(2)
        
        logger.info(f"Total combined entries: {len(all_cars_data)}")
        return all_cars_data
    
    def save_to_json(self, cars_data, filename="iran_car_prices_combined.json"):
        """Save car data to JSON file in the khodroyar/data directory"""
        if not cars_data:
            logger.warning("No data to save")
            return
        
        try:
            # Create the data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(__file__), 'khodroyar', 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Full path to the JSON file
            file_path = os.path.join(data_dir, filename)
            
            # Save a JSON version with only car_name and current_price_numeric
            simplified_data = []
            for car in cars_data:
                simplified_car = {
                    'car_name': car.get('car_name', ''),
                    'current_price': car.get('current_price_numeric', None)
                }
                simplified_data.append(simplified_car)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(simplified_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Data saved to {file_path}")
            logger.info(f"Successfully saved {len(cars_data)} car entries")
            
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def print_sample_data(self, cars_data, num_samples=10):
        """Print sample data for verification"""
        if not cars_data:
            logger.info("No data to display")
            return
        
        logger.info(f"Sample data (showing first {min(num_samples, len(cars_data))} entries):")
        for i, car in enumerate(cars_data[:num_samples]):
            logger.info(f"Entry {i+1}: {car}")
        
        # Print summary statistics
        if cars_data:
            prices_with_numeric = [car for car in cars_data if car.get('current_price_numeric') is not None]
            
            logger.info(f"Total entries: {len(cars_data)}")
            logger.info(f"Entries with numeric prices: {len(prices_with_numeric)}")
            
            # Show breakdown by source
            sources = {}
            for car in cars_data:
                source = car.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            
            logger.info("Breakdown by source:")
            for source, count in sources.items():
                logger.info(f"  {source}: {count} entries")
            
            # Show price range if available
            if prices_with_numeric:
                prices = [car['current_price_numeric'] for car in prices_with_numeric]
                min_price = min(prices)
                max_price = max(prices)
                logger.info(f"Price range: {min_price:,} to {max_price:,} Toman")

def main():
    """Main function to run the working scraper with multiple URLs"""
    scraper = WorkingCarPriceScraper()
    
    # Define URLs with their source names
    urls_with_names = [
        ("https://www.iranjib.ir/showgroup/45/", "Group 45"),
        ("https://www.iranjib.ir/showgroup/46/", "Group 46")
    ]
    
    try:
        # Scrape car prices from multiple URLs
        cars_data = scraper.scrape_multiple_urls(urls_with_names)
        
        if cars_data:
            # Print sample data
            scraper.print_sample_data(cars_data)
            
            # Save to JSON in the new location
            scraper.save_to_json(cars_data, "iran_car_prices_combined.json")
            
            logger.info("Combined scraper completed successfully!")
        else:
            logger.warning("No car data found.")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 