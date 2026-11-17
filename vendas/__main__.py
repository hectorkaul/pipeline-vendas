"""
Roda o pipeline completo:

    python -m vendas
    python -m vendas --entrada dados/entrada --saida saida --sem-api
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import analises, banco, extracao, feriados, limpeza, relatorio


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline de vendas das filiais")
    parser.add_argument("--entrada", default="dados/entrada", help="pasta com os CSVs exportados")
    parser.add_argument("--saida", default="saida", help="pasta onde ficam o banco, os CSVs e o relatorio")
    parser.add_argument("--sem-api", action="store_true", help="nao consultar a API de feriados")
    args = parser.parse_args(argumentos)

    entrada = Path(args.entrada)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    print("[1/5] Lendo arquivos...")
    try:
        brutas = extracao.ler_vendas(entrada)
        produtos = extracao.ler_produtos(entrada)
    except FileNotFoundError as erro:
        print(f"  erro: {erro}")
        return 1
    for filial, linhas in brutas.items():
        print(f"  {filial}: {len(linhas)} linhas")

    print("[2/5] Limpando e validando...")
    codigos = {p["codigo"].strip().upper() for p in produtos}
    validas, rejeitadas = limpeza.limpar(brutas, codigos)
    print(f"  {len(validas)} validas, {len(rejeitadas)} rejeitadas")
    for motivo, quantidade in Counter(r.motivo.split(":")[0] for r in rejeitadas).most_common():
        print(f"    - {motivo}: {quantidade}")
    if not validas:
        print("  nenhuma linha valida, nada para carregar.")
        return 1

    datas = {v.data for v in validas}
    inicio, fim = min(datas), max(datas)

    print("[3/5] Buscando feriados (BrasilAPI)...")
    lista_feriados = {} if args.sem_api else feriados.feriados_do_periodo(datas, Path("dados/cache"))
    no_periodo = {d: n for d, n in lista_feriados.items() if inicio <= d <= fim}
    print(f"  {len(no_periodo)} feriados entre {inicio:%d/%m/%Y} e {fim:%d/%m/%Y}")

    print("[4/5] Carregando no banco...")
    arquivo_banco = saida / "vendas.db"
    with banco.conectar(arquivo_banco) as conexao:
        banco.criar_tabelas(conexao)
        custos = banco.carregar_produtos(conexao, produtos)
        banco.carregar_calendario(conexao, inicio, fim, no_periodo)
        total = banco.carregar_vendas(conexao, validas, custos)
        print(f"  {total} linhas em fato_venda ({arquivo_banco})")

        print("[5/5] Gerando analises...")
        resultados = analises.todas(conexao)
    conexao.close()

    for resultado in resultados:
        relatorio.salvar_csv(resultado, saida)
    relatorio.salvar_rejeitadas(rejeitadas, saida)
    pagina = relatorio.gerar_html(resultados, rejeitadas, len(validas), saida)

    print(f"  {len(resultados)} CSVs + rejeitadas.csv em {saida}/")
    print(f"  relatorio: {pagina}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
