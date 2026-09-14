# Hero Atlas — Especificação técnica

**Documento de auditoria.** Estado em 2026-09-12. Repositório:
`https://github.com/Lanzinhu/hero-atlas`

Laboratório virtual de dinâmica e controle para um traje de propulsão pessoal. O
entregável é o simulador e o estudo de viabilidade. Sem hardware. Custo zero. Python.

---

## 0. Como ler este documento

Ele não é um relatório de sucesso. É o mapa do que foi construído, do que foi assumido,
do que foi medido e **do que a evidência não permite afirmar**.

Três marcas aparecem ao longo do texto:

- **medido** — saiu de um cálculo do simulador, com teste que o prende;
- **assumido** — entrou como hipótese declarada, e o resultado herda a incerteza;
- **desconhecido** — não há dado, e o código **recusa** inventar um.

⚠ **Nada aqui representa hardware.** Toda geometria é plausível e não medida. Todo
consumo é de catálogo extrapolado. Nenhuma tecnologia de propulsão foi selecionada, e a
seleção é estruturalmente impossível no estágio atual, por construção do código.

---

## 1. A pergunta do projeto

```
R = { (τ_atuador, τ_humano, K_humano, Ṫ_max, q_braços, m, r_cg) :
      estável sobre o envelope de cenários declarado }
```

E quais variáveis encolhem essa região até ela desaparecer. **Descobrir que a região é
estreita ou vazia é sucesso**: o projeto encontrou a barreira antes de alguém gastar
dinheiro ou sobrancelhas.

---

## 2. Estado por marco

| Marco | Entrega | Estado |
|---|---|---|
| 0 | Unidades, procedência, agregação de massa, eventos, telemetria | entregue |
| 1 | Envelope de massa e empuxo, autonomia | entregue |
| 1b | Energia por missão, elétrico contra combustível | entregue |
| 2 | Trim com momento do peso, mapa de autoridade | entregue |
| 3 | Dinâmica seis graus de liberdade, laço fechado | **entregue** |
| 4 | Controlador e alocação por efetividade prevista | parcial: existe, não foi varrido |
| 5 | Varreduras de sensibilidade | parcial: atraso e rampa feitos |
| 6 | Piloto humano, região R completa | não começou |
| 7 | Falha, detecção, contingência, região de captura | não começou |
| 8 | CAD e estrutura | requisitos levantados, sem CAD |

**600 testes.** Portão de lint e formatação sobre `src/`, `tests/`, `tools/` e
`noxfile.py`, mais a sessão `resultados` do nox, que regenera `docs/resultados/` e falha
se o Git acusar diferença.

---

## 3. Arquitetura do código

O núcleo importa **apenas** NumPy, SciPy e pydantic, verificado por varredura de árvore
sintática que inclui importes dinâmicos e blocos `try/except ImportError`.

```
src/hero_atlas/
  units.py                 SI no núcleo; dimensão e tipo semântico na fronteira
  verdict.py               satisfeito, violado, indeterminado
  provenance.py            o que a fonte mede, declara, calcula ou infere
  model_status.py          carimbo que recusa saída condicional sem marca
  propulsion_family.py     ramos coexistem; "aprovado" não é expressável

  airframe/mass_properties agregação com rotação de tensor e eixos paralelos
  airframe/geometry        bocais com posição, direção, limites e torque de reação

  environment/atmosphere   atmosfera padrão sem dupla contagem

  analysis/envelope        força requerida separada de capacidade de entrega
  analysis/energy          turbina integrada; elétrico com máximo interior em bateria
  analysis/mission_energy  energia por missão, trim como porteiro
  analysis/trim            equilíbrio vetorial com o momento do peso
  analysis/authority       posto, carga interna, janela de centro de massa
  analysis/control_budget  as duas margens do ADR-004, medidas
  analysis/funnel          funil de arquiteturas, oito filtros
  analysis/requirements    o deck produz requisito, não estimativa

  propulsion/actuator      atraso, constante de tempo, rampa, saturação
  control/allocator        wrench para comando, com a caixa do horizonte
  control/attitude         controlador amostrado, domínio de tempo declarado

  dynamics/quaternion      convenção fixada e verificada por equivariância
  dynamics/rigid_body      corpo rígido, rota reduzida do ADR-001
  dynamics/integrators     Runge-Kutta de quarta ordem, renormalização de atitude

  sim/events               agenda de eventos e limite de passo
  sim/closed_loop          a ordem correta entre controlador, alocador e planta
  io/telemetry             evento de alocação com quatro modos de falha
```

---

## 4. Decisões de arquitetura

| ADR | Decisão |
|---|---|
| 001 | Ponto de referência fixo no corpo; rota reduzida nos marcos 3 a 5, espacial completa a partir do 6 |
| 002 | Trim sobre o ponto de referência **inclui o momento do peso** |
| 003 | O alocador usa efetividade dinâmica prevista, **não comando como empuxo** |
| 004 | Duas margens de autoridade, estática e de curto prazo, ambas no relatório |
| 005 | Saturação e limite de rampa são **telemetria**, não guarda |
| 006 | Exploração de R em três fases, começando por sensibilidade unidimensional |
| 007 | Deck de propulsão instalada com incerteza correlacionada declarada |
| 008 | Ramos de propulsão coexistem; a seleção é **estruturalmente impossível** hoje |

Quatro regras operacionais: conservação com braços móveis só a partir do marco 6; trim
tem dois níveis de viabilidade; R explora parâmetros finitos e declarados, não uma
função de postura; resultado humano é sempre condicional.

---

## 5. Modelos matemáticos implementados

### 5.1 Alocação e trim

```
W = [ n_i ; (r_i − r_O) × n_i + c_i·n_i ]        matriz 6 × N

Σ T_i n_i + m R_BI g_I = 0
Σ (r_i − r_O) × T_i n_i + r_C/O × (m R_BI g_I) = 0
T_min ≤ T_i ≤ T_max
```

O termo `c_i·n_i` é o **torque de reação** do propulsor: zero em jato, não zero em
rotor. Sem ele, um anel plano de rotores tem a linha de guinada identicamente nula.

### 5.2 Atuador

```
T_ss  = clip( u(t − T_d), T_min, T_max )
Tdot  = clip( (T_ss − T)/τ, −Ṫ↓max, +Ṫ↑max )
```

Tempo de resposta a degrau, em forma fechada, com duas fases e cruzamento em
`|e| = Ṫmax·τ`:

```
D ≤ e_c        →  t = −τ ln(1 − f)
e_f ≥ e_c      →  t = f·D/Ṫmax
caso contrário →  t = (D − e_c)/Ṫmax + τ ln(e_c/e_f)
```

Conferida contra integração numérica da própria lei: erro relativo abaixo de 3e-6.

### 5.3 Dinâmica, rota reduzida

```
I_C ω̇ + ω × (I_C ω) = M_C
a_C,I = R_IB F_B / m + g_I
a_O,I = a_C,I − R_IB ( ω̇ × d + ω × (ω × d) )
q̇ = ½ q ⊗ (0, ω_B)
```

O estado integra o **ponto de referência**; o centro é derivado, nunca integrado.

### 5.4 Energia

```
Turbina:  ṁ = TSFC·ΣT_i ;  t = ln( m₀/(m₀ − combustível) ) / k,  k = TSFC·g/cos θ
Elétrico: P = Σ T_i^1.5 / sqrt(2ρA_i) / (FM·η_motor·η_inv) + P_aux
          E_útil = m_bat · e · η_pack · DoD
          ótimo sem carga auxiliar:  m_bat = 2 · m_seco
```

A potência é somada **rotor a rotor**, não agregada: a potência induzida é convexa em
empuxo e a forma agregada subestima sempre que o trim distribui desigual.

### 5.5 Controle

```
Atitude:  M_C = I ( −ω_n²·2·e_vec − 2ζω_n·ω )          amostrado, sem integral
Altitude: a_z = ω_z²·e + (ω_z²/T_i)·∫e − 2ζ_zω_z·ẇ     soma discreta
Força:    F_B = [0, 0, −m(g + a_z)/cos θ]              **só no eixo do corpo**
Alocador: min ‖S(WT − w)‖² sujeito à caixa do horizonte
```

⚠ A força é só no eixo vertical do corpo. Pedir a força que cancela o vetor peso
inteiro tem componente lateral com o tronco inclinado, e nesta geometria força lateral e
momento de rolagem são quase proporcionais: o controlador de altitude passaria a brigar
com o de atitude.

---

## 6. Resultados, por experimento

Todos versionados em `docs/resultados/`, regenerados por `tools/refresh_results.py`.

### Experimento 1 — Geometria de autoridade

Onze arquiteturas, nove eliminadas. O filtro decisivo é **rolagem pura**: um centro
deslocado lateralmente exige momento de rolagem sem força lateral, o que exige três
graus de liberdade antissimétricos. Dois pares de bocais dão dois.

⚠ **Corrigido durante o trabalho:** a afirmação de que os pares precisam diferir em
envergadura, altura **e** inclinação estava errada. Teste mostrou que inclinação sozinha
basta e que altura mais envergadura juntas não bastam.

### Experimento 2 — Energia armazenada sob massa seca e geometria fixadas

| Massa embarcada | Combustão | Elétrico |
|---:|---:|---:|
| 10 kg | 2,46 min | 0,50 min |
| 20 kg | 4,83 min | 1,07 min |
| 50 kg | 10,62 min | 2,21 min |

Por quilo: combustão 14,7 s/kg, elétrico 3,1 s/kg.

O ramo elétrico **fecha trim e voa**. O que o limita são dois tetos de massa: o ótimo de
bateria pede 190 kg, a geometria equilibra até 208,1 kg brutos ou 113,1 kg de bateria, e
exigir 0,5 m/s² de subida corta para 103,0 kg. Melhor caso elétrico: **2,98 min**, que a
combustão alcança com **12,0 kg** de combustível.

⚠ Isto compara **armazenamento de energia**, não arquiteturas completas: a massa seca é
mantida igual entre famílias, e na prática não é.

### Experimento 3 — Funil de arquiteturas

Seis famílias, oito filtros estáticos do mais barato ao mais caro, parando na primeira
reprovação.

| | Família | Resultado |
|---|---|---|
| A | bocais vetorizados compactos | passa nos oito |
| B | rotores compactos, 4 unidades | morre em posto, 4 de 6 |
| C | rotores em estrutura lateral | morre em centro de massa lateral, 0,4 cm |
| D | estrutura larga, 4 rotores grandes | morre em posto, 4 de 6 |
| E | turbina com buffer elétrico | passa nos oito |
| F | híbrido série | morre em centro de massa lateral, 0,3 cm |

⚠ As mortes de C e F contam como **não julgadas**. O filtro de centro de massa lateral
exige equilíbrio sem inclinar o tronco, que é requisito de traje; multirrotor responde
inclinando o veículo.

### Experimento 4 — Tolerância a atraso e rampa

**As duas margens do ADR-004, medidas:**

| Eixo | Estática | No horizonte 0,2 s | Razão |
|---|---:|---:|---:|
| Rolagem | 128,5 N·m | 20,1 N·m | 6,4× |
| Arfagem | 64,1 N·m | 12,6 N·m | 5,1× |
| Guinada | 17,1 N·m | 2,8 N·m | 6,1× |

**O resultado que reordena o projeto:**

| Banda exigida | Período | Maior atraso tolerado |
|---:|---:|---:|
| 1,05 rad/s | 6,0 s | 0,40 s |
| 2,00 rad/s | 3,1 s | 0,15 s |
| 3,00 rad/s | 2,1 s | 0,02 s |
| 4,50 rad/s | 1,4 s | nenhum |

**A arquitetura tolera atraso porque é obrigada a ser lenta.** A autoridade de curto
prazo permite cerca de 1,5 rad/s. O parâmetro limitante **não é o atraso**: é o momento
disponível no horizonte.

### Experimento 5 — Triagem de turbinas contra especificação parcial

⚠ **Nenhuma turbina foi validada nem selecionada.** O experimento confronta dados
publicados contra a parte **estática** da especificação e mostra que a parte dinâmica
continua indisponível. Triagem contra especificação parcial e condicional não é seleção.

| Turbina | Empuxo máx | Massa | Fração do teto no trim | Momento no horizonte |
|---|---:|---:|---:|---:|
| JetCat P400-PRO-LN | 425 N | 4,01 kg | 0,54 | 20,1 N·m |
| Kingtech K-260G4 | 255 N | 2,20 kg | 0,82 | 20,1 N·m |
| Kingtech K-210G4 | 206 N | 1,74 kg | **0,99** | **0,9 N·m** |

A K-210G4 é **triada fora** por autoridade, não por empuxo: opera a 99% do teto no trim e
não sobra margem para momento. As outras duas passam a triagem estática e permanecem
**não avaliadas** nos critérios dinâmicos.

**Quatro dos oito requisitos não podem ser verificados** com dado publicado, e são
exatamente os que dependem de dinâmica: momento no horizonte, banda alcançável,
tolerância a atraso e estabilidade.

Verificado na página do fabricante da JetCat em 2026-09-12: **nenhuma especificação de
tempo, resposta, constante ou taxa aparece**.

⚠ **Inferência de engenharia, não dado de catálogo.** A literatura de operação descreve
que a unidade de controle limita a taxa de combustível deliberadamente, para não afogar a
câmara na aceleração nem apagar a chama na desaceleração. Daí **não** se segue que a
rampa seja ajustável.

Ela pode estar presa a limites duros de estabilidade de chama, temperatura de entrada de
turbina, rotação máxima, inércia do conjunto rotativo, margem de surge do compressor,
proteção interna da unidade de controle ou segurança do equipamento. A formulação que o
projeto sustenta é: **a rampa pode depender de calibração e lógica da unidade de
controle, e qualquer possibilidade de alteração permanece desconhecida até confirmação
documentada do fabricante.**

### Experimento 6 — Triagem estrutural e de ressonância

**Espectro de excitação**, com a JetCat de 30.000 a 98.000 rotações por minuto:

| Fonte | Faixa |
|---|---|
| Rotação do eixo | 500 a 1.633 Hz |
| Segundo harmônico | 1.000 a 3.267 Hz |
| Passagem de pá (12 pás, **hipótese**) | 6.000 a 19.600 Hz |
| Tique do controlador | 100 Hz |
| Banda de atitude | 0,24 Hz |

Requisito: nenhum modo estrutural pode cair nessas bandas, e a faixa é varrida
continuamente, então não há "passar rápido pela ressonância".

**Cargas de fixação:** cada berço suporta o **teto** do propulsor, não o valor de trim.
Maior momento de fixação no teto: **178 N·m**, em flexão, com o piloto do outro lado.

**Quanto a incerteza escalar de inércia custa:** a fronteira de atraso foi refeita com o
tensor inteiro escalado de 0,7× a 1,6×, e o resultado se move de 0,40 s para 0,30 s
apenas no extremo inferior.

⚠ **O que isso demonstra, e só isso:** para esta geometria, este controlador, esta
missão, esta inércia nominal e esta faixa de escala, a incerteza **escalar** de inércia
não dominou a fronteira de atraso encontrada.

⚠ **O que isso não demonstra.** Nada foi dito sobre massa seca por família, posição real
do centro de massa, produtos de inércia fora da diagonal, braços de alavanca reais,
interferência geométrica entre bocais e corpo, frequências naturais, rigidez, modos
estruturais, ou massa e fixação de propulsores reais. Uma versão anterior deste
documento concluía daqui que "o CAD pode esperar", e a frase era ampla demais: o teste
cobria uma variável escalar e a conclusão falava do projeto inteiro.

---

## 7. O que o código recusa fazer

Quatro recusas estruturais, todas com teste que as prende.

| Recusa | Onde | Por quê |
|---|---|---|
| Emitir resultado condicional sem carimbo | `model_status.assert_stamped` | família paramétrica ganha aparência de medição |
| Calcular resposta de pequeno sinal sem dado | `UnknownSmallStepDynamicsError` | o número não é publicado; extrapolar seria inventar |
| Expressar "tecnologia aprovada" | `FamilyStatus` não tem o valor | o projeto já escreveu isso uma vez, sem base |
| Aceitar fase de missão que nunca executa | `MissionProfile` | perfil parecia operacional e não era |

---

## 8. Erros encontrados e corrigidos

Esta seção existe porque o padrão se repete: **uma frase intuitiva que, implementada
literalmente, introduz erro sistemático exatamente na análise mais sensível.**

| Erro | Efeito | Como apareceu |
|---|---|---|
| Massa da bateria fora da massa bruta | autonomia elétrica inflada em 37% | confronto com forma fechada |
| Força cancelando o vetor peso | perturbação de 5° excedia 23° | trajetória inspecionada |
| Banda escolhida a olho em 6 rad/s | limite de arquitetura virava falha de sintonia | rampa em 0% na falha |
| Banda seguindo o envelope da célula | media adaptatividade, não tolerância | inspeção do desenho |
| Linha de guinada sem torque de reação | 4 famílias de rotor eliminadas por engano | 4 mortes idênticas |
| "Autonomia elétrica é função da área" | contradizia a assinatura da própria função | revisão externa |
| "16,7 kgf por bocal" | era massa dividida por sete | revisão externa |
| Híbrido série eliminado | confundia energia com potência | revisão externa |
| Código morto de piso e teto | aparentava proteção inexistente | teste falhando |

**Três desses erros apontavam para a conclusão que o projeto estava prestes a tirar.**
O bug da bateria favorecia descartar o elétrico; a política de força teria virado "a
arquitetura é instável"; a banda a olho teria virado "o atuador é lento demais".

---

## 9. Incógnitas bloqueantes

| Incógnita | Estado | Quem ataca |
|---|---|---|
| Constante de tempo de pequeno sinal | **desconhecido**, verificado no fabricante | pedido ao fabricante |
| Rampa máxima de empuxo | **desconhecido** | pedido ao fabricante |
| Atraso de transporte do comando | **desconhecido** | pedido ao fabricante |
| Empuxo mínimo estável em voo | **desconhecido** | pedido ao fabricante |
| Consumo específico em carga parcial | **desconhecido** | deck de propulsão |
| Perda de instalação em arranjo vestível | **sem base publicada** | deck de propulsão |
| Massa seca por família | assumida em bloco | CAD conceitual |
| Atraso e ganho humanos | não modelados | marco 6 |
| Trim pós-falha | **não existe** nesta geometria | marco 7 |
| Aerodinâmica do corpo com jatos ao lado | não modelada | incerteza paramétrica larga |

**Nenhum ramo de propulsão está aprovado.** O veredito de seleção devolve
`INDETERMINATE` por construção: três ramos abertos, dezesseis incógnitas bloqueantes.

---

## 10. Conclusões permitidas hoje

Sob geometria plausível e não medida, massa e inércia estimadas, consumo de catálogo
extrapolado, dinâmica reduzida e modelo de atuador assumido:

1. A conta de massa e empuxo fecha para a família A.
2. Das onze geometrias varridas, duas preservam autoridade de rolagem pura.
3. Das seis famílias de arquitetura, duas passam os oito filtros estáticos, e duas
   morreram em um critério que não se aplica a elas.
4. Com a mesma massa embarcada, combustão entrega cerca de cinco vezes mais tempo de
   pairado que elétrico, e o elétrico satura em três minutos por teto de massa.
5. A margem de autoridade de curto prazo é cinco a seis vezes menor que a estática.
6. O parâmetro limitante desta arquitetura não é o atraso: é o momento disponível no
   horizonte.
7. Quatro dos oito requisitos de propulsão não podem ser verificados com dado
   publicado, e as turbinas foram **triadas**, nunca selecionadas.

**Não é permitido concluir** que a arquitetura funciona, que uma turbina serve, que um
piloto conseguiria pilotar, ou que há estabilidade fora da faixa varrida.

---

## 10b. Procedência das fontes externas

Registros em `docs/sources/`, com origem, data de consulta, valores transcritos,
derivações feitas pelo projeto e **o que a fonte não publica**.

⚠ São **transcrições**, não cópias arquivadas do original, e portanto ainda não
satisfazem o ADR-007. A diferença: com cópia arquivada, uma alteração silenciosa na
página do fabricante seria detectável; com transcrição, não é.

| Nível de evidência | Estado |
|---|---|
| número citado sem origem | eliminado do projeto |
| transcrição com origem e data | **onde estamos** |
| cópia do documento com hash | pendente |
| medição própria em bancada | fora do escopo |

## 11. Reprodução

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
nox
./.venv/Scripts/python.exe tools/refresh_results.py
git diff --exit-code -- docs/resultados/
```

Experimentos individuais em `tools/`: `sweep_geometry`, `compare_energy_architectures`,
`funnel`, `delay_sweep`, `turbine_match`, `structure_screen`, `dump_geometry_detail`.

---

## 11b. Guia de modelagem

`docs/GUIA-MODELAGEM.md` é autocontido e destinado a quem vai abrir o FreeCAD: unidades,
referencial, tabela mestra de coordenadas, passo a passo com o portão de envelope,
dimensionamento preliminar, exportação, verificação e lista de checagem.

⚠ Ele traz uma correção relevante que não estava nos experimentos 1 a 4: aqueles usaram
uma **classe genérica de 35 kgf por bocal**, que nenhuma turbina real da lista atinge. A
K-260G4 dá 26 kgf, e com ela os números mudam:

| Grandeza | Classe genérica | K-260G4 real |
|---|---:|---:|
| Empuxo instalado | 245 kgf | 182 kgf |
| Massa bruta máxima com trim | 208,1 kg | **154,6 kg** |
| Folga superior a 127,4 kg | 38,8% | **17,6%** |
| Momento de fixação no teto | 178 N·m | 132 N·m |

A folga de massa cai de 80,7 kg para **27,2 kg**, e o orçamento de 12 kg de estrutura
passa a ser o número que decide se a conta fecha.

## 11c. Manequim do piloto, e dois portões reprovados

Um manequim articulado de 14 segmentos, 80 kg, em duas poses, gerado por
`tools/freecad_mannequin.py` e versionado em `docs/decks/manequim/`.

| O quê | Estado |
|---|---|
| Frações de massa por segmento | de Leva (1996), **não verificadas** em documento legível |
| Centro e inércia de cada segmento | geometria do primitivo, densidade uniforme **assumida** |
| Validação | só no corpo inteiro, contra Matsuo et al. (1995), **verificado** |

Na pose anatômica, os momentos transversais dão 13,23 e 12,31 kg·m², contra 14,02 e
13,00 da regressão de Matsuo extrapolada para 1,75 m e 80 kg. ⚠ É banda de sanidade,
não validação: a regressão é de adolescentes deitados, e o resumo não define qual eixo
é qual.

⚠ **Incidente de fonte.** Um resumo automático de busca apresentou valores de inércia
de adultos em pé e os atribuiu a um artigo que, lido diretamente, não contém inércia
nenhuma. Os números foram descartados. Registro em
`docs/sources/de-leva-1996-segmentos-NAO-VERIFICADO.md`.

### O traje inteiro, somado

`tools/suit_mass_budget.py`, resultado em `docs/resultados/orcamento-traje.txt`.

| Grandeza | Modelado | Assumido até hoje | Razão |
|---|---:|---:|---:|
| Massa | 127,40 kg | 115,0 kg | — |
| Centro de massa, x | **+1,0 mm** | +157,5 mm | — |
| Ixx | 23,85 kg·m² | 32,20 kg·m² | 0,74× |
| Iyy | 22,72 kg·m² | 32,20 kg·m² | 0,71× |
| Izz, guinada | **7,93 kg·m²** | 2,30 kg·m² | **3,45×** |
| Ixz | +1,08 kg·m² | 0 | — |

⚠ A inércia de guinada modelada está **fora** da faixa da checagem de sensibilidade do
experimento 6, que escalou os três eixos juntos até 1,6×. E o experimento 4 usou tensor
diagonal, sem o produto de inércia.

### Primeiro portão reprovado: o trim não fecha

| Classe de empuxo | Janela viável de centro, x | Centro modelado | Falta |
|---|---:|---:|---:|
| Genérica 35 kgf | +115 a +210 mm | +1 mm | 114 mm |
| K-260G4, 26 kgf | +145 a +210 mm | +1 mm | **144 mm** |

Corrigir só movendo o tanque de 20 kg exigiria levá-lo **917 mm para frente**, para a
frente do peito. Corrigir com lastro exigiria **105 kg** no bocal dianteiro.

Isso não é ajuste fino: é **incompatibilidade entre a geometria A e um tanque nas
costas**. ⚠ Reprova *este* arranjo de massa, com posições declaradas no guia, não
otimizadas. Não prova que nenhum arranjo funciona.

### Segundo portão reprovado: a turbina dorsal está dentro das costas

`tools/freecad_envelope_gate.py`, resultado em `docs/resultados/portao-envelope.txt`.

| Turbina | Folga real | Envelope de 180 mm invade |
|---|---:|---|
| seis de braço | 90 a 182 mm | não |
| **dorsal** | **0 mm** | **tronco 2.090 cm³, cabeça 35 cm³** |

O bocal dorsal está a 150 mm atrás da origem, o raio da turbina é 60 mm, e a face das
costas fica a 120 mm. A tabela de coordenadas saiu de uma otimização de autoridade de
controle que **nunca perguntou onde está o corpo**, e o guia de modelagem avisava que
este portão podia reprovar.

### Hipótese registrada, não testada

Recuar o bocal dorsal resolveria a colisão **e** puxaria a janela de trim para trás, na
direção do centro modelado. As duas reprovações podem ter a mesma correção.

⚠ **A tabela de coordenadas não foi alterada.** O guia manda parar e avisar quando um
portão reprova. Testar a hipótese é o próximo passo, e exige rodar o funil de novo com
restrição de envelope.

## 12. O próximo passo

Não é escolher turbina. É **pedir quatro números** a um fabricante, porque nenhum deles
é publicado e todos os quatro decidem:

1. constante de tempo a degrau pequeno perto do ponto de operação;
2. taxa máxima de variação de empuxo, subindo e descendo;
3. atraso entre comando e início da resposta;
4. empuxo mínimo estável em voo, não em bancada.

Com esses quatro, os marcos 6 e 7 podem rodar. Sem eles, a região R permanece
indeterminada, e isso é a conclusão honesta do projeto até aqui.
