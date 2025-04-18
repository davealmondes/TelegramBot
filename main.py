import os
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
    encerrar_edicao,
    menu_lembrete,
    mostrar_detalhes_lembrete,
    salvar_alteracoes,
    limpar,
    listar,
    valor_campo
)

def limite(admin_id: int):
    async def handler(update, context):
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


def main():
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
        entry_points=[CallbackQueryHandler(campo_lembrete, pattern=f"^{ADICIONAR_LEMBRETE}|{EDITAR_LEMBRETE}$")],
        states={
            SELECIONANDO_CAMPO: [CallbackQueryHandler(valor_campo, pattern=f"^(?!{END}|{CANCELAR}).*$")],
            DIGITANDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_alteracoes)]
        },
        fallbacks=[
            CallbackQueryHandler(encerrar_edicao, pattern=f"^{END}|{CANCELAR}$"),
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
        CallbackQueryHandler(apagar_lembrete, pattern=f"^{EXCLUIR_LEMBRETE}$"),
        CallbackQueryHandler(limpar, pattern="^limpar_")
    ]

    lembretes_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_lembrete, pattern=f"^{MENU_LEMBRETES}$")],
        states={SELECAO_MENU_LEMBRETE: lembretes_selecao},
        fallbacks=[CallbackQueryHandler(voltar, pattern=f"^{END}$")],
        map_to_parent={END: SELECAO_MENU}
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={SELECAO_MENU: [lembretes_conv, add_conv, CallbackQueryHandler(encerrar, pattern=f"^{END}$")]},
        fallbacks=[CommandHandler("cancelar", encerrar)]
    )

    application.add_handler(CommandHandler("limite", limite(admin_id)))
    application.add_handler(conv_handler)

    application.bot.set_webhook(
        url=OS.getenv("WEBHOOK_URL"),
        secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
    )

    application.run_webhook(
        listen='0.0.0.0',
        port=8000,
        url_path='webhook',
        secret_token=os.getenv("WEBHOOK_SECRET_TOKEN"),
        webhook_url=os.getenv("WEBHOOK_URL")
    )
    

if __name__ == '__main__':
    main()
