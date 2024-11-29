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

                # Find all child-category divs (group names)
                group_elements = soup.find_all('div', class_='child-category')

                # List to store the group names and their corresponding products
                groups = {}

                for group_element in group_elements:
                    # Get the group name from the span within the div
                    group_name = group_element.find('span').text.strip()

                    # Find the next product containers after the group name
                    product_containers = group_element.find_all_next('li', class_='item product product-item')

                    # List to store all products under this group
                    products = []

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

                        # Append the product details to the list
                        products.append({
                            'group': group_name,  # Add the group field
                            'data_id': data_id,
                            'product_name': product_name,
                            'unit_price': unit_price,
                            'uom': uom
                        })

                    # Store the group and its products in the groups dictionary
                    groups[group_name] = products

                return groups

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
                # Flatten the groups into a single list of products
                for group, products in product_details.items():
                    all_products.extend(products)

        return all_products

    def write_to_csv(self, products, filename):
        fieldnames = ['group', 'data_id', 'product_name', 'unit_price', 'uom']

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