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

## A licao que se repete

Sete vezes o mesmo padrao: **uma frase intuitiva que, implementada literalmente, introduz erro
sistematico exatamente na analise mais sensivel.**

Somar tensores. Congelar buffer. Dividir forca requerida pelo derating. Recalcular inercia sobre
centro movel. Testar conservacao onde ela nao vale.

Todas pareciam certas. Nenhuma era.

## Ligacoes

[[Indice de decisoes]] · [[MOC - Hero Atlas]]
