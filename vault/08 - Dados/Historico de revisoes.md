---
tags: [processo, historico]
atualizado: 2026-09-11
---

# Historico de revisoes do plano

O plano passou por sete revisoes antes de fechar. Cada uma corrigiu defeitos reais, e vale guardar
o registro porque os erros sao instrutivos e podem voltar.

## Revisao 1 para 2

Cinematica de braco prescrita com agregacao de massa por pose. Atraso e perda ambiental viram
envelopes de incerteza. Momento giroscopico vira vetorial. Garantia do cone corrigida para
aproximacao convexa. Criterio modal vira diagrama de Campbell. Tolerancia estratificada por
procedencia. Controlabilidade promovida para antes do controlador. Monte Carlo vira sensibilidade
condicionada.

## Revisao 2 para 3

Taxonomia de evidencia refeita: origem, classe, data, hash, aplicabilidade e incerteza, em vez de
niveis A, B e C. Tolerancia pertence a grandeza. **Empuxo requerido separado de instalado.** Dupla
contagem atmosferica eliminada. Estado formalizado. Massa movel dinamicamente fechada. Alocacao
separada de controlabilidade. **Alocacao incremental vira metodo primario.**

## Revisao 3 para 4

**Forca efetiva requerida separada de capacidade de entrega.** Cosseno vira modelo de ordem zero.
Estabilidade definida operacionalmente. Derivadas de pose fornecidas analiticamente. **Malha fechada
integrada num relogio unico.** Trim, alocacao e retrim como operacoes distintas. JSBSim documentado
como oraculo parcial. Massa contabil no lugar de inercia de CAD.

## Revisao 4 para 5

Regra sobre congelar buffer era **falsa como generalizacao**: tres casos distinguidos. Integrador
orientado a evento em vez de taxa fixa. Limite de rampa contra o proprio periodo declarado.
Interpolacao de historico ao menos cubica. Inviabilidade como evento registrado. Trim com gravidade
no referencial do corpo. **Falha separa existencia de capacidade de captura.** Tres classes de teste
numerico separadas.

## Revisao 5 para 6

**Agregacao de massa corrigida: tensores nao se somam diretamente.** Dinamica sobre ponto de
referencia fixo. Eventos separados em agendados e por guarda, com histerese. Interpolacao causal com
proibicao de atraso menor que o passo. Limite de comando da ECU separado do limite fisico.
**Quatro modos de falha da alocacao**, com `wrench_unattainable` como principal.

## Revisao 6 para 7

**ADR-001**: ponto de referencia com rota reduzida ate o marco 5 e espacial a partir do 6.
**ADR-002**: trim inclui o momento do peso. **ADR-003**: alocador usa efetividade dinamica.
**ADR-004**: margem estatica e dinamica. **ADR-005**: saturacao vira telemetria. **ADR-006**:
exploracao de R em tres fases. Parametros humanos sob o mesmo regime de procedencia. Prazo por marco
com ordem de corte.

## Rodadas 17 e 18: energia por missao

**Rodada 17.** O projeto escreveu "recomendacao: combustao" com zero dinamica implementada. Tres
afirmacoes cairam: "autonomia eletrica e funcao da area, nao da bateria" era falsa e contradizia a
assinatura da propria funcao; "16,7 kgf por bocal" era massa dividida por sete; e a eliminacao do
hibrido serie confundia energia com potencia. Resposta estrutural em
[[ADR-008 - Ramos de propulsao sem selecao]].

Um bug apareceu por confronto com forma fechada: a massa da bateria nao entrava na massa bruta,
inflando a autonomia eletrica em 37 por cento. **O erro favorecia exatamente a arquitetura que o
projeto estava prestes a descartar.**

**Rodada 18.** Seis pontos, tres deles defeito de contrato e nao de redacao:

1. A missao de referencia tinha **fase morta**: descida depois do pairado aberto, que nunca
   executava. `MissionProfile` agora recusa.
2. `minimum_thrust_margin_ratio` **nao era margem de wrench**. Renomeado para
   `min_upper_thrust_headroom_ratio`, com o que **nao** mede no docstring.
3. "Bateria otima = 2 x massa seca" tinha hipoteses nao declaradas. Com carga auxiliar o otimo
   sobe, e agora existe forma para isso.
4. Massa seca e **especifica da familia**: a comparacao e de armazenamento de energia, nao de
   arquiteturas. Registrado como incognita bloqueante nos quatro ramos.
5. A potencia de barramento usava caminho escalar, e foi refeita pelo caminho do trim.
6. `tools/` estava fora do portao de lint, e e justamente onde nascem os numeros de relatorio.

E uma falha de transparencia, apontada pelo Alan: as tabelas viviam so no terminal. As saidas dos
experimentos agora sao versionadas em `docs/resultados/`, geradas por `tools/refresh_results.py`.

## Rodadas 17 e 18: energia por missao

**Rodada 17.** O projeto escreveu "recomendacao: combustao" com zero dinamica implementada. Tres
afirmacoes cairam: "autonomia eletrica e funcao da area, nao da bateria" era falsa e contradizia a
assinatura da propria funcao; "16,7 kgf por bocal" era massa dividida por sete, e o solver mostra
12,1 a 35,0 kgf com um par no teto; e a eliminacao do hibrido serie confundia energia com
potencia. Resposta estrutural em [[ADR-008 - Ramos de propulsao sem selecao]].

Um bug apareceu por confronto com forma fechada: a massa da bateria nao entrava na massa bruta,
inflando a autonomia eletrica em 37 por cento. **O erro favorecia exatamente a arquitetura que o
projeto estava prestes a descartar.**

**Rodada 18.** Seis pontos, tres deles defeito de contrato e nao de redacao:

1. A missao de referencia tinha **fase morta**: descida depois do pairado aberto, que nunca
   executava. `MissionProfile` agora recusa, com a mensagem explicando o porque.
2. `minimum_thrust_margin_ratio` **nao era margem de wrench**. Renomeado para
   `min_upper_thrust_headroom_ratio`, com o que **nao** mede no docstring.
3. "Bateria otima = 2 x massa seca" tinha hipoteses nao declaradas. Com carga auxiliar o otimo
   sobe, e agora existe forma para isso, conferida contra maximizacao numerica.
4. Massa seca e **especifica da familia**: a comparacao e de armazenamento de energia sob
   geometria fixa, nao de arquiteturas. Incognita bloqueante nos quatro ramos.
5. A potencia de barramento usava caminho escalar, e foi refeita pelo caminho do trim. A forma
   escalar subestimava em ate 12 por cento.
6. `tools/` estava fora do portao de lint, e e justamente onde nascem os numeros de relatorio.

E uma falha de transparencia, apontada pelo Alan: as tabelas viviam so no terminal, entao a
revisao externa tinha que confiar na transcricao. As saidas dos experimentos agora sao
versionadas em `docs/resultados/`, geradas por `tools/refresh_results.py`.

## A licao que se repete

Sete vezes o mesmo padrao: **uma frase intuitiva que, implementada literalmente, introduz erro
sistematico exatamente na analise mais sensivel.**

Somar tensores. Congelar buffer. Dividir forca requerida pelo derating. Recalcular inercia sobre
centro movel. Testar conservacao onde ela nao vale.

Todas pareciam certas. Nenhuma era.

## Ligacoes

[[Indice de decisoes]] · [[MOC - Hero Atlas]]
