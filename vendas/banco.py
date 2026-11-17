"""Carga no SQLite. Os valores em dinheiro ficam em centavos (inteiro) para nao ter erro de arredondamento."""

import sqlite3
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .limpeza import VendaLimpa, converter_decimal

SCHEMA = Path(__file__).parent / "sql" / "schema.sql"
NOMES_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def para_centavos(valor: Decimal) -> int:
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def conectar(caminho: str | Path) -> sqlite3.Connection:
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas(conexao: sqlite3.Connection) -> None:
    conexao.executescript(SCHEMA.read_text(encoding="utf-8"))


def carregar_produtos(conexao: sqlite3.Connection, produtos: list[dict]) -> dict[str, int]:
    """Grava o cadastro e devolve {codigo: custo_em_centavos}, usado para calcular a margem."""
    custos = {}
    for p in produtos:
        codigo = p["codigo"].strip().upper()
        custo = para_centavos(converter_decimal(p["custo"]))
        custos[codigo] = custo
        conexao.execute(
            "INSERT INTO dim_produto (codigo, descricao, categoria, custo_centavos) VALUES (?, ?, ?, ?)",
            (codigo, p["descricao"].strip(), p["categoria"].strip(), custo),
        )
    return custos


def carregar_calendario(conexao: sqlite3.Connection, inicio: date, fim: date, feriados: dict[date, str]) -> None:
    """Uma linha por dia do periodo, mesmo nos dias sem venda (assim da para ver os 'buracos')."""
    dia = inicio
    linhas = []
    while dia <= fim:
        nome_feriado = feriados.get(dia)
        linhas.append((dia.isoformat(), dia.year, dia.month, dia.day, dia.weekday(), NOMES_DIAS[dia.weekday()],
                       1 if nome_feriado else 0, nome_feriado))
        dia += timedelta(days=1)
    conexao.executemany("INSERT INTO dim_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)


def carregar_vendas(conexao: sqlite3.Connection, vendas: list[VendaLimpa], custos: dict[str, int]) -> int:
    filiais: dict[str, int] = {}
    for nome in sorted({v.filial for v in vendas}):
        cursor = conexao.execute("INSERT INTO dim_filial (nome) VALUES (?)", (nome.capitalize(),))
        filiais[nome] = cursor.lastrowid

    linhas = []
    for v in vendas:
        unitario = para_centavos(v.valor_unitario)
        linhas.append((
            filiais[v.filial], v.numero_venda, v.data.isoformat(), v.codigo_produto, v.quantidade,
            unitario, unitario * v.quantidade, custos[v.codigo_produto] * v.quantidade,
            v.cliente, v.vendedor,
        ))

    conexao.executemany(
        """
        INSERT INTO fato_venda (filial_id, numero_venda, data, codigo_produto, quantidade,
                                valor_unit_centavos, valor_total_centavos, custo_total_centavos,
                                cliente, vendedor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        linhas,
    )
    return len(linhas)
