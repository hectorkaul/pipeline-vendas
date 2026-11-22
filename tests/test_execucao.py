import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from vendas import execucao
from vendas.__main__ import main


class ResumoTest(unittest.TestCase):

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)

    def test_resumo_vai_para_json_e_historico_acumula(self):
        for _ in range(2):
            resumo = execucao.Resumo()
            resumo.linhas_por_filial = {"centro": 10, "sul": 5}
            resumo.validas, resumo.rejeitadas = 14, 1
            resumo.finalizar("ok")
            execucao.salvar_resumo(resumo, self.pasta)

        dados = json.loads((self.pasta / "resumo_execucao.json").read_text(encoding="utf-8"))
        self.assertEqual(dados["status"], "ok")
        self.assertNotIn("_relogio", dados)

        with (self.pasta / "historico_execucoes.csv").open(encoding="utf-8-sig") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[0]["linhas_lidas"], "15")

    def test_pasta_de_entrada_errada_registra_erro(self):
        saida = self.pasta / "saida"
        codigo = main(["--entrada", str(self.pasta / "nao_existe"), "--saida", str(saida), "--sem-api"])

        self.assertEqual(codigo, 1)
        dados = json.loads((saida / "resumo_execucao.json").read_text(encoding="utf-8"))
        self.assertEqual(dados["status"], "erro")
        self.assertIn("erro", (saida / "pipeline.log").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
