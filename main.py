"""
main.py
-------
Ponto de entrada do bot. Registra handlers e inicia o servidor de webhook.
"""

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
    filters,
)

from constantes import *
from usuarios_handler import start, voltar, encerrar
from ponto_handler import (
    baixar,
    campo_ponto,
    encerrar_edicao_ponto,
    gerar,
    gerar_futuro,
    gerar_dia,
    escolher_mes,
    gerar_planilha_acoes,
    info_planilha,
    valor_campo,
)
from utils import limite, salvar_alteracoes


def _definir_locale() -> None:
    for loc in ("pt_BR.UTF-8", "pt_BR.utf8", "Portuguese_Brazil.1252"):
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return
        except locale.Error:
            continue


def main() -> None:
    _definir_locale()
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    token    = os.getenv("BOT_TOKEN")
    admin_id = int(os.getenv("BOT_ADMIN_ID"))

    application = ApplicationBuilder().token(token).build()

    # ------------------------------------------------------------------
    # Sub-conversa: edição manual de um dia (campo a campo)
    # ------------------------------------------------------------------
    ponto_add_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r"^\d{2}$"),
                campo_ponto,
            )
        ],
        states={
            SELECIONANDO_CAMPO: [
                CallbackQueryHandler(
                    valor_campo,
                    pattern=f"^(?!{END}|{CANCELAR}).*$",
                )
            ],
            DIGITANDO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    salvar_alteracoes(campo_ponto),
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(encerrar_edicao_ponto, pattern=f"^{END}|{CANCELAR}$"),
            CommandHandler("cancelar", encerrar),
        ],
        map_to_parent={END: SELECAO_MENU_PONTO},
    )

    # ------------------------------------------------------------------
    # Estados do submenu de ponto
    # ------------------------------------------------------------------
    ponto_menu_states = [
        CallbackQueryHandler(gerar,              pattern=f"^{GERAR}$"),
        CallbackQueryHandler(gerar_futuro,       pattern=f"^{GERAR_FUTURO}$"),
        CallbackQueryHandler(gerar_planilha_acoes, pattern=f"^{GERAR_PLANILHA}$"),
        CallbackQueryHandler(baixar,             pattern=f"^{BAIXAR_PLANILHA}$"),
        CallbackQueryHandler(gerar_dia,          pattern=f"^{GERAR_DIA}$"),
        ponto_add_conv,
    ]

    ponto_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r"^\d{2}-\d{4}$"),
                info_planilha,
            )
        ],
        states={SELECAO_MENU_PONTO: ponto_menu_states},
        fallbacks=[CallbackQueryHandler(voltar, pattern=f"^{END}|{CANCELAR}$")],
        map_to_parent={END: SELECAO_MENU},
    )

    # ------------------------------------------------------------------
    # Conversa raiz
    # ------------------------------------------------------------------
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECAO_MENU: [
                ponto_conv,
                CallbackQueryHandler(start,     pattern=f"^{CANCELAR}$"),
                CallbackQueryHandler(escolher_mes, pattern=f"^{MENU_PONTO}$"),
                CallbackQueryHandler(encerrar,  pattern=f"^{END}$"),
            ]
        },
        fallbacks=[CommandHandler("cancelar", encerrar)],
    )

    application.add_handler(CommandHandler("limite", limite(admin_id)))
    application.add_handler(conv_handler)

    application.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path="webhook",
        secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
        webhook_url=os.getenv("WEBHOOK_URL"),
    )

    #application.run_polling() --- Para desenvolvimento local, sem necessidade de webhook


if __name__ == "__main__":
    main()