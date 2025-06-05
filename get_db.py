from contextlib import contextmanager
from database import conectar
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_db():
    conn = None
    cur = None
    try:
        conn = conectar()
        cur = conn.cursor()
        yield conn, cur
    finally:
        if cur:
            logger.info("Fechando cursor")
            cur.close()
        if conn:
            logger.info("Fechando cursor")
            conn.close()