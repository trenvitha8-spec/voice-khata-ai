
from backend.database import get_db_connection


def add_customer(name):
    name = name.strip()

    if not name:
        raise ValueError("Customer name cannot be empty.")

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM customers WHERE name = ? COLLATE NOCASE",
            (name,)
        ).fetchone()

        if existing:
            return existing["id"]

        cursor = conn.execute(
            "INSERT INTO customers (name) VALUES (?)",
            (name,)
        )

        return cursor.lastrowid


def record_transaction(customer_name, transaction_type, amount, description=""):
    transaction_type = transaction_type.upper()

    if transaction_type not in ("CREDIT", "PAYMENT"):
        raise ValueError("Invalid transaction type.")

    amount = float(amount)

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    customer_id = add_customer(customer_name)

    with get_db_connection() as conn:
        if transaction_type == "PAYMENT":
            balance = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE
                        WHEN transaction_type = 'CREDIT'
                        THEN amount ELSE -amount END), 0) AS balance
                FROM transactions
                WHERE customer_id = ?
                """,
                (customer_id,)
            ).fetchone()["balance"]

            if amount > balance:
                raise ValueError("Payment exceeds the outstanding balance.")

        conn.execute(
            """
            INSERT INTO transactions
            (customer_id, transaction_type, amount, description)
            VALUES (?, ?, ?, ?)
            """,
            (customer_id, transaction_type, amount, description)
        )

    return f"{transaction_type} of ₹{amount:.2f} recorded for {customer_name}."


def get_customer_balance(customer_name):
    with get_db_connection() as conn:
        customer = conn.execute(
            "SELECT id, name FROM customers WHERE name = ? COLLATE NOCASE",
            (customer_name.strip(),)
        ).fetchone()

        if not customer:
            return None

        balance = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE
                    WHEN transaction_type = 'CREDIT'
                    THEN amount ELSE -amount END), 0) AS balance
            FROM transactions
            WHERE customer_id = ?
            """,
            (customer["id"],)
        ).fetchone()["balance"]

        return {
            "customer": customer["name"],
            "balance": round(balance, 2)
        }


def get_transaction_history(customer_name):
    with get_db_connection() as conn:
        return conn.execute(
            """
            SELECT t.transaction_type, t.amount,
                   t.description, t.created_at
            FROM transactions t
            JOIN customers c ON c.id = t.customer_id
            WHERE c.name = ? COLLATE NOCASE
            ORDER BY t.id DESC
            """,
            (customer_name.strip(),)
        ).fetchall()


def get_all_customers():
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT id, name FROM customers ORDER BY name"
        ).fetchall()

def add_product(name, price, quantity=0):
    name = name.strip()

    if not name:
        raise ValueError("Product name cannot be empty.")

    if price < 0 or quantity < 0:
        raise ValueError("Price and quantity cannot be negative.")

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM products WHERE name = ? COLLATE NOCASE",
            (name,)
        ).fetchone()

        if existing:
            raise ValueError("Product already exists.")

        cursor = conn.execute(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            (name, price)
        )

        product_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO stock (product_id, quantity) VALUES (?, ?)",
            (product_id, quantity)
        )

    return f"{name} added successfully with stock {quantity}."


def update_stock(product_name, quantity_change):
    with get_db_connection() as conn:
        product = conn.execute(
            "SELECT id FROM products WHERE name = ? COLLATE NOCASE",
            (product_name.strip(),)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        current = conn.execute(
            "SELECT quantity FROM stock WHERE product_id = ?",
            (product["id"],)
        ).fetchone()

        new_quantity = current["quantity"] + quantity_change

        if new_quantity < 0:
            raise ValueError("Insufficient stock.")

        conn.execute(
            """
            UPDATE stock
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (new_quantity, product["id"])
        )

    return f"{product_name} stock updated. Available quantity: {new_quantity}."


def get_stock(product_name):
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT p.name, p.price, s.quantity
            FROM products p
            JOIN stock s ON p.id = s.product_id
            WHERE p.name = ? COLLATE NOCASE
            """,
            (product_name.strip(),)
        ).fetchone()

        if not result:
            return None

        return dict(result)


def get_all_products():
    with get_db_connection() as conn:
        return [
            dict(row) for row in conn.execute(
                """
                SELECT p.name, p.price, s.quantity
                FROM products p
                JOIN stock s ON p.id = s.product_id
                ORDER BY p.name
                """
            ).fetchall()
        ]

def record_sale(product_name, quantity, payment_method="CASH"):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    payment_method = payment_method.upper()

    if payment_method not in ("CASH", "UPI", "CARD"):
        raise ValueError("Invalid payment method.")

    with get_db_connection() as conn:
        product = conn.execute(
            """
            SELECT p.id, p.name, p.price, s.quantity
            FROM products p
            JOIN stock s ON p.id = s.product_id
            WHERE p.name = ? COLLATE NOCASE
            """,
            (product_name.strip(),)
        ).fetchone()

        if not product:
            raise ValueError("Product not found.")

        if product["quantity"] < quantity:
            raise ValueError("Insufficient stock.")

        total = product["price"] * quantity

        cursor = conn.execute(
            """
            INSERT INTO sales (total_amount, payment_method)
            VALUES (?, ?)
            """,
            (total, payment_method)
        )

        sale_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO sale_items
            (sale_id, product_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sale_id, product["id"], quantity,
             product["price"], total)
        )

        remaining = product["quantity"] - quantity

        conn.execute(
            """
            UPDATE stock
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (remaining, product["id"])
        )

    return {
        "product": product["name"],
        "quantity_sold": quantity,
        "total": total,
        "remaining_stock": remaining,
        "payment_method": payment_method
    }


def get_today_sales():
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT COUNT(*) AS number_of_sales,
                   COALESCE(SUM(total_amount), 0) AS total_sales
            FROM sales
            WHERE DATE(created_at) = DATE('now', 'localtime')
            """
        ).fetchone()

        return dict(result)

# ---------------- EXPENSE MANAGEMENT ----------------

def record_expense(category, amount, description=""):
    if not category or not category.strip():
        raise ValueError("Expense category is required.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (category, amount, description)
            VALUES (?, ?, ?)
            """,
            (category.strip(), amount, description.strip())
        )

    return {
        "message": "Expense recorded successfully.",
        "category": category.strip(),
        "amount": amount,
        "description": description
    }


def get_today_expenses():
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT COUNT(*) AS number_of_expenses,
                   COALESCE(SUM(amount), 0) AS total_expenses
            FROM expenses
            WHERE DATE(created_at) = DATE('now', 'localtime')
            """
        ).fetchone()

        return dict(result)


def get_all_expenses():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, category, amount, description, created_at
            FROM expenses
            ORDER BY id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


# ---------------- BUSINESS SUMMARY ----------------

def get_total_outstanding_balance():
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN transaction_type = 'CREDIT' THEN amount
                        WHEN transaction_type = 'PAYMENT' THEN -amount
                    END
                ), 0
            ) AS outstanding_balance
            FROM transactions
            """
        ).fetchone()

        return result["outstanding_balance"]


def get_daily_business_summary():
    sales = get_today_sales()
    expenses = get_today_expenses()
    outstanding = get_total_outstanding_balance()

    return {
        "total_sales": sales["total_sales"],
        "number_of_sales": sales["number_of_sales"],
        "total_expenses": expenses["total_expenses"],
        "number_of_expenses": expenses["number_of_expenses"],
        "sales_minus_expenses": sales["total_sales"] - expenses["total_expenses"],
        "customer_outstanding": outstanding
    }


# ---------------- SUPPLIER MANAGEMENT ----------------

def add_supplier(name, phone=""):
    if not name or not name.strip():
        raise ValueError("Supplier name is required.")

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE",
            (name.strip(),)
        ).fetchone()

        if existing:
            return "Supplier already exists."

        conn.execute(
            "INSERT INTO suppliers (name, phone) VALUES (?, ?)",
            (name.strip(), phone.strip())
        )

    return f"Supplier {name} added successfully."


def get_all_suppliers():
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM suppliers ORDER BY name"
        ).fetchall()

        return [dict(row) for row in rows]


# ---------------- PURCHASE MANAGEMENT ----------------

def record_purchase(supplier_name, product_name, quantity, unit_price):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")

    if not supplier_name or not supplier_name.strip():
        raise ValueError("Supplier name is required.")

    if not product_name or not product_name.strip():
        raise ValueError("Product name is required.")

    with get_db_connection() as conn:
        supplier = conn.execute(
            "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE",
            (supplier_name.strip(),)
        ).fetchone()

        if not supplier:
            raise ValueError("Supplier not found. Add the supplier first.")

        product = conn.execute(
            "SELECT id, name FROM products WHERE name = ? COLLATE NOCASE",
            (product_name.strip(),)
        ).fetchone()

        if not product:
            raise ValueError("Product not found. Add the product first.")

        total = quantity * unit_price

        cursor = conn.execute(
            """
            INSERT INTO purchases (supplier_id, total_amount)
            VALUES (?, ?)
            """,
            (supplier["id"], total)
        )

        purchase_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO purchase_items
            (purchase_id, product_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
            """,
            (purchase_id, product["id"], quantity, unit_price, total)
        )

        conn.execute(
            """
            UPDATE stock
            SET quantity = quantity + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
            """,
            (quantity, product["id"])
        )

    return {
        "message": "Purchase recorded successfully.",
        "supplier": supplier_name,
        "product": product["name"],
        "quantity_purchased": quantity,
        "total_amount": total
    }


def get_purchase_history():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, s.name AS supplier,
                   pr.name AS product,
                   pi.quantity, pi.unit_price,
                   pi.subtotal, p.created_at
            FROM purchases p
            JOIN suppliers s ON p.supplier_id = s.id
            JOIN purchase_items pi ON p.id = pi.purchase_id
            JOIN products pr ON pi.product_id = pr.id
            ORDER BY p.id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

