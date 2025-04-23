from telegram.ext import ConversationHandler

# Estados principais da conversa
(
    SELECAO_MENU,        # Tela inicial
    MENU_LEMBRETES,      # Entrada do menu de lembretes
    MENU_PONTO,          # Entrada do menu de ponto
    SELECAO_MENU_LEMBRETE,  # Submenu de lembretes
    SELECAO_MENU_PONTO,  # Submenu de ponto
    LISTAR_LEMBRETES,    # Lista de lembretes
    LIMPAR_LEMBRETES     # Apagar todos
) = map(chr, range(7))

# Operações com lembretes
(
    ADICIONAR_LEMBRETE,  # Inicia criação de novo lembrete
    EDITAR_LEMBRETE,     # Editar lembrete existente
    SELECIONANDO_CAMPO,  # Escolhendo campo (horário, mensagem)
    CANCELAR,            # Cancelamento de operação
    EXCLUIR_LEMBRETE,     # Apagar um lembrete
    GERAR_PLANILHA,     # Menu de geração de planilha
    ACAO_PLANILHA,     # Escolha de ação para menu de geração de planilha
    BAIXAR_PLANILHA,     # Menu de download de planilha
) = map(chr, range(7, 15))

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
    TEXTO,               # Texto temporário a ser exibido em telas
    GERAR,               # Gerar planilha
) = map(chr, range(15, 24))
