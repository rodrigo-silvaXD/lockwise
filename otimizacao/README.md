# Otimização da escala de vigilância

O último elo da corrente: o histórico de acessos que o circuito gerou vira a demanda de um modelo de programação linear inteira, que decide quantos vigilantes escalar em cada turno ao menor custo.

```
circuito → gateway → API → banco → GET /acessos/demanda-horaria → este modelo
```

PuLP com o solver CBC. Python 3.11+.

---

## O problema

Uma portaria precisa de gente de plantão nas 24 horas, mas o movimento não é constante: às 18h entram quinze pessoas, às 3h da manhã nenhuma. Escalar o mesmo efetivo o dia inteiro cobre a demanda e paga gente parada. Escalar de menos deixa a portaria descoberta na hora do movimento.

O modelo responde: **quantos vigilantes em cada turno, ao menor custo, sem deixar nenhuma hora descoberta.**

## Formulação

```
Conjuntos   H = {0..23}              horas do dia
            T = {0..5}               turnos de 8 h começando a cada 4 h

Parâmetros  a(t,h) ∈ {0,1}           1 se o turno t cobre a hora h
            d_h ∈ ℤ⁺                 vigilantes exigidos na hora h
            c_t ∈ ℝ⁺                 custo de um vigilante no turno t
            N_max ∈ ℤ⁺               vigilantes disponíveis

Variável    x_t ∈ ℤ⁺                 vigilantes escalados no turno t

minimizar   Σ_t c_t · x_t

sujeito a   Σ_t a(t,h) · x_t ≥ d_h   ∀h ∈ H      (cobertura)
            Σ_t x_t ≤ N_max                       (equipe disponível)
            x_t ≥ 0, inteiro         ∀t ∈ T
```

### Por que turnos de 8 h a cada 4 h

É a decisão que faz o problema existir. Seis turnos de 4 h sem sobreposição cobririam cada hora exatamente uma vez, e a resposta ótima seria imediata: `x_t` = maior demanda dentro do turno. Não haveria o que otimizar.

Com turnos de 8 h começando a cada 4 h, **cada hora é coberta por dois turnos**, e escalar alguém no turno 12–20 ajuda tanto a tarde quanto o início da noite. Decidir onde concentrar pessoal passa a ser um problema combinatório de verdade. E turno de 8 h é o que um vigilante trabalha.

### De acessos para vigilantes

`d_h` não é o número de acessos: é quanta gente aquele movimento exige.

```
d_h = max(presença mínima, ⌈ (acessos na hora h ÷ dias do período) ÷ K ⌉)
```

Dois cuidados embutidos aí. O primeiro é **dividir pelos dias**: a rota devolve o acumulado do período, e dimensionar a escala por 28 dias de movimento somados daria um resultado absurdo. O segundo é **K**, a capacidade: estimando quinze minutos de atenção por acesso — conferir, registrar, acompanhar —, um vigilante dá conta de quatro por hora.

A presença mínima existe porque portaria vazia é risco, não economia.

### Custo do turno

R$ 220 por vigilante por turno de 8 h, com adicional noturno de 20% **proporcional às horas noturnas** (22h–06h) do turno. Um turno inteiramente noturno custa 20% a mais; um com metade das horas à noite, 10%. É o que faz o modelo preferir concentrar gente de dia quando a demanda permite.

---

## O resultado

Com sete dias de operação de uma portaria de cerca de cinquenta unidades:

| | vigilantes | custo/dia |
|---|---:|---:|
| escala ingênua (mesmo efetivo em todo turno) | 12 | R$ 2.816,00 |
| **escala otimizada** | **9** | **R$ 2.068,00** |
| economia | 3 | R$ 748,00 (**26,6%**) |

R$ 22.440 por mês. A escala ingênua é o que sai de uma planilha: dimensiona tudo pelo pior horário e paga gente parada na madrugada.

Duas leituras que o relatório destaca:

- O modelo **não abre dois dos seis turnos**. Deixar um turno vazio é permitido; o que não pode é deixar uma *hora* descoberta.
- As horas 04h–06h ficam com folga de dois vigilantes. É o preço da granularidade de 8 h: não existe contratar alguém para trabalhar só das 6h às 8h.

---

## Uso

```bash
cd otimizacao
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # Windows; em Linux/mac: .venv/bin/pip
```

**Semear o histórico** (uma vez, se o banco ainda não tem movimento):

```bash
.venv/Scripts/python -m lockwise_otimizacao.cli semear --dias 7 --chave "<a chave da API>"
```

**Resolver:**

```bash
.venv/Scripts/python -m lockwise_otimizacao.cli resolver --dias 7 --saida relatorio.txt
```

| Opção | Padrão | Efeito |
|---|---|---|
| `--api` | a URL de produção | de onde ler a demanda |
| `--arquivo` | — | lê de um JSON salvo, sem rede |
| `--dias` | 7 | dias que o período abrange |
| `--capacidade` | 4 | K: acessos por vigilante por hora |
| `--presenca-minima` | 1 | vigilantes de plantão mesmo sem movimento |
| `--equipe` | 12 | N_max |
| `--saida` | — | salva o relatório num arquivo |

---

## Sobre os dados

O histórico é **sintético**, e isso está dito no relatório. O que ele não é: fabricado por fora. Cada evento nasce da **mesma máquina de estados do gateway** — os mesmos pinos, a mesma sequência de clock — e é enviado pela **mesma API** com a mesma chave. Por isso `tentativa`, `energia_mj` e a ordem dos estados saem corretos: quem os produz é o circuito replicado, não um gerador de JSON.

O que muda em relação à operação real é só o relógio: em vez de esperar sete dias, os eventos são carimbados com datas passadas. O perfil é o de um prédio residencial — pico ao sair de manhã e ao voltar à noite, madrugada parada, fim de semana mais espalhado. A semente é fixa, então o resultado é reprodutível.

O cenário é a **portaria de um condomínio**, não uma porta isolada: ninguém escala turnos de vigilância para uma única porta. O circuito demonstra o controle de um ponto de acesso com uma senha; a tabela `usuario` do banco já modela vários moradores.

---

## Testes

```bash
.venv/Scripts/python -m pytest
```

| Arquivo | Cobre |
|---|---|
| `test_turnos.py` | sobreposição (cada hora com dois turnos), virada da meia-noite, custo noturno proporcional |
| `test_demanda.py` | divisão pelos dias, arredondamento, presença mínima, leitura da API e do arquivo |
| `test_modelo.py` | cobertura de todas as horas, limite de equipe, comparação com a ingênua, inviabilidade |

Um dos testes merece nota: `test_nenhuma_escala_alternativa_e_mais_barata` enumera por força bruta todas as escalas viáveis e confirma que nenhuma custa menos que a devolvida pelo solver. É uma verificação independente de que o CBC achou o ótimo de verdade, e não um resultado qualquer.
