"""SQLite storage layer for the My Lending web application."""

import sqlite3
from datetime import datetime
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


class LendingDatabase:
    """Encapsulates all persistence used by the web application."""

    def __init__(self, database_path: str = "my_lending.db"):
        self.path = Path(database_path)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower TEXT NOT NULL,
                contact TEXT,
                principal REAL NOT NULL,
                monthly_interest REAL NOT NULL,
                months INTEGER NOT NULL,
                total_interest REAL NOT NULL,
                total_payable REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                paid_at TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY (loan_id) REFERENCES loans(id)
            );
            """
        )
        self.connection.commit()

    # ---------------------------------------------------------------- auth
    def has_admin(self) -> bool:
        return self.connection.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None

    def create_user(self, username, password):
        self.connection.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username.strip(), generate_password_hash(password), datetime.now().isoformat(timespec="seconds")),
        )
        self.connection.commit()

    def verify_user(self, username, password):
        row = self.connection.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return row
        return None

    def get_user(self, user_id):
        return self.connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def update_password(self, user_id, new_password):
        self.connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )
        self.connection.commit()

    # --------------------------------------------------------------- loans
    def add_loan(self, borrower, contact, principal, monthly_interest, months):
        # Total interest is the entered monthly percentage multiplied by term months.
        total_interest = principal * (monthly_interest / 100) * months
        total_payable = principal + total_interest
        cursor = self.connection.execute(
            """INSERT INTO loans (borrower, contact, principal, monthly_interest, months,
               total_interest, total_payable, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (borrower, contact, principal, monthly_interest, months, total_interest,
             total_payable, datetime.now().isoformat(timespec="seconds")),
        )
        self.connection.commit()
        return cursor.lastrowid

    def add_payment(self, loan_id, amount, paid_at, note=""):
        self.connection.execute(
            "INSERT INTO payments (loan_id, amount, paid_at, note) VALUES (?, ?, ?, ?)",
            (loan_id, amount, paid_at, note),
        )
        self.connection.commit()

    def loans(self):
        return self.connection.execute(
            """SELECT l.*, COALESCE(SUM(p.amount), 0) AS paid,
               l.total_payable - COALESCE(SUM(p.amount), 0) AS balance
               FROM loans l LEFT JOIN payments p ON p.loan_id = l.id
               GROUP BY l.id ORDER BY l.id DESC"""
        ).fetchall()

    def loan_choices(self):
        return self.connection.execute(
            "SELECT id, borrower FROM loans WHERE status='Active' ORDER BY borrower"
        ).fetchall()

    def payments(self):
        return self.connection.execute(
            """SELECT p.*, l.borrower FROM payments p JOIN loans l ON l.id=p.loan_id
               ORDER BY p.paid_at DESC, p.id DESC"""
        ).fetchall()

    def search_loans(self, search_text=""):
        """Return loan summaries filtered by borrower name, contact, or loan ID."""
        term = f"%{search_text.strip()}%"
        return self.connection.execute(
            """SELECT l.*, COALESCE(SUM(p.amount), 0) AS paid,
               l.total_payable - COALESCE(SUM(p.amount), 0) AS balance
               FROM loans l LEFT JOIN payments p ON p.loan_id = l.id
               WHERE l.borrower LIKE ? OR l.contact LIKE ? OR CAST(l.id AS TEXT) LIKE ?
               GROUP BY l.id ORDER BY l.borrower COLLATE NOCASE""",
            (term, term, term),
        ).fetchall()

    def loan_detail(self, loan_id):
        """Return one loan with its calculated payment totals."""
        return self.connection.execute(
            """SELECT l.*, COALESCE(SUM(p.amount), 0) AS paid,
               l.total_payable - COALESCE(SUM(p.amount), 0) AS balance
               FROM loans l LEFT JOIN payments p ON p.loan_id = l.id
               WHERE l.id = ? GROUP BY l.id""", (loan_id,)
        ).fetchone()

    def loan_payments(self, loan_id):
        return self.connection.execute(
            "SELECT * FROM payments WHERE loan_id = ? ORDER BY paid_at DESC, id DESC", (loan_id,)
        ).fetchall()

    def update_borrower_name(self, loan_id, borrower_name):
        """Rename the borrower shown for a loan record."""
        self.connection.execute("UPDATE loans SET borrower = ? WHERE id = ?", (borrower_name, loan_id))
        self.connection.commit()

    def delete_loan(self, loan_id):
        """Remove a loan and its dependent payment history as one action."""
        self.connection.execute("DELETE FROM payments WHERE loan_id = ?", (loan_id,))
        self.connection.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
        self.connection.commit()

    def summary(self):
        return self.connection.execute(
            """SELECT COUNT(*) AS borrowers, COALESCE(SUM(principal),0) AS released,
               COALESCE(SUM(total_payable),0) AS receivable,
               COALESCE((SELECT SUM(amount) FROM payments),0) AS collected FROM loans"""
        ).fetchone()

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.commit()
        self.connection.close()
