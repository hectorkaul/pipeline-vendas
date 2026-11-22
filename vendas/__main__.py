"""
Roda o pipeline completo:

    python -m vendas
    python -m vendas --entrada dados/entrada --saida saida --sem-api
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import analises, banco, execucao, extracao, feriados, limpeza, relatorio


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline de vendas das filiais")
    parser.add_argument("--entrada", default="dados/entrada", help="pasta com os CSVs exportados")
    parser.add_argument("--saida", default="saida", help="pasta onde ficam o banco, os CSVs e o relatorio")
    parser.add_argument("--sem-api", action="store_true", help="nao consultar a API de feriados")
    args = parser.parse_args(argumentos)

    entrada = Path(args.entrada)
    saida = Path(args.saida)
    log = execucao.configurar_log(saida)
    resumo = execucao.Resumo()
    try:
        codigo = executar(entrada, saida, args.sem_api, log, resumo)
        resumo.finalizar("ok" if codigo == 0 else "erro")
        return codigo
    except Exception as erro:
        # rodando agendado, um erro inesperado precisa ficar registrado no log
        log.exception(f"erro inesperado: {erro}")
        resumo.finalizar("erro")
        return 1
    finally:
        execucao.salvar_resumo(resumo, saida)
        log.info(f"  tempo total: {resumo.segundos:.1f}s (status: {resumo.status})")
        execucao.fechar_log(log)


def executar(entrada: Path, saida: Path, sem_api: bool, log, resumo: execucao.Resumo) -> int:
    log.info("[1/5] Lendo arquivos...")
    try:
        brutas = extracao.ler_vendas(entrada)
        produtos = extracao.ler_produtos(entrada)
    except FileNotFoundError as erro:
        log.error(f"  erro: {erro}")
        return 1
    for filial, linhas in brutas.items():
        log.info(f"  {filial}: {len(linhas)} linhas")
        resumo.linhas_por_filial[filial] = len(linhas)

    log.info("[2/5] Limpando e validando...")
    codigos = {p["codigo"].strip().upper() for p in produtos}
    validas, rejeitadas = limpeza.limpar(brutas, codigos)
    log.info(f"  {len(validas)} validas, {len(rejeitadas)} rejeitadas")
    resumo.validas, resumo.rejeitadas = len(validas), len(rejeitadas)
    for motivo, quantidade in Counter(r.motivo.split(":")[0] for r in rejeitadas).most_common():
        log.info(f"    - {motivo}: {quantidade}")
        resumo.rejeitadas_por_motivo[motivo] = quantidade
    if not validas:
        log.error("  nenhuma linha valida, nada para carregar.")
        return 1

    datas = {v.data for v in validas}
    inicio, fim = min(datas), max(datas)
    resumo.periodo = f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"

    log.info("[3/5] Buscando feriados (BrasilAPI)...")
    lista_feriados = {} if sem_api else feriados.feriados_do_periodo(datas, Path("dados/cache"))
    no_periodo = {d: n for d, n in lista_feriados.items() if inicio <= d <= fim}
    resumo.feriados_no_periodo = len(no_periodo)
    log.info(f"  {len(no_periodo)} feriados entre {inicio:%d/%m/%Y} e {fim:%d/%m/%Y}")

    log.info("[4/5] Carregando no banco...")
    arquivo_banco = saida / "vendas.db"
    with banco.conectar(arquivo_banco) as conexao:
        banco.criar_tabelas(conexao)
        custos = banco.carregar_produtos(conexao, produtos)
        banco.carregar_calendario(conexao, inicio, fim, no_periodo)
        total = banco.carregar_vendas(conexao, validas, custos)
        log.info(f"  {total} linhas em fato_venda ({arquivo_banco})")

        log.info("[5/5] Gerando analises...")
        resultados = analises.todas(conexao)
    conexao.close()

    for resultado in resultados:
        relatorio.salvar_csv(resultado, saida)
    relatorio.salvar_rejeitadas(rejeitadas, saida)
    pagina = relatorio.gerar_html(resultados, rejeitadas, len(validas), saida)

    log.info(f"  {len(resultados)} CSVs + rejeitadas.csv em {saida}/")
    log.info(f"  relatorio: {pagina}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
