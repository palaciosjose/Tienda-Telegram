import sqlite3
import atexit
import files

_connection = None
_connection_path = None

def get_db_connection():
    """Return a cached connection to the main database."""
    global _connection, _connection_path

    if _connection is None or _connection_path != files.main_db:
        if _connection is not None:
            try:
                _connection.close()
            except Exception:
                pass
        _connection = sqlite3.connect(files.main_db, check_same_thread=False)
        _connection_path = files.main_db
    else:
        try:
            _connection.cursor()
        except sqlite3.ProgrammingError:
            _connection = sqlite3.connect(files.main_db, check_same_thread=False)
            _connection_path = files.main_db

    return _connection

def close_connection():
    """Close the cached database connection if it exists."""
    global _connection, _connection_path
    if _connection is not None:
        _connection.close()
        _connection = None
        _connection_path = None

atexit.register(close_connection)
