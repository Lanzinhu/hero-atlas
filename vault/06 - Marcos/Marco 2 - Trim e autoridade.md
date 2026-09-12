---
tags: [marco]
marco: 2
prazo: 1 semana
estado: entregue
entregue_em: 2026-09-12
---

# Marco 2 - Trim e autoridade

## Pergunta

**Os atuadores produzem as forcas e torques necessarios, inclusive com falha, e em quanto tempo?**

## Entregavel

- `solve_trim()` com tipo parametrizado e momento do peso sobre `O`
- Matriz de alocacao instantanea
- Mapa de autoridade com **margem estatica e margem dinamica**
- Conjunto de momentos atingiveis, com e sem falha
- Numero de condicao por pose

## Criterio de sucesso

As duas margens aparecem **lado a lado** em toda figura.
Ver [[ADR-004 - Margem estatica e dinamica]].

E a reserva provisoria de 10 por cento e **substituida** pela margem calculada a partir do conjunto
de forcas atingiveis.

## Por que vem antes da dinamica

Analise barata pode eliminar ou transformar uma arquitetura antes de semanas gastas em integracao
de quaternion. Se a geometria nao tem autoridade de guinada, nenhum controlador vai salvar.

## ⚠ Resultado: tres achados duros

A geometria usada e **plausivel, nao medida**: cinco propulsores de 35 kgf, quatro de braco
inclinados 25 graus a 0,35 m de meia envergadura, mais um dorsal. Ainda assim, os achados sao
propriedades da **classe** de arquitetura, nao daquele numero.

### Condicoes em que tudo abaixo vale

⚠ **Pairado nivelado, sem aceleracao lateral, geometria nominal congelada, atuadores disponiveis,
massa de 117 kg.** Nenhuma destas conclusoes e propriedade do conceito em geral.

### 1. Forca lateral e rolagem sao o mesmo canal

As colunas de forca lateral e momento de rolagem sao **linearmente dependentes**, com fator menos
0,55. Nao da para comandar rolagem sem gerar forca lateral, nem o contrario.

O mecanismo, com envergadura `b`, altura `z0` e inclinacao `theta`:

```
Mx / Fy = -( b*cos(theta) + z0*sin(theta) ) / sin(theta)
```

⚠ **Correcao de uma leitura anterior, minha e da avaliacao externa.** Eu disse que o decisivo era
"mesma altura e mesma envergadura". A avaliacao disse que era so a altura comum. **As duas estavam
erradas.** Testado: variar **qualquer um dos tres** entre os pares quebra o acoplamento, porque
todos entram na razao. O que causa a dependencia e os quatro bocais compartilharem o **mesmo valor
da razao**, nao um parametro especifico.

### 2. Um milimetro de desvio lateral ja nao fecha

Consequencia direta. Um centro deslocado lateralmente exige momento de rolagem **sem** forca
lateral. Com a razao fixa, forca lateral nula forca rolagem nula, e o wrench exigido fica fora do
espaco coluna.

**Geometricamente inatingivel, nao falta de capacidade.** Motor maior nao resolve.

⚠ **Escopo, corrigido.** Eu havia escrito que "piloto com bracos assimetricos nao tem equilibrio".
Generalizacao indevida: bracos assimetricos deslocam **simultaneamente** o centro de massa, a
posicao dos bocais e as direcoes de empuxo, o que e outra geometria congelada, com outro resultado
possivel. A afirmacao dura vale para **esta** geometria com o centro deslocado, nao para qualquer
assimetria humana.

### 3. Nenhuma perda unica admite trim

⚠ **Concluido do solver, nao do posto.** "Posto 4 com cinco atuadores, logo sem folga" **nao e
derivacao valida**: remover um atuador pode manter o posto e ainda assim preservar ou destruir um
trim particular.

O resultado real: para cada uma das cinco perdas unicas, o solver **nao** reproduziu o wrench de
pairado nivelado no centro de massa nominal. Portanto nao existe trim estatico naquele cenario e
naquela geometria.

### 4. Ha uma carga interna que desperdica um atuador

Achado que so apareceu ao decompor a matriz. Existe uma combinacao de empuxos que produz **wrench
identicamente nulo**: os propulsores brigam entre si e o resultado se cancela.

Cinco atuadores, **quatro** graus de liberdade uteis. Contar propulsores superestima autoridade
exatamente nessa quantidade.

### 5. As duas limitacoes sao separadas

Escalonar altura entre os pares desacopla forca lateral de rolagem, **mas o posto continua 4**.
Inclinar os bocais para frente e para tras recupera forca longitudinal e sobe o posto para **5**.

| Limitacao | Causa | O que corrige |
|---|---|---|
| Sem forca longitudinal | nenhum bocal tem componente em x | inclinar bocais para frente e tras |
| Lateral acoplado a rolagem | razao comum entre os quatro bocais | escalonar altura, envergadura **ou** inclinacao |
| Carga interna | dependencia entre colunas | geometria com direcoes mais independentes |

Resolver uma **nao** resolve as outras.

### A janela de centro de massa

| Eixo | Janela |
|---|---|
| Longitudinal | 13,5 cm, de +0,085 a +0,220 m |
| **Lateral** | **zero** |

E o centro precisa ficar **sob o centroide de empuxo**, nao sobre o ponto de referencia.

### O que o marco 1 nao conseguia ver

O envelope escalar presumia que toda capacidade instalada contribui para a direcao util. O trim
mostra que a **razao de projecao vertical** fica entre 85 e 100 por cento nesta geometria.

⚠ **Razao de projecao, nao eficiencia.** Ela mede quanto da soma escalar de empuxo vira forca
vertical por **geometria**: direcao de bocal e cancelamento mutuo. Nao e eficiencia de instalacao,
nem propulsiva, nem de motor. Essas sao outra coisa e vivem em `InstallationLosses`. Chamar de
eficiencia confundiria quatro perdas distintas numa palavra so.

E o envelope do marco 1 fica no seu lugar: ele era **condicao necessaria de forca vertical**, nunca
previsao de capacidade de voo.

### Duas causas de inviabilidade, que nao se confundem

| Causa | O que significa | O que resolve |
|---|---|---|
| `geometrically_unattainable` | wrench fora do espaco coluna | geometria diferente |
| `bounds_infeasible` | direcao atingivel, limites bloqueiam | motor maior ou marcha lenta menor |

Fundir as duas faz alguem comprar turbina maior para um problema que turbina nenhuma resolve.

## Ligacoes

[[Trim]] · [[Alocacao de controle]] · [[ADR-002 - Trim inclui momento do peso]] ·
[[ADR-004 - Margem estatica e dinamica]] · [[R-02 - Dois niveis de trim]]
