"""PostgreSQL helpers."""
import psycopg2
from psycopg2.extras import execute_values

import config


def connect():
    return psycopg2.connect(**config.DB_CONFIG)


def insert(conn, table, columns, rows, on_conflict="ON CONFLICT DO NOTHING"):
    """Bulk insert in a single statement. Returns the number of rows written.

    The caller owns the transaction (commit / rollback).
    """
    if not rows:
        return 0
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s {on_conflict}"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=len(rows))
        return cur.rowcount
