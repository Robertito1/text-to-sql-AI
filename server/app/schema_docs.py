SCHEMA_SNIPPETS = [
    """
    Table: Customers
    Description: Stores customer profiles.
    Columns:
      - CustomerId (int, primary key)
      - Name (nvarchar(100))
      - Email (nvarchar(255))
      - Country (nvarchar(100))
      - CreatedAt (datetime2, signup timestamp)
    Example query:
      SELECT Country, COUNT(*) AS CustomerCount
      FROM Customers
      GROUP BY Country;
    """,
    """
    Table: Orders
    Description: Stores purchase orders made by customers.
    Columns:
      - OrderId (int, primary key)
      - CustomerId (int, foreign key to Customers.CustomerId)
      - OrderDate (datetime2, order timestamp)
      - Amount (decimal(18,2), order total)
      - Status (nvarchar(50), e.g. 'PAID','PENDING','CANCELLED')
    Example query:
      SELECT FORMAT(OrderDate, 'yyyy-MM') AS YearMonth,
             SUM(Amount) AS TotalRevenue
      FROM Orders
      WHERE Status = 'PAID'
      GROUP BY FORMAT(OrderDate, 'yyyy-MM');
    """
]
