"""
Busca os feriados nacionais na BrasilAPI (https://brasilapi.com.br).

A resposta fica salva em cache num JSON, assim a API so e chamada uma vez por ano.
Se estiver sem internet, o pipeline continua normalmente, so sem a marcacao de feriado.
"""

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

URL = "https://brasilapi.com.br/api/feriados/v1/{ano}"


def buscar_na_api(ano: int, timeout: float = 10) -> list[dict]:
    requisicao = urllib.request.Request(
        URL.format(ano=ano),
        # sem User-Agent a API responde 403
        headers={"User-Agent": "pipeline-vendas/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
        return json.load(resposta)


def feriados_do_ano(ano: int, pasta_cache: Path) -> dict[date, str]:
    cache = pasta_cache / f"feriados_{ano}.json"
    if cache.exists():
        dados = json.loads(cache.read_text(encoding="utf-8"))
    else:
        try:
            dados = buscar_na_api(ano)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as erro:
            print(f"  aviso: nao consegui buscar os feriados de {ano} ({erro}). Seguindo sem eles.")
            return {}
        pasta_cache.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    return {date.fromisoformat(f["date"]): f["name"] for f in dados}


def feriados_do_periodo(datas: set[date], pasta_cache: Path) -> dict[date, str]:
    feriados: dict[date, str] = {}
    for ano in sorted({d.year for d in datas}):
        feriados.update(feriados_do_ano(ano, pasta_cache))
    return feriados
