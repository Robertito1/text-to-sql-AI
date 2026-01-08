import random
from datetime import datetime, timedelta
from faker import Faker
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables from .env file (in server folder)
load_dotenv('server/.env')

# Initialize Faker
fake = Faker()

# Database connection
conn_str = os.getenv("ODBC_STR")
if not conn_str:
    raise ValueError("ODBC_STR environment variable not found. Please check your .env file")

print(f"Connecting to database with connection string: {conn_str[:30]}...")  # Print first 30 chars for debugging

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Clear existing data
    print("Clearing existing data...")
    cursor.execute("IF OBJECT_ID('Orders', 'U') IS NOT NULL DELETE FROM Orders")
    cursor.execute("IF OBJECT_ID('Customers', 'U') IS NOT NULL DELETE FROM Customers")
    conn.commit()

    # Create tables if they don't exist
    print("Creating tables if they don't exist...")
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Customers')
    CREATE TABLE Customers (
        CustomerId INT PRIMARY KEY,
        Name NVARCHAR(100),
        Email NVARCHAR(255),
        Country NVARCHAR(100),
        CreatedAt DATETIME2
    )
    """)
    
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Orders')
    CREATE TABLE Orders (
        OrderId INT PRIMARY KEY,
        CustomerId INT FOREIGN KEY REFERENCES Customers(CustomerId),
        OrderDate DATETIME2,
        Amount DECIMAL(18,2),
        Status NVARCHAR(50)
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

        # Insert in batches of 100
        if i % 100 == 0:
            cursor.executemany("""
                INSERT INTO Customers (CustomerId, Name, Email, Country, CreatedAt)
                VALUES (?, ?, ?, ?, ?)
            """, customers)
            conn.commit()
            customers = []
            print(f"Inserted {i} customers...")

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

        # Insert in batches of 1000
        if i % 1000 == 0:
            cursor.executemany("""
                INSERT INTO Orders (OrderId, CustomerId, OrderDate, Amount, Status)
                VALUES (?, ?, ?, ?, ?)
            """, orders)
            conn.commit()
            orders = []
            print(f"Inserted {i} orders...")

    print("\nData generation complete!")

except pyodbc.Error as e:
    print(f"Database error: {e}")
    if 'conn' in locals():
        conn.rollback()
    raise
finally:
    if 'conn' in locals():
        conn.close()