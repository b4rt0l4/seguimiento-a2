from __future__ import annotations

from datetime import date
from enum import Enum

import psycopg2

from src.config import DATABASE_URL


class TipoPersona(str, Enum):
    EXAMENES = "examenes"
    PREGUNTA = "pregunta"


COLUMN_BY_TIPO = {
    TipoPersona.EXAMENES: "puede_examenes",
    TipoPersona.PREGUNTA: "puede_pregunta",
}

CREATE_PERSONA = """
CREATE TABLE IF NOT EXISTS persona (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    puede_examenes BOOLEAN NOT NULL DEFAULT false,
    puede_pregunta BOOLEAN NOT NULL DEFAULT false
);
"""

ADD_COLUMNS_IF_MISSING = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'persona' AND column_name = 'puede_examenes') THEN
        ALTER TABLE persona ADD COLUMN puede_examenes BOOLEAN NOT NULL DEFAULT false;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'persona' AND column_name = 'puede_pregunta') THEN
        ALTER TABLE persona ADD COLUMN puede_pregunta BOOLEAN NOT NULL DEFAULT false;
    END IF;
END $$;
"""

SEED_PERSONAS = """
INSERT INTO persona (nombre, puede_examenes, puede_pregunta)
VALUES ('Rafa', true, true), ('Sergio', true, true)
ON CONFLICT (nombre) DO UPDATE SET
    puede_examenes = EXCLUDED.puede_examenes,
    puede_pregunta = EXCLUDED.puede_pregunta;
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

CREATE_PREGUNTA_DIA = """
CREATE TABLE IF NOT EXISTS pregunta_dia (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES persona(id),
    fecha DATE NOT NULL,
    acertada BOOLEAN NOT NULL
);
"""


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def ensure_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_PERSONA)
            cur.execute(ADD_COLUMNS_IF_MISSING)
            cur.execute(SEED_PERSONAS)
            cur.execute(CREATE_EXAMENES)
            cur.execute(CREATE_PREGUNTA_DIA)
            cur.execute("ALTER TABLE persona ENABLE ROW LEVEL SECURITY")
            cur.execute("ALTER TABLE examenes ENABLE ROW LEVEL SECURITY")
            cur.execute("ALTER TABLE pregunta_dia ENABLE ROW LEVEL SECURITY")
            for tabla in ("persona", "examenes", "pregunta_dia"):
                cur.execute(f"""
                    DO $$ BEGIN
                        CREATE POLICY app_full_access ON {tabla}
                            FOR ALL TO postgres USING (true) WITH CHECK (true);
                    EXCEPTION WHEN duplicate_object THEN NULL;
                    END $$;
                """)
        conn.commit()


def obtener_personas(tipo: TipoPersona = None) -> list[dict]:
    query = "SELECT id, nombre FROM persona"
    if tipo is not None:
        query += f" WHERE {COLUMN_BY_TIPO[tipo]} = true"
    query += " ORDER BY nombre"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]


def buscar_persona_por_nombre(nombre: str, tipo: TipoPersona = None) -> dict | None:
    query = "SELECT id, nombre FROM persona WHERE LOWER(nombre) = LOWER(%s)"
    if tipo is not None:
        query += f" AND {COLUMN_BY_TIPO[tipo]} = true"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (nombre,))
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


def registrar_pregunta(persona_id: int, fecha: date, acertada: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pregunta_dia (persona_id, fecha, acertada) VALUES (%s, %s, %s)",
                (persona_id, fecha, acertada),
            )
        conn.commit()
