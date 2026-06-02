CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL);
CREATE TABLE line_items (id INTEGER PRIMARY KEY, order_id INTEGER, sku TEXT);

INSERT INTO customers (id, name) VALUES
  (1, 'Alice'), (2, 'Bob'), (3, 'Carol'), (4, 'Dave'), (5, 'Erin');

-- Erin (id 5) has no orders this period and should still appear with 0.00.
INSERT INTO orders (id, customer_id, amount) VALUES
  (1, 1, 100.0), (2, 1, 50.0),
  (3, 2, 200.0),
  (4, 3, 75.0), (5, 3, 25.0),
  (6, 4, 300.0);

-- This period each order happens to have exactly one line item.
INSERT INTO line_items (id, order_id, sku) VALUES
  (1, 1, 'A'), (2, 2, 'B'), (3, 3, 'C'),
  (4, 4, 'D'), (5, 5, 'E'), (6, 6, 'F');
