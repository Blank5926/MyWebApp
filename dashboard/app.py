import requests
from flask import Flask, render_template, request
from datetime import datetime, timedelta
import json
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env
api_key = os.getenv("API_KEY")
# API Configuration
BASE_URL = "https://anywhere-solutions-pty-ltd.booqable.com/api/boomerang"


# Fetch all product groups
def get_product_groups():
    response = requests.get(f"{BASE_URL}/product_groups", headers={"Authorization": f"Bearer {API_KEY}"})
    return response.json()['product_groups']

# # Fetch active orders
# def get_orders(start_date, end_date):
#     response = requests.get(f"{BASE_URL}/orders?include=lines", headers={"Authorization": f"Bearer {API_KEY}"})
#     return response.json()['orders']

def build_url_w_params(url, params):
    query_string = "&".join(f"{key}={value}" for key, value in params)
    full_url = f"{url}?{query_string}"
    print(full_url)
    return full_url

def get_orders_by_time_period(start_date, end_date):
    url = f"{BASE_URL}/orders"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = [
        ("sort", "-number"),
        ("filter[conditions][operator]", "or"),
        ("filter[conditions][attributes][][operator]", "and"),
        ("filter[conditions][attributes][][attributes][][starts_at][gte]", start_date),
        ("filter[conditions][attributes][][attributes][][starts_at][lte]", end_date),
        ("filter[conditions][attributes][][operator]", "and"),
        ("filter[conditions][attributes][][attributes][][stops_at][gte]", start_date),
        ("filter[conditions][attributes][][attributes][][stops_at][lte]", end_date),
        ("filter[statuses][not_eq][]", "canceled"),
        ("filter[statuses][not_eq][]", "archived"),
        ("filter[statuses][not_eq][]", "new"),
        ("stats[tag_list][]", "count"),
        ("stats[statuses][]", "count"),
        ("stats[payment_status][]", "count"),
        ("stats[total]", "count"),
        ("include", "customer%2Cstart_location%2Cstop_location")
    ]

    full_url = build_url_w_params(url, params)
    response = requests.get(full_url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("data")
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return []

def get_order_details(order_id):
    url = f"{BASE_URL}/orders/{order_id}?include=lines"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    response = requests.get(url, headers=headers)
    return response.json()

from dataclasses import dataclass
@dataclass
class OrderLine:
    client_code: str
    order_number: int
    job_site: str
    units: int
    product_name: str

# Combine data for dashboard
def create_dashboard_data(start_date, end_date):
    orders = get_orders_by_time_period(start_date, end_date)
    order_lines = []
    for order in orders:
        order_number = order['attributes']['number']
        job_site = order['attributes']['properties'].get('job_site', '')
        client_code = order['attributes']['properties'].get('client_code', '')
        order_id = order['id']
        order_details = get_order_details(order_id=order_id)
        for line in order_details['included']:
            product_name = line['attributes']['title']
            units = line['attributes']['quantity']

            line = OrderLine(client_code=client_code, order_number=order_number, job_site=job_site, units=units, product_name=product_name)
            order_lines.append(line)

    return order_lines

def process_data(data):
    summary = defaultdict(int)
    for line in data:
        summary[line.product_name] += line.units

    # Convert to a list of dictionaries for easier template usage
    summary_list = [{"name": product, "units": units} for product, units in summary.items()]
    return summary_list

app = Flask(__name__)

@app.route("/")
def dashboard():
    # Get current week's data
    # get the date of 3 weeks ago
    delt = timedelta(days = 21)
    today = datetime.today() - delt
    start_date = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    end_date = (today - timedelta(days=today.weekday() - 6)).strftime('%Y-%m-%d')
    print("Generating report for week starting from", start_date, "to", end_date)
    data = create_dashboard_data(start_date, end_date)
    product_summary = process_data(data)
    print(product_summary)
    return render_template("dashboard.html", orders=data, product_summary=product_summary,
                           start_date=start_date, end_date=end_date)

if __name__ == "__main__":
    app.run(debug=True)
