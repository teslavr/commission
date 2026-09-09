"""Deliberately bad. Two real defects, one N+1 and one accidental O(n^2)."""
import sqlite3


def order_report(db_path, customer_ids):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    customers = []
    for cid in customer_ids:
        cur.execute("SELECT id, name FROM customers WHERE id = ?", (cid,))
        row = cur.fetchone()
        if row:
            customers.append(row)

    all_orders = cur.execute("SELECT id, customer_id, total FROM orders").fetchall()

    report = []
    for cust_id, name in customers:
        mine = []
        for order in all_orders:
            if order[1] == cust_id:
                mine.append(order)
        report.append({"customer": name, "orders": len(mine), "total": sum(o[2] for o in mine)})

    return report
