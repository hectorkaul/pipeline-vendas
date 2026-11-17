"""Leitura dos arquivos exportados pelas filiais."""

import csv
from pathlib import Path


def ler_csv(arquivo: Path) -> list[dict[str, str]]:
    """
    Le um CSV separado por ';'. Tenta UTF-8 primeiro e, se falhar,
    le como latin-1 (alguns sistemas antigos ainda exportam assim).
    """
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with open(arquivo, newline="", encoding=encoding) as f:
                return list(csv.DictReader(f, delimiter=";"))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Nao consegui ler {arquivo}")


def ler_vendas(pasta: Path) -> dict[str, list[dict[str, str]]]:
    """Retorna {nome_da_filial: linhas} para cada arquivo vendas_<filial>.csv da pasta."""
    arquivos = sorted(pasta.glob("vendas_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo vendas_*.csv em {pasta}. Rode antes: python -m vendas.gerar_dados")
    return {arquivo.stem.removeprefix("vendas_"): ler_csv(arquivo) for arquivo in arquivos}


def ler_produtos(pasta: Path) -> list[dict[str, str]]:
    arquivo = pasta / "produtos.csv"
    if not arquivo.exists():
        raise FileNotFoundError(f"Cadastro de produtos nao encontrado: {arquivo}")
    return ler_csv(arquivo)
