from datetime import datetime, timedelta
import re
import numpy as np
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from constantes import CAMPO_SELECIONADO, CAMPOS, MENSAGENS

# ---- MENSAGENS PADRÃO ----
MSG_SUCESSO = "✅ Operação concluída!"
MSG_ERRO = "❌ Algo deu errado."
MSG_CANCELADO = "❌ Operação cancelada!"
MSG_LIMITE = "❌ Limite de lembretes atingido!"
MSG_HORARIO_INVALIDO = "⚠️ Horário inválido. Ex: 12:00"
MSG_HORARIO_OBRIGATORIO = "⚠️ Campo horário é obrigatório"
MSG_SEM_LEMBRETES = "❌ Sem lembretes registrados."

# ---- BOTÕES REUTILIZÁVEIS ----
def botoes_confirmacao(callback_sim: str, callback_nao: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Sim", callback_data=callback_sim)],
        [InlineKeyboardButton("Não", callback_data=callback_nao)]
    ])

# ---- PARSER FLEXÍVEL DE HORÁRIO ----
def parse_horario(texto: str) -> str | None:
    """Tenta extrair um horário válido do texto. Retorna HH:MM ou None."""
    texto = texto.strip()
    match = re.match(r'^(\d{1,2})([:h\.]?(\d{2}))?$', texto)
    if match:
        hora = int(match.group(1))
        minuto = int(match.group(3)) if match.group(3) else 0

        if 0 <= hora < 24 and 0 <= minuto < 60:
            return f"{hora:02d}:{minuto:02d}"
    return None

def random_entrada(data) -> datetime:
    base: datetime = datetime.combine(data, datetime.min.time()) + timedelta(hours=8)
    aleatorio: datetime = base + timedelta(seconds=np.random.randint(0, 30*60))
    return aleatorio

def random_saida(entrada: datetime, carga_horaria = 9, min: int = 15, max: int = 60) -> datetime:
    extra_segundos = np.random.randint(min * 60, (max + 1) * 60)
    saida_dt  = entrada + timedelta(hours=carga_horaria, seconds=extra_segundos)
    return saida_dt

def limite(admin_id: int):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.chat_id != admin_id:
            await update.message.reply_text("Comando disponível apenas para administradores.")
            return

        if len(context.args) != 1:
            await update.message.reply_text("Parâmetros inválidos. Exemplo: /limite 3")
            return

        try:
            novo_limite = max(1, int(context.args[0]))
            from database import Database
            db = Database()
            db.set_limite(novo_limite)
            await update.message.reply_text(f"Limite ajustado para {novo_limite}.")
        except ValueError:
            await update.message.reply_text("O valor do limite deve ser um número inteiro.")

    return handler

def salvar_alteracoes(func):
    async def wrapper(update, context):
        mensagem: Message = update.message
        context.user_data[MENSAGENS].append(mensagem)
        valor = mensagem.text
        campo = context.user_data[CAMPO_SELECIONADO]
        context.user_data[CAMPOS][campo] = valor
        return await func(update, context)
    return wrapper