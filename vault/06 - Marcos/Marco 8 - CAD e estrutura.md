---
tags: [marco, opcional]
marco: 8
prazo: 2 dias por item
estado: aguardando
---

# Marco 8 e alem - CAD, estrutura e alta fidelidade

> **So com pergunta especifica.** Nada aqui e feito "porque sim".
> Prazo de dois dias por item. Estouro abandona e documenta.

## Itens possiveis

| Item | Pergunta que justifica |
|---|---|
| LQR e MPC | O controlador melhor compra margem? |
| Alocacao hierarquica | A prioridade lexicografica explicita muda o resultado? |
| Multicorpo completo | Os segmentos articulados mudam a conclusao? |
| FreeCAD e STEP | Qual a inercia da geometria real? |
| CalculiX modal e Campbell | Ha ressonancia na faixa de rotacao? |
| OpenFOAM | Quanto vale o efeito solo e a reingestao? |
| ArduPilot SITL | O modelo aguenta autopiloto real? |

Os tres ultimos dependem de WSL, que **nao esta instalado**.

## O laco CAD e simulador

O mesmo arquivo de configuracao alimenta a macro que constroi o chassi e exporta STEP, e um segundo
script exporta as propriedades de massa **por componente, com orientacao e centro proprios**, que
entram no agregador de [[Propriedades de massa]].

E so aqui que a massa contabil pode ser reconciliada. **Ate entao, toda conclusao dos marcos 1 a 7
repousa sobre massa estimada.**

## Criterio estrutural em duas etapas

### Triagem por Campbell

| Fonte | Expressao |
|---|---|
| Frequencia de rotacao do eixo | `f_shaft = RPM / 60` |
| Harmonico de rotacao | `n * f_shaft` |
| Frequencia de passagem de pas | `f_BPF = N_pas * f_shaft` |
| Harmonico de passagem de pas | `n * f_BPF` |
| Atualizacao de controle | `f_ctrl` |
| Excitacao aerodinamica | depende de velocidade e geometria |

Para 35 mil a 120 mil rotacoes por minuto, `f_shaft` vai de **583 Hz a 2.000 Hz**.

### Avaliacao de resposta

Nao existe separacao de seguranca universal. Para os cruzamentos relevantes, estimar amplificacao
dinamica, deslocamento, aceleracao, tensao, dano por fadiga e transmissibilidade para o piloto.

A severidade depende de amortecimento modal, massa modal efetiva, participacao do modo, direcao da
forca, rigidez dos suportes, tempo de permanencia e amplitude.

**Nem toda passagem de pas em dezenas de quilohertz e relevante para o chassi**, porque o caminho de
transmissao filtra. A analise identifica o que **chega** a estrutura, em vez de listar todas as
frequencias possiveis.

## Ligacoes

[[Propriedades de massa]] · [[Escopo e nao-escopo]] · [[Nivel de evidencia]]
