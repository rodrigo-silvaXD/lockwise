-- LOCKWISE — esquema de referencia (PostgreSQL).
-- O codigo cria as tabelas com SQLAlchemy (create_all) e garante a semente;
-- este arquivo documenta o resultado para leitura humana e para o relatorio.

CREATE TABLE usuario (
    id            SERIAL PRIMARY KEY,
    nome          VARCHAR(100) NOT NULL,
    codigo_senha  SMALLINT     NOT NULL,           -- 4 bits do comparador: 1011 = 11
    ativo         BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE acesso (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER      REFERENCES usuario(id),  -- NULL em NEGADO e BLOQUEADO
    momento     TIMESTAMPTZ  NOT NULL,                -- instante da transicao no circuito (UTC)
    resultado   VARCHAR(20)  NOT NULL,                -- LIBERADO | NEGADO | BLOQUEADO
    tentativa   SMALLINT     NOT NULL,                -- 1, 2 ou 3 (o hardware bloqueia na 3a)
    energia_mj  INTEGER      NOT NULL                 -- 18200 em LIBERADO (docs/fisica.md §6), 0 nos demais
);

CREATE INDEX idx_acesso_momento ON acesso(momento);

CREATE TABLE alerta (
    id         SERIAL PRIMARY KEY,
    tipo       VARCHAR(30)  NOT NULL,                 -- BLOQUEIO | DESBLOQUEIO_ADMIN (gateway)
                                                      -- TENTATIVAS_SUSPEITAS | ACESSO_FORA_DO_HORARIO (politica)
    momento    TIMESTAMPTZ  NOT NULL,
    resolvido  BOOLEAN      NOT NULL DEFAULT FALSE,
    detalhe    VARCHAR(200),
    acesso_id  INTEGER      REFERENCES acesso(id)     -- o acesso que gerou o alerta, quando houver
);

CREATE INDEX idx_alerta_momento ON alerta(momento);

-- Semente: o circuito tem uma senha gravada, logo um morador. O gateway envia usuario_id = 1.
INSERT INTO usuario (id, nome, codigo_senha, ativo) VALUES (1, 'Morador', 11, TRUE)
ON CONFLICT (id) DO NOTHING;
