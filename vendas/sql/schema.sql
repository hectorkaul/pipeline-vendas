-- Modelo em estrela: uma tabela fato (as vendas) e dimensoes ao redor.
-- E o formato que o Power BI trabalha melhor.

DROP TABLE IF EXISTS fato_venda;
DROP TABLE IF EXISTS dim_produto;
DROP TABLE IF EXISTS dim_filial;
DROP TABLE IF EXISTS dim_data;

CREATE TABLE dim_produto (
    codigo        TEXT PRIMARY KEY,
    descricao     TEXT NOT NULL,
    categoria     TEXT NOT NULL,
    custo_centavos INTEGER NOT NULL
);

CREATE TABLE dim_filial (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_data (
    data          TEXT PRIMARY KEY,   -- aaaa-mm-dd
    ano           INTEGER NOT NULL,
    mes           INTEGER NOT NULL,
    dia           INTEGER NOT NULL,
    dia_semana    INTEGER NOT NULL,   -- 0 = segunda ... 6 = domingo
    nome_dia      TEXT NOT NULL,
    feriado       INTEGER NOT NULL DEFAULT 0,
    nome_feriado  TEXT
);

CREATE TABLE fato_venda (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filial_id           INTEGER NOT NULL REFERENCES dim_filial (id),
    numero_venda        TEXT    NOT NULL,
    data                TEXT    NOT NULL REFERENCES dim_data (data),
    codigo_produto      TEXT    NOT NULL REFERENCES dim_produto (codigo),
    quantidade          INTEGER NOT NULL CHECK (quantidade > 0),
    valor_unit_centavos INTEGER NOT NULL,
    valor_total_centavos INTEGER NOT NULL,
    custo_total_centavos INTEGER NOT NULL,
    cliente             TEXT NOT NULL,
    vendedor            TEXT NOT NULL
);

CREATE INDEX idx_fato_data ON fato_venda (data);
CREATE INDEX idx_fato_produto ON fato_venda (codigo_produto);
CREATE INDEX idx_fato_filial ON fato_venda (filial_id);
