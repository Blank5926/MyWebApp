import requests
import json

# Booqable API Configuration
access_token = ""
api_url = f'https://anywhere-solutions-pty-ltd.booqable.com/api/boomerang'

# Headers
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

def fetch_inventory_stock(product_group_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    params = {
        'filter[product_id]': product_group_id,  # Filter by product group
        'filter[status]': 'in_stock',  # Only fetch items in stock
        'stats[inventory_breakdown_type][]': 'sum',
        'stats[started][]': 'sum',
        'stats[status][]': 'sum',
        'stats[stock_count][]': 'sum',
    }

    response = requests.get(f"{api_url}/inventory_breakdowns", headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        
        inventory_info = data.get("data")[0]
        attributes = inventory_info.get("attributes", {})
        product_id = attributes.get("product_id", "N/A")
        stock_count = attributes.get("stock_count", 0)
        return {"Product ID": product_id, "Stock Count": stock_count}


    else:
        print(f"Failed to fetch inventory breakdowns. Status code: {response.status_code}")
        print(response.text)
        return []

def fetch_product_groups_sku(pg_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get(f"{api_url}/product_groups/{pg_id}", headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch product groups. Status code: {response.status_code}")
        print(response.text)
        return []

    data = response.json()
    the_data = data.get('data', [])
    attr = the_data.get('attributes')
    return attr.get('sku')

def fetch_product_groups():
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get(f"{api_url}/products?filter[archived]=false&filter[product_type]=consumable", headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch product groups. Status code: {response.status_code}")
        print(response.text)
        return []

    data = response.json()
    product_groups = data.get('data', [])
    import json
    results = []
    for group in product_groups:
        group_id = group.get('id', 'N/A')
        attributes = group.get('attributes', {})
        is_variant = attributes.get('variation')
        pg_id = attributes.get('product_group_id')
        if is_variant:
            variation_values = attributes.get('variation_values')
            if len(variation_values) > 1:
                print(f"SKU: {variation_values[1]}")
            else:
                print(f"SKU: {fetch_product_groups_sku(pg_id)}")
        else:
            print(f"SKU: {attributes.get('sku', 'None')}")
    
        print(attributes.get('name', 'Unnamed'))
        print(fetch_inventory_stock(group_id))
        results.append(group_id)

    print(len(results))
    return results


if __name__ == "__main__":
    fetch_product_groups()