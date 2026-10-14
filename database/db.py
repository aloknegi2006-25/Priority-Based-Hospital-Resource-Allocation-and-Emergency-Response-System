"""
Database connection utility module.
Provides connection helper for MySQL using mysql-connector-python.
Phase B: Scaffolding only. Live database interactions are stubbed and deferred to Phase 3.
"""

import logging
from config import Config

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Attempts to establish a connection to the MySQL database using parameters from Config.
    Returns:
        connection object if successful, or None if MySQL is unreachable.
        
    TODO (Phase 3 - Alok Negi):
    1. Implement connection pooling using mysql.connector.pooling.MySQLConnectionPool
    2. Configure transaction isolation levels (Repeatable Read / Serializable)
    3. Add retry logic and proper context manager support (with get_db_connection() as conn:)
    """
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        return connection
    except ImportError:
        logger.warning("mysql-connector-python is not installed in the current environment.")
        return None
    except Exception as e:
        logger.warning("Could not connect to MySQL database at %s:%s. Details: %s", Config.DB_HOST, Config.DB_PORT, str(e))
        return None

def check_db_health():
    """
    Lightweight health check probe for database connectivity.
    Returns:
        dict containing status and message.
    """
    conn = get_db_connection()
    if conn and conn.is_connected():
        conn.close()
        return {"status": "connected", "database": Config.DB_NAME}
    return {
        "status": "disconnected",
        "message": "MySQL server is currently unreachable. Scaffold runs safely in offline presentation mode."
    }
