SCHEMA_SNIPPETS = [
    """
    Table: Customers
    Description: Stores customer profiles.
    Columns:
      - CustomerId (INTEGER, primary key)
      - Name (VARCHAR(100))
      - Email (VARCHAR(255))
      - Country (VARCHAR(100))
      - CreatedAt (TIMESTAMP, signup timestamp)
    Example query:
      SELECT Country, COUNT(*) AS CustomerCount
      FROM Customers
      GROUP BY Country;
    """,
    """
    Table: Orders
    Description: Stores purchase orders made by customers.
    Columns:
      - OrderId (INTEGER, primary key)
      - CustomerId (INTEGER, foreign key to Customers.CustomerId)
      - OrderDate (TIMESTAMP, order timestamp)
      - Amount (DECIMAL(18,2), order total)
      - Status (VARCHAR(50), e.g. 'PAID','PENDING','CANCELLED')
    Example query:
      SELECT TO_CHAR(OrderDate, 'YYYY-MM') AS YearMonth,
             SUM(Amount) AS TotalRevenue
      FROM Orders
      WHERE Status = 'PAID'
      GROUP BY TO_CHAR(OrderDate, 'YYYY-MM');
    """
]
