# ADR 0028 — C4 em Mermaid versionado, com as camadas verificadas por teste

Data: 2026-09-22
Situação: aceita

## Contexto

O requisito de arquitetura pede documentação em C4 ou UML. A tentação é abrir uma ferramenta de diagramas, desenhar caixas bonitas, exportar PNG e colar no repositório.

Dois problemas com isso. O primeiro é que a imagem se descola do código no primeiro refactor: alguém move uma responsabilidade, o diagrama continua mostrando o desenho antigo, e ninguém percebe porque imagem não aparece em diff. O segundo é que nem o diagrama nem o texto obrigam nada — "o domínio não depende de infraestrutura" é uma afirmação que envelhece em silêncio no dia em que alguém importa `sqlalchemy` dentro de `dominio/` para resolver um problema às pressas.

## Decisão

Os diagramas são **Mermaid em Markdown**, versionados junto do código. O GitHub renderiza direto, e uma mudança de arquitetura aparece no diff como qualquer outra linha.

Quatro níveis: contexto, contêiner, componente e — só para o padrão State, que é a mesma máquina de estados que aparece três vezes no projeto — código. Mais um diagrama de sequência de um `POST /acessos` que dispara a política de supervisão.

Cada padrão GoF e cada princípio SOLID aponta **arquivo e linha**. "Aplicamos SOLID" sem evidência não conta, e conferimos uma a uma as citações antes de publicar: duas apontavam para linha errada de `main.py`.

E o que sustenta tudo isso: `backend/tests/test_arquitetura.py` lê a árvore sintática dos módulos e falha se o domínio importar `fastapi`, `sqlalchemy` ou `pydantic`, se importar de fora do próprio pacote, se `servicos.py` tocar em `sqlalchemy`, ou se uma rota falar com o banco sem passar por um serviço. O desenho vira restrição executável.

## Alternativas que consideramos

PlantUML com a biblioteca oficial de C4: produz diagramas mais fiéis à notação, com legenda e estilos prontos. Exige um servidor de renderização ou um passo de build para virar imagem, e o GitHub não renderiza `.puml` sozinho. Mermaid perde em fidelidade à notação e ganha em ficar visível onde as pessoas leem.

Ferramenta gráfica (draw.io, Excalidraw, Figma) exportando PNG: melhor acabamento, e é a opção que mais rápido apodrece. Descartada pelo motivo do contexto.

UML clássico em vez de C4: o roteiro aceita os dois. C4 tem a vantagem de partir do contexto e ir fechando o zoom, o que casa com um sistema que atravessa hardware, máquina local e nuvem — um diagrama de classes sozinho não mostraria que existe um circuito do outro lado.

Só documentar, sem os testes de arquitetura: era o plano inicial. Enquanto escrevíamos a frase "nenhuma seta sai do domínio", ocorreu que a frase podia deixar de ser verdade sem ninguém notar. Os testes custaram cerca de oitenta linhas.

## Consequências

Um refactor que quebre as camadas quebra o CI, com uma mensagem que diz qual arquivo, qual import proibido e o que fazer. Testamos injetando um `import sqlalchemy` em `politicas.py` para confirmar que a falha aparece.

Os diagramas Mermaid foram validados com o parser da versão 11 antes do commit. Um ponto e vírgula dentro de uma `Note` quebrava o diagrama de sequência — e isso apareceria como um bloco de erro vermelho na página do GitHub, exatamente onde o avaliador olharia.

A notação é aproximada. Não usamos a biblioteca C4 oficial do Mermaid, e sim `graph` com `classDef` imitando as convenções de cor. Quem conhece C4 a fundo vai notar; a alternativa era um diagrama mais correto que ninguém veria renderizado.
