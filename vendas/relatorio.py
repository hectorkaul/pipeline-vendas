"""Saidas do pipeline: um CSV por analise (para Excel/Power BI) e um relatorio HTML simples."""

import csv
import html
from collections import Counter
from datetime import datetime
from pathlib import Path

from .analises import Resultado
from .limpeza import Rejeitada


def _formatar(valor) -> str:
    """Numero no padrao brasileiro para o CSV: 1234.5 -> 1234,5"""
    if isinstance(valor, float):
        return f"{valor:.2f}".replace(".", ",")
    return "" if valor is None else str(valor)


def salvar_csv(resultado: Resultado, pasta: Path) -> Path:
    arquivo = pasta / f"{resultado.nome}.csv"
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(resultado.colunas)
        for linha in resultado.linhas:
            escritor.writerow([_formatar(v) for v in linha])
    return arquivo


def salvar_rejeitadas(rejeitadas: list[Rejeitada], pasta: Path) -> Path:
    arquivo = pasta / "rejeitadas.csv"
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["filial", "linha", "motivo", "conteudo_original"])
        for r in rejeitadas:
            escritor.writerow([r.filial, r.linha, r.motivo, " | ".join(str(v or "") for v in r.conteudo.values())])
    return arquivo


def _inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _moeda(valor) -> str:
    if valor is None:
        return "-"
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _celula(coluna: str, valor) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, float):
        if coluna.endswith("_pct") or coluna in ("pct", "pct_acumulado"):
            return f"{valor:.1f}%".replace(".", ",")
        return _moeda(valor)
    return html.escape(str(valor))


def _tabela(resultado: Resultado) -> str:
    cabecalho = "".join(f"<th>{html.escape(_rotulo(c))}</th>" for c in resultado.colunas)
    linhas = []
    for linha in resultado.linhas:
        celulas = "".join(f"<td>{_celula(c, v)}</td>" for c, v in zip(resultado.colunas, linha))
        linhas.append(f"<tr>{celulas}</tr>")
    return f"<table><thead><tr>{cabecalho}</tr></thead><tbody>{''.join(linhas)}</tbody></table>"


def _grafico_mensal(resultado: Resultado) -> str:
    """Barras feitas so com CSS, para o relatorio nao depender de biblioteca nenhuma."""
    maior = max((linha[1] for linha in resultado.linhas), default=0) or 1
    barras = []
    for mes, faturamento, *_ in resultado.linhas:
        largura = faturamento / maior * 100
        barras.append(
            f'<div class="barra"><span class="rotulo">{mes}</span>'
            f'<span class="trilho"><span class="valor" style="width:{largura:.1f}%"></span></span>'
            f'<span class="numero">{_moeda(faturamento)}</span></div>')
    return "".join(barras)


ROTULOS = {
    "mes": "Mês", "codigo": "Código", "descricao": "Descrição", "ticket_medio": "Ticket médio",
    "margem_pct": "Margem", "variacao_pct": "Variação", "participacao_pct": "Participação",
    "pct": "% do total", "pct_acumulado": "% acumulado", "lucro_bruto": "Lucro bruto",
    "nome_dia": "Dia", "media_faturamento": "Média por dia", "nome_feriado": "Feriado",
    "posicao": "Posição", "ultima_compra": "Última compra",
}


def _rotulo(coluna: str) -> str:
    return ROTULOS.get(coluna, coluna.replace("_", " ").capitalize())


def gerar_html(resultados: list[Resultado], rejeitadas: list[Rejeitada], total_validas: int, pasta: Path) -> Path:
    motivos = Counter(r.motivo.split(":")[0] for r in rejeitadas)
    lista_motivos = "".join(f"<li>{html.escape(m)}: {q}</li>" for m, q in motivos.most_common())

    secoes = []
    for r in resultados:
        extra = _grafico_mensal(r) if r.nome == "faturamento_mensal" else ""
        secoes.append(f"<section><h2>{html.escape(r.titulo)}</h2>{extra}{_tabela(r)}</section>")

    pagina = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório de vendas</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px auto; max-width: 980px; color: #222; padding: 0 16px; }}
  h1 {{ margin-bottom: 4px; }}
  .sub {{ color: #666; margin-top: 0; }}
  section {{ margin-top: 36px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  th, td {{ border-bottom: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
  th {{ background: #f3f5f7; }}
  td:not(:first-child) {{ font-variant-numeric: tabular-nums; }}
  .barra {{ display: flex; align-items: center; gap: 10px; margin: 4px 0; font-size: 14px; }}
  .rotulo {{ width: 70px; }}
  .trilho {{ flex: 1; }}
  .valor {{ display: block; background: #3a5a80; height: 16px; border-radius: 2px; }}
  .numero {{ width: 120px; text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
  .qualidade {{ background: #fff8e6; border: 1px solid #f0d78c; padding: 12px 16px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Relatório de vendas</h1>
<p class="sub">Gerado em {datetime.now():%d/%m/%Y %H:%M}</p>

<div class="qualidade">
  <strong>Qualidade dos dados:</strong> {_inteiro(total_validas)} linhas carregadas, {len(rejeitadas)} rejeitadas
  (detalhes em <code>rejeitadas.csv</code>).
  <ul>{lista_motivos}</ul>
</div>

{''.join(secoes)}
</body>
</html>
"""
    arquivo = pasta / "relatorio.html"
    arquivo.write_text(pagina, encoding="utf-8")
    return arquivo
