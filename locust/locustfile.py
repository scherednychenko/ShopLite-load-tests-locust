"""
ShopLite load test — Locust.

Mirrors the JMeter/k6 scenario: Browse catalog -> Add to cart (N items) -> Checkout,
against placeholder endpoints served by the local mock backend.
"""
import os
import random
import uuid

from locust import HttpUser, task, between

CART_SIZE = int(os.getenv("CART_SIZE", "10"))
PRODUCTS = ["1001", "1002", "1003"]


class ShopLiteUser(HttpUser):
    # Think time between full journeys (seconds).
    wait_time = between(0.3, 1.2)

    @task
    def journey(self):
        # --- Browse catalog ---
        with self.client.get(
            "/api/catalog?page=1&size=20",
            name="TX_Browse_Catalog",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"unexpected status {r.status_code}")

        # --- Add to cart (CART_SIZE items), correlate cartId ---
        cart_id = None
        for _ in range(CART_SIZE):
            with self.client.post(
                "/api/cart/items",
                json={"productId": random.choice(PRODUCTS), "qty": 1},
                name="TX_Add_To_Cart",
                catch_response=True,
            ) as r:
                if r.status_code in (200, 201):
                    try:
                        cart_id = r.json().get("cartId")
                    except ValueError:
                        pass
                else:
                    r.failure(f"unexpected status {r.status_code}")

        # --- Checkout, unique guest data ---
        payload = {
            "cartId": cart_id,
            "guest": {
                "email": f"qa.perf+{uuid.uuid4().hex[:8]}@example.com",
                "firstName": "Perf",
                "lastName": "Guest",
                "phone": "+10000000000",
            },
            "shippingAddress": {
                "country": "HR",
                "city": "Zagreb",
                "addressLine1": "Perf Street 1",
                "zip": "10000",
            },
        }
        with self.client.post(
            "/api/orders",
            json=payload,
            name="TX_Checkout_PlaceOrder",
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 201):
                r.failure(f"unexpected status {r.status_code}")
