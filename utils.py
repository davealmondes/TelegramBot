"""
utils.py
--------
Utilitários compartilhados: parsing, gerador de horários e decoradores.
"""

from datetime import date, datetime, timedelta
import re
import numpy as np
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from constantes import CAMPO_SELECIONADO, CAMPOS, MENSAGENS

# ---------------------------------------------------------------------------
# Mensagens padrão
# ---------------------------------------------------------------------------
MSG_SUCESSO             = "✅ Operação concluída!"
MSG_ERRO                = "❌ Algo deu errado."
MSG_CANCELADO           = "❌ Operação cancelada!"
MSG_HORARIO_INVALIDO    = "⚠️ Horário inválido. Ex: 12:00"
MSG_HORARIO_OBRIGATORIO = "⚠️ Campo horário é obrigatório"

# ---------------------------------------------------------------------------
# Botões reutilizáveis
# ---------------------------------------------------------------------------

def botoes_confirmacao(callback_sim: str, callback_nao: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Sim", callback_data=callback_sim)],
        [InlineKeyboardButton("Não", callback_data=callback_nao)],
    ])

# ---------------------------------------------------------------------------
# Parser flexível de horário
# ---------------------------------------------------------------------------

def parse_horario(texto: str) -> str | None:
    """Extrai HH:MM de entradas como '830', '8h30', '8:30', '8'. Retorna None se inválido."""
    texto = texto.strip()
    match = re.match(r'^(\d{1,2})([:h\.]?(\d{2}))?$', texto)
    if match:
        hora = int(match.group(1))
        minuto = int(match.group(3)) if match.group(3) else 0
        if 0 <= hora < 24 and 0 <= minuto < 60:
            return f"{hora:02d}:{minuto:02d}"
    return None

# ---------------------------------------------------------------------------
# Gerador de horários realistas — 4 marcações
# ---------------------------------------------------------------------------

def _rand_minutos(centro_minutos: int, desvio_max: int = 20) -> int:
    """Retorna uma variação inteira uniforme em torno de `centro_minutos`."""
    return int(np.random.randint(-desvio_max, desvio_max + 1))


def gerar_marcacoes(
    data: date,
    debito_horas: float = 0.0,
    carga_horaria_horas: float = 9.0,
    almoco_incluso_na_carga: bool = True,
    hora_extra_minutos: tuple[int, int] = (15, 45),
) -> tuple[str, str, str, str]:
    """
    Gera 4 marcações realistas para `data`.

    Lógica de horários
    ------------------
    - Entrada:       08:00 +/- 20 min
    - Saída almoço:  12:00 +/- 15 min  (base fixa, variacao pequena)
    - Volta almoço:  saida_almoco + 60 min +/- 1 min
    - Saida:         entrada + carga horaria + compensacao_debito + extra aleatoria
                     (+ duracao_almoco quando almoco nao esta incluso na carga)

    Parâmetros
    ----------
    data                   : data do dia a gerar
    debito_horas           : horas a compensar nesse dia (estende a saida)
    carga_horaria_horas    : carga horaria diaria
    almoco_incluso_na_carga: se True, nao soma almoco novamente na saida
    hora_extra_minutos     : intervalo da hora extra aleatoria diaria
    Retorna
    -------
    (entrada, inicio_almoco, fim_almoco, saida) como strings HH:MM
    """
    base = datetime.combine(data, datetime.min.time())

    # Entrada: 08:00 + (0 a 20 min)
    entrada_dt = base + timedelta(hours=8, minutes=int(np.random.randint(0, 21)))

    # Saida pro almoco: 12:00 +/- 15 min (base fixa)
    almoco_out_dt = base + timedelta(hours=12, minutes=_rand_minutos(0, 15))

    # Volta do almoco: saida_almoco + 60 min +/- 1 min
    duracao_almoco = timedelta(minutes=60 + _rand_minutos(0, 1))
    almoco_in_dt = almoco_out_dt + duracao_almoco

    # Saida: fecha a carga configurada, compensa debito e inclui extra diaria.
    compensacao = timedelta(hours=debito_horas)
    extra_min = int(np.random.randint(hora_extra_minutos[0], hora_extra_minutos[1] + 1))
    saida_dt = entrada_dt + timedelta(hours=carga_horaria_horas, minutes=extra_min) + compensacao
    if not almoco_incluso_na_carga:
        saida_dt += duracao_almoco

    fmt = "%H:%M"
    return (
        entrada_dt.strftime(fmt),
        almoco_out_dt.strftime(fmt),
        almoco_in_dt.strftime(fmt),
        saida_dt.strftime(fmt),
    )


def calcular_horas_trabalhadas(
    entrada: str, inicio_almoco: str, fim_almoco: str, saida: str
) -> float:
    """
    Retorna horas líquidas trabalhadas:
        (saida - entrada) - (fim_almoco - inicio_almoco)
    Todos os parâmetros no formato HH:MM.
    Retorna 0.0 se qualquer valor estiver ausente.
    """
    if not all([entrada, inicio_almoco, fim_almoco, saida]):
        return 0.0
    _p = lambda s: datetime.strptime(s, "%H:%M")
    bruto   = (_p(saida)      - _p(entrada)).seconds / 3600
    almoco  = (_p(fim_almoco) - _p(inicio_almoco)).seconds / 3600
    return max(0.0, bruto - almoco)

# ---------------------------------------------------------------------------
# Decoradores / middlewares de handlers
# ---------------------------------------------------------------------------

def salvar_alteracoes(func):
    """Persiste o texto digitado em context.user_data[CAMPOS] antes de delegar."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        mensagem: Message = update.message
        context.user_data[MENSAGENS].append(mensagem)
        valor = mensagem.text
        campo = context.user_data[CAMPO_SELECIONADO]
        context.user_data[CAMPOS][campo] = valor
        return await func(update, context)
    return wrapper


def limite(admin_id: int):
    """Handler do comando /limite — exclusivo para o admin."""
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
            db.set_config("limite", str(novo_limite))
            await update.message.reply_text(f"Limite ajustado para {novo_limite}.")
        except ValueError:
            await update.message.reply_text("O valor do limite deve ser um número inteiro.")
    return handler
