import unittest
from datetime import date
from decimal import Decimal

from vendas import analises, banco
from vendas.limpeza import VendaLimpa


def venda(numero, dia, codigo, quantidade, valor, filial="centro", cliente="Maria", vendedor="Carlos"):
    return VendaLimpa(filial, str(numero), dia, codigo, quantidade, Decimal(valor), cliente, vendedor)


class AnalisesTest(unittest.TestCase):

    def setUp(self):
        self.conexao = banco.conectar(":memory:")
        banco.criar_tabelas(self.conexao)
        custos = banco.carregar_produtos(self.conexao, [
            {"codigo": "A", "descricao": "Produto A", "categoria": "Basico", "custo": "6,00"},
            {"codigo": "B", "descricao": "Produto B", "categoria": "Pintura", "custo": "50,00"},
            {"codigo": "C", "descricao": "Produto C", "categoria": "Pintura", "custo": "1,00"},
        ])
        banco.carregar_calendario(self.conexao, date(2026, 9, 1), date(2026, 10, 31),
                                  {date(2026, 10, 12): "Nossa Senhora Aparecida"})
        banco.carregar_vendas(self.conexao, [
            venda(1, date(2026, 9, 1), "A", 10, "10.00"),                 # 100
            venda(2, date(2026, 9, 2), "B", 1, "100.00", filial="norte"),  # 100
            venda(3, date(2026, 10, 5), "A", 30, "10.00"),                 # 300
            venda(3, date(2026, 10, 5), "C", 2, "2.50"),                   # 5   (mesma venda)
            venda(4, date(2026, 10, 6), "B", 1, "100.00", cliente="Consumidor"),
        ], custos)

    def tearDown(self):
        self.conexao.close()

    def test_faturamento_mensal_com_variacao(self):
        r = analises.faturamento_mensal(self.conexao)
        por_mes = {linha[0]: linha for linha in r.linhas}

        self.assertEqual(por_mes["2026-09"][1], 200.0)
        self.assertEqual(por_mes["2026-10"][1], 405.0)
        self.assertEqual(por_mes["2026-10"][2], 2)          # vendas distintas em outubro
        self.assertIsNone(por_mes["2026-09"][5])           # primeiro mes nao tem anterior
        self.assertEqual(por_mes["2026-10"][5], 102.5)      # (405 - 200) / 200

    def test_curva_abc(self):
        r = analises.curva_abc(self.conexao)
        classes = {linha[0]: linha[-1] for linha in r.linhas}

        # A = 400 (65,8%), B = 200 (32,9%), C = 5 (0,8%)
        # a regra olha o acumulado ANTES do produto: o B comeca em 65,8% (< 80%),
        # entao tambem e classe A. O C comeca em 99,2%, entao e classe C.
        self.assertEqual(classes["A"], "A")
        self.assertEqual(classes["B"], "A")
        self.assertEqual(classes["C"], "C")

    def test_margem_por_categoria(self):
        r = analises.margem_por_categoria(self.conexao)
        margens = {linha[0]: linha[4] for linha in r.linhas}
        self.assertEqual(margens["Basico"], 40.0)  # custo 6, venda 10

    def test_feriado_aparece_mesmo_sem_venda(self):
        r = analises.vendas_em_feriados(self.conexao)
        self.assertEqual(len(r.linhas), 1)
        self.assertEqual(r.linhas[0][2], "Nossa Senhora Aparecida")
        self.assertEqual(r.linhas[0][3], 0.0)

    def test_melhores_clientes_ignora_consumidor(self):
        r = analises.melhores_clientes(self.conexao)
        nomes = [linha[0] for linha in r.linhas]
        self.assertEqual(nomes, ["Maria"])

    def test_participacao_soma_100_no_mes(self):
        r = analises.participacao_filiais(self.conexao)
        setembro = [linha[3] for linha in r.linhas if linha[0] == "2026-09"]
        self.assertAlmostEqual(sum(setembro), 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
