import os
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_conn():
    """Devuelve conexion psycopg o None (modo memoria/mock si no hay DB)."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg
        return psycopg.connect(DATABASE_URL)
    except Exception:
        return None
