"""
ponto_handler.py
----------------
Handlers do módulo de ponto. Toda leitura/escrita de DB passa pelo
objeto `db` (Database), que usa connection-per-call internamente.
"""

import calendar
from datetime import date, datetime, timedelta
import math
import os

import holidays
import pandas as pd
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from constantes import *
from database import Database
from utils import calcular_horas_trabalhadas, gerar_marcacoes

db = Database()

# ---------------------------------------------------------------------------
# valor_campo — solicita digitação de um campo específico
# ---------------------------------------------------------------------------

async def valor_campo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe prompt para o usuário digitar o valor do campo selecionado."""
    campo = update.callback_query.data
    context.user_data[CAMPO_SELECIONADO] = campo

    nomes = {
        str(ENTRADA):      "Entrada",
        str(INICIO_ALMOCO): "Início do Almoço",
        str(FIM_ALMOCO):   "Fim do Almoço",
        str(SAIDA):        "Saída",
        str(OBSERVACAO):   "Observação",
    }
    nome_campo = nomes.get(campo, campo)
    atual = context.user_data.get(CAMPOS, {}).get(campo)
    texto = (
        f'Digite o valor para *{nome_campo}* (atual: `{atual}`):' if atual
        else f"Digite o valor para *{nome_campo}* (ex: `08:00`):"
    )
    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])
    mensagens.append(
        await update.callback_query.edit_message_text(texto, parse_mode="Markdown")
    )
    return DIGITANDO


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _usuario_id(update: Update) -> int:
    if update.message:
        return update.message.from_user.id
    return update.callback_query.from_user.id


def _parse_mes(context) -> tuple[int, int]:
    """Retorna (mes, ano) a partir de context.user_data[MES] ('MM-YYYY')."""
    return tuple(map(int, context.user_data[MES].split("-")))


def _config_bool(chave: str, padrao: bool) -> bool:
    valor = db.get_config(chave)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "s", "yes", "y")


def _config_float(chave: str, padrao: float) -> float:
    valor = db.get_config(chave)
    if valor is None:
        return padrao
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return padrao


def _config_int(chave: str, padrao: int) -> int:
    valor = db.get_config(chave)
    if valor is None:
        return padrao
    try:
        return int(valor)
    except ValueError:
        return padrao


def _feriados_sp(ano: int):
    return holidays.country_holidays(
        "BR",
        subdiv="SP",
        years=ano,
        categories=("public", "optional"),
    )


def _nome_feriado(data_atual: date, feriados) -> str | None:
    if data_atual in feriados:
        return feriados[data_atual]
    data_iso = data_atual.isoformat()
    if data_iso in feriados:
        return feriados[data_iso]
    return None


def _tem_valor(valor) -> bool:
    return not pd.isna(valor) and str(valor).strip() != ""


def _registro_manual_nao_util(row) -> bool:
    if not _tem_valor(row.get("feriado")):
        return False
    return not any(
        _tem_valor(row.get(campo))
        for campo in ("entrada", "inicio_almoco", "fim_almoco", "saida")
    )


def _datas_nao_uteis_manuais(pontos: pd.DataFrame) -> set[str]:
    if pontos.empty:
        return set()
    return {
        row["data"]
        for _, row in pontos.iterrows()
        if _registro_manual_nao_util(row)
    }


def _config_jornada() -> tuple[float, bool, float, int, int]:
    carga_horaria = _config_float("carga_horaria_horas", 9.0)
    almoco_incluso = _config_bool("almoco_incluso_na_carga", True)
    almoco_padrao = _config_float("almoco_padrao_horas", 1.0)
    extra_min = _config_int("hora_extra_minutos_min", 15)
    extra_max = _config_int("hora_extra_minutos_max", 45)
    if extra_max < extra_min:
        extra_min, extra_max = extra_max, extra_min
    return carga_horaria, almoco_incluso, almoco_padrao, extra_min, extra_max


def _horas_esperadas_dia(
    carga_horaria: float,
    almoco_incluso_na_carga: bool,
    almoco_padrao_horas: float,
) -> float:
    if almoco_incluso_na_carga:
        return max(0.0, carga_horaria - almoco_padrao_horas)
    return carga_horaria


# ---------------------------------------------------------------------------
# escolher_mes — exibido ao clicar em "Ponto" no menu principal
# ---------------------------------------------------------------------------

async def escolher_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mes = datetime.now().month
    ano = datetime.now().year
    meses = [
        f"{(mes - i - 1) % 12 + 1:02}-{ano - ((mes - i - 1) // 12)}"
        for i in range(12)
    ]
    buttons = [[InlineKeyboardButton(text=m, callback_data=m)] for m in meses]

    await update.callback_query.edit_message_reply_markup(
        InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Voltar", callback_data=str(CANCELAR))]]
        )
    )
    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])
    mensagens.append(
        await context.bot.send_message(
            update.callback_query.from_user.id,
            "Selecione o mês para gerenciar o ponto.",
            reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True),
        )
    )
    context.user_data[INICIO] = True
    return SELECAO_MENU


# ---------------------------------------------------------------------------
# info_planilha — tela principal do submenu de ponto
# ---------------------------------------------------------------------------

async def info_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Calcula e exibe o resumo mensal. Também é usado como 'voltar' interno."""
    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])
    context.user_data[EDITANDO] = None
    context.user_data[INICIO] = True
    usuario_id = _usuario_id(update)

    if update.message:
        mensagens.append(update.message)
        context.user_data[MES] = update.message.text

    mes_str = context.user_data[MES]
    mes, ano = tuple(map(int, mes_str.split("-")))

    pontos: pd.DataFrame = db.get_pontos(usuario_id, mes_str)
    feriados = _feriados_sp(ano)
    (
        carga_horaria,
        almoco_incluso_na_carga,
        almoco_padrao_horas,
        _extra_min,
        _extra_max,
    ) = _config_jornada()
    horas_esperadas_dia = _horas_esperadas_dia(
        carga_horaria,
        almoco_incluso_na_carga,
        almoco_padrao_horas,
    )

    dias_do_mes = [date(ano, mes, d) for d in range(1, calendar.monthrange(ano, mes)[1] + 1)]
    datas_nao_uteis_manuais = _datas_nao_uteis_manuais(pontos)
    dias_uteis  = [
        d for d in dias_do_mes
        if d.weekday() < 5
        and not _nome_feriado(d, feriados)
        and d.isoformat() not in datas_nao_uteis_manuais
    ]

    datas_com_ponto = set(pontos["data"].values)
    dias_com_ponto  = [d for d in dias_uteis if d.strftime("%Y-%m-%d") in datas_com_ponto]
    dias_faltando   = [d for d in dias_uteis if d.strftime("%Y-%m-%d") not in datas_com_ponto]

    horas_trabalhadas = 0.0
    horas_devidas     = 0.0
    horas_extras      = 0.0
    horas_esperadas   = len(dias_com_ponto) * horas_esperadas_dia

    for d in dias_com_ponto:
        row = pontos.query(f"data == '{d.strftime('%Y-%m-%d')}'")
        if row.empty:
            continue
        r = row.iloc[0]
        horas = calcular_horas_trabalhadas(
            r["entrada"], r["inicio_almoco"], r["fim_almoco"], r["saida"]
        )
        if horas == 0.0:
            continue
        horas_trabalhadas += horas
        saldo = horas_esperadas_dia - horas
        if saldo > 0:
            if r["contabilizado"] == 0:
                db.update_contabilizado(usuario_id, r["data"], saldo)
            horas_devidas += saldo
        else:
            horas_extras += abs(saldo)

    def _fmt(h: float) -> str:
        hh = math.floor(h)
        mm = math.floor((h - hh) * 60)
        return f"{hh}h {mm:02d}min"

    context.user_data[DIAS_FALTANDO] = len(dias_faltando)

    texto = (
        f"📅 *Ponto — {calendar.month_name[mes]} {ano}*\n\n"
        f"Dias úteis no mês: {len(dias_uteis)}\n"
        f"Dias trabalhados registrados: {len(dias_com_ponto)}\n"
        f"Dias a registrar: {len(dias_faltando)}\n\n"
        f"Horas trabalhadas: {_fmt(horas_trabalhadas)}\n"
        f"Horas esperadas: {_fmt(horas_esperadas)}\n"
        f"Horas devidas acumuladas: {_fmt(horas_devidas)}\n"
        f"Horas extras: {_fmt(horas_extras)}\n"
    )

    texto_extra = context.user_data.pop(TEXTO, None)
    if texto_extra:
        texto = f"{texto_extra}\n\n{texto}"

    buttons = [
        [
            InlineKeyboardButton("Gerar Planilha", callback_data=str(GERAR_PLANILHA)),
            InlineKeyboardButton("Baixar Planilha", callback_data=str(BAIXAR_PLANILHA)),
        ],
        [InlineKeyboardButton("Recalcular Horas Devidas", callback_data=str(RECALCULAR))],
        [InlineKeyboardButton("Voltar", callback_data=str(END))],
    ]
    markup = InlineKeyboardMarkup(buttons)

    if update.message:
        mensagens.append(await update.message.reply_text(texto, reply_markup=markup, parse_mode="Markdown"))
    else:
        mensagens.append(
            await update.callback_query.edit_message_text(texto, reply_markup=markup, parse_mode="Markdown")
        )
    return SELECAO_MENU_PONTO


async def recalcular_horas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recalcula o saldo de horas do mês, abatendo extras de débitos."""
    usuario_id = _usuario_id(update)
    mes_str    = context.user_data[MES]
    
    pontos = db.get_pontos(usuario_id, mes_str)
    (carga_horaria, almoco_incluso, almoco_padrao, _, _) = _config_jornada()
    horas_esperadas_dia = _horas_esperadas_dia(carga_horaria, almoco_incluso, almoco_padrao)
    
    saldo_total = 0.0
    for _, r in pontos.iterrows():
        horas = calcular_horas_trabalhadas(r["entrada"], r["inicio_almoco"], r["fim_almoco"], r["saida"])
        if horas > 0.0:
            saldo_total += (horas_esperadas_dia - horas)
            
    novo_debito = max(0.0, saldo_total)
    db.set_horas_devidas(usuario_id, novo_debito)
    
    with db._conn() as conn:
        conn.execute("UPDATE ponto SET contabilizado = 1 WHERE usuario_id = ? AND strftime('%m-%Y', data) = ?", (usuario_id, mes_str))
    
    context.user_data[TEXTO] = "✅ Horas devidas recalculadas com sucesso."
    return await info_planilha(update, context)


# ---------------------------------------------------------------------------
# gerar_planilha_acoes — submenu de geração
# ---------------------------------------------------------------------------

async def gerar_planilha_acoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = context.user_data.pop(TEXTO, "Como deseja gerar os pontos?")
    buttons = [
        [
            InlineKeyboardButton("Gerar dias passados", callback_data=str(GERAR)),
            InlineKeyboardButton("Gerar dia específico", callback_data=str(GERAR_DIA)),
        ],
        [InlineKeyboardButton("Gerar incluindo futuros", callback_data=str(GERAR_FUTURO))],
        [InlineKeyboardButton("Voltar", callback_data=str(END))],
    ]
    await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_PONTO


# ---------------------------------------------------------------------------
# gerar_dia — seleciona um dia específico via ReplyKeyboard
# ---------------------------------------------------------------------------

async def gerar_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mes, ano = _parse_mes(context)
    total_dias = calendar.monthrange(ano, mes)[1]
    keyboard = [
        [f"{d:02}", f"{d+1:02}"] if d + 1 <= total_dias else [f"{d:02}"]
        for d in range(1, total_dias + 1, 2)
    ]
    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Voltar", callback_data=str(CANCELAR))]]
        )
    )
    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])
    mensagens.append(
        await context.bot.send_message(
            update.callback_query.from_user.id,
            "Selecione o dia para registrar o ponto.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
        )
    )
    return SELECAO_MENU_PONTO


# ---------------------------------------------------------------------------
# campo_ponto — exibe os 4 campos editáveis para um dia
# ---------------------------------------------------------------------------

async def campo_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])

    if update.message:
        mensagens.append(update.message)
        if context.user_data.get(INICIO):
            context.user_data[DIA] = update.message.text
            context.user_data[CAMPOS] = {}
            context.user_data[INICIO] = False

    texto = f"Adicionando ponto para o dia {context.user_data.get(DIA, '??')}..."
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Entrada",       callback_data=str(ENTRADA)),
            InlineKeyboardButton("Início Almoço", callback_data=str(INICIO_ALMOCO)),
        ],
        [
            InlineKeyboardButton("Fim Almoço",    callback_data=str(FIM_ALMOCO)),
            InlineKeyboardButton("Saída",         callback_data=str(SAIDA)),
        ],
        [
            InlineKeyboardButton("Observação",    callback_data=str(OBSERVACAO)),
        ],
        [
            InlineKeyboardButton("Limpar Dia",    callback_data=str(LIMPAR_DIA)),
        ],
        [
            InlineKeyboardButton("Cancelar",  callback_data=str(CANCELAR)),
            InlineKeyboardButton("Concluir",  callback_data=str(END)),
        ],
    ])

    if update.message:
        await update.message.reply_text(texto, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(texto, reply_markup=keyboard)
    return SELECIONANDO_CAMPO


# ---------------------------------------------------------------------------
# encerrar_edicao_ponto — salva ou cancela o ponto em edição
# ---------------------------------------------------------------------------

async def encerrar_edicao_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    usuario_id = _usuario_id(update)
    data_cb = update.callback_query.data

    if data_cb == str(CANCELAR):
        context.user_data[CAMPOS] = {}
        context.user_data[TEXTO] = "Edição cancelada."
        await info_planilha(update, context)
        return END

    if data_cb == str(LIMPAR_DIA):
        mes, ano = _parse_mes(context)
        dia     = int(context.user_data[DIA])
        data_dt = date(ano, mes, dia)
        db.delete_ponto(usuario_id, data_dt.strftime("%Y-%m-%d"))
        
        context.user_data[CAMPOS] = {}
        context.user_data[TEXTO] = "✅ Apontamento do dia apagado."
        await info_planilha(update, context)
        return END

    if data_cb == str(END):
        mes, ano = _parse_mes(context)
        dia     = int(context.user_data[DIA])
        data_dt = date(ano, mes, dia)
        campos  = context.user_data.get(CAMPOS, {})

        db.insert_ponto(
            usuario_id,
            data_dt.strftime("%Y-%m-%d"),
            campos.get(ENTRADA),
            campos.get(INICIO_ALMOCO),
            campos.get(FIM_ALMOCO),
            campos.get(SAIDA),
            campos.get(OBSERVACAO),
        )
        context.user_data[TEXTO] = "✅ Ponto registrado com sucesso."
        await info_planilha(update, context)
        return END


# ---------------------------------------------------------------------------
# gerar — gera marcações automáticas para dias sem ponto
# ---------------------------------------------------------------------------

async def gerar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    incluir_futuros: bool = False,
) -> int:
    """
    Percorre os dias úteis do mês selecionado e insere pontos nos dias
    sem registro. Por padrão ignora dias futuros; com `incluir_futuros=True`
    gera também datas após hoje.
    """
    usuario_id = _usuario_id(update)
    mes_str    = context.user_data[MES]
    mes, ano   = tuple(map(int, mes_str.split("-")))

    pontos_existentes: pd.DataFrame = db.get_pontos(usuario_id, mes_str)
    datas_com_ponto = set(pontos_existentes["data"].values)

    hoje           = date.today()
    feriados       = _feriados_sp(ano)
    datas_nao_uteis_manuais = _datas_nao_uteis_manuais(pontos_existentes)
    (
        carga_horaria,
        almoco_incluso_na_carga,
        _almoco_padrao_horas,
        extra_min,
        extra_max,
    ) = _config_jornada()
    total_dias = calendar.monthrange(ano, mes)[1]
    dias_faltando_no_mes = [
        date(ano, mes, dia)
        for dia in range(1, total_dias + 1)
        if date(ano, mes, dia).weekday() < 5
        and date(ano, mes, dia).isoformat() not in datas_com_ponto
        and date(ano, mes, dia).isoformat() not in datas_nao_uteis_manuais
        and not _nome_feriado(date(ano, mes, dia), feriados)
    ]
    
    semanas_do_mes = sorted(list(set(
        date(ano, mes, dia).isocalendar()[1] for dia in range(1, total_dias + 1)
    )))

    debito_acumulado = 0.0

    for semana in semanas_do_mes:
        pontos_semana = pontos_existentes[
            pontos_existentes["data"].apply(lambda d: date.fromisoformat(d).isocalendar()[1] == semana)
        ]
        
        saldo_semana = 0.0
        for _, r in pontos_semana.iterrows():
            horas = calcular_horas_trabalhadas(r["entrada"], r["inicio_almoco"], r["fim_almoco"], r["saida"])
            if horas > 0.0:
                saldo_semana += (_horas_esperadas_dia(carga_horaria, almoco_incluso_na_carga, _almoco_padrao_horas) - horas)
                
        debito_acumulado += saldo_semana

        dias_uteis_faltando_semana = [d for d in dias_faltando_no_mes if d.isocalendar()[1] == semana]
        
        if len(dias_uteis_faltando_semana) > 0 and debito_acumulado > 0:
            debito_por_dia = debito_acumulado / len(dias_uteis_faltando_semana)
        else:
            debito_por_dia = 0.0
            
        dias_uteis_para_gerar_semana = [
            d for d in dias_uteis_faltando_semana if incluir_futuros or d < hoje
        ]
        
        dias_da_semana = [
            date(ano, mes, dia) for dia in range(1, total_dias + 1) 
            if date(ano, mes, dia).isocalendar()[1] == semana
        ]
        
        for data_atual in dias_da_semana:
            if not incluir_futuros and data_atual >= hoje:
                continue
            
            data_str = data_atual.strftime("%Y-%m-%d")
            
            if data_str in datas_com_ponto:
                continue
                
            if data_atual.weekday() >= 5:
                db.insert_ponto(usuario_id, data_str, None, None, None, None, None)
                continue
                
            feriado_nome = _nome_feriado(data_atual, feriados)
            if feriado_nome:
                db.insert_ponto(usuario_id, data_str, None, None, None, None, feriado_nome)
                continue
                
            if data_atual.isoformat() in datas_nao_uteis_manuais:
                continue
                
            if data_atual in dias_uteis_para_gerar_semana:
                if debito_por_dia > 2.0:
                    ex_min, ex_max = 0, 0
                else:
                    ex_min, ex_max = extra_min, extra_max
                    
                entrada, inicio_alm, fim_alm, saida = gerar_marcacoes(
                    data_atual,
                    debito_horas=debito_por_dia,
                    carga_horaria_horas=carga_horaria,
                    almoco_incluso_na_carga=almoco_incluso_na_carga,
                    hora_extra_minutos=(ex_min, ex_max),
                )
                db.insert_ponto(usuario_id, data_str, entrada, inicio_alm, fim_alm, saida, None)
                
        if debito_acumulado > 0:
            debito_acumulado -= debito_por_dia * len(dias_uteis_para_gerar_semana)
            
    pontos_finais = db.get_pontos(usuario_id, mes_str)
    saldo_total = 0.0
    for _, r in pontos_finais.iterrows():
        horas = calcular_horas_trabalhadas(r["entrada"], r["inicio_almoco"], r["fim_almoco"], r["saida"])
        if horas > 0.0:
            saldo_total += (_horas_esperadas_dia(carga_horaria, almoco_incluso_na_carga, _almoco_padrao_horas) - horas)
            
    db.set_horas_devidas(usuario_id, max(0.0, saldo_total))
    with db._conn() as conn:
        conn.execute("UPDATE ponto SET contabilizado = 1 WHERE usuario_id = ? AND strftime('%m-%Y', data) = ?", (usuario_id, mes_str))

    context.user_data[TEXTO] = (
        f"✅ Planilha gerada para {calendar.month_name[mes]} de {ano}"
        + (" (incluindo dias futuros)." if incluir_futuros else ".")
    )
    return await info_planilha(update, context)


async def gerar_futuro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Atalho que delega para gerar() com incluir_futuros=True."""
    return await gerar(update, context, incluir_futuros=True)


# ---------------------------------------------------------------------------
# baixar — exporta XLSX com as 4 colunas de marcação
# ---------------------------------------------------------------------------

async def baixar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    usuario_id = _usuario_id(update)
    mes_str    = context.user_data[MES]
    pontos: pd.DataFrame = db.get_pontos(usuario_id, mes_str)

    if pontos.empty:
        context.user_data[TEXTO] = "Não há pontos registrados para este mês."
        return await info_planilha(update, context)

    # Prepara DataFrame para exportação
    export = pontos.copy()
    export["Dia"]          = export["data"].apply(lambda d: int(d.split("-")[2]))
    export["Entrada"]      = export.apply(
        lambda r: "FERIADO" if r["feriado"] else r["entrada"], axis=1
    )
    export["Início Almoço"] = export["inicio_almoco"]
    export["Fim Almoço"]   = export["fim_almoco"]
    export["Saída"]        = export["saida"]
    export["Observação"]   = export["feriado"]
    export = export[["Dia", "Entrada", "Início Almoço", "Fim Almoço", "Saída", "Observação"]]

    pasta = f"uploads/{usuario_id}"
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = f"{pasta}/{mes_str}.xlsx"

    with pd.ExcelWriter(nome_arquivo, engine="xlsxwriter") as writer:
        export.to_excel(writer, sheet_name="Ponto", index=False)
        workbook  = writer.book
        worksheet = writer.sheets["Ponto"]

        center_fmt = workbook.add_format({"align": "center", "valign": "vcenter"})
        header_fmt = workbook.add_format({"bold": True, "align": "center", "bg_color": "#D9E1F2"})

        # Cabeçalho estilizado
        for col, name in enumerate(export.columns):
            worksheet.write(0, col, name, header_fmt)

        # Mescla feriados na linha (Entrada cobre até Saída)
        for i, row in export.iterrows():
            if pd.isna(row["Saída"]) and pd.notna(row["Entrada"]):
                if str(row["Entrada"]) in ("FERIADO",):
                    worksheet.merge_range(
                        i + 1, 1, i + 1, 4, row["Entrada"], center_fmt
                    )

        # Larguras de coluna
        worksheet.set_column(0, 0, 6)   # Dia
        worksheet.set_column(1, 4, 14)  # marcações
        worksheet.set_column(5, 5, 20)  # Observação

    mensagens: list[Message] = context.user_data.setdefault(MENSAGENS, [])
    mensagens.append(
        await context.bot.send_document(
            update.callback_query.from_user.id, open(nome_arquivo, "rb")
        )
    )
    context.user_data[TEXTO] = "📥 Planilha enviada."
    return SELECAO_MENU_PONTO
