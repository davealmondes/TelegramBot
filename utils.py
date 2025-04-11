import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
