CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);

INSERT INTO customers (id, name) VALUES
  (1, 'Alice'), (2, 'Bob'), (3, 'Carol'), (4, 'Dave'), (5, 'Erin');

-- Erin (id 5) has no orders this period and should still appear with 0.00.
INSERT INTO orders (id, customer_id, amount) VALUES
  (1, 1, 100.0), (2, 1, 50.0),
  (3, 2, 200.0),
  (4, 3, 75.0), (5, 3, 25.0),
  (6, 4, 300.0);
