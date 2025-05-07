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
    ADICIONAR,           # Inicia criação de novo registro
    EDITAR,              # Editar registro existente
    SELECIONANDO_CAMPO,  # Escolhendo campo (horário, mensagem)
    CANCELAR,            # Cancelamento de operação
    EXCLUIR,             # Apagar um registro
    GERAR_PLANILHA,      # Menu de geração de planilha
    ACAO_PLANILHA,       # Escolha de ação para menu de geração de planilha
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
    GERAR_DIA,          # Gerar dia específico
    MENSAGENS,           # Mensagem a ser exibida
    ENTRADA,            # Campo de entrada
    SAIDA,              # Campo de saída
    OBSERVACAO,         # Campo de observação
) = map(chr, range(15, 29))
