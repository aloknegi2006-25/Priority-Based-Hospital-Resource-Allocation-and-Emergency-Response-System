"""
Database connection, query utility, and transaction module.
Provides connection helper, parameterized query execution, and atomic transaction context.
Supports MySQL via mysql-connector-python and isolated test database execution.
"""

import logging
from contextlib import contextmanager
from flask import current_app, has_app_context
from config import Config

logger = logging.getLogger(__name__)

class TransactionContext:
    """Helper wrapper for multi-statement atomic transactions."""
    def __init__(self, conn, is_sqlite=False):
        self.conn = conn
        self.is_sqlite = is_sqlite
        if is_sqlite:
            self.cursor = conn.cursor()
        else:
            self.cursor = conn.cursor(dictionary=True)
        self.lastrowid = None
        self.rowcount = 0

    def execute(self, sql, params=None):
        params = params or ()
        query = sql
        if self.is_sqlite:
            query = query.replace('FOR UPDATE', '').replace('%s', '?')
        self.cursor.execute(query, params)
        self.lastrowid = self.cursor.lastrowid
        self.rowcount = self.cursor.rowcount
        return self.cursor

    def fetchone(self, sql, params=None):
        self.execute(sql, params)
        row = self.cursor.fetchone()
        if row and self.is_sqlite:
            return dict(row)
        return row

    def fetchall(self, sql, params=None):
        self.execute(sql, params)
        rows = self.cursor.fetchall()
        if self.is_sqlite:
            return [dict(r) for r in rows]
        return rows


def get_db_connection():
    """
    Establishes and returns a database connection.
    Defaults to MySQL using mysql.connector with credentials from Config.
    If running under testing mode (TESTING=True), connects to isolated test database.
    """
    is_testing = False
    if has_app_context():
        is_testing = current_app.config.get('TESTING', False)

    if is_testing:
        import sqlite3
        test_db_path = current_app.config.get('TEST_DB_PATH', ':memory:')
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # Production & Development: MySQL via mysql-connector-python
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=False
        )
        return connection
    except ImportError:
        logger.error("mysql-connector-python is not installed in the current environment.")
        return None
    except Exception as e:
        logger.warning(
            "Could not connect to MySQL database '%s' at %s:%s. Details: %s",
            Config.DB_NAME, Config.DB_HOST, Config.DB_PORT, str(e)
        )
        return None


@contextmanager
def get_db_transaction():
    """
    Context manager for multi-query atomic transactions.
    Rolls back automatically on exception, commits on success, and closes resources.

    Usage:
        with get_db_transaction() as tx:
            tx.execute("UPDATE ...")
            tx.execute("INSERT ...")
    """
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError(
            f"Database connection unavailable. Ensure MySQL server is running at {Config.DB_HOST}:{Config.DB_PORT}."
        )

    is_sqlite = (type(conn).__module__ == 'sqlite3')
    tx = TransactionContext(conn, is_sqlite=is_sqlite)
    try:
        yield tx
        conn.commit()
    except Exception as err:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error("Transaction rolled back due to error: %s", str(err))
        raise err
    finally:
        try:
            tx.cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def execute_query(sql, params=None, fetch=None):
    """
    Executes a single parameterized SQL query safely.

    Args:
        sql (str): SQL query string (%s placeholders).
        params (tuple or list, optional): Parameters for SQL binding.
        fetch (str, optional): 'all' to fetchall, 'one' to fetchone, or None for write operations.

    Returns:
        dict, list of dicts, lastrowid, or None depending on fetch parameter.
    """
    with get_db_transaction() as tx:
        if fetch == 'all':
            return tx.fetchall(sql, params)
        elif fetch == 'one':
            return tx.fetchone(sql, params)
        else:
            tx.execute(sql, params)
            return tx.lastrowid


def check_db_health():
    """
    Lightweight health check probe for database connectivity.
    Returns:
        dict containing status and message.
    """
    conn = get_db_connection()
    if conn:
        try:
            is_sqlite = (type(conn).__module__ == 'sqlite3')
            if is_sqlite:
                conn.close()
                return {"status": "connected", "database": "sqlite_test_env"}
            if conn.is_connected():
                conn.close()
                return {"status": "connected", "database": Config.DB_NAME}
        except Exception:
            pass
    return {
        "status": "disconnected",
        "message": f"MySQL server at {Config.DB_HOST}:{Config.DB_PORT} is currently unreachable."
    }
