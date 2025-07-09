import sqlite3
from typing import Any
from datetime import datetime

import pandas as pd

class Database:
    def __init__(self, db_name: str = "usuarios.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._criar_tabelas()

    def _criar_tabelas(self) -> None:
        """Cria as tabelas necessárias se não existirem."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                nomeusuario TEXT,
                nome TEXT,
                idioma TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                horas_devidas NUMERIC DEFAULT 0            
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY,
                usuario_id INTEGER,
                horario TEXT,
                mensagem TEXT,
                enviado_em DATETIME,
                CONSTRAINT fx_usuario_id FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ponto(
                data TEXT PRIMARY KEY,
                entrada TEXT,
                saida TEXT,
                feriado TEXT,
                contabilizado INTEGER DEFAULT 0
            )
        """)

        self.cursor.execute("CREATE INDEX IF NOT EXISTS lembretes_usuario_id ON lembretes (usuario_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS lembretes_horario_enviado_em ON lembretes (horario, enviado_em)")
        self.conn.commit()

    def add_usuario(self, usuario_id: int, nomeusuario: str | None = None, nome: str | None = None, idioma: str | None = None) -> None:
        """Adiciona um novo usuário, se ainda não existir."""
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO usuarios (id, nomeusuario, nome, idioma)
            VALUES (?, ?, ?, ?)
            """,
            (usuario_id, nomeusuario, nome, idioma)
        )
        self.conn.commit()

    def update_contabilizado(self, ponto_data: str, usuario_id: int, horas: float) -> None:
        """Atualiza o campo contabilizado para 1 para o ponto do usuário."""
        self.cursor.execute(
            "UPDATE ponto SET contabilizado = 1 WHERE data = ?",
            (ponto_data,)
        )
        self.cursor.execute(
            "SELECT horas_devidas FROM usuarios WHERE id = ?",
            (usuario_id,)
        )
        horas_devidas = self.cursor.fetchone()
        self.cursor.execute(
            "UPDATE usuarios SET horas_devidas = ? WHERE id = ?",
            (horas_devidas[0] + horas, usuario_id)
        )
        self.conn.commit()

    def get_usuario(self, usuario_id: int) -> Any:
        self.cursor.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,))
        return self.cursor.fetchone()
    
    def get_horas_devidas(self, usuario_id: int) -> float:
        self.cursor.execute("SELECT horas_devidas FROM usuarios WHERE id = ?", (usuario_id,))
        result = self.cursor.fetchone()
        return float(result[0]) if result else 0.0
    
    def update_horas_devidas(self, usuario_id: int, horas: float) -> None:
        if horas == 0.0:
            return
        """Atualiza as horas devidas do usuário."""
        self.cursor.execute(
            "UPDATE usuarios SET horas_devidas = horas_devidas + ? WHERE id = ?",
            (horas, usuario_id)
        )
        self.conn.commit()

    def add_lembrete(self, usuario_id: int, horario: str, mensagem: str) -> None:
        self.cursor.execute(
            "INSERT INTO lembretes (usuario_id, horario, mensagem) VALUES (?, ?, ?)",
            (usuario_id, horario, mensagem)
        )
        self.conn.commit()

    def get_lembretes_usuarios(self, usuario_id: int) -> list[Any]:
        self.cursor.execute("SELECT id, horario, mensagem FROM lembretes WHERE usuario_id = ?", (usuario_id,))
        return self.cursor.fetchall()

    def get_lembrete_por_id(self, lembrete_id: int) -> Any:
        self.cursor.execute("SELECT id, horario, mensagem FROM lembretes WHERE id = ?", (lembrete_id,))
        return self.cursor.fetchone()

    def update_lembrete(self, lembrete_id: int, novo_horario: str | None = None, nova_mensagem: str | None = None) -> None:
        if novo_horario:
            self.cursor.execute("UPDATE lembretes SET enviado_em = NULL, horario = ? WHERE id = ?", (novo_horario, lembrete_id))
        if nova_mensagem:
            self.cursor.execute("UPDATE lembretes SET enviado_em = NULL, mensagem = ? WHERE id = ?", (nova_mensagem, lembrete_id))
        self.conn.commit()

    def delete_lembrete_usuario(self, usuario_id: int, lembrete_id: int) -> None:
        self.cursor.execute("DELETE FROM lembretes WHERE usuario_id = ? AND id = ?", (usuario_id, lembrete_id))
        self.conn.commit()

    def delete_lembretes_usuario(self, usuario_id: int) -> None:
        self.cursor.execute("DELETE FROM lembretes WHERE usuario_id = ?", (usuario_id,))
        self.conn.commit()

    def get_lembretes_a_enviar(self, horario: str) -> list[Any]:
        day: str = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(
            """
            SELECT id, usuario_id, mensagem FROM lembretes
            WHERE horario = ? AND (enviado_em IS NULL OR enviado_em != ?)
            """,
            (horario, day)
        )
        return self.cursor.fetchall()

    def update_enviado_em(self, lembrete_id: int) -> None:
        day: str = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("UPDATE lembretes SET enviado_em = ? WHERE id = ?", (day, lembrete_id))
        self.conn.commit()

    def get_limite(self) -> int:
        self.cursor.execute("SELECT value FROM config WHERE key = 'limite'")
        result = self.cursor.fetchone()
        return int(result[0]) if result else 3

    def set_limite(self, limite: int) -> None:
        self.cursor.execute("INSERT OR REPLACE INTO config VALUES (?, ?)", ("limite", str(limite)))
        self.conn.commit()
    
    def get_ponto(self, data: str) -> Any:
        self.cursor.execute("SELECT entrada, saida, feriado FROM ponto WHERE strftime('') = ?", (data,))
        return self.cursor.fetchone()

    def get_pontos(self, data) -> pd.DataFrame:
        return pd.read_sql_query("""
        SELECT data, entrada, saida, feriado, contabilizado FROM ponto 
        WHERE strftime('%m-%Y', data) = ? 
        order by data""", self.conn, params=(data,))
    
    def insert_ponto(self, data: str, entrada: str, saida: str, feriado: str) -> None:
        self.cursor.execute("""
            INSERT OR REPLACE INTO ponto (data, entrada, saida, feriado) VALUES (?, ?, ?, ?)
        """, (data, entrada, saida, feriado))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __del__(self):
        self.close()
