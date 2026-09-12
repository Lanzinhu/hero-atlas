---
tipo: experimento
id: EXP-002
estado: concluido
data: 2026-09-12
tags: [energia, missao, autonomia, propulsao]
---

# Experimento 2 — Energia armazenada sob massa seca e geometria fixadas

⚠ **O título importa.** Isto **não** é "comparação entre arquitetura elétrica e
arquitetura a combustão". É comparação de **armazenamento de energia** com massa
seca, geometria, piloto, reserva e missão fixados. A diferença está na seção
[[#O que este experimento não compara]].

`python tools/compare_energy_architectures.py`

## A pergunta

Com a **mesma massa embarcada de energia**, a mesma geometria, a mesma massa seca, a
mesma reserva e a mesma missão, quanto tempo cada arquitetura entrega, e quanto custa
sair do chão?

A comparação errada, que este experimento evita, é "10 litros de combustível contra
uma bateria qualquer". Só massa embarcada igual torna a comparação justa.

## Três perguntas que "autonomia" funde

| Pergunta | O que é calculado |
|---|---|
| Consegue sair do chão? | Existe `T` dentro dos limites que produz o wrench com a aceleração pedida. **Não** é "empuxo total maior que o peso" |
| Quanto custa sair do chão? | Energia ou combustível integrado na trajetória declarada |
| Quanto tempo fica no ar? | Energia útil embarcada dividida pelo consumo, até a reserva |

⚠ Sair do chão é barato. **Sustentar massa no ar é o que custa.** Os três segundos de
arranque consomem menos de 10 por cento do que consomem os minutos de pairado.

## Configuração

Massa seca 95 kg sem energia. Geometria de sete bocais, posto 6, a única do
[[Experimento 1 - Geometria de autoridade]] com rolagem pura. Missão de 3 s de
arranque a 0,5 m/s², 10 s de subida, pairado até a reserva de 20 por cento.

⚠ Geometria **plausível, não medida**. Consumo específico de catálogo extrapolado
para pairado. Energia específica de pack declarada, sem cópia arquivada.

## Resultado

| Massa embarcada | Combustão | Elétrico | Razão |
|---|---|---|---|
| 5 kg | 1,17 min | 0,16 min | 7,4 |
| 10 kg | 2,46 min | 0,50 min | 4,9 |
| 20 kg | 4,83 min | 1,07 min | 4,5 |
| 30 kg | 6,96 min | 1,54 min | 4,5 |
| 50 kg | 10,62 min | 2,21 min | 4,8 |

Por quilo embarcado: combustão entrega cerca de 14,7 s/kg, elétrico cerca de 3,1 s/kg.

## O que este experimento não compara

Manter a massa seca igual entre as famílias é o que torna a comparação controlada, e é
também o que a limita. Na prática as massas secas **não** são iguais:

| Família | Massa que só ela carrega |
|---|---|
| Elétrico distribuído | rotores, motores, inversores, barramento, gerenciamento de bateria, cabeamento de alta corrente, estrutura de suporte |
| Turbina direta | microturbinas, unidade de controle, tanques, linhas, bombas, proteção térmica, estrutura |
| Híbrido série | gerador, eletrônica de potência, buffer, motores, cabos, tanque, controle térmico |
| Turbina com buffer | turbina, buffer, eletrônica, atuadores auxiliares, estrutura e proteção térmica |

Nenhuma dessas massas entrou no livro de massa ainda. Está registrado como incógnita
bloqueante nos quatro ramos de [[ADR-008 - Ramos de propulsao sem selecao]].

## O que a autonomia aqui mede, exatamente

**Tempo de pairado até a reserva, sem reserva separada de descida ou retorno.**

Uma versão anterior do perfil declarava uma fase de descida depois do pairado aberto.
Essa fase **nunca executava**: o pairado aberto só termina quando a reserva acaba, e
nesse instante a missão encerra. O perfil parecia operacional e não era. Agora
`MissionProfile` **recusa** qualquer fase depois de uma fase aberta.

## O achado principal: o elétrico satura, não é impossível

O ramo elétrico **fecha trim e voa**. O que o limita não é diâmetro de rotor, e sim
**dois tetos de massa**, dos quais manda o menor:

| Grandeza | Valor |
|---|---|
| Empuxo instalado | 245 kgf |
| Maior massa bruta com trim de pairado | 208,1 kg |
| Bateria correspondente | 113,1 kg |
| Bateria que ainda **acelera** para cima a 0,5 m/s² | 103,0 kg |
| Bateria do ótimo irrestrito de autonomia | 190,0 kg |

O ótimo de bateria fica **fora** do que a geometria equilibra. E a massa que ainda
paira já não consegue acelerar: exigir subida corta mais 10 kg. Preso a isso, o melhor
caso elétrico é **2,98 min**, que a combustão alcança com **12,0 kg** de combustível.
Fator de **8,5** em massa embarcada.

Dobrar a área de disco leva o elétrico a 4,30 min; quadruplicar, a 6,17 min. Área
cresce com o quadrado da autonomia alvo, então é uma alavanca cara.

## O que isto corrige

⚠ Duas afirmações anteriores do projeto caíram aqui.

**"Autonomia elétrica é função da área, não da bateria"** era falsa, e contradizia a
assinatura da própria função. A afirmação correta é quantitativa: a autonomia tem
**máximo interior** em massa de bateria, com forma fechada `m_b = 2 · m_seco`.

⚠ E essa forma fechada é **referência analítica do modelo idealizado, não identidade
universal**. Ela supõe potência auxiliar nula, sem teto de trim, sem saturação e sem
fase de aceleração. Com carga auxiliar o ótimo **sobe**, e a forma para isso é
`optimal_battery_mass_with_auxiliary_kg`. Com o teto de trim ele **desce**, de 190 kg
para 103 kg, que é exatamente o achado desta página. Ver [[Autonomia e energia]].

**A eliminação do híbrido série** confundia energia com potência e foi retirada. Ver
[[ADR-008 - Ramos de propulsao sem selecao]].

## Conflito entre autonomia e folga de empuxo

O trim de menor empuxo minimiza consumo, que é o objetivo certo para autonomia. Mas
ele **encosta um par de bocais no teto**, então a folga superior de empuxo vai a zero
exatamente. Maximizar folga preserva capacidade de subir empuxo e gasta mais.

⚠ **A grandeza medida é `min_upper_thrust_headroom_ratio`, não a margem de wrench.**
Ela é `min_i (1 − T_i/T_i_max)`, e ignora `T_min`, a geometria da matriz de alocação,
as direções possíveis de variação, o wrench exigido e toda a autoridade dinâmica.

Zero aqui é **evidência de saturação local**: um bocal no teto só pode descer, então o
conjunto de variações admissíveis perdeu uma direção. Não é condição **suficiente** de
perda de autoridade, porque os outros bocais continuam podendo subir. E não é condição
**necessária**, porque uma geometria de posto deficiente perde direções de wrench com
todos os bocais longe do teto. Saturação e falta de posto são mecanismos distintos, e
esta grandeza só enxerga o primeiro.

A perda de um wrench específico tem que ser demonstrada pela margem de wrench ou pela
alocação sob restrições, nunca inferida daqui.

Autonomia e folga puxam para lados opostos, e a escolha é de projeto, não de solver.
Fixado em `test_trim_de_menor_consumo_gasta_toda_a_margem_de_controle`.

## Potência de barramento: faixa paramétrica, não especificação

Calculada pelo mesmo caminho do experimento, com trim geométrico e soma rotor a rotor:

| Massa bruta | Rotor a rotor | Escalar agregado |
|---|---|---|
| 120,0 kg | 113,4 kW | 101,3 kW |
| 150,0 kg | 150,7 kW | 142,8 kW |
| 208,1 kg | 242,8 kW | 235,5 kW |

A forma escalar subestima em até 12 por cento, porque a potência induzida é convexa em
empuxo e a forma agregada ignora a desigualdade que o trim produz.

⚠ **Não é requisito de gerador.** Dentro: potência induzida rotor a rotor, figura de
mérito, rendimento de motor e de inversor. Fora: perdas de barramento, rendimento do
gerador, buffer, potência auxiliar, derating térmico e margem de contingência. Cada um
desses **sobe** o requisito.

## Veredito de seleção

`INDETERMINATE`. Três ramos abertos, dezesseis incógnitas bloqueantes. A evidência de
hoje **restringe arquitetura, não seleciona tecnologia**.

## Verificação

A integração numérica da missão reproduz a forma fechada
`t = ln(m0/(m0−combustível))/k` de `turbine_endurance_s` dentro de 0,2 por cento, em
doze combinações de inclinação e reserva. Duas rotas independentes, mesmo número.
