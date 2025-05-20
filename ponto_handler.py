import calendar
from datetime import date, datetime
import math
import os
import holidays
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes
from constantes import *
from database import Database
from utils import random_entrada, random_saida

db = Database()

async def menu_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the menu selection."""
    """Mostra o menu principal de ponto."""
    texto = context.user_data.pop(TEXTO, 'Menu de ponto...')
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    if update.message:
        context.user_data[MES] = update.message.text
        mensagens.append(update.message)

    context.user_data[EDITANDO] = None
    context.user_data[INICIO] = True

    buttons = [
        [
            InlineKeyboardButton(text='Gerar Planilha', callback_data=str(GERAR_PLANILHA)),
            InlineKeyboardButton(text='Baixar Planilha', callback_data=str(BAIXAR_PLANILHA)),
            InlineKeyboardButton(text='Info Planilha', callback_data=str(INFO_PLANILHA))
        ],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]
    if update.message:
        mensagens.append(await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(buttons)))
    else:
        mensagens.append(await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons)))
    return SELECAO_MENU_PONTO

async def escolher_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
                
    mes = datetime.now().month
    ano = datetime.now().year
    meses = [f"{ mes - (-(12 - i) if mes -i <= 0 else i):02}-{ano - (1 if mes - i <= 0 else 0)}" for i in range(12)]
    buttons = [
        [InlineKeyboardButton(text=mes, callback_data=str(mes))] for mes in meses
    ]
    await update.callback_query.edit_message_reply_markup(InlineKeyboardMarkup([[InlineKeyboardButton(text='Voltar', callback_data=str(CANCELAR))]]))
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    mensagens.append(await context.bot.send_message(update.callback_query.from_user.id,
        "Selecione o mês para gerar a planilha.",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    ))
    context.user_data[INICIO] = True
    return SELECAO_MENU

async def info_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe informações sobre a planilha."""
    data = context.user_data.get(MES)
    (mes, ano) = map(int, data.split('-'))
    pontos_existentes: pd.DataFrame= db.get_pontos(data)
    feriados = holidays.BR(years=ano, state='SP', language='pt_BR')
    dias_do_mes = [
        date(ano, mes, dia)
        for dia in range(1, calendar.monthrange(ano, mes)[1] + 1)
    ]
    dias_uteis = [
        d for d in dias_do_mes if d.weekday() < 5 and d not in feriados
    ]
    dias_com_ponto = [
        d for d in dias_uteis if d.strftime("%Y-%m-%d") in pontos_existentes["data"].values
    ]

    dias_faltando = [
        d for d in dias_uteis if d.strftime("%Y-%m-%d") not in pontos_existentes["data"].values
    ]

    horas_trabalhadas = 0.0
    horas_esperadas = len(dias_com_ponto) * 9
    horas_devidas = 0.0
    horas_extras = 0.0

    for d in dias_com_ponto:
        ponto =  pontos_existentes.query(f"data == '{d.strftime('%Y-%m-%d')}'")
        if not ponto.empty:
            entrada = ponto["entrada"].values[0]
            saida = ponto["saida"].values[0]
            if entrada and saida:
                entrada_dt = datetime.strptime(entrada, "%H:%M")
                saida_dt = datetime.strptime(saida, "%H:%M")
                horas = (saida_dt - entrada_dt).seconds / 3600
                horas_trabalhadas += horas
                saldo = 9 - horas
                if saldo > 0:
                    horas_devidas += saldo
                else:
                    horas_extras += abs(saldo)
    
    horas_trabalhadas_horas = math.floor(horas_trabalhadas)
    horas_trabalhadas_minutos = math.floor((horas_trabalhadas - horas_trabalhadas_horas) * 60)
    horas_devidas_horas = math.floor(horas_devidas)
    horas_devidas_minutos = math.floor((horas_devidas - horas_devidas_horas) * 60)
    horas_extras_horas = math.floor(horas_extras)
    horas_extras_minutos = math.floor((horas_extras - horas_extras_horas) * 60)

    texto = f"Planilha de {calendar.month_name[mes]} de {ano}:\n"
    texto += f"Total de dias úteis: {len(dias_uteis)}\n"
    texto += f"Total de dias trabalhados registrados: {len(dias_com_ponto)}\n"
    texto += f"Total de dias a trabalhar / registrar: {len(dias_faltando)}\n"
    texto += f"Total de horas trabalhadas registradas: {horas_trabalhadas_horas} horas e {horas_trabalhadas_minutos} minutos\n"
    texto += f"Total de horas trabalhadas esperadas: {horas_esperadas:.2f} horas\n"
    texto += f"Total de horas devidas registradas: {horas_devidas_horas} horas e {horas_devidas_minutos} minutos\n"
    texto += f"Total de horas extras registradas: {horas_extras_horas} horas e {horas_extras_minutos} minutos\n"

    mensagens = context.user_data.get(MENSAGENS, [])
    mensagens.append(await update.callback_query.edit_message_text(texto, reply_markup=update.callback_query.message.reply_markup))
    return SELECAO_MENU_PONTO



async def gerar_planilha_acoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = context.user_data.pop(TEXTO, 'Gerando planilha...')
    buttons = [
        [
            InlineKeyboardButton(text='Gerar dias faltantes.', callback_data=str(GERAR)),
            InlineKeyboardButton(text='Gerar dia específico.', callback_data=str(GERAR_DIA))
        ],
        [InlineKeyboardButton(text='Voltar', callback_data=str(END))]
    ]
    await update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons)) #callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    return SELECAO_MENU_PONTO

async def menu_ponto_superior(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await menu_ponto(update, context)
    return END

async def gerar_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    (mes, ano) = map(int, context.user_data.get(MES, "").split('-'))
    dias = calendar.monthrange(ano, mes)[1]
    keyboard = [
         [f"{dia:02}", f"{dia +1:02}"] if dia + 1 <= dias else [f"{dia:02}"] for dia in range(1, dias + 1, 2)
    ]
    await update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Voltar', callback_data=str(CANCELAR))]]))
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    mensagens.append(await context.bot.send_message(update.callback_query.from_user.id,
        "Selecione o dia para gerar a planilha.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    ))
    return SELECAO_MENU_PONTO

async def campo_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe campos a preencher/editáveis do ponto."""
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    if update.message:
        mensagens.append(update.message)
        if context.user_data.get(INICIO):
            context.user_data[DIA] = update.message.text
            context.user_data[INICIO] = False


    (mes, ano) = map(int, context.user_data.get(MES, "").split('-'))
    ponto = db.get_ponto(date(ano, mes, int(update.message.text)))
    if ponto:
        context.user_data[CAMPOS] = {
            ENTRADA: ponto[0],
            SAIDA: ponto[1],
            OBSERVACAO: ponto[2]
        }
        texto = f"Editando ponto..."
    else:
        if context.user_data.get(INICIO):
            context.user_data[CAMPOS] = {}
        texto = f"Adicionando ponto..."        

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Entrada", callback_data=str(ENTRADA)),
        InlineKeyboardButton("Saida", callback_data=str(SAIDA)),
        InlineKeyboardButton("Observação", callback_data=str(OBSERVACAO))],
        [InlineKeyboardButton("Cancelar", callback_data=str(CANCELAR)),
        InlineKeyboardButton("Concluir", callback_data=str(END))]
    ])

    if update.message:
        await update.message.reply_text(texto, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(texto, reply_markup=keyboard)
    return SELECIONANDO_CAMPO

async def encerrar_edicao_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = update.callback_query.data
    usuario_id = update.callback_query.from_user.id

    if data == str(CANCELAR):
        context.user_data[CAMPOS] = {}
        context.user_data[TEXTO] = "Edição cancelada..."
        await menu_ponto(update, context)
        return END

    if data == str(END):
        (mes, ano) = map(int, context.user_data.get(MES, "").split('-'))
        dia = int(context.user_data.get(DIA))
        data_dt = date(ano, mes, dia)
        campos = context.user_data.get(CAMPOS, {})
        entrada = campos.get(ENTRADA)
        saida = campos.get(SAIDA)
        observacao = campos.get(OBSERVACAO)

        db.insert_ponto(data_dt, entrada, saida, observacao)
        context.user_data[TEXTO] = "Ponto registrado com sucesso."
        await menu_ponto(update, context)
        return END

async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    (mes, ano) = map(int, context.user_data.get(MES, "").split('-'))
    data = context.user_data.get(MES)
    (mes, ano) = map(int, data.split('-'))
    pontos_existentes: pd.DataFrame = db.get_pontos(data)
    mes_atual: int = datetime.now().month
    hoje: int = datetime.now().day
    feriados = holidays.BR(years=ano, state='SP', language='pt_BR')
    for dia in range(1, calendar.monthrange(ano, mes)[1] + 1):
        if dia > hoje and mes_atual == mes:
            break
        data: datetime = datetime(ano, mes, dia)
        data_str: str = data.strftime("%Y-%m-%d")
        if (data_str,) in pontos_existentes["data"].values:
            continue
        elif data.weekday() >= 5:
            entrada = saida = feriado_nome = None
        elif data in feriados:
            entrada = saida = None
            feriado_nome = feriados[data]
        else:
            entrada_dt = random_entrada(data)
            saida_dt = random_saida(entrada_dt)
            entrada = entrada_dt.strftime("%H:%M")
            saida = saida_dt.strftime("%H:%M")
            feriado_nome = None
        db.insert_ponto(data_str, entrada, saida, feriado_nome)
    context.user_data[TEXTO] = f"Planilha gerada com sucesso para {calendar.month_name[mes]} de {ano}."
    return await menu_ponto(update, context)

async def baixar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.get(MES)
    pontos: pd.DataFrame = db.get_pontos(data)
    if pontos.empty:
        context.user_data[TEXTO] = f"Não há pontos registrados."
        return await menu_ponto(update, context)

    # Corrigir coluna para exportação
    pontos["entrada"] = pontos.apply(lambda row: "FERIADO" if row['feriado'] else row['entrada'], axis=1)
    pontos = pontos[["dia", "entrada", "saida", "feriado"]]
    pontos.columns = ["Dia", "Entrada", "Saída", "Observação"]

    # Exportar com mesclagem dos feriados
    pasta: str = f"uploads/{update.callback_query.from_user.id}"
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo: str = f"{pasta}/{data}.xlsx"
    with pd.ExcelWriter(nome_arquivo, engine='xlsxwriter') as writer:
        pontos.to_excel(writer, sheet_name='Ponto', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Ponto']

        center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        
        for i, row in pontos.iterrows():
            if pd.isna(row['Saída']) and not pd.isna(row['Entrada']):
                if "FERIADO" in row['Entrada'] or "PRESENCIAL" in row['Entrada']:
                    worksheet.merge_range(i + 1, 1, i + 1, 2, row['Entrada'], center_format)
    mensagens: list[Message] = context.user_data.get(MENSAGENS, [])
    mensagens.append(await context.bot.send_document(update.callback_query.from_user.id, open(nome_arquivo, "rb")))
    context.user_data[TEXTO] = "Planilha resgatada..."
    return SELECAO_MENU_PONTO