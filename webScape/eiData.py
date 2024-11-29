import requests
import csv
from bs4 import BeautifulSoup

# Function to scrape the product information
def get_product_details(url):
    try:
        # Make the HTTP request to fetch the page content with a timeout
        response = requests.get(url, timeout=10)  # Timeout set to 10 seconds
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        if response.status_code == 200:
            # Parse the HTML page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all product containers
            product_containers = soup.find_all('li', class_='item product product-item')
            
            # List to store the product details
            products = []

            if product_containers:
                # Loop through each product container and extract details
                for container in product_containers:
                    # Get the product name and URL
                    product_name_tag = container.find('a')
                    product_name = product_name_tag.text.strip() if product_name_tag else "N/A"
                    
                    # Get the price
                    price_tag = container.find('span', class_='price')
                    unit_price = price_tag.text.strip() if price_tag else "N/A"

                    # Append the product details to the list
                    products.append({
                        'product_name': product_name,
                        'unit_price': unit_price
                    })
                return products
            else:
                print("No product containers found.")
                return []

        else:
            print(f"Failed to fetch the webpage: {response.status_code}")
            return []

    except requests.exceptions.Timeout:
        print(f"Request timed out while trying to fetch the URL: {url}")
        return []
    except requests.exceptions.RequestException as e:
        # Catch all other request-related errors (e.g., network issues, invalid URL)
        print(f"An error occurred while fetching the URL: {url}\nError: {str(e)}")
        return []

# Function to write data to a CSV file
def write_to_csv(products, filename):
    # Define the column names for the CSV
    fieldnames = ['product_name','unit_price']

    # Open the file in write mode and create the CSV writer
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the header row
        writer.writeheader()

        # Write each product as a new row
        for product in products:
            writer.writerow(product)

    print(f"Data written to {filename}")

# Main function
def main():
    # Define the URL for the THHN/THWN product categories page
    url = "https://www.wireandcableyourway.com/thhn-thwn/"
    
    # Get the product details from the page
    products = get_product_details(url)

    # If products were found, write them to a CSV
    if products:
        filename = 'thhn_thwn_products.csv'  # You can specify the desired filename here
        write_to_csv(products, filename)
    else:
        print("No products found.")

# Entry point of the program
if __name__ == "__main__":
    main()