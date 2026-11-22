"""
Log e resumo de cada execucao.

Quando o pipeline roda sozinho (agendado de manha), ninguem esta olhando o terminal.
Entao tudo que aparece na tela tambem vai para saida/pipeline.log com data e hora,
e no fim fica um resumo em JSON e uma linha a mais no historico_execucoes.csv.
"""

import csv
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

NOME_LOG = "pipeline"


def configurar_log(pasta_saida: Path) -> logging.Logger:
    log = logging.getLogger(NOME_LOG)
    log.setLevel(logging.INFO)
    log.handlers.clear()
    log.propagate = False

    tela = logging.StreamHandler()
    tela.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(tela)

    pasta_saida.mkdir(parents=True, exist_ok=True)
    arquivo = logging.FileHandler(pasta_saida / "pipeline.log", encoding="utf-8")
    arquivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%d/%m/%Y %H:%M:%S"))
    log.addHandler(arquivo)
    return log


def fechar_log(log: logging.Logger) -> None:
    # no Windows o arquivo fica preso se o handler nao for fechado
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


@dataclass
class Resumo:
    inicio: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    status: str = "erro"
    linhas_por_filial: dict[str, int] = field(default_factory=dict)
    validas: int = 0
    rejeitadas: int = 0
    rejeitadas_por_motivo: dict[str, int] = field(default_factory=dict)
    feriados_no_periodo: int = 0
    periodo: str = ""
    segundos: float = 0.0
    _relogio: float = field(default_factory=time.perf_counter, repr=False)

    def finalizar(self, status: str) -> None:
        self.status = status
        self.segundos = round(time.perf_counter() - self._relogio, 2)

    def como_dict(self) -> dict:
        dados = asdict(self)
        dados.pop("_relogio")
        return dados


CAMPOS_HISTORICO = ["inicio", "status", "linhas_lidas", "validas", "rejeitadas", "periodo", "segundos"]


def salvar_resumo(resumo: Resumo, pasta_saida: Path) -> Path:
    arquivo = pasta_saida / "resumo_execucao.json"
    arquivo.write_text(json.dumps(resumo.como_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    historico = pasta_saida / "historico_execucoes.csv"
    novo = not historico.exists()
    with historico.open("a", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_HISTORICO, delimiter=";")
        if novo:
            escritor.writeheader()
        escritor.writerow({
            "inicio": resumo.inicio,
            "status": resumo.status,
            "linhas_lidas": sum(resumo.linhas_por_filial.values()),
            "validas": resumo.validas,
            "rejeitadas": resumo.rejeitadas,
            "periodo": resumo.periodo,
            "segundos": str(resumo.segundos).replace(".", ","),
        })
    return arquivo
