import requests
import csv
from bs4 import BeautifulSoup

class ProductScraper:
    def __init__(self, base_url, product_paths):
        # Initialize with a base URL and a list of product paths
        self.base_url = base_url
        self.product_paths = product_paths
    
    def get_product_details(self, url):
        try:
            # Make the HTTP request to fetch the page content with a timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                # Parse the HTML page
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all product containers (assuming each product is in an <li> tag)
                product_containers = soup.find_all('div', class_='product-item-info')

                # List to store all products
                products = []

                # Loop through all the product containers and extract details
                for container in product_containers:
                    # Extract the data-id (used as a key for the database)
                    data_id = container.get('data-id', 'N/A')

                    # Extract product name
                    product_name_tag = container.find('a')
                    product_name = product_name_tag.text.strip() if product_name_tag else "N/A"
                    
                    # Extract price
                    price_tag = container.find('span', class_='price')
                    unit_price = price_tag.text.strip() if price_tag else "N/A"

                    # Extract the unit of measure (UOM) like '/ft'
                    uom_tag = container.find('span', class_='price-unit')
                    uom = uom_tag.text.strip().replace('/', '').replace('.', '') if uom_tag else "N/A"
                    uom = uom_tag.text.strip() if uom_tag else "N/A"

                    # Remove the '/' from the UOM
                    uom = uom.replace('/', '').strip()                    

                    # Append the product details to the list
                    products.append({
                        'data_id': data_id,
                        'product_name': product_name,
                        'unit_price': unit_price,
                        'uom': uom
                    })

                return products
            else:
                print(f"Failed to fetch the webpage: {response.status_code}")
                return []

        except requests.exceptions.Timeout:
            print(f"Request timed out while trying to fetch the URL: {url}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {str(e)}")
            return []

    def scrape_products(self):
        # List to store all products across all product pages
        all_products = []

        for path in self.product_paths:
            # Construct the full URL for each product page
            url = f"{self.base_url}{path}"
            product_details = self.get_product_details(url)
            if product_details:
                all_products.extend(product_details)

        return all_products

    def write_to_csv(self, products, filename):
        fieldnames = ['data_id', 'product_name', 'unit_price', 'uom']

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='|')
            writer.writeheader()

            for product in products:
                writer.writerow(product)

        print(f"Data written to {filename}")


# Main function to drive the script
def main():
    # The base URL for the website
    base_url = "https://www.wireandcableyourway.com"

    # List of product paths (you can add more paths here)
    product_paths = [
        "/tray-cable-thhn-pvc",
        "/18-2c-thhn-pvc-tray-cable"
    ]

    # Create an instance of ProductScraper
    scraper = ProductScraper(base_url, product_paths)

    # Scrape the products
    products = scraper.scrape_products()

    # If products were found, write them to a CSV
    if products:
        scraper.write_to_csv(products, 'products.csv')
    else:
        print("No products found.")

# Entry point of the program
if __name__ == "__main__":
    main()
