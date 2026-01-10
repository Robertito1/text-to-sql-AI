import random
from datetime import datetime, timedelta
from faker import Faker
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('server/.env')

# Override with correct region if needed
import os
if os.getenv("DATABASE_URL") and "us-west-1" in os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL").replace("us-west-1", "us-west-2")

# Initialize Faker
fake = Faker()

# Database connection
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable not found. Please check your .env file")

print(f"Connecting to PostgreSQL database...")

try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Clear existing data
    print("Clearing existing data...")
    cursor.execute("DROP TABLE IF EXISTS Orders CASCADE")
    cursor.execute("DROP TABLE IF EXISTS Customers CASCADE")
    conn.commit()

    # Create tables
    print("Creating tables...")
    cursor.execute("""
    CREATE TABLE Customers (
        CustomerId INTEGER PRIMARY KEY,
        Name VARCHAR(100),
        Email VARCHAR(255),
        Country VARCHAR(100),
        CreatedAt TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE Orders (
        OrderId INTEGER PRIMARY KEY,
        CustomerId INTEGER REFERENCES Customers(CustomerId),
        OrderDate TIMESTAMP,
        Amount DECIMAL(18,2),
        Status VARCHAR(50)
    )
    """)
    conn.commit()

    # Generate and insert 1000 customers
    print("Inserting customers...")
    countries = ['USA', 'Canada', 'UK', 'Germany', 'France', 'Japan', 'Australia', 'Brazil']
    customers = []
    for i in range(1, 1001):
        customer = (
            i,  # CustomerId
            fake.name(),
            fake.email(),
            random.choice(countries),
            datetime.now() - timedelta(days=random.randint(1, 365))
        )
        customers.append(customer)

    cursor.executemany("""
        INSERT INTO Customers (CustomerId, Name, Email, Country, CreatedAt)
        VALUES (%s, %s, %s, %s, %s)
    """, customers)
    conn.commit()
    print(f"Inserted {len(customers)} customers")

    # Generate and insert 10,000 orders
    print("\nInserting orders...")
    statuses = ['PAID', 'PENDING', 'CANCELLED']
    orders = []
    for i in range(1, 10001):
        order = (
            i,  # OrderId
            random.randint(1, 1000),  # CustomerId
            datetime.now() - timedelta(days=random.randint(1, 365)),  # OrderDate (last 12 months)
            round(random.uniform(10, 1000), 2),  # Amount
            random.choice(statuses)
        )
        orders.append(order)

    # Insert in batches
    batch_size = 1000
    for i in range(0, len(orders), batch_size):
        batch = orders[i:i+batch_size]
        cursor.executemany("""
            INSERT INTO Orders (OrderId, CustomerId, OrderDate, Amount, Status)
            VALUES (%s, %s, %s, %s, %s)
        """, batch)
        conn.commit()
        print(f"Inserted {min(i+batch_size, len(orders))} orders...")

    print("\nData generation complete!")

except psycopg2.Error as e:
    print(f"Database error: {e}")
    if 'conn' in locals():
        conn.rollback()
    raise
finally:
    if 'conn' in locals():
        conn.close()
