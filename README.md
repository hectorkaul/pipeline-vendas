# Pipeline de Vendas (Python + SQL)

![testes](https://github.com/hectorkaul/pipeline-vendas/actions/workflows/ci.yml/badge.svg)

Projeto de ETL que junta as vendas de três filiais de uma loja, limpa os dados, carrega num banco SQLite modelado para BI e gera análises em SQL.

O problema que eu quis resolver é bem comum: cada filial exporta a planilha de vendas de um jeito. Uma usa data `03/08/2026`, outra `2026-08-03`, uma usa vírgula decimal, outra ponto, e sempre vem alguma linha duplicada, código digitado errado ou quantidade em branco. Antes de fazer qualquer relatório, alguém precisa arrumar isso. Aqui o script faz essa parte.

## O que o pipeline faz

1. **Extração:** lê os CSV de cada filial (`vendas_centro.csv`, `vendas_norte.csv`...) e o cadastro de produtos. Detecta se o arquivo está em UTF-8 ou Latin-1.
2. **Limpeza:** padroniza datas, valores e códigos de produto. Linhas com problema não somem: vão para `rejeitadas.csv` com o número da linha e o motivo.
3. **Feriados:** consulta a [BrasilAPI](https://brasilapi.com.br) para marcar os feriados nacionais do período. A resposta fica em cache, e sem internet o pipeline continua normalmente, só sem os feriados.
4. **Carga:** grava num SQLite em modelo estrela (`fato_venda` + `dim_produto`, `dim_filial`, `dim_data`).
5. **Análises:** consultas SQL que geram um CSV cada (no padrão brasileiro, pronto para Excel/Power BI) e um relatório HTML.

## Análises

| Análise | O que mostra | SQL usado |
|---|---|---|
| Faturamento mensal | faturamento, nº de vendas, ticket médio, margem e variação em relação ao mês anterior | CTE + `LAG()` |
| Participação das filiais | quanto cada filial representa no mês | `SUM() OVER (PARTITION BY mes)` |
| Curva ABC | quais produtos fazem 80% do faturamento | soma acumulada com `SUM() OVER (ORDER BY ...)` |
| Margem por categoria | lucro bruto e margem % | `GROUP BY` + `JOIN` |
| Média por dia da semana | dia mais forte e mais fraco, contando também os dias sem venda | `LEFT JOIN` com a tabela calendário |
| Feriados | faturamento em cada feriado do período | `LEFT JOIN` + filtro |
| Ranking de vendedores | posição de cada vendedor dentro da filial | `RANK() OVER (PARTITION BY filial)` |
| Melhores clientes | total comprado e última compra | `GROUP BY` + `MAX()` |

## Como rodar

Usa só a biblioteca padrão do Python (3.10 ou mais novo), não precisa instalar nada.

```bash
# 1. gera arquivos de exemplo em dados/entrada (6 meses, 3 filiais)
python -m vendas.gerar_dados

# 2. roda o pipeline
python -m vendas
```

Saída:

```
[1/5] Lendo arquivos...
  centro: 3349 linhas
  norte: 2287 linhas
  sul: 1443 linhas
[2/5] Limpando e validando...
  6923 validas, 156 rejeitadas
    - linha duplicada: 69
    - quantidade vazia ou inválida: 48
    - quantidade menor ou igual a zero: 28
    - produto não cadastrado: 11
[3/5] Buscando feriados (BrasilAPI)...
  4 feriados entre 01/05/2026 e 31/10/2026
[4/5] Carregando no banco...
  6923 linhas em fato_venda (saida\vendas.db)
[5/5] Gerando analises...
  8 CSVs + rejeitadas.csv em saida/
  relatorio: saida\relatorio.html
```

Opções: `--entrada` (pasta dos CSV), `--saida` (pasta dos resultados) e `--sem-api` (não consulta os feriados).

Testes:

```bash
python -m unittest discover -s tests -t .
```

Os testes também rodam no GitHub Actions a cada push, em Python 3.10 e 3.12, e no final o pipeline roda de ponta a ponta com dados gerados.

## Rodar todo dia automaticamente

Na prática, um pipeline desses roda sozinho de manhã, antes de alguém abrir o Power BI. Para isso:

- Tudo que aparece na tela também vai para `saida/pipeline.log`, com data e hora. Se der erro no meio da madrugada, o erro completo fica registrado lá.
- No fim de cada execução é gerado o `saida/resumo_execucao.json` (linhas lidas por filial, válidas, rejeitadas por motivo, período e tempo) e uma linha a mais no `saida/historico_execucoes.csv`. Com o histórico dá para perceber, por exemplo, que uma filial parou de mandar arquivo ou que as rejeições aumentaram de repente.
- O script `scripts/agendar_windows.ps1` cria a tarefa no Agendador de Tarefas do Windows:

```powershell
.\scripts\agendar_windows.ps1                  # todo dia às 07:00
.\scripts\agendar_windows.ps1 -Horario 06:30
.\scripts\agendar_windows.ps1 -Remover
```

## Estrutura

```
vendas/
├── gerar_dados.py   gera CSVs de exemplo, com erros de propósito
├── extracao.py      leitura dos arquivos
├── limpeza.py       validação e padronização
├── feriados.py      consumo da BrasilAPI com cache
├── banco.py         criação das tabelas e carga
├── analises.py      consultas SQL
├── relatorio.py     CSV + HTML
├── execucao.py      log em arquivo e resumo de cada execução
└── sql/schema.sql   modelo estrela
scripts/
└── agendar_windows.ps1
tests/
├── test_limpeza.py
├── test_analises.py
├── test_feriados.py  cache e funcionamento sem internet (API simulada com mock)
└── test_execucao.py
```

## Decisões que tomei

- **Dinheiro em centavos (inteiro) no banco.** Assim não aparece 0,30000000000000004 nas somas. Só divido por 100 na hora de mostrar.
- **Tabela calendário (`dim_data`).** Sem ela, um dia sem nenhuma venda simplesmente não existiria na consulta e a média por dia da semana sairia maior do que é de verdade.
- **Duplicidade por filial + número da venda + produto.** O mesmo número de venda pode existir em filiais diferentes, então não basta olhar só o número.
- **Nada é descartado em silêncio.** Toda linha recusada fica registrada com o motivo, porque em dado real alguém vai querer saber o que ficou de fora.
- **API externa nunca derruba o pipeline.** Se a BrasilAPI estiver fora do ar, o pipeline segue sem os feriados e registra um aviso no log. Nos testes a API é simulada com `unittest.mock`, então eles não dependem de internet.

## Power BI

Os CSVs da pasta `saida/` já saem com `;` e vírgula decimal, então importam direto no Power BI. Como o banco segue o modelo estrela, também dá para ligar as tabelas `dim_*` na `fato_venda` e montar o dashboard por cima. Essa é a próxima etapa do projeto, junto com a formação de Power BI que estou fazendo.

## Próximos passos

- [ ] Dashboard no Power BI em cima do `vendas.db`
- [ ] Ler direto de uma API do ERP em vez de CSV
- [x] Rodar o pipeline agendado (todo dia de manhã)
