from telegram.ext import ConversationHandler

# Estados principais da conversa
(
    SELECAO_MENU,        # Tela inicial
    MENU_LEMBRETES,      # Entrada do menu de lembretes
    SELECAO_MENU_LEMBRETE,  # Submenu de lembretes
    LISTAR_LEMBRETES,    # Lista de lembretes
    LIMPAR_LEMBRETES     # Apagar todos
) = map(chr, range(5))

# Operações com lembretes
(
    ADICIONAR_LEMBRETE,  # Inicia criação de novo lembrete
    EDITAR_LEMBRETE,     # Editar lembrete existente
    SELECIONANDO_CAMPO,  # Escolhendo campo (horário, mensagem)
    CANCELAR,            # Cancelamento de operação
    EXCLUIR_LEMBRETE     # Apagar um lembrete
) = map(chr, range(5, 10))

# Marcador de fim de conversa
END = ConversationHandler.END

# Constantes auxiliares para controle de estado interno
(
    INICIO,              # Marca início de conversa
    DIGITANDO,           # Usuário digitando valor de campo
    HORARIO,             # Campo "horário"
    EDITANDO,            # Flag para edição ativa
    MENSAGEM,            # Campo "mensagem"
    CAMPOS,              # Dicionário dos campos sendo editados
    CAMPO_SELECIONADO,   # Campo que está sendo editado no momento
    TEXTO                # Texto temporário a ser exibido em telas
) = map(chr, range(10, 18))
