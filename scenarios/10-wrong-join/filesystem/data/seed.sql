CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, status TEXT);

INSERT INTO customers (id, name) VALUES
  (1, 'Alice'), (2, 'Bob'), (3, 'Carol'), (4, 'Dave'), (5, 'Erin');

-- Revenue counts PAID orders only; pending/refunded orders must NOT be summed.
-- Every customer must appear, including ones with no paid revenue (shown as 0).
INSERT INTO orders (id, customer_id, amount, status) VALUES
  (1, 1, 100.0, 'paid'),
  (2, 1, 50.0, 'pending'),     -- Alice: pending must NOT count -> 100.00
  (3, 2, 200.0, 'paid'),       -- Bob -> 200.00
  (4, 3, 75.0, 'paid'),
  (5, 3, 25.0, 'paid'),        -- Carol: two paid -> 100.00
  (6, 5, 40.0, 'paid');        -- Erin -> 40.00
-- Dave (id 4) has NO orders at all this period and must still appear with 0.00.
