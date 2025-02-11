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

# Fetch sales data from Square API
def fetch_sold_items(start_date, end_date, csv_prefix):
    body = {
        "location_ids": ["YOUR_LOCATION_ID"],  # Replace with your Square location ID
        "query": {
            "filter": {
                "date_time_filter": {
                    "created_at": {
                        "start_at": start_date,
                        "end_at": end_date
                    }
                }
            }
        }
    }

    result = client.orders.search_orders(body)

    if result.is_success():
        orders = result.body.get("orders", [])
        new_sold_items = []

        for order in orders:
            order_id = order.get("id")
            created_at = order.get("created_at")  # Timestamp from Square

            for item in order.get("line_items", []):
                sku = item.get("catalog_object_id")
                quantity = int(item.get("quantity", 0))

                if sku and quantity > 0:
                    new_sold_items.append({"order_id": order_id, "sku": sku, "quantity": quantity, "created_at": created_at})

        if new_sold_items:
            recovered_orders = save_sold_items(new_sold_items)

            # Generate timestamp for CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{csv_prefix}_{timestamp}.csv"

            save_to_csv(new_sold_items, filename)

            if recovered_orders:
                print("✅ Recovered missing sales data:")
                for item in recovered_orders:
                    print(f"Order ID: {item['order_id']}, SKU: {item['sku']}, Quantity: {item['quantity']}, Date: {item['created_at']}")
            else:
                print("✅ No missing orders found in this time period.")

        else:
            print("No new orders found in this time range.")

    elif result.is_error():
        print("❌ Error fetching orders:", result.errors)

# Auto-run for the last 1 hour (normal operation)
def run_hourly():
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    fetch_sold_items(one_hour_ago.isoformat(), now.isoformat(), "hourly")

# Run manual recovery for a chosen date range
def recover_missed_orders(days_back):
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days_back)

    print(f"⏳ Checking for missing orders from {start_date.date()} to {now.date()}...")
    fetch_sold_items(start_date.isoformat(), now.isoformat(), "recovered")

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
