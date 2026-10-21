
import json
import os
import time
import pika


def consume_orders(on_order):
    # Read RabbitMQ connection settings
    rabbitmq_url = os.environ.get(
        "RABBITMQ_CONNECTION_STRING",
        "amqp://guest:guest@localhost:5672/"
    )

    while True:
        connection = None

        try:
            # Connect to RabbitMQ
            parameters = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Use the same queue as the Order Service
            channel.queue_declare(
                queue="order_queue",
                durable=True
            )

            # Process one unacknowledged message at a time
            channel.basic_qos(prefetch_count=1)

            # This function runs when a message arrives
            def callback(ch, method, properties, body):
                try:
                    # Convert JSON bytes into a Python dictionary
                    order = json.loads(body)

                    # Pass the order to our application
                    on_order(order)

                    # Confirm successful processing
                    ch.basic_ack(
                        delivery_tag=method.delivery_tag
                    )

                    print("Order received:", order)

                except (ValueError, TypeError, KeyError) as error:
                    print("Invalid order:", error)

                    # Reject invalid messages without requeueing
                    ch.basic_reject(
                        delivery_tag=method.delivery_tag,
                        requeue=False
                    )

            # Start listening for orders
            channel.basic_consume(
                queue="order_queue",
                on_message_callback=callback,
                auto_ack=False
            )

            print("Waiting for orders...")
            channel.start_consuming()

        except pika.exceptions.AMQPError as error:
            print("RabbitMQ connection error:", error)
            time.sleep(5)

        finally:
            if connection and connection.is_open:
                connection.close()
