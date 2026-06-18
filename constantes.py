from telegram.ext import ConversationHandler

# ---------------------------------------------------------------------------
# Estados principais da conversa
# ---------------------------------------------------------------------------
(
    SELECAO_MENU,           # Tela inicial
    MENU_PONTO,             # Entrada do menu de ponto
    SELECAO_MENU_PONTO,     # Submenu de ponto
) = map(chr, range(3))

# ---------------------------------------------------------------------------
# Operações com ponto
# ---------------------------------------------------------------------------
(
    ADICIONAR,          # Inicia criação de novo registro
    SELECIONANDO_CAMPO, # Escolhendo campo
    CANCELAR,           # Cancelamento de operação
    GERAR_PLANILHA,     # Menu de geração de planilha
    BAIXAR_PLANILHA,    # Menu de download de planilha
    GERAR,              # Gerar dias faltantes (passados)
    GERAR_DIA,          # Gerar dia específico
    GERAR_FUTURO,       # Gerar dias faltantes incluindo futuros
    PREENCHER_AUTO,     # Preencher dia atual automaticamente no lançamento manual
) = map(chr, range(3, 12))

LIMPAR_DIA = chr(28)
RECALCULAR = chr(29)

# Marcador de fim de conversa
END = ConversationHandler.END

# ---------------------------------------------------------------------------
# Constantes auxiliares para controle de estado interno (user_data keys)
# ---------------------------------------------------------------------------
(
    INICIO,             # Marca início de conversa
    DIGITANDO,          # Usuário digitando valor de campo
    HORARIO,            # Campo "horário" (legado lembrete — mantido p/ compat.)
    EDITANDO,           # Flag para edição ativa
    MENSAGEM,           # Campo "mensagem"
    CAMPOS,             # Dicionário dos campos sendo editados
    CAMPO_SELECIONADO,  # Campo que está sendo editado no momento
    TEXTO,              # Texto temporário a ser exibido em telas
    MENSAGENS,          # Lista de Message para cleanup
    ENTRADA,            # Campo de entrada
    SAIDA,              # Campo de saída
    INICIO_ALMOCO,      # Campo início do almoço
    FIM_ALMOCO,         # Campo fim do almoço
    OBSERVACAO,         # Campo de observação / feriado
    MES,                # Mês selecionado (formato MM-YYYY)
    DIA,                # Dia selecionado
    DIAS_FALTANDO,      # Contagem de dias a registrar
) = map(chr, range(11, 28))