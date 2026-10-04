import psycopg2
from psycopg2.extras import RealDictCursor


def conectar():
    return psycopg2.connect(
        host="localhost",
        port=2020,
        dbname="ejercicios_db",
        user="postgres",
        password="lina123"
    )


def guardar(sql, parametros, varios=False):
    """INSERT / UPDATE / DELETE sin devolver datos."""
    conexion = conectar()
    try:
        with conexion:
            with conexion.cursor() as cursor:
                if varios:
                    cursor.executemany(sql, parametros)
                else:
                    cursor.execute(sql, parametros)
    finally:
        conexion.close()


def consultar(sql, parametros=None):
    """SELECT (o INSERT ... RETURNING). Devuelve lista de diccionarios."""
    conexion = conectar()
    try:
        with conexion:
            with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, parametros)
                if cursor.description:
                    return cursor.fetchall()
                return []
    finally:
        conexion.close()