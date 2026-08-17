import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2

# Load environment variables
dotenv_paths = ['server/.env', '.env']
for dotenv_path in dotenv_paths:
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        break

# Override with correct region if needed
if os.getenv("DATABASE_URL") and "us-west-1" in os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL").replace("us-west-1", "us-west-2")

# Configuration
YEAR = 2026
START_DATE = datetime(YEAR, 1, 1, 0, 0, 0)
END_DATE = datetime(YEAR, 8, 15, 23, 59, 59)
TOTAL_ORDERS = 10000
BATCH_SIZE = 1000

# Date range in seconds for uniform random sampling
date_range_seconds = int((END_DATE - START_DATE).total_seconds())

# Database connection
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable not found. Please check your .env file")

print("Connecting to PostgreSQL database...")

try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Get the current max OrderId so we don't collide with existing rows
    cursor.execute("SELECT COALESCE(MAX(OrderId), 0) FROM Orders")
    max_order_id = cursor.fetchone()[0]
    print(f"Current max OrderId: {max_order_id}")

    # Verify customers exist
    cursor.execute("SELECT COUNT(*) FROM Customers")
    customer_count = cursor.fetchone()[0]
    if customer_count == 0:
        raise ValueError("No customers found. Run populate_database_postgres.py first.")
    print(f"Found {customer_count} customers")

    # Generate 10,000 new orders
    print("\nGenerating new orders...")
    statuses = ['PAID', 'PENDING', 'CANCELLED']
    orders = []
    for i in range(TOTAL_ORDERS):
        order_id = max_order_id + i + 1
        customer_id = random.randint(1, customer_count)
        order_date = START_DATE + timedelta(seconds=random.randint(0, date_range_seconds))
        amount = round(random.uniform(10, 1000), 2)
        status = random.choice(statuses)
        orders.append((order_id, customer_id, order_date, amount, status))

    # Insert in batches
    print("\nInserting orders...")
    for i in range(0, len(orders), BATCH_SIZE):
        batch = orders[i:i+BATCH_SIZE]
        cursor.executemany(
            """
            INSERT INTO Orders (OrderId, CustomerId, OrderDate, Amount, Status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            batch
        )
        conn.commit()
        print(f"  Inserted {min(i + BATCH_SIZE, len(orders))} / {TOTAL_ORDERS} orders...")

    # Sanity check
    cursor.execute("SELECT COUNT(*) FROM Orders")
    final_count = cursor.fetchone()[0]
    print(f"\nDone. Total orders in table now: {final_count}")

except psycopg2.Error as e:
    print(f"Database error: {e}")
    if 'conn' in locals():
        conn.rollback()
    raise
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
