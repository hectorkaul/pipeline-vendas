"""
Gera arquivos de exemplo parecidos com exportacoes reais de ERP.

Cada filial exporta de um jeito (formato de data, separador decimal, encoding)
e os arquivos vem com alguns problemas de proposito: linhas duplicadas,
codigo de produto digitado errado, quantidade vazia ou negativa etc.
E justamente isso que a etapa de limpeza precisa resolver.

Uso:
    python -m vendas.gerar_dados
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

PRODUTOS = [
    # codigo, descricao, categoria, custo, preco
    ("CIM50", "Cimento CP-II 50kg", "Básico", "29.90", "39.90"),
    ("ARG20", "Argamassa AC-I 20kg", "Básico", "14.50", "21.90"),
    ("CAL20", "Cal hidratada 20kg", "Básico", "12.00", "17.50"),
    ("ARE01", "Areia média (m³)", "Básico", "95.00", "140.00"),
    ("BRI01", "Brita 1 (m³)", "Básico", "110.00", "165.00"),
    ("TIJ06", "Tijolo 6 furos (milheiro)", "Básico", "620.00", "790.00"),
    ("VER10", "Vergalhão CA-50 10mm 12m", "Ferragem", "42.00", "58.90"),
    ("VER08", "Vergalhão CA-50 8mm 12m", "Ferragem", "28.00", "39.90"),
    ("PRE25", "Prego 17x27 1kg", "Ferragem", "13.80", "19.90"),
    ("ARA18", "Arame recozido 1kg", "Ferragem", "16.00", "24.90"),
    ("TIN18", "Tinta acrílica branca 18L", "Pintura", "189.00", "259.90"),
    ("TIN36", "Tinta acrílica cores 3,6L", "Pintura", "58.00", "84.90"),
    ("ROL23", "Rolo de lã 23cm", "Pintura", "14.00", "24.90"),
    ("MAS25", "Massa corrida 25kg", "Pintura", "52.00", "74.90"),
    ("LIX01", "Lixa para parede (unidade)", "Pintura", "0.90", "2.20"),
    ("TUB25", "Tubo PVC soldável 25mm 6m", "Hidráulica", "18.50", "27.90"),
    ("TUB50", "Tubo esgoto 50mm 6m", "Hidráulica", "24.00", "36.90"),
    ("JOE25", "Joelho PVC 90° 25mm", "Hidráulica", "0.95", "2.50"),
    ("REG34", "Registro de gaveta 3/4", "Hidráulica", "38.00", "56.90"),
    ("CXA10", "Caixa d'água 1000L", "Hidráulica", "410.00", "549.00"),
    ("FIO25", "Fio flexível 2,5mm rolo 100m", "Elétrica", "165.00", "229.90"),
    ("FIO15", "Fio flexível 1,5mm rolo 100m", "Elétrica", "112.00", "159.90"),
    ("DIS20", "Disjuntor unipolar 20A", "Elétrica", "9.80", "16.90"),
    ("TOM10", "Tomada 10A com placa", "Elétrica", "6.20", "12.90"),
    ("LAM09", "Lâmpada LED 9W", "Elétrica", "5.50", "11.90"),
    ("LUV01", "Luva de raspa (par)", "EPI", "7.50", "14.90"),
    ("CAP01", "Capacete de segurança", "EPI", "16.00", "29.90"),
    ("OCU01", "Óculos de proteção", "EPI", "6.00", "12.90"),
]

# cada filial "exporta" num formato diferente
FILIAIS = {
    "centro": {"formato_data": "%d/%m/%Y", "decimal": ",", "encoding": "utf-8", "peso": 1.0},
    "norte": {"formato_data": "%Y-%m-%d", "decimal": ".", "encoding": "utf-8", "peso": 0.7},
    "sul": {"formato_data": "%d/%m/%Y", "decimal": ",", "encoding": "latin-1", "peso": 0.5},
}

CLIENTES = ["", "", "", "Construtora Lopes", "João Pereira", "Márcia Schneider", "Obra Rua XV",
            "Paulo Krüger", "Ana Beatriz Souza", "Reformas Bom Jesus", "Ivo Hartwig", "Cláudia Rocha"]
VENDEDORES = ["Carlos", "Fernanda", "Rodrigo", "Simone"]

CABECALHO = ["numero_venda", "data", "codigo_produto", "descricao", "quantidade",
             "valor_unitario", "cliente", "vendedor"]


def formatar_decimal(valor: str, separador: str) -> str:
    return valor.replace(".", separador)


def sujar_codigo(codigo: str, rnd: random.Random) -> str:
    """Simula erro de digitacao: minusculo, espaco sobrando ou codigo inexistente."""
    sorteio = rnd.random()
    if sorteio < 0.4:
        return codigo.lower()
    if sorteio < 0.8:
        return f" {codigo} "
    return codigo[:-1] + "X"  # vira um codigo que nao existe


def gerar_filial(nome: str, config: dict, inicio: date, fim: date, rnd: random.Random) -> list[list[str]]:
    linhas = []
    numero = 1000
    dia = inicio
    while dia <= fim:
        if dia.weekday() == 6:  # domingo fechado
            dia += timedelta(days=1)
            continue

        # sabado e dia mais fraco; fim de mes um pouco mais forte
        base = 5 if dia.weekday() == 5 else 9
        if dia.day >= 25:
            base += 3
        vendas_no_dia = max(1, int(rnd.gauss(base * config["peso"], 2)))

        for _ in range(vendas_no_dia):
            numero += 1
            cliente = rnd.choice(CLIENTES)
            vendedor = rnd.choice(VENDEDORES)
            for codigo, descricao, _cat, _custo, preco in rnd.sample(PRODUTOS, k=rnd.randint(1, 4)):
                if float(preco) > 100:
                    quantidade = str(rnd.choice([1, 1, 1, 2]))  # item caro sai em pouca quantidade
                else:
                    quantidade = str(rnd.choice([1, 1, 1, 2, 2, 3, 5, 10]))
                cod = codigo

                problema = rnd.random()
                if problema < 0.01:
                    cod = sujar_codigo(codigo, rnd)
                elif problema < 0.015:
                    quantidade = ""
                elif problema < 0.018:
                    quantidade = "-" + quantidade

                linha = [str(numero), dia.strftime(config["formato_data"]), cod, descricao, quantidade,
                         formatar_decimal(preco, config["decimal"]), cliente, vendedor]
                linhas.append(linha)

                if rnd.random() < 0.01:
                    linhas.append(list(linha))  # linha exportada duas vezes
        dia += timedelta(days=1)
    return linhas


def gerar(pasta: Path, inicio: date, fim: date, semente: int = 7) -> None:
    rnd = random.Random(semente)
    pasta.mkdir(parents=True, exist_ok=True)

    with open(pasta / "produtos.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["codigo", "descricao", "categoria", "custo"])
        for codigo, descricao, categoria, custo, _preco in PRODUTOS:
            escritor.writerow([codigo, descricao, categoria, custo])

    for nome, config in FILIAIS.items():
        linhas = gerar_filial(nome, config, inicio, fim, rnd)
        arquivo = pasta / f"vendas_{nome}.csv"
        with open(arquivo, "w", newline="", encoding=config["encoding"]) as f:
            escritor = csv.writer(f, delimiter=";")
            escritor.writerow(CABECALHO)
            escritor.writerows(linhas)
        print(f"{arquivo.name}: {len(linhas)} linhas")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera CSVs de exemplo das filiais")
    parser.add_argument("--pasta", default="dados/entrada")
    parser.add_argument("--inicio", default="2026-05-01", help="data inicial (aaaa-mm-dd)")
    parser.add_argument("--fim", default="2026-10-31", help="data final (aaaa-mm-dd)")
    args = parser.parse_args()

    gerar(Path(args.pasta), date.fromisoformat(args.inicio), date.fromisoformat(args.fim))


if __name__ == "__main__":
    main()
