import unittest
from datetime import date
from decimal import Decimal

from vendas.limpeza import converter_data, converter_decimal, limpar, normalizar_codigo


def linha(**campos):
    base = {
        "numero_venda": "1001", "data": "03/08/2026", "codigo_produto": "CIM50",
        "descricao": "Cimento", "quantidade": "2", "valor_unitario": "39,90",
        "cliente": "Maria", "vendedor": "Carlos",
    }
    base.update(campos)
    return base


class ConversoesTest(unittest.TestCase):

    def test_data_nos_formatos_das_filiais(self):
        self.assertEqual(converter_data("03/08/2026"), date(2026, 8, 3))
        self.assertEqual(converter_data("2026-08-03"), date(2026, 8, 3))
        self.assertEqual(converter_data(" 03-08-2026 "), date(2026, 8, 3))

    def test_data_invalida(self):
        with self.assertRaises(ValueError):
            converter_data("31/02/2026")
        with self.assertRaises(ValueError):
            converter_data("")

    def test_decimal_brasileiro_e_americano(self):
        self.assertEqual(converter_decimal("39,90"), Decimal("39.90"))
        self.assertEqual(converter_decimal("39.90"), Decimal("39.90"))
        self.assertEqual(converter_decimal("1.234,56"), Decimal("1234.56"))
        self.assertEqual(converter_decimal("R$ 10,00"), Decimal("10.00"))

    def test_decimal_invalido(self):
        with self.assertRaises(ValueError):
            converter_decimal("abc")
        with self.assertRaises(ValueError):
            converter_decimal("")

    def test_codigo(self):
        self.assertEqual(normalizar_codigo("  cim50 "), "CIM50")


class LimparTest(unittest.TestCase):

    CODIGOS = {"CIM50", "ARG20"}

    def test_linha_boa_passa(self):
        validas, rejeitadas = limpar({"centro": [linha()]}, self.CODIGOS)
        self.assertEqual(len(validas), 1)
        self.assertEqual(rejeitadas, [])
        self.assertEqual(validas[0].valor_total, Decimal("79.80"))

    def test_codigo_com_espaco_e_minusculo_e_corrigido(self):
        validas, _ = limpar({"centro": [linha(codigo_produto=" cim50 ")]}, self.CODIGOS)
        self.assertEqual(validas[0].codigo_produto, "CIM50")

    def test_produto_inexistente_e_rejeitado(self):
        validas, rejeitadas = limpar({"centro": [linha(codigo_produto="CIM5X")]}, self.CODIGOS)
        self.assertEqual(validas, [])
        self.assertIn("produto não cadastrado", rejeitadas[0].motivo)
        self.assertEqual(rejeitadas[0].linha, 2)

    def test_quantidade_vazia_ou_negativa(self):
        _, rejeitadas = limpar({"centro": [linha(quantidade=""), linha(numero_venda="2", quantidade="-3")]},
                               self.CODIGOS)
        self.assertEqual(len(rejeitadas), 2)
        self.assertIn("vazia", rejeitadas[0].motivo)
        self.assertIn("menor ou igual a zero", rejeitadas[1].motivo)

    def test_duplicada_na_mesma_filial(self):
        validas, rejeitadas = limpar({"centro": [linha(), linha()]}, self.CODIGOS)
        self.assertEqual(len(validas), 1)
        self.assertEqual(rejeitadas[0].motivo, "linha duplicada")

    def test_mesmo_numero_em_filiais_diferentes_nao_e_duplicado(self):
        validas, rejeitadas = limpar({"centro": [linha()], "norte": [linha(data="2026-08-03")]}, self.CODIGOS)
        self.assertEqual(len(validas), 2)
        self.assertEqual(rejeitadas, [])

    def test_cliente_vazio_vira_consumidor(self):
        validas, _ = limpar({"centro": [linha(cliente="  ")]}, self.CODIGOS)
        self.assertEqual(validas[0].cliente, "Consumidor")


if __name__ == "__main__":
    unittest.main()
