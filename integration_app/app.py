import os
import csv
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta, timezone
from square.client import Client

# Initialize Square Client
client = Client(
    access_token=os.getenv("SQUARE_ACCESS_TOKEN"),  # Store securely
    environment="production"  # Change to "sandbox" for testing
)
location_id = "LG3ZXFCTEXV12"

# MySQL Database Connection
def connect_db():
    return mysql.connector.connect(
        host="YOUR_MYSQL_HOST",  # e.g., "localhost"
        user="YOUR_MYSQL_USER",
        password="YOUR_MYSQL_PASSWORD",
        database="square_sales"
    )

# Check if order exists in MySQL
def is_order_processed(order_id, cursor):
    query = "SELECT COUNT(*) FROM sold_items WHERE order_id = %s"
    cursor.execute(query, (order_id,))
    return cursor.fetchone()[0] > 0

# Save new sales data to MySQL
def save_sold_items(sold_items):
    db = connect_db()
    cursor = db.cursor()

    recovered_orders = []

    for item in sold_items:
        if not is_order_processed(item["order_id"], cursor):
            query = """
            INSERT INTO sold_items (order_id, sku, quantity, created_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (item["order_id"], item["sku"], item["quantity"], item["created_at"]))

            # Track recovered orders
            recovered_orders.append(item)

    db.commit()
    cursor.close()
    db.close()

    return recovered_orders

# Save orders to a CSV file
def save_to_csv(sold_items, filename):
    if not sold_items:
        print("No new sales to save in CSV.")
        return

    keys = ["order_id", "sku", "quantity", "created_at"]
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(sold_items)

    print(f"📁 CSV file saved: {filename}")

def get_skus_for_orders(client, orders):
    """
    Given a list of order objects, return a list of tuples: (order_id, catalog_object_id, sku, quantity).
    """
    # 1. Gather all catalog_object_ids
    catalog_ids = set()
    for order in orders:
        for item in order.get("line_items", []):
            catalog_object_id = item.get("catalog_object_id")
            if catalog_object_id:
                catalog_ids.add(catalog_object_id)

    # 2. Batch retrieve all item variations in one go
    if not catalog_ids:
        return []  # No catalog items to retrieve
    
    catalog_response = client.catalog.batch_retrieve_catalog_objects(
        body={"object_ids": list(catalog_ids)}
    )
    
    if not catalog_response.is_success():
        print("Error in batch retrieval:", catalog_response.errors)
        return []

    # Map catalog_object_id -> SKU
    sku_map = {}
    retrieved_objects = catalog_response.body.get("objects", [])
    for obj in retrieved_objects:
        if obj.get("type") == "ITEM_VARIATION":
            sku = obj.get("item_variation_data", {}).get("sku", None)
            sku_map[obj["id"]] = sku

    # 3. Build the result: For each line item, get the SKU from the map
    results = []
    for order in orders:
        order_id = order.get("id")
        for item in order.get("line_items", []):
            catalog_object_id = item.get("catalog_object_id")
            quantity = item.get("quantity")
            sku = sku_map.get(catalog_object_id, None)
            results.append((order_id, catalog_object_id, sku, quantity))

    return results

def get_time_range(hours=0, days=0, weeks=0):
    """
    Returns a (start_iso, end_iso) tuple for the specified time window.
    - hours, days, and weeks are integers that will be summed up into a single timedelta.
    """
    now = datetime.now(timezone.utc)
    delta = timedelta(hours=hours, days=days, weeks=weeks)
    start_time = now - delta
    
    # Convert to ISO 8601 strings as required by the Square API
    start_iso = start_time.isoformat()
    end_iso = now.isoformat()
    
    return start_iso, end_iso

# Fetch sales data from Square API
def search_completed_orders_in_time_window(client, location_id, hours=0, days=0, weeks=0):
    """
    Search completed orders that occurred within the last 'hours', 'days', or 'weeks'.
    Returns a list of orders.
    """
    start_at, end_at = get_time_range(hours, days, weeks)
    
    # Build the request with date/time filter and state filter
    request_body = {
        "location_ids": [location_id],
        "query": {
            "filter": {
                "state_filter": {
                    "states": ["COMPLETED"]
                },
                "date_time_filter": {
                    "created_at": {
                        "start_at": start_at,  # Only orders created after this datetime
                        "end_at": end_at       # and before this datetime
                    }
                }
            }
        }
    }
    
    response = client.orders.search_orders(body=request_body)
    
    if response.is_success():
        return response.body.get("orders", [])
    else:
        print("Error searching orders:", response.errors)
        return []

def remove_stock(product_id, amount_to_remove)
    stock_count_url = "https://anywhere-solutions-pty-ltd.booqable.com/api/3/stock_counts"
    request_body = {
        "data": {
            "type":"stock_counts",
            "attributes": {
                "item_id": product_id,
                "quantity": -amount_to_remove
            }
        }
    }
    response = requests.post(stock_count_url, headers=headers, body=request_body)


# Auto-run for the last 1 hour (normal operation)
def run_hourly():
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    orders_last_week = search_completed_orders_in_time_window(client, location_id, hour=1)
    order_skus = get_skus_for_orders(client, orders_last_week)
    print(f"Found {len(orders_last_week)} completed orders in the last week.")

    # 5. Do something with the orders, e.g., print out line items
    for (order_id, cat_id, sku, qty) in order_skus:
            print(f"Order ID: {order_id} | Catalog Obj: {cat_id} | SKU: {sku} | Quantity: {qty}")

    fetch_sold_items(one_hour_ago.isoformat(), now.isoformat(), "hourly")

# Run manual recovery for a chosen date range
def recover_missed_orders(days_back):
    orders_last_week = search_completed_orders_in_time_window(client, location_id, days=1)
    order_skus = get_skus_for_orders(client, orders_last_week)
    print(f"Found {len(orders_last_week)} completed orders in the last week.")

    # 5. Do something with the orders, e.g., print out line items
    for (order_id, cat_id, sku, qty) in order_skus:
            print(f"Order ID: {order_id} | Catalog Obj: {cat_id} | SKU: {sku} | Quantity: {qty}")

# Choose between normal operation and recovery mode
if __name__ == "__main__":
    print("Choose an option:")
    print("1️⃣ Run normally (fetch last 1 hour)")
    print("2️⃣ Recover past orders (choose a time range)")

    choice = input("Enter 1 or 2: ")

    if choice == "1":
        run_hourly()
    elif choice == "2":
        days = int(input("Enter the number of days back to check (e.g., 7 for last week, 30 for last month): "))
        recover_missed_orders(days)
    else:
        print("❌ Invalid choice. Exiting.")


# pip install squareup mysql-connector-python pandas

# CREATE DATABASE square_sales;

# USE square_sales;

# CREATE TABLE sold_items (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     order_id VARCHAR(50) UNIQUE NOT NULL,
#     sku VARCHAR(50) NOT NULL,
#     quantity INT NOT NULL,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
