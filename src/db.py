from datetime import date

import psycopg2

from src.config import DATABASE_URL

CREATE_PERSONA = """
CREATE TABLE IF NOT EXISTS persona (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
);
"""

SEED_PERSONAS = """
INSERT INTO persona (nombre) VALUES ('Rafa'), ('Sergio')
ON CONFLICT (nombre) DO NOTHING;
"""

CREATE_EXAMENES = """
CREATE TABLE IF NOT EXISTS examenes (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES persona(id),
    fecha DATE NOT NULL,
    num_examenes INTEGER NOT NULL CHECK (num_examenes > 0),
    num_aprobados INTEGER NOT NULL CHECK (num_aprobados >= 0),
    CHECK (num_aprobados <= num_examenes)
);
"""


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_PERSONA)
            cur.execute(SEED_PERSONAS)
            cur.execute(CREATE_EXAMENES)
        conn.commit()


def obtener_personas() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre FROM persona ORDER BY nombre")
            return [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]


def buscar_persona_por_nombre(nombre: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre FROM persona WHERE LOWER(nombre) = LOWER(%s)",
                (nombre,),
            )
            row = cur.fetchone()
            return {"id": row[0], "nombre": row[1]} if row else None


def registrar_examen(persona_id: int, fecha: date, num_examenes: int, num_aprobados: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO examenes (persona_id, fecha, num_examenes, num_aprobados) VALUES (%s, %s, %s, %s)",
                (persona_id, fecha, num_examenes, num_aprobados),
            )
        conn.commit()
