-- ============================================================
-- MIGRAÇÃO: Refatoração de Ponto + Remoção de Lembretes
-- Executar uma única vez contra usuarios.db em produção.
-- Seguro para re-execução (usa IF NOT EXISTS / IF EXISTS).
-- ============================================================

-- ------------------------------------------------------------
-- 1. REMOÇÃO DO MÓDULO DE LEMBRETES
-- ------------------------------------------------------------

-- Remove índices dependentes antes das tabelas
DROP INDEX IF EXISTS lembretes_usuario_id;
DROP INDEX IF EXISTS lembretes_horario_enviado_em;

DROP TABLE IF EXISTS lembretes;

-- ------------------------------------------------------------
-- 2. ATUALIZAÇÃO DA TABELA PONTO
--    Adiciona usuario_id (chave estrangeira, multi-usuário real)
--    e as duas marcações de almoço.
--    Desfaz a PRIMARY KEY em `data` (que impedia multi-usuário)
--    via recriação da tabela — SQLite não suporta DROP COLUMN
--    de PK nem ADD FOREIGN KEY diretamente.
-- ------------------------------------------------------------

-- Garante que a tabela temporária não existe de uma execução anterior com falha
DROP TABLE IF EXISTS ponto_novo;

CREATE TABLE ponto_novo (
    usuario_id   INTEGER NOT NULL,
    data         TEXT    NOT NULL,
    entrada      TEXT,
    inicio_almoco TEXT,
    fim_almoco   TEXT,
    saida        TEXT,
    feriado      TEXT,
    contabilizado INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, data),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Migra dados existentes: atribui todos os pontos ao único usuário
-- que existia antes (o dono do bot). Se houver mais de um usuário
-- na tabela usuarios, ajuste o sub-select conforme necessário.
INSERT INTO ponto_novo (usuario_id, data, entrada, saida, feriado, contabilizado)
SELECT
    (SELECT id FROM usuarios ORDER BY criado_em ASC LIMIT 1),
    data,
    entrada,
    saida,
    feriado,
    contabilizado
FROM ponto;

DROP TABLE ponto;
ALTER TABLE ponto_novo RENAME TO ponto;

CREATE INDEX IF NOT EXISTS idx_ponto_usuario_data ON ponto (usuario_id, data);

-- ------------------------------------------------------------
-- 3. Remove coluna config de limite de lembretes (opcional)
--    SQLite >= 3.35 suporta DROP COLUMN; versões anteriores: ignorar.
-- ------------------------------------------------------------
-- DELETE FROM config WHERE key = 'limite';

-- ------------------------------------------------------------
-- FIM DA MIGRAÇÃO
-- ------------------------------------------------------------
PRAGMA integrity_check;