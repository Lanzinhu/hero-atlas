---
tags: [marco]
marco: 1
prazo: 1 semana
estado: aguardando
---

# Marco 1 - Envelope

## Pergunta

**O conceito fecha na conta?** Quanto empuxo, quanta massa, quantos minutos.

## Entregavel

- Envelope de massa e forca efetiva requerida
- Laco de fechamento de massa por ponto fixo
- Autonomia integrada para turbina e eletrico
- Tres familias de veiculo separadas, sem requisito compartilhado

## Criterio de sucesso

Devolve **faixa** de empuxo necessario, nunca numero unico. E reproduz os benchmarks dentro da
tolerancia do nivel de procedencia de cada um. Ver [[Nivel de evidencia]].

Referencia de calibracao: piloto de 80 kg, traje de 25 kg, combustivel de 12 kg tem que dar
**142,0 kgf de exigencia fisica de empuxo efetivo**. Ver
[[Forca requerida x capacidade de entrega]].

## Saida esperada

Tabela no terminal mais grafico de T/W contra massa do piloto e combustivel, com a linha de
viabilidade, mais grafico de autonomia contra diametro de rotor cruzando a linha da turbina.

O fator de crescimento de massa, isto e a derivada da massa bruta em relacao a carga paga, e a saida
mais informativa. **Acima de 4 o conceito e fragil.**

## Ligacoes

[[Forca requerida x capacidade de entrega]] · [[Autonomia e energia]] · [[Atmosfera]]
