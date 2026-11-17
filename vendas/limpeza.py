"""
Transformacao: padroniza datas, valores e codigos e separa o que nao da para aproveitar.

Nada e descartado em silencio: toda linha recusada vai para a lista de
rejeitadas com o motivo, para alguem conferir depois.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

FORMATOS_DATA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


@dataclass(frozen=True)
class VendaLimpa:
    filial: str
    numero_venda: str
    data: date
    codigo_produto: str
    quantidade: int
    valor_unitario: Decimal
    cliente: str
    vendedor: str

    @property
    def valor_total(self) -> Decimal:
        return self.valor_unitario * self.quantidade


@dataclass(frozen=True)
class Rejeitada:
    filial: str
    linha: int
    motivo: str
    conteudo: dict


def converter_data(texto: str) -> date:
    texto = (texto or "").strip()
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: '{texto}'")


def converter_decimal(texto: str) -> Decimal:
    """
    Aceita '1.234,56', '1234,56', '1234.56' e 'R$ 10,00'.
    Se tem virgula, a virgula e o decimal e o ponto e milhar.
    """
    valor = (texto or "").replace("R$", "").strip()
    if not valor:
        raise ValueError("valor vazio")
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        return Decimal(valor)
    except InvalidOperation:
        raise ValueError(f"valor inválido: '{texto}'") from None


def normalizar_codigo(texto: str) -> str:
    return (texto or "").strip().upper()


def limpar(linhas_por_filial: dict[str, list[dict]], codigos_validos: set[str]
           ) -> tuple[list[VendaLimpa], list[Rejeitada]]:
    validas: list[VendaLimpa] = []
    rejeitadas: list[Rejeitada] = []
    ja_vistas: set[tuple] = set()

    for filial, linhas in linhas_por_filial.items():
        # linha 2 porque a 1 e o cabecalho, assim bate com o numero que aparece no Excel
        for numero_linha, linha in enumerate(linhas, start=2):
            def rejeitar(motivo: str) -> None:
                rejeitadas.append(Rejeitada(filial, numero_linha, motivo, linha))

            codigo = normalizar_codigo(linha.get("codigo_produto"))
            if codigo not in codigos_validos:
                rejeitar(f"produto não cadastrado: '{linha.get('codigo_produto')}'")
                continue

            try:
                data = converter_data(linha.get("data"))
                valor = converter_decimal(linha.get("valor_unitario"))
            except ValueError as erro:
                rejeitar(str(erro))
                continue

            quantidade_txt = (linha.get("quantidade") or "").strip()
            if not quantidade_txt.lstrip("-").isdigit():
                rejeitar("quantidade vazia ou inválida")
                continue
            quantidade = int(quantidade_txt)
            if quantidade <= 0:
                rejeitar(f"quantidade menor ou igual a zero: {quantidade}")
                continue

            numero_venda = (linha.get("numero_venda") or "").strip()
            chave = (filial, numero_venda, codigo)
            if chave in ja_vistas:
                rejeitar("linha duplicada")
                continue
            ja_vistas.add(chave)

            validas.append(VendaLimpa(
                filial=filial,
                numero_venda=numero_venda,
                data=data,
                codigo_produto=codigo,
                quantidade=quantidade,
                valor_unitario=valor,
                cliente=(linha.get("cliente") or "").strip() or "Consumidor",
                vendedor=(linha.get("vendedor") or "").strip() or "Nao informado",
            ))

    return validas, rejeitadas
