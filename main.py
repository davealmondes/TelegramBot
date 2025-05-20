import os
import locale
import logging
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

from constantes import *
from jobs import callback30
from usuarios_handler import start, voltar, encerrar
from lembretes_handler import (
    apagar_lembrete,
    apagar_lembretes,
    campo_lembrete,
    encerrar_edicao_lembrete,
    menu_lembrete,
    mostrar_detalhes_lembrete,
    limpar,
    listar,
    valor_campo
)
from ponto_handler import baixar, campo_ponto, encerrar_edicao_ponto, gerar, gerar_dia, escolher_mes, gerar_planilha_acoes, info_planilha, menu_ponto
from utils import limite, salvar_alteracoes

def definir_locale():
    """Define a localidade para o sistema."""
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')


def main() -> None:
    definir_locale()
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    token = os.getenv("BOT_TOKEN")
    admin_id = int(os.getenv("BOT_ADMIN_ID"))

    application = ApplicationBuilder().token(token).build()

    # Agendamento do job
    application.job_queue.run_repeating(callback30, interval=30, first=1)

    # Conversa de preenchimento de lembrete
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(campo_lembrete, pattern=f"^{ADICIONAR}|{EDITAR}$")],
        states={
            SELECIONANDO_CAMPO: [CallbackQueryHandler(valor_campo, pattern=f"^(?!{END}|{CANCELAR}).*$")],
            DIGITANDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_alteracoes(campo_lembrete))]
        },
        fallbacks=[
            CallbackQueryHandler(encerrar_edicao_lembrete, pattern=f"^{END}|{CANCELAR}$"),
            CommandHandler("cancelar", encerrar)
        ],
        map_to_parent={
            END: SELECAO_MENU_LEMBRETE,
            SELECAO_MENU: SELECAO_MENU
        }
    )

    # Submenu de lembretes
    lembretes_selecao = [
        add_conv,
        CallbackQueryHandler(menu_lembrete, pattern=f"^{MENU_LEMBRETES}$"),
        CallbackQueryHandler(listar, pattern=f"^{LISTAR_LEMBRETES}$"),
        CallbackQueryHandler(mostrar_detalhes_lembrete, pattern="^info_"),
        CallbackQueryHandler(apagar_lembretes, pattern=f"^{LIMPAR_LEMBRETES}$"),
        CallbackQueryHandler(apagar_lembrete, pattern=f"^{EXCLUIR}$"),
        CallbackQueryHandler(limpar, pattern="^limpar_")
    ]

    lembretes_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_lembrete, pattern=f"^{MENU_LEMBRETES}$")],
        states={SELECAO_MENU_LEMBRETE: lembretes_selecao},
        fallbacks=[CallbackQueryHandler(voltar, pattern=f"^{END}$")],
        map_to_parent={END: SELECAO_MENU}
    )

    ponto_add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~ filters.COMMAND & filters.Regex("^\\d{2}$"), campo_ponto)],
        states={
            SELECIONANDO_CAMPO: [CallbackQueryHandler(valor_campo, pattern=f"^(?!{END}|{CANCELAR}).*$")],
            DIGITANDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_alteracoes(campo_ponto))]
        },
        fallbacks=[
            CallbackQueryHandler(encerrar_edicao_ponto, pattern=f"^{END}|{CANCELAR}$"),
            CommandHandler("cancelar", encerrar),
        ],
        map_to_parent={
            END: SELECAO_MENU_PONTO
        }
    )

    ponto_menu = [
        CallbackQueryHandler(gerar, pattern=f"^{GERAR}$"),
        CallbackQueryHandler(gerar_planilha_acoes, pattern=f"^{GERAR_PLANILHA}$"),
        CallbackQueryHandler(baixar, pattern=f"^{BAIXAR_PLANILHA}$"),
        CallbackQueryHandler(gerar_dia, pattern=f"^{GERAR_DIA}$"),
        CallbackQueryHandler(info_planilha, pattern=f"^{INFO_PLANILHA}$"),
        ponto_add_conv
    ]

    ponto_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~ filters.COMMAND & filters.Regex("^\\d{2}-\\d{4}$"), menu_ponto)],
        states={SELECAO_MENU_PONTO: ponto_menu},
        fallbacks=[CallbackQueryHandler(voltar, pattern=f"^{END}|{CANCELAR}$")],
        map_to_parent={END: SELECAO_MENU}
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={SELECAO_MENU: [
            lembretes_conv, 
            ponto_conv, 
            add_conv, 
            CallbackQueryHandler(start, pattern=f"^{CANCELAR}$"),
            CallbackQueryHandler(escolher_mes, pattern=f"^{MENU_PONTO}"),
            CallbackQueryHandler(encerrar, pattern=f"^{END}$")]},
        fallbacks=[CommandHandler("cancelar", encerrar)],
    )

    application.add_handler(CommandHandler("limite", limite(admin_id)))
    application.add_handler(conv_handler)

    webhook_url: str = os.getenv("WEBHOOK_URL")
    webhook_secret_token: str = os.getenv("WEBHOOK_SECRET_TOKEN")
   
    # Run the webhook server in a separate thread
    application.run_webhook(
        listen='0.0.0.0',
        port=8000,
        url_path='webhook',
        secret_token=webhook_secret_token,
        webhook_url=webhook_url,
    )

if __name__ == '__main__':
    main()


    
