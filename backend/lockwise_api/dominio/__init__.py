"""Regras do LOCKWISE que não dependem de HTTP nem de banco.

Três padrões GoF, cada um com um trabalho concreto:

- `estados.py`     State     — projeção do estado da fechadura a partir dos eventos
- `politicas.py`   Strategy  — política de supervisão que decide quando gerar alerta
- `notificacao.py` Observer  — quem é avisado quando um alerta nasce

Nada aqui importa FastAPI ou SQLAlchemy. Isso é o que permite testar o
domínio em milissegundos e trocar a infraestrutura sem tocar nas regras.
"""
