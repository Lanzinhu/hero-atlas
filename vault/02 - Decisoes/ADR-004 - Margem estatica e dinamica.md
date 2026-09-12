---
tags: [adr, alocacao, autoridade]
adr: 004
estado: aceita
data: 2026-09-11
---

# ADR-004 - Duas margens de autoridade, ambas no relatorio

> Provavelmente a distincao mais importante de todo o projeto.

## O problema

Um conjunto de propulsores pode ter **forca maxima excelente** e **autoridade de curto prazo
miseravel**. Musculo forte, reflexo de preguica.

Reportar apenas a margem estatica cria falsa sensacao de viabilidade: o traje "tem potencia" e
mesmo assim e dinamicamente lento demais para pairar de forma robusta.

## Decisao

### Margem estatica

O que seria atingivel **se os motores tivessem tempo suficiente**.

```
T_min <= T_i <= T_max
```

Responde: a geometria e o tamanho dos motores bastam?

### Margem dinamica no horizonte Ha

O que e atingivel **antes que a perturbacao cresca demais**.

```
T_i(t + Ha) pertence a [ T_i(t) - Tdot_down,max * Ha ,  T_i(t) + Tdot_up,max * Ha ]
```

ou uma previsao nao linear da turbina.

Responde: da tempo de reagir?

## Consequencia

Para microturbina a **segunda e provavelmente a metrica decisiva**. As duas aparecem lado a lado em
toda figura de autoridade, nunca isoladas.

Isso tambem alimenta [[R-02 - Dois niveis de trim]]: um trim pos-falha pode existir estaticamente e
ser inalcancavel dinamicamente.

## Ligacoes

[[Alocacao de controle]] · [[ADR-003 - Efetividade dinamica no alocador]] ·
[[Marco 2 - Trim e autoridade]] · [[Numeros decisivos]]
