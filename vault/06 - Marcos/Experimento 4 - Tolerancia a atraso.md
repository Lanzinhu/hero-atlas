---
tipo: experimento
id: EXP-004
estado: concluido
data: 2026-09-12
commit: dc3ad37
marco: 3
tags: [dinamica, propulsao, atraso, sensibilidade, controle]
---

# Experimento 4 — Tolerância a atraso e rampa

## 1. Pergunta exata

> Para a família A, com massa, centro de massa, inércia, missão e limites de falha
> declarados, quais combinações de atraso de transporte e constante de tempo ainda
> permitem recuperar de uma perturbação de rolagem declarada, dentro dos limites
> físicos de empuxo?

**Este experimento não responde:** se há estabilidade em malha fechada fora da faixa
varrida e da perturbação declarada; se um humano pilotaria; se alguma turbina real
atende; se o conjunto é seguro. Não há piloto humano no laço, não há vento, não há
aerodinâmica, não há falha de propulsor.

## 2. Artefatos revisados

| Artefato | Caminho | Papel |
|---|---|---|
| Modelo de atuador | `src/hero_atlas/propulsion/actuator.py` | atraso, constante de tempo, rampa, saturação |
| Alocador | `src/hero_atlas/control/allocator.py` | wrench para comando, com caixa do horizonte |
| Controlador | `src/hero_atlas/control/attitude.py` | amostrado, retido, domínio declarado |
| Orçamento de momento | `src/hero_atlas/analysis/control_budget.py` | as duas margens do ADR-004 |
| Dinâmica | `src/hero_atlas/dynamics/rigid_body.py` | corpo rígido, rota reduzida |
| Agenda de eventos | `src/hero_atlas/sim/events.py` | tique do controlador |
| Laço fechado | `src/hero_atlas/sim/closed_loop.py` | a ordem entre as peças |
| Experimento | `tools/delay_sweep.py` | gera a varredura |
| Resultado | `docs/resultados/experimento-4-atraso.txt` | tabela versionada |
| Testes | `tests/validation/test_closed_loop.py` | 20 contratos |

## 3. Hipóteses declaradas

| Hipótese | Valor | Tipo | Procedência | Impacto |
|---|---:|---|---|---|
| Massa bruta | 115 kg | estimativa | bloco, sem CAD | alto |
| Centro de massa | (0,1575; 0; 0) m | escolha | meio da janela do EXP-001 | alto |
| Inércia | diag(32,2; 32,2; 2,3) kg·m² | estimativa | cilindro equivalente | **medido: baixo** |
| Atraso de transporte | 0 a 0,40 s | **varredura** | hipótese | crítico |
| Constante de tempo | 0,10 a 1,80 s | **varredura** | hipótese | crítico |
| Rampa máxima | 40 a 400 N/s | varredura | hipótese | baixo na faixa |
| Empuxo por bocal | 34 a 343 N | hipótese de classe | catálogo, sem hash | alto |
| Horizonte do alocador | 0,20 s | escolha de projeto | declarado | alto |
| Banda do controlador | 1,05 rad/s | **derivada** | 70% da alcançável | alto |
| Tique do controlador | 100 Hz | escolha | declarado | médio |
| Atmosfera | ISA nível do mar | cenário | declarado | baixo |
| Objetivo de trim | `MAX_MARGIN` | escolha de estudo | declarado | alto |

⚠ **O atraso é varrido, nunca usado como fato.** Nenhum fabricante publica resposta de
pequeno sinal, então o parâmetro entra como eixo e sai como fronteira.

## 4. Configuração avaliada

| ID | Família | Propulsores | Massa | Centro de massa | Estado |
|---|---|---:|---:|---|---|
| A | bocais vetorizados compactos | 7 | 115 kg | x = 0,1575 m | candidata |

⚠ A família E não foi varrida separadamente: no modelo atual ela é a família A mais
nove quilos, porque o canal elétrico rápido entra como massa e **não** como
autoridade. As duas só se separam quando esse canal for modelado.

## 5. Critério de sucesso e falha, definidos antes de rodar

**Sucesso:** o erro angular entra em três graus e **permanece** por um segundo. O tempo
de retenção existe porque uma trajetória que cruza a região alvo a caminho da
divergência seria contada como sucesso sem ele.

| Código | Significado no modelo |
|---|---|
| `captured` | entrou e ficou na região alvo |
| `horizon_reached` | acabou o tempo sem falhar e sem capturar. **Não é sucesso** |
| `attitude_limit_exceeded` | passou de 60 graus |
| `altitude_loss_limit` | perdeu mais de 3 m |
| `wrench_unattainable` | resíduo normalizado acima de 0,35 por mais de 0,5 s |
| `allocator_infeasible` | nenhum atuador disponível |
| `numerical_failure` | estado não finito. **Não interpretar como física** |

## 6. Modelo matemático

Atuador, conforme ADR-005:

```
T_ss  = clip( u(t - T_d) , T_min , T_max )
Tdot  = clip( (T_ss - T)/tau , -Tdot_desce , +Tdot_sobe )
```

Alocador, conforme ADR-003 e ADR-004, com a caixa do **horizonte**:

```
min_T  || S (W T - w) ||²    s.a.   T em [ max(T_min, T_i - Tdot_desce·Ha) ,
                                           min(T_max, T_i + Tdot_sobe·Ha) ]
S = diag(1, 1, 1, 1/L, 1/L, 1/L),  L = maior braço da geometria
```

Onde cada coisa vive:

- **atraso de transporte**: linha de histórico causal, interpolação cúbica, consulta a
  instante futuro é recusada;
- **retenção de ordem zero**: o comando do alocador fica retido entre tiques de 10 ms;
- **saturação**: de comando dentro do alocador, de estado por projeção após o passo;
- **projeção de estado**: depois do passo, com registro, nunca como guarda;
- **eventos**: o tique do controlador é evento agendado, e o passo nunca cruza a
  fronteira discreta;
- **integrador**: Runge-Kutta de quarta ordem, passo máximo 2 ms, quaternion
  renormalizado a cada passo.

## 7. Verificação

| Verificação | Resultado | Critério |
|---|---|---|
| Forma fechada do atuador contra integração da própria lei | passou | erro relativo < 2e-4, 7 casos |
| Interpolação causal da linha de atraso | passou | erro < 1e-6 em sinal suave |
| Recusa de consulta a comando futuro | passou | levanta erro |
| Recusa de atraso menor que o passo | passou | levanta erro |
| Alocador nunca comanda fora da caixa | passou | verificado célula a célula |
| Empuxo nunca sai da faixa física | passou | verificado na trajetória |
| Margem dinâmica menor que a estática | passou | razão > 2 nos três eixos |
| Reprodutibilidade | passou | saída idêntica, sessão `resultados` do nox |

600 testes na suíte; lint e formatação cobrem `src/`, `tests/`, `tools/` e `noxfile.py`.

## 8. Resultados

Tabela completa em `docs/resultados/experimento-4-atraso.txt`.

### Orçamento de momento: as duas margens do ADR-004

| Eixo | Margem estática | No horizonte de 0,2 s | Razão |
|---|---:|---:|---:|
| Rolagem | 128,5 N·m | 20,1 N·m | 6,4× |
| Arfagem | 64,1 N·m | 12,6 N·m | 5,1× |
| Guinada | 17,1 N·m | 2,8 N·m | 6,1× |

### Fronteira de atraso, banda fixa em 1,05 rad/s

| Constante de tempo | Maior atraso que ainda recupera |
|---:|---:|
| 0,10 a 0,35 s | 0,40 s ou mais |
| 0,50 a 0,80 s | 0,30 s |
| 1,20 s | 0,20 s |
| 1,80 s | 0,10 s |

Modo de falha além da fronteira: `attitude_limit_exceeded` para constante moderada,
`wrench_unattainable` para constante grande.

### O resultado que reordena o projeto

| Banda exigida | Período | Maior atraso tolerado |
|---:|---:|---:|
| 0,50 rad/s | 12,6 s | 0,40 s |
| 1,05 rad/s | 6,0 s | 0,40 s |
| 2,00 rad/s | 3,1 s | 0,15 s |
| 3,00 rad/s | 2,1 s | 0,02 s |
| 4,50 rad/s | 1,4 s | nenhum |

### Dependência da condição

| Perturbação | Maior atraso, com constante de 0,35 s |
|---:|---:|
| 5 graus | 0,30 s |
| 10 graus | 0,40 s |
| 20 graus | 0,30 s |
| 30 graus | 0,20 s |

O limite de rampa **não ativou** em nenhuma célula da faixa de 40 a 400 N/s, porque a
banda utilizável é baixa e os comandos são mansos.

## 9. Conclusão limitada

> Sob a geometria A, com massa, centro de massa, inércia, missão e limites declarados,
> e sob a dinâmica reduzida e o modelo de atuador assumido, a arquitetura recupera de
> uma perturbação de dez graus com atrasos de até 0,40 s enquanto a constante de tempo
> ficar abaixo de 0,5 s, e a fronteira cai para 0,10 s com constante de 1,8 s.
>
> E, dentro da faixa varrida, **o atraso não é o parâmetro limitante desta
> arquitetura**. A autoridade de curto prazo limita a banda utilizável a cerca de
> 1,5 rad/s, um período de quatro segundos, e qualquer atraso da faixa é fração pequena
> disso. Exigir banda acima de 3 rad/s derruba a tolerância a atraso para 0,02 s e
> acima de 4,5 rad/s nenhum atraso da faixa recupera.

**Não é permitido concluir:** que a arquitetura funciona; que uma turbina serve; que um
piloto conseguiria; que há estabilidade fora da faixa varrida.

## 10. Incertezas e bloqueios

| Incógnita | Por que bloqueia | Quem ataca |
|---|---|---|
| Constante de pequeno sinal real | é o eixo da varredura, não um valor | pedido ao fabricante |
| Rampa real | decide a margem de curto prazo | pedido ao fabricante |
| Perda de instalação | altera empuxo e margem | deck de propulsão |
| Massa e inércia reais | contaminam a fronteira | CAD, **medido: efeito baixo** |
| Piloto humano no laço | atraso humano é maior que o do atuador | marco 6 |
| Falha de propulsor em voo | trim pós-falha não existe nesta geometria | marco 7 |

## 11. Reprodução

```bash
nox
./.venv/Scripts/python.exe tools/refresh_results.py
git diff --exit-code -- docs/resultados/
./.venv/Scripts/python.exe tools/delay_sweep.py
```

## 12. Mudanças desde o relatório anterior

**Bug encontrado, e ele apontava para a conclusão errada.** A primeira versão do
controlador pedia a força que cancela o vetor peso inteiro. Com o tronco inclinado esse
pedido tem componente lateral, e nesta geometria força lateral e momento de rolagem são
quase proporcionais, o acoplamento do [[Experimento 1 - Geometria de autoridade]]. O
pedido de força arrastava momento junto, e uma perturbação de cinco graus excedia vinte
e três antes de voltar. Sem investigar, isso teria virado "a arquitetura é instável".

**Hipótese removida.** A banda do controlador era escolhida a olho em 6 rad/s. Ganho a
olho transforma limite de arquitetura em falha de sintonia, e as duas exigem correções
opostas. A banda passou a ser derivada da autoridade medida.

**Vício de experimento, corrigido antes de publicar número.** A banda seguia o envelope
de cada célula, então tornar o atuador mais lento também tornava o controlador mais
manso, e a fronteira media a adaptatividade do controlador em vez da tolerância da
planta. A banda agora é fixa na varredura.

**Teste novo:** `test_recupera_sem_sobressinal_com_forca_so_no_eixo_do_corpo` prende a
correção da política de força; o pico não pode passar da perturbação inicial.

**Efeito nos números:** com a política antiga, a fronteira de atraso teria aparecido
muito mais apertada, e a causa teria sido atribuída ao atuador em vez ao acoplamento da
geometria.
