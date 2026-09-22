"""Transforma a solução em texto que uma pessoa lê e defende numa banca.

Um número concreto vale mais que a explicação do modelo, então o relatório
começa pela economia e só depois mostra de onde ela veio.
"""

from __future__ import annotations

from .demanda import Demanda
from .modelo import Comparacao, Escala, comparar
from .turnos import TURNOS

LARGURA = 72

# Tarifa residencial média, para dimensionar o custo da energia da trava.
TARIFA_KWH = 0.80


def _titulo(texto: str) -> str:
    return f"\n{texto}\n{'─' * len(texto)}"


def _barra(n: int, escala: int = 1, char: str = "█") -> str:
    return char * (n * escala)


def demanda_em_texto(d: Demanda) -> str:
    linhas = [
        _titulo("DEMANDA — de onde vem"),
        f"Origem: {d.origem}",
        f"Período: {d.dias} dia(s) · fuso {d.fuso}",
        f"Total: {d.total_acessos} acessos · {d.total_energia_mj / 1000:.1f} J de energia de trava",
        "",
        f"Um vigilante acompanha {d.capacidade} acessos por hora "
        f"({60 // d.capacidade} min por acesso); a portaria nunca fica com menos de "
        f"{d.presenca_minima}.",
        "",
        "hora   acessos/dia   vigilantes exigidos (d_h)",
    ]
    for h in range(24):
        linhas.append(
            f"  {h:02d}h  {d.media_diaria[h]:9.1f}   {d.vigilantes[h]}  {_barra(d.vigilantes[h])}"
        )
    pico = d.hora_de_pico
    linhas.append("")
    linhas.append(f"Pico às {pico:02d}h com {d.media_diaria[pico]:.1f} acessos/dia.")
    return "\n".join(linhas)


def modelo_em_texto(equipe_maxima: int) -> str:
    return "\n".join([
        _titulo("MODELO — programação linear inteira"),
        "Conjuntos   H = {0..23} horas do dia",
        "            T = {0..5} turnos de 8 h começando a cada 4 h",
        "",
        "Parâmetros  a(t,h) = 1 se o turno t cobre a hora h",
        "            d_h    vigilantes exigidos na hora h",
        "            c_t    custo de um vigilante no turno t",
        f"            N_max  = {equipe_maxima} vigilantes disponíveis",
        "",
        "Variável    x_t ∈ ℤ⁺   vigilantes escalados no turno t",
        "",
        "  minimizar    Σ_t c_t · x_t",
        "",
        "  sujeito a    Σ_t a(t,h) · x_t ≥ d_h    ∀h ∈ H     (cobertura)",
        "               Σ_t x_t ≤ N_max                       (equipe)",
        "               x_t ≥ 0, inteiro          ∀t ∈ T",
        "",
        "Turnos de 8 h a cada 4 h fazem cada hora ser coberta por dois turnos.",
        "Sem essa sobreposição o problema seria trivial: bastaria olhar a maior",
        "demanda dentro de cada bloco.",
        "",
        "Resolvido com CBC (COIN-OR), via PuLP.",
    ])


def escala_em_texto(e: Escala) -> str:
    linhas = [
        _titulo(f"ESCALA {e.rotulo.upper()}"),
        "turno          custo unitário   vigilantes        custo",
    ]
    for t, x in zip(TURNOS, e.por_turno):
        marca = "  —" if x == 0 else ""
        linhas.append(
            f"  {t.rotulo}  R$ {t.custo:8.2f}   {x:>10}   R$ {t.custo * x:8.2f}{marca}"
        )
    linhas.append(f"{'':>17}{'TOTAL':>14}   {e.total_vigilantes:>10}   R$ {e.custo:8.2f}")
    return "\n".join(linhas)


def cobertura_em_texto(e: Escala) -> str:
    linhas = [
        _titulo("COBERTURA HORA A HORA"),
        "hora  exigido  escalado  folga",
    ]
    for h in range(24):
        folga = e.folga[h]
        nota = "  ← restrição justa" if folga == 0 else ""
        linhas.append(
            f"  {h:02d}h      {e.demanda.vigilantes[h]}        {e.presentes(h)}      {folga:+d}{nota}"
        )
    justas = [h for h in range(24) if e.folga[h] == 0]
    linhas += [
        "",
        f"Horas em que a restrição de cobertura está justa: "
        f"{', '.join(f'{h:02d}h' for h in justas) or 'nenhuma'}.",
        "São elas que determinam o tamanho da equipe — aliviar qualquer outra hora",
        "não reduziria o custo.",
    ]
    return "\n".join(linhas)


def comparacao_em_texto(c: Comparacao) -> str:
    return "\n".join([
        _titulo("O QUE A OTIMIZAÇÃO ECONOMIZA"),
        f"  escala ingênua (mesmo efetivo em todo turno)   "
        f"{c.ingenua.total_vigilantes:>2} vigilantes   R$ {c.ingenua.custo:8.2f}/dia",
        f"  escala otimizada                               "
        f"{c.otimizada.total_vigilantes:>2} vigilantes   R$ {c.otimizada.custo:8.2f}/dia",
        "",
        f"  economia                                       "
        f"{c.vigilantes_a_menos:>2} vigilantes   R$ {c.economia:8.2f}/dia",
        f"  redução de {c.economia_percentual}% no custo diário · "
        f"R$ {c.economia_mensal:.2f} por mês",
        "",
        "A escala ingênua é o que sai de uma planilha: o mesmo efetivo em todos os",
        "turnos, dimensionado pelo pior horário. Ela cobre a demanda, mas paga gente",
        "parada na madrugada para dar conta do fim da tarde.",
    ])


def sensibilidade_em_texto(d: Demanda, equipe_maxima: int) -> str:
    """Como a resposta muda se a estimativa de capacidade estiver errada.

    K é o parâmetro mais frágil do modelo — é uma estimativa de quanto tempo
    um acesso consome. Mostrar o efeito de errá-lo é mais honesto do que
    apresentar um número único como se fosse exato.
    """
    from dataclasses import replace as _replace

    linhas = [
        _titulo("SENSIBILIDADE — e se a capacidade estiver errada?"),
        "K = acessos que um vigilante acompanha por hora",
        "",
        "  K   min/acesso   vigilantes   custo/dia    vs. adotado",
    ]

    def resolver(k: int):
        try:
            return comparar(_replace(d, capacidade=k), equipe_maxima)
        except Exception:  # noqa: BLE001 — demanda que não cabe na equipe
            return None

    resultados = {k: resolver(k) for k in sorted({2, 3, 4, 6, 8, d.capacidade})}
    referencia = resultados.get(d.capacidade)
    base = referencia.otimizada.custo if referencia else None

    for k, c in resultados.items():
        marca = " ←" if k == d.capacidade else ""
        if c is None:
            linhas.append(
                f"  {k}   {60 // k:>6}       (não cabe em {equipe_maxima} vigilantes){marca}"
            )
            continue
        variacao = f"   {100 * (c.otimizada.custo / base - 1):+.0f}%" if base else ""
        linhas.append(
            f"  {k}   {60 // k:>6}       {c.otimizada.total_vigilantes:>6}   "
            f"R$ {c.otimizada.custo:8.2f}{variacao}{marca}"
        )
    linhas += [
        "",
        f"A estimativa adotada é K = {d.capacidade}. Subestimá-la encarece a escala;",
        "superestimá-la deixa a portaria sem gente na hora do movimento.",
    ]
    return "\n".join(linhas)


def energia_em_texto(d: Demanda) -> str:
    """Por que a energia da física não entra no custo — e onde ela entra."""
    import math

    from .turnos import CUSTO_BASE

    kwh = d.total_energia_mj / 3_600_000_000
    por_dia = kwh / d.dias
    custo_energia = por_dia * TARIFA_KWH
    ordens = math.floor(math.log10(CUSTO_BASE / custo_energia)) if custo_energia else 0
    return "\n".join([
        _titulo("A ENERGIA DA TRAVA, E POR QUE ELA NÃO ENTRA NO OBJETIVO"),
        f"O histórico acumula {d.total_energia_mj / 1000:.1f} J de acionamento de trava "
        f"({kwh * 1000:.3f} Wh),",
        f"o que dá {por_dia * 1000:.4f} Wh por dia. A R$ {TARIFA_KWH:.2f} o kWh, "
        f"R$ {custo_energia:.8f} por dia.",
        "",
        f"Contra R$ {CUSTO_BASE:.2f} de um turno de vigilante, são {ordens} ordens de",
        "grandeza de diferença. Incluir esse custo no objetivo seria teatro: não",
        "mudaria uma única decisão do modelo.",
        "",
        "Onde a energia serve de verdade: ela é a assinatura física de cada acesso",
        "liberado (docs/fisica.md §6 — 12 V × 292,5 mA × 5,16 s = 18 200 mJ). É por",
        "ela que se confere se o histórico bate com o número de aberturas reais.",
    ])


def completo(d: Demanda, equipe_maxima: int) -> str:
    c = comparar(d, equipe_maxima)
    partes = [
        "=" * LARGURA,
        "LOCKWISE — ESCALA DE VIGILÂNCIA DE MENOR CUSTO".center(LARGURA),
        "=" * LARGURA,
        comparacao_em_texto(c),
        demanda_em_texto(d),
        modelo_em_texto(equipe_maxima),
        escala_em_texto(c.otimizada),
        escala_em_texto(c.ingenua),
        cobertura_em_texto(c.otimizada),
        sensibilidade_em_texto(d, equipe_maxima),
        energia_em_texto(d),
        "",
    ]
    return "\n".join(partes)
