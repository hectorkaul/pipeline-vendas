import json
import shutil
import tempfile
import unittest
import urllib.error
from datetime import date
from pathlib import Path
from unittest import mock

from vendas import feriados

RESPOSTA_API = [
    {"date": "2026-09-07", "name": "Independência do Brasil", "type": "national"},
    {"date": "2026-10-12", "name": "Nossa Senhora Aparecida", "type": "national"},
]


class FeriadosTest(unittest.TestCase):

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)

    def test_busca_na_api_e_salva_o_cache(self):
        with mock.patch.object(feriados, "buscar_na_api", return_value=RESPOSTA_API) as api:
            resultado = feriados.feriados_do_ano(2026, self.pasta)

        api.assert_called_once_with(2026)
        self.assertEqual(resultado[date(2026, 9, 7)], "Independência do Brasil")
        self.assertTrue((self.pasta / "feriados_2026.json").exists())

    def test_com_cache_nao_chama_a_api(self):
        (self.pasta / "feriados_2026.json").write_text(json.dumps(RESPOSTA_API), encoding="utf-8")

        with mock.patch.object(feriados, "buscar_na_api") as api:
            resultado = feriados.feriados_do_ano(2026, self.pasta)

        api.assert_not_called()
        self.assertEqual(len(resultado), 2)

    def test_sem_internet_segue_sem_feriados_e_nao_grava_cache(self):
        erro = urllib.error.URLError("sem conexao")
        with mock.patch.object(feriados, "buscar_na_api", side_effect=erro), \
                self.assertLogs("pipeline", level="WARNING") as aviso:
            resultado = feriados.feriados_do_ano(2026, self.pasta)

        self.assertEqual(resultado, {})
        self.assertFalse((self.pasta / "feriados_2026.json").exists())
        self.assertIn("Seguindo sem eles", aviso.output[0])

    def test_periodo_que_vira_o_ano_busca_os_dois_anos(self):
        anos = []

        def falsa(ano):
            anos.append(ano)
            return []

        with mock.patch.object(feriados, "buscar_na_api", side_effect=falsa):
            feriados.feriados_do_periodo({date(2026, 12, 30), date(2027, 1, 2)}, self.pasta)

        self.assertEqual(anos, [2026, 2027])


if __name__ == "__main__":
    unittest.main()
