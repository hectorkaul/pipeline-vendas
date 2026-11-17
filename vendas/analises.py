"""
Consultas de analise. Tudo em SQL, usando CTE e funcoes de janela (LAG, SUM OVER, RANK).
Cada funcao devolve um Resultado, que depois vira CSV e tabela no relatorio HTML.
"""

import sqlite3
from dataclasses import dataclass


@dataclass
class Resultado:
    nome: str          # vira o nome do arquivo CSV
    titulo: str
    colunas: list[str]
    linhas: list[tuple]


def _consultar(conexao: sqlite3.Connection, nome: str, titulo: str, sql: str) -> Resultado:
    cursor = conexao.execute(sql)
    colunas = [c[0] for c in cursor.description]
    return Resultado(nome, titulo, colunas, cursor.fetchall())


def faturamento_mensal(conexao: sqlite3.Connection) -> Resultado:
    sql = """
    WITH mensal AS (
        SELECT substr(data, 1, 7)                          AS mes,
               SUM(valor_total_centavos)                   AS faturamento,
               SUM(custo_total_centavos)                   AS custo,
               COUNT(DISTINCT filial_id || '-' || numero_venda) AS vendas
          FROM fato_venda
         GROUP BY mes
    )
    SELECT mes,
           ROUND(faturamento / 100.0, 2)                                   AS faturamento,
           vendas,
           ROUND(faturamento / 100.0 / vendas, 2)                          AS ticket_medio,
           ROUND((faturamento - custo) * 100.0 / faturamento, 1)           AS margem_pct,
           ROUND((faturamento - LAG(faturamento) OVER (ORDER BY mes)) * 100.0
                 / LAG(faturamento) OVER (ORDER BY mes), 1)                AS variacao_pct
      FROM mensal
     ORDER BY mes
    """
    return _consultar(conexao, "faturamento_mensal", "Faturamento mensal", sql)


def participacao_filiais(conexao: sqlite3.Connection) -> Resultado:
    sql = """
    WITH por_filial AS (
        SELECT substr(f.data, 1, 7) AS mes, fi.nome AS filial, SUM(f.valor_total_centavos) AS faturamento
          FROM fato_venda f
          JOIN dim_filial fi ON fi.id = f.filial_id
         GROUP BY mes, fi.nome
    )
    SELECT mes,
           filial,
           ROUND(faturamento / 100.0, 2)                                          AS faturamento,
           ROUND(faturamento * 100.0 / SUM(faturamento) OVER (PARTITION BY mes), 1) AS participacao_pct
      FROM por_filial
     ORDER BY mes, faturamento DESC
    """
    return _consultar(conexao, "participacao_filiais", "Participação de cada filial no mês", sql)


def curva_abc(conexao: sqlite3.Connection) -> Resultado:
    """
    Curva ABC: os produtos que somam ~80% do faturamento sao A, os proximos ate 95% sao B
    e o resto e C. Ajuda a decidir em quais produtos o estoque nunca pode faltar.
    """
    sql = """
    WITH por_produto AS (
        SELECT p.codigo, p.descricao, p.categoria, SUM(f.valor_total_centavos) AS faturamento
          FROM fato_venda f
          JOIN dim_produto p ON p.codigo = f.codigo_produto
         GROUP BY p.codigo, p.descricao, p.categoria
    ),
    acumulado AS (
        SELECT *,
               faturamento * 100.0 / SUM(faturamento) OVER () AS pct,
               SUM(faturamento) OVER (ORDER BY faturamento DESC ROWS UNBOUNDED PRECEDING) * 100.0
                   / SUM(faturamento) OVER ()                 AS pct_acumulado
          FROM por_produto
    )
    SELECT codigo,
           descricao,
           categoria,
           ROUND(faturamento / 100.0, 2) AS faturamento,
           ROUND(pct, 2)                 AS pct,
           ROUND(pct_acumulado, 2)       AS pct_acumulado,
           CASE
               WHEN pct_acumulado - pct < 80 THEN 'A'
               WHEN pct_acumulado - pct < 95 THEN 'B'
               ELSE 'C'
           END                           AS classe
      FROM acumulado
     ORDER BY faturamento DESC
    """
    return _consultar(conexao, "curva_abc", "Curva ABC de produtos", sql)


def margem_por_categoria(conexao: sqlite3.Connection) -> Resultado:
    sql = """
    SELECT p.categoria,
           SUM(f.quantidade)                                                             AS itens,
           ROUND(SUM(f.valor_total_centavos) / 100.0, 2)                                 AS faturamento,
           ROUND(SUM(f.valor_total_centavos - f.custo_total_centavos) / 100.0, 2)        AS lucro_bruto,
           ROUND(SUM(f.valor_total_centavos - f.custo_total_centavos) * 100.0
                 / SUM(f.valor_total_centavos), 1)                                       AS margem_pct
      FROM fato_venda f
      JOIN dim_produto p ON p.codigo = f.codigo_produto
     GROUP BY p.categoria
     ORDER BY lucro_bruto DESC
    """
    return _consultar(conexao, "margem_categoria", "Margem por categoria", sql)


def media_por_dia_da_semana(conexao: sqlite3.Connection) -> Resultado:
    # parte do calendario (dim_data) para contar tambem os dias que nao tiveram venda
    sql = """
    WITH por_dia AS (
        SELECT d.data, d.dia_semana, d.nome_dia, d.feriado,
               COALESCE(SUM(f.valor_total_centavos), 0) AS faturamento
          FROM dim_data d
          LEFT JOIN fato_venda f ON f.data = d.data
         GROUP BY d.data, d.dia_semana, d.nome_dia, d.feriado
    )
    SELECT nome_dia,
           COUNT(*)                            AS dias,
           ROUND(AVG(faturamento) / 100.0, 2)  AS media_faturamento
      FROM por_dia
     WHERE feriado = 0 AND dia_semana <> 6
     GROUP BY dia_semana, nome_dia
     ORDER BY dia_semana
    """
    return _consultar(conexao, "media_dia_semana",
                      "Média de faturamento por dia da semana (sem feriados e domingos)", sql)


def vendas_em_feriados(conexao: sqlite3.Connection) -> Resultado:
    sql = """
    SELECT d.data,
           d.nome_dia,
           d.nome_feriado,
           ROUND(COALESCE(SUM(f.valor_total_centavos), 0) / 100.0, 2) AS faturamento
      FROM dim_data d
      LEFT JOIN fato_venda f ON f.data = d.data
     WHERE d.feriado = 1
     GROUP BY d.data, d.nome_dia, d.nome_feriado
     ORDER BY d.data
    """
    return _consultar(conexao, "feriados", "Feriados no período", sql)


def ranking_vendedores(conexao: sqlite3.Connection) -> Resultado:
    sql = """
    WITH por_vendedor AS (
        SELECT fi.nome AS filial, f.vendedor,
               COUNT(DISTINCT f.numero_venda)  AS vendas,
               SUM(f.valor_total_centavos)     AS faturamento
          FROM fato_venda f
          JOIN dim_filial fi ON fi.id = f.filial_id
         GROUP BY fi.nome, f.vendedor
    )
    SELECT filial,
           RANK() OVER (PARTITION BY filial ORDER BY faturamento DESC) AS posicao,
           vendedor,
           vendas,
           ROUND(faturamento / 100.0, 2)                               AS faturamento
      FROM por_vendedor
     ORDER BY filial, posicao
    """
    return _consultar(conexao, "ranking_vendedores", "Ranking de vendedores por filial", sql)


def melhores_clientes(conexao: sqlite3.Connection, limite: int = 10) -> Resultado:
    sql = f"""
    SELECT cliente,
           COUNT(DISTINCT filial_id || '-' || numero_venda) AS compras,
           ROUND(SUM(valor_total_centavos) / 100.0, 2)      AS total,
           MAX(data)                                        AS ultima_compra
      FROM fato_venda
     WHERE cliente <> 'Consumidor'
     GROUP BY cliente
     ORDER BY total DESC
     LIMIT {int(limite)}
    """
    return _consultar(conexao, "melhores_clientes", "Melhores clientes", sql)


def todas(conexao: sqlite3.Connection) -> list[Resultado]:
    return [
        faturamento_mensal(conexao),
        participacao_filiais(conexao),
        curva_abc(conexao),
        margem_por_categoria(conexao),
        media_por_dia_da_semana(conexao),
        vendas_em_feriados(conexao),
        ranking_vendedores(conexao),
        melhores_clientes(conexao),
    ]
