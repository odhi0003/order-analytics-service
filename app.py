
from flask import Flask, jsonify
import threading
from consumer import consume_orders

# Create our Flask application
app = Flask(__name__)

# Store orders received from RabbitMQ
orders = []
orders_lock = threading.Lock()


# Save incoming orders from RabbitMQ

def save_order(order):
    # Check that the order is a JSON object
    if not isinstance(order, dict):
        raise ValueError("Order must be a JSON object")

    # Check required fields
    if "product" not in order:
        raise ValueError("Missing product")

    if "quantity" not in order:
        raise ValueError("Missing quantity")

    if "totalPrice" not in order:
        raise ValueError("Missing totalPrice")

    # Check product information
    product = order["product"]

    if not isinstance(product, dict):
        raise ValueError("Product must be an object")

    if "id" not in product or "name" not in product:
        raise ValueError("Missing product id or name")

    if not isinstance(product["id"], int) or isinstance(product["id"], bool):
        raise ValueError("Product id must be an integer")

    if not isinstance(product["name"], str) or not product["name"].strip():
        raise ValueError("Product name must be a non-empty string")

    # Check quantity
    quantity = order["quantity"]

    if type(quantity) is not int or quantity <= 0:
        raise ValueError("Quantity must be a positive integer")

    # Check total price
    total_price = order["totalPrice"]

    if type(total_price) not in (int, float):
        raise ValueError("Total price must be a number")

    if not 0 <= total_price < float("inf"):
        raise ValueError("Total price must be finite and non-negative")

    # Save the validated order
    with orders_lock:
        orders.append(order)

    print("Order saved:", order)


# Safely read a copy of all orders
def get_orders_snapshot():
    with orders_lock:
        return list(orders)


# 1. Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "order-analytics-service"
    })


# 2. Get all orders
@app.route('/orders', methods=['GET'])
def get_orders():
    current_orders = get_orders_snapshot()
    return jsonify(current_orders)


# 3. Summary analytics
@app.route('/analytics/summary', methods=['GET'])
def analytics_summary():
    current_orders = get_orders_snapshot()

    total_orders = len(current_orders)

    total_revenue = sum(
        float(order.get('totalPrice', 0))
        for order in current_orders
    )

    average_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )

    return jsonify({
        "totalOrders": total_orders,
        "totalRevenue": round(total_revenue, 2),
        "averageOrderValue": round(average_order_value, 2)
    })


# 4. Analytics for each product
@app.route('/analytics/products', methods=['GET'])
def analytics_products():
    current_orders = get_orders_snapshot()
    products = {}

    for order in current_orders:
        product = order['product']
        product_id = str(product['id'])

        if product_id not in products:
            products[product_id] = {
                "productId": product['id'],
                "productName": product['name'],
                "orderCount": 0,
                "totalRevenue": 0
            }

        products[product_id]['orderCount'] += 1
        products[product_id]['totalRevenue'] += float(
            order['totalPrice']
        )

    for product in products.values():
        product['totalRevenue'] = round(
            product['totalRevenue'], 2
        )

    return jsonify(list(products.values()))


# 5. Top 3 products by quantity sold
@app.route('/analytics/top-products', methods=['GET'])
def analytics_top_products():
    current_orders = get_orders_snapshot()
    products = {}

    for order in current_orders:
        product = order['product']
        product_id = str(product['id'])
        quantity = int(order['quantity'])

        if product_id not in products:
            products[product_id] = {
                "productId": product['id'],
                "productName": product['name'],
                "totalQuantity": 0
            }

        products[product_id]['totalQuantity'] += quantity

    top_products = sorted(
        products.values(),
        key=lambda product: product['totalQuantity'],
        reverse=True
    )

    return jsonify(top_products[:3])


# Start the RabbitMQ consumer and Flask application
if __name__ == '__main__':

    # Run RabbitMQ consumer in a background thread
    consumer_thread = threading.Thread(
        target=consume_orders,
        args=(save_order,),
        daemon=True
    )

    consumer_thread.start()

    # Start Flask REST API
    app.run(
        host='0.0.0.0',
        port=4000,
        debug=False
    )
