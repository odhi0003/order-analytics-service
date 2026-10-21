
import threading

from app import app, save_order
from consumer import consume_orders

# Start RabbitMQ consumer in a background thread
consumer_thread = threading.Thread(
    target=consume_orders,
    args=(save_order,),
    daemon=True,
    name="rabbitmq-consumer"
)

consumer_thread.start()
