"""O interpretador reproduz os gestos do Logisim e dispara os eventos certos."""

from lockwise_gateway.cli import Interprete, main
from lockwise_gateway.eventos import Resultado, TipoAlerta
from lockwise_gateway.fontes import Roteiro
from lockwise_gateway.transporte import ClienteEco


def interprete(**kw) -> tuple[Interprete, list[str], ClienteEco]:
    linhas: list[str] = []
    eco = ClienteEco(saida=linhas.append)
    return Interprete(eco, saida=linhas.append, **kw), linhas, eco


def test_sequencia_do_readme_passo_a_passo():
    it, linhas, eco = interprete()
    it.rodar(Roteiro([
        "senha 1011",
        "confirma on",
        "clk",  # -> VERIFICANDO
        "confirma off",
        "clk",  # -> LIBERADO
        "timeout on",
        "clk",  # -> AGUARDANDO
        "timeout off",
    ]))
    assert it.maquina.estado.nome == "AGUARDANDO"
    assert [e.resultado for e in it.eventos] == [Resultado.LIBERADO]
    assert eco.enviados[0][1]["energia_mj"] == 18_200
    assert any("AGUARDANDO -> VERIFICANDO" in l for l in linhas)
    assert any("VERIFICANDO -> LIBERADO" in l for l in linhas)


def test_macros_tentar_e_desbloquear():
    it, _, eco = interprete()
    it.rodar(Roteiro(["tentar 0000", "tentar 1111", "tentar 0101", "desbloquear"]))
    tipos = [(type(e).__name__, getattr(e, "resultado", None) or e.tipo) for e in it.eventos]
    assert tipos == [
        ("EventoAcesso", Resultado.NEGADO),
        ("EventoAcesso", Resultado.NEGADO),
        ("EventoAcesso", Resultado.BLOQUEADO),
        ("Alerta", TipoAlerta.BLOQUEIO),
        ("Alerta", TipoAlerta.DESBLOQUEIO_ADMIN),
    ]
    assert [r for r, _ in eco.enviados] == ["/acessos", "/acessos", "/acessos", "/alertas", "/alertas"]


def test_bits_individuais_e_toggle():
    it, _, _ = interprete()
    it.rodar(Roteiro(["s3 on", "s1 on", "s0 on", "confirma", "clk", "confirma", "clk"]))
    assert it.pinos.senha == 0b1011 and it.pinos.confirma is False
    assert it.maquina.estado.nome == "LIBERADO"


def test_comando_desconhecido_e_argumento_invalido_nao_derrubam():
    it, linhas, _ = interprete()
    it.rodar(Roteiro(["abracadabra", "senha 12", "confirma talvez", "clk"]))
    assert sum("!" in l for l in linhas) == 3
    assert it.maquina.estado.nome == "AGUARDANDO"


def test_roteiro_ignora_comentarios_e_linhas_vazias():
    assert list(Roteiro(["# cabecalho", "", "clk  # borda", "   "]).comandos()) == ["clk"]


def test_timeout_fisico_agenda_fechamento_apos_liberar():
    agendados: list[float] = []

    def agendar(segundos, acao):
        agendados.append(segundos)
        acao()  # executa na hora, para o teste ser sincrono

    it, linhas, _ = interprete(timeout_fisico=True, agendar=agendar)
    it.rodar(Roteiro(["tentar 1011"]))
    assert agendados == [5.16]
    assert it.maquina.estado.nome == "AGUARDANDO"
    assert it.pinos.timeout is False
    assert any("NE555" in l for l in linhas)


def test_estado_lista_saidas_acesas():
    it, linhas, _ = interprete()
    it.rodar(Roteiro(["senha 1011", "estado"]))
    assert any("AGUARDANDO SENHA_OK" in l for l in linhas)


def test_sair_encerra():
    it, _, _ = interprete()
    it.rodar(Roteiro(["sair", "clk"]))
    assert it.encerrado and it.eventos == [] and it.maquina.estado.nome == "AGUARDANDO"


def test_main_em_modo_eco_com_roteiro(tmp_path, capsys):
    roteiro = tmp_path / "demo.txt"
    roteiro.write_text("tentar 1011\nfechar\nsair\n", encoding="utf-8")
    assert main(["--roteiro", str(roteiro), "--fila", str(tmp_path / "fila.jsonl")]) == 0
    saida = capsys.readouterr().out
    assert "modo eco" in saida
    assert "VERIFICANDO -> LIBERADO" in saida
    assert '"energia_mj": 18200' in saida
