import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "hbc_project_cost.db"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    conn.close()


def get_connection():
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            status TEXT DEFAULT 'Active',
            budget REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT UNIQUE NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            supplier_category TEXT,
            notes TEXT,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS gl_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gl_code TEXT UNIQUE NOT NULL,
            gl_account_name TEXT NOT NULL,
            reporting_category TEXT,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            project_code TEXT NOT NULL,
            project_name TEXT NOT NULL,
            supplier TEXT,
            invoice_number TEXT,
            reference_number TEXT,
            gl_code TEXT,
            gl_account_name TEXT,
            expense_category TEXT,
            description TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            amount REAL NOT NULL,
            payment_method TEXT,
            source TEXT DEFAULT 'Manual Entry',
            remarks TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edited_by TEXT,
            last_modified TEXT,
            imported_from TEXT,
            is_deleted INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT NOT NULL,
            project_name TEXT NOT NULL,
            gl_code TEXT,
            category TEXT,
            budget_amount REAL DEFAULT 0,
            actual_amount REAL DEFAULT 0,
            remaining_amount REAL DEFAULT 0,
            variance REAL DEFAULT 0,
            budget_used_pct REAL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT,
            rows_detected INTEGER,
            valid_rows INTEGER,
            duplicate_rows INTEGER,
            invalid_rows INTEGER,
            imported_by TEXT,
            summary TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id INTEGER,
            action TEXT,
            changed_by TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        );
        """
    )

    seed_default_data(conn)


def seed_default_data(conn):
    # Projects
    conn.execute(
        "INSERT OR IGNORE INTO projects (project_code, project_name, description, start_date, status, budget) VALUES (?, ?, ?, ?, ?, ?)",
        ("26061", "SEEF LUSAIL", "Modification of Fit Out", "2026-09-01", "Active", 1500000.00),
    )

    # Default GL mappings
    default_gls = [
        ("2500-020", "Consumables", "Consumables", 1),
        ("2500-025", "Sub Contractor", "Subcontractor", 1),
        ("2500-030", "Cement", "Cement", 1),
        ("2500-035", "Steel", "Steel", 1),
        ("2500-040", "Marble & Tiles", "Marble & Tiles", 1),
        ("2500-045", "Paint", "Paint", 1),
        ("2500-050", "Transportation", "Transportation", 1),
        ("2500-055", "Diesel & Petrol", "Diesel & Petrol", 1),
        ("2500-060", "MEP Supplies", "MEP Supplies", 1),
        ("2500-065", "Carpentry", "Carpentry", 1),
        ("2500-070", "Tools", "Tools", 1),
        ("2500-075", "Other", "Other", 1),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO gl_accounts (gl_code, gl_account_name, reporting_category, is_active) VALUES (?, ?, ?, ?)",
        default_gls,
    )

    # Some starter supplier records
    suppliers = [
        ("Al Jaber Trading", "Manager", "+974 0000 0000", "info@aljaber.example", "General", "Starter supplier"),
        ("Lusail Material Supply", "Procurement", "+974 1111 1111", "sales@lusailmaterial.example", "Material", "Starter supplier"),
        ("Qatar Transport Co.", "Operations", "+974 2222 2222", "ops@qatartransport.example", "Transport", "Starter supplier"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO suppliers (supplier_name, contact_person, phone, email, supplier_category, notes) VALUES (?, ?, ?, ?, ?, ?)",
        suppliers,
    )

    conn.commit()


def backup_database(destination_dir: str = None):
    backup_dir = Path(destination_dir) if destination_dir else Path(__file__).resolve().parent / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"hbc_project_cost_backup_{timestamp}.db"
    src = DB_PATH
    if src.exists():
        import shutil
        shutil.copy2(src, backup_path)
        return str(backup_path)
    return None
