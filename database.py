"""
database.py
-----------
Acesso ao SQLite via connection-per-call para evitar problemas de
concorrência com o servidor de webhooks assíncrono.

Cada método público abre, usa e fecha sua própria conexão dentro de
um context manager, eliminando o risco de cursor/connection vazando
entre coroutines distintas que o asyncio pode intercalar.
"""

import sqlite3
from contextlib import contextmanager
from typing import Any
from datetime import datetime

import pandas as pd

DB_NAME = "usuarios.db"


class Database:
    def __init__(self, db_name: str = DB_NAME):
        self._db_name = db_name
        self._init_schema()

    # ------------------------------------------------------------------
    # Infraestrutura
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        """Abre uma conexão dedicada, entrega o cursor e faz commit/rollback."""
        conn = sqlite3.connect(self._db_name, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")   # leituras não bloqueiam escrita
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Cria tabelas e índices se ainda não existirem (idempotente)."""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id           INTEGER PRIMARY KEY,
                    nomeusuario  TEXT,
                    nome         TEXT,
                    idioma       TEXT,
                    criado_em    DATETIME DEFAULT CURRENT_TIMESTAMP,
                    horas_devidas NUMERIC  DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS ponto (
                    usuario_id    INTEGER NOT NULL,
                    data          TEXT    NOT NULL,
                    entrada       TEXT,
                    inicio_almoco TEXT,
                    fim_almoco    TEXT,
                    saida         TEXT,
                    feriado       TEXT,
                    contabilizado INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (usuario_id, data),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );

                CREATE INDEX IF NOT EXISTS idx_ponto_usuario_data
                    ON ponto (usuario_id, data);
            """)
            conn.execute("UPDATE usuarios SET horas_devidas = 0 WHERE horas_devidas < 0")

    # ------------------------------------------------------------------
    # Usuários
    # ------------------------------------------------------------------

    def add_usuario(
        self,
        usuario_id: int,
        nomeusuario: str | None = None,
        nome: str | None = None,
        idioma: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO usuarios (id, nomeusuario, nome, idioma)
                VALUES (?, ?, ?, ?)
                """,
                (usuario_id, nomeusuario, nome, idioma),
            )

    def get_usuario(self, usuario_id: int) -> Any:
        with self._conn() as conn:
            return conn.execute(
                "SELECT id FROM usuarios WHERE id = ?", (usuario_id,)
            ).fetchone()

    def get_horas_devidas(self, usuario_id: int) -> float:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT horas_devidas FROM usuarios WHERE id = ?", (usuario_id,)
            ).fetchone()
        return max(float(row[0]), 0.0) if row else 0.0

    def update_horas_devidas(self, usuario_id: int, delta: float) -> None:
        """Adiciona `delta` às horas devidas (use negativo para abater)."""
        if delta == 0.0:
            return
        with self._conn() as conn:
            conn.execute(
                "UPDATE usuarios SET horas_devidas = MAX(horas_devidas + ?, 0) WHERE id = ?",
                (delta, usuario_id),
            )
            conn.execute(
                "UPDATE usuarios SET horas_devidas = 0 WHERE id = ? AND horas_devidas < 0.000001",
                (usuario_id,),
            )

    def set_horas_devidas(self, usuario_id: int, horas: float) -> None:
        """Define as horas devidas do usuário para um valor específico."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE usuarios SET horas_devidas = MAX(?, 0) WHERE id = ?",
                (horas, usuario_id),
            )

    # ------------------------------------------------------------------
    # Ponto
    # ------------------------------------------------------------------

    def get_pontos(self, usuario_id: int, mes_ano: str) -> pd.DataFrame:
        """Retorna DataFrame com todos os pontos do usuário no mês (MM-YYYY)."""
        with self._conn() as conn:
            return pd.read_sql_query(
                """
                SELECT data, entrada, inicio_almoco, fim_almoco, saida,
                       feriado, contabilizado
                FROM   ponto
                WHERE  usuario_id = ?
                AND    strftime('%m-%Y', data) = ?
                ORDER  BY data
                """,
                conn,
                params=(usuario_id, mes_ano),
            )

    def get_ponto(self, usuario_id: int, data: str) -> Any:
        """Retorna uma linha de ponto ou None."""
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT entrada, inicio_almoco, fim_almoco, saida, feriado
                FROM   ponto
                WHERE  usuario_id = ? AND data = ?
                """,
                (usuario_id, data),
            ).fetchone()

    def insert_ponto(
        self,
        usuario_id: int,
        data: str,
        entrada: str | None,
        inicio_almoco: str | None,
        fim_almoco: str | None,
        saida: str | None,
        feriado: str | None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ponto
                    (usuario_id, data, entrada, inicio_almoco, fim_almoco,
                     saida, feriado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (usuario_id, data, entrada, inicio_almoco, fim_almoco,
                 saida, feriado),
            )

    def update_contabilizado(
        self, usuario_id: int, ponto_data: str, horas_debito: float
    ) -> None:
        """Marca o ponto como contabilizado e acumula débito no usuário."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE ponto SET contabilizado = 1 WHERE usuario_id = ? AND data = ?",
                (usuario_id, ponto_data),
            )
            conn.execute(
                "UPDATE usuarios SET horas_devidas = MAX(horas_devidas, 0) + ? WHERE id = ?",
                (horas_debito, usuario_id),
            )

    def reset_contabilizado_mes(self, usuario_id: int, mes_ano: str) -> None:
        """Reseta a flag de contabilizado para todos os pontos de um mês (MM-YYYY)."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE ponto SET contabilizado = 0 WHERE usuario_id = ? AND strftime('%m-%Y', data) = ?",
                (usuario_id, mes_ano),
            )

    def delete_ponto(self, usuario_id: int, data: str) -> None:
        """Remove o registro de ponto para um dia específico."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM ponto WHERE usuario_id = ? AND data = ?",
                (usuario_id, data),
            )

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self, key: str, default: str | None = None) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM config WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else default

    def set_config(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config VALUES (?, ?)", (key, value)
            )
