# ADR 0026 — Modelo de cobertura com turnos sobrepostos

Data: 2026-09-22
Situação: aceita

## Contexto

O requisito de Pesquisa Operacional pede "um problema de otimização real do sistema, modelado e resolvido matematicamente". O plano original, registrado no documento de contexto, previa seis turnos de 4 h e um modelo de cobertura para a escala de vigilância.

Ao começar a implementar, percebemos que essa formulação não tem o que otimizar. Seis turnos de 4 h sem sobreposição cobrem cada hora exatamente uma vez; a restrição de cobertura de cada hora envolve uma única variável, e a solução ótima sai por inspeção: para cada turno, o maior `d_h` dentro dele. Não há troca a decidir, não há conflito entre restrições, e um avaliador de Pesquisa Operacional identifica isso de imediato.

## Decisão

Turnos de 8 h começando a cada 4 h. São seis turnos — 00–08, 04–12, 08–16, 12–20, 16–00, 20–04 — e cada hora do dia é coberta por exatamente dois deles.

Com a sobreposição, escalar alguém no turno 12–20 ajuda tanto a tarde quanto o início da noite, e a mesma hora pode ser atendida por combinações diferentes de turnos. A escolha passa a ser combinatória, que é o que caracteriza um problema de cobertura.

O custo do turno leva adicional noturno de 20% **proporcional às horas noturnas** que ele contém, e não como um rótulo de "turno noturno" tudo ou nada. Isso dá ao modelo motivo para preferir concentrar pessoal nos turnos diurnos quando a demanda permite.

Turno de 8 h também é o que um vigilante trabalha na prática, o que torna o modelo mais fácil de defender do que blocos de 4 h.

## Alternativas que consideramos

Manter os turnos de 4 h do plano original: descartado pelo motivo acima. Ficaria um modelo com aparência de otimização e resposta trivial.

Turnos de 12 h, dois por dia, como em muitas portarias: reduz o problema a duas variáveis e volta a ser quase trivial.

Modelar por hora, decidindo quantos vigilantes em cada uma das 24 horas: seria mais flexível e daria custo menor, mas ninguém contrata vigilante por hora avulsa. O modelo perderia contato com a realidade que deveria representar.

Incluir a energia da trava no objetivo: o documento de contexto sugeria que o número da física reaparecesse aqui. Medimos: o acionamento consome cerca de 0,6 Wh por dia, ou R$ 0,0005 — cinco ordens de grandeza abaixo do custo de um turno. Incluir isso no objetivo não mudaria uma única decisão do modelo, e apresentá-lo como se mudasse seria desonesto. A energia entra no relatório como verificação: é a assinatura física de cada acesso liberado, e serve para conferir se o histórico bate com o número de aberturas.

## Consequências

O resultado tem substância: com a demanda de uma semana, a escala otimizada usa 9 vigilantes contra 12 da escala ingênua, uma redução de 26,6% no custo diário.

Duas propriedades do resultado valem a pena na apresentação. O modelo deixa dois dos seis turnos vazios — o que a restrição proíbe é hora descoberta, não turno vazio. E sobram vigilantes entre 4h e 6h, porque com blocos de 8 h não existe contratar alguém para as duas horas que faltam; é o custo da granularidade, e aparece explicitamente na tabela de cobertura.

A verificação do ótimo não depende de confiar no solver: um teste enumera por força bruta todas as escalas viáveis e confirma que nenhuma custa menos que a devolvida pelo CBC.

O parâmetro mais frágil é K, a capacidade por vigilante, que é uma estimativa de quanto tempo um acesso consome. O relatório traz uma análise de sensibilidade mostrando o custo para K de 2 a 8, em vez de apresentar um número único como se fosse exato.
