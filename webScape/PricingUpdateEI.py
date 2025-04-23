#| Item	        | Documentation Notes                                         |
#|--------------|-------------------------------------------------------------|
#| Filename     | PricingUpdateEI.py                                          |
#| EntryPoint   | __main__                                                    |
#| Purpose      | get website data and store in a csv file                    |                   
#| Inputs       | url - is hard coded                                         |                                                                         
#| Outputs      | csv file                                                    |                                                           
#| Dependencies | requests, pandas, bs4/BeautifulSoup (html parser)           |                                     
#| By Name,Date | T.Sciple, 11/30/2024                                        |    

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time


def getWebData(url, all_product_data):
    try:
        # Make the HTTP request to fetch the page content with a timeout
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        if response.status_code == 200:
            # Parse the HTML page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Manually set the desired field names in table
            #               1.           2.           3.              4.        5.
            headers = ['group_name', 'data_id', 'product_Name', 'price_unit', 'uom']

            # Initialize Lists to hold all the product data and product_groups
            product_data = []
            product_groups = []

            # Get chunck of data associated with the group
            product_groups_data = soup.find_all('div', class_='products wrapper b2b-list products-b2b-list')
            
            # Loop through each product group and get the group name
            for group in product_groups_data:
                # Extract the group name (assuming it's inside a span tag)
                group_name = group.find('span')
                if group_name:
                    product_groups.append(group_name.text.strip())  # Add to product_groups list
        
            # Now create a separate loop to handle each product group
            for index, group_name in enumerate(product_groups):
                
                # create a separate object with the enumerated index
                table = soup.find_all('ol')[index+1]
                product_rows = table.find_all('li', class_='item product product-item')
        
                # Loop through the product rows
                for product in product_rows:
                    # 1. group_name field is already determined in the loop before 
                    #    'for index, group_name' therefore we don't need to set this value
                    # 2. Get the `data-id` from the `div` with class `product-item-info`
                    data_id = product.find('div', class_='product-item-info')['data-id'] \
                            if product.find('div', class_='product-item-info') else "N/A"
                                
                    #3. Get the Product Name
                    product_name = product.find('div', class_='product-name').text.strip()
                    product_name = product_name.replace("Product Name: ", "")  # Remove "Product Name: "

                    #4. Get the Product Unit Price in two steps
                    price_wrapper = product.find('span', class_='price-wrapper')
                    price_unit = price_wrapper['data-price-amount'] if price_wrapper else "0"
                    
                    #5. Get the unit of measure
                    uom_tag = product.find('span', class_='price-unit')
                    uom = uom_tag.text.strip().replace('/', '').replace('.', '') if uom_tag else "N/a"
                    
                    # Store the product data in the list
                    all_product_data.append({
                        'group_name': group_name,
                        'data_id': data_id,  # Placeholder for now
                        'product_Name': product_name,
                        'price_unit': price_unit,
                        'uom': uom
                    })
    except Exception as e:
        print(f"Error processing URL {url}: {e}")

if __name__ == "__main__":
    # List of URLs to scrape
    
    start_time = time.perf_counter()

    urls = [
        "https://www.wireandcableyourway.com/tray-cable-thhn-pvc",
        "https://www.wireandcableyourway.com/thhn-thwn"
    ]

    # Master list to store all product data from all URLs
    all_product_data = []

    # Loop through each URL
    for url in urls:
        print(f"Processing URL: {url}")
        getWebData(url, all_product_data)

    # Create a DataFrame from the aggregated product data
    headers = ['group_name', 'data_id', 'product_Name', 'price_unit', 'uom']

    df = pd.DataFrame(all_product_data, columns=headers)

    # Display DataFrame and save it as a CSV file
    print(df)
    df.to_csv("c:/dev/py/webscape/product_data.csv", index=False, sep='|')

    end_time = time.perf_counter()

    duration = end_time - start_time
    print("Duration: ", duration)