import os
import logging
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.ext import ApplicationBuilder, CommandHandler,CallbackQueryHandler, MessageHandler, ConversationHandler, filters
from handlers import ajuda, apagar_lembretes, cancelar_edicao, editar, editar_horario, editar_mensagem, escolher_campo, mostrar_detalhes_lembrete, salvar_alteracoes, start, inscrever, limpar, listar, limite
from jobs import callback30

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

# Estados para a conversa de edição
EDIT_CHOOSE, EDIT_FIELD, EDIT_TIME, EDIT_MESSAGE = range(4)

def main():
    token: str = os.getenv("BOT_TOKEN")
    admin_id: int = int(os.getenv("BOT_ADMIN_ID"))
    application = ApplicationBuilder().token(token).build()

    job_queue = application.job_queue
    job_queue.run_repeating(callback30, interval=30, first=1)

    # ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('editar', editar)],
        states={
            EDIT_CHOOSE:[CallbackQueryHandler(escolher_campo, pattern='^editar_')],
            EDIT_FIELD:[CallbackQueryHandler(editar_horario, pattern='^horario$'),
                CallbackQueryHandler(editar_mensagem, pattern='^mensagem$'),
                CallbackQueryHandler(cancelar_edicao, pattern='^cancelar')],
            EDIT_TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_alteracoes)],
            EDIT_MESSAGE:[MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_alteracoes)]
        }, fallbacks=[CommandHandler('cancelar', cancelar_edicao)]
    )


    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('inscrever', inscrever))
    application.add_handler(CommandHandler('limpar', limpar))
    application.add_handler(CallbackQueryHandler(apagar_lembretes, pattern='^limpar'))
    application.add_handler(CommandHandler('listar', listar))
    application.add_handler(CommandHandler('limite', limite(admin_id)))
    application.add_handler(CommandHandler('ajuda', ajuda))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(mostrar_detalhes_lembrete, pattern='^info_'))

    application.run_polling()

if __name__ == '__main__':
    main()