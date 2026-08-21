"""
SmartShed AI - Database Helper Layer
Handles MySQL connections, parameterized query executions, transaction rollbacks,
and dictionary cursor management using mysql-connector-python.
"""

import mysql.connector
from mysql.connector import Error, pooling
from backend.config import Config

def get_db_connection(use_database=True):
    """
    Establishes and returns a connection to the MySQL server.
    """
    try:
        config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
            "charset": "utf8mb4",
            "autocommit": False,
            "connection_timeout": 5
        }
        if use_database:
            config["database"] = Config.DB_NAME

        conn = mysql.connector.connect(**config)
        return conn
    except Error as e:
        raise ConnectionError(f"Database connection error: {str(e)}")

def test_connection():
    """
    Tests whether the MySQL server is reachable and credentials are valid.
    """
    try:
        conn = get_db_connection(use_database=False)
        if conn.is_connected():
            conn.close()
            return True, "Connected successfully to MySQL server."
        return False, "Failed to connect to MySQL server."
    except Exception as e:
        return False, str(e)

def execute_query(query, params=None, fetch=None, commit=False):
    """
    Executes a parameterized SQL query safely.
    
    Args:
        query (str): SQL statement with %s placeholders.
        params (tuple/list/dict, optional): Parameters for the query.
        fetch (str, optional): 'all' for fetchall(), 'one' for fetchone(), 'rowcount' for affected rows, None for nothing.
        commit (bool): Whether to commit the transaction.
        
    Returns:
        Results as list of dicts, single dict, inserted ID, or rowcount.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection(use_database=True)
        # Using dictionary=True for clean key-based column access in templates/scheduler
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        result = None
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        elif fetch == "lastrowid":
            result = cursor.lastrowid
        elif fetch == "rowcount":
            result = cursor.rowcount

        if commit:
            conn.commit()
            if fetch == "lastrowid":
                result = cursor.lastrowid

        return result
    except Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def execute_transaction(queries_with_params):
    """
    Executes a list of (query, params) in a single atomic transaction.
    If any query fails, the entire batch is rolled back.
    
    Args:
        queries_with_params (list): List of tuples [(query1, params1), (query2, params2), ...]
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor(dictionary=True)
        for query, params in queries_with_params:
            cursor.execute(query, params or ())
        conn.commit()
        return True
    except Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def execute_script(sql_file_path):
    """
    Executes a multi-statement SQL script file (e.g., schema.sql).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection(use_database=False)
        cursor = conn.cursor()
        with open(sql_file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Split statements on semicolon ignoring empty blocks
        for statement in sql_script.split(";"):
            cleaned = statement.strip()
            if cleaned:
                cursor.execute(cleaned)
        conn.commit()
        return True, "Schema executed successfully."
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
