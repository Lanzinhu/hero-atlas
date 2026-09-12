# Hero Atlas

Laboratório virtual para descobrir quais limites físicos e de controle tornam um traje de
propulsão pessoal controlável, marginal ou inevitavelmente instável.

**Não é** "simular um Homem de Ferro". O entregável é o simulador e o estudo de viabilidade.
Sem hardware. Custo zero. Python.

> ## ⚠ Estado epistemológico
>
> **Os parâmetros de propulsão instalada são paramétricos e não validados.** Sete dos oito grupos
> de parâmetro do deck não têm dado algum, e **nenhuma fonte está arquivada com hash**.
>
> Todo resultado deste repositório é **condicional à geometria e à família declarada de modelos**.
> Nada aqui representa hardware.
>
> **A dinâmica fechada ainda não foi implementada.** Os resultados atuais pertencem ao trim
> **estático** de uma geometria parametrizada e à integração de energia por cima dele. Nada aqui
> diz respeito a estabilidade, resposta ou pilotabilidade.
>
> **Nenhuma tecnologia de propulsão foi selecionada, e a seleção é estruturalmente impossível
> hoje.** Os resultados restringem arquitetura; não aprovam motor. Aprovar exigiria que a família
> de atraso e rampa sobrevivesse aos marcos 3 a 5. O vocabulário do projeto não tem valor de
> "aprovado": ver [`propulsion_family.py`](src/hero_atlas/propulsion_family.py) e o ADR-008.
>
> Isso não é ressalva de rodapé: é o resultado principal do levantamento de evidência até agora, e
> está codificado em [`model_status.py`](src/hero_atlas/model_status.py), que **recusa** emitir
> resultado condicional sem carimbo.

## Estado do projeto

**Onde estamos: marco 3 entregue, marco 4 parcial.** O laço fechado existe e roda:
controlador amostrado, alocador com horizonte, atuador com atraso e corpo rígido no
mesmo passo de integração.

📄 **[Especificação técnica completa](docs/ESPECIFICACAO.md)** — o documento de auditoria.
📐 **[Guia de modelagem](docs/GUIA-MODELAGEM.md)** — o que modelar em CAD, passo a passo, com todos os números.
🎓 **[Trilha de aprendizado](docs/APRENDER.md)** — a física do projeto em onze paradas, no código que já existe.
🔰 **[Primeiro CAD](docs/PRIMEIRO-CAD.md)** — nunca modelou nada? Comece aqui: três exercícios, uma hora.

| Marco | Entrega | Estado |
|---|---|---|
| 0 | Unidades, procedência, agregação de massa, eventos, telemetria | entregue |
| 1 | Envelope de massa e empuxo, autonomia | entregue |
| 1b | Energia por missão, elétrico contra combustível | entregue |
| 2 | Trim com momento do peso, mapa de autoridade | entregue |
| 3 | Dinâmica seis graus de liberdade, laço fechado | **entregue** |
| 4 | Controlador e alocação por efetividade prevista | parcial |
| 5 | Varreduras de sensibilidade | parcial: atraso e rampa |

Dentro do marco 3:

| Peça | Estado |
|---|---|
| Corpo rígido seis graus de liberdade | pronto, com Dzhanibekov e equivariância |
| Atuador com atraso, constante de tempo, rampa e saturação | pronto, forma fechada conferida |
| Agenda de eventos | pronto desde o marco 0 |
| **Os três no mesmo passo de integração** | **não** |

Três experimentos rodaram em cima do que já existe, todos **estáticos**:

| Experimento | Pergunta | Resultado |
|---|---|---|
| 1 | quais geometrias equilibram | 9 de 11 eliminadas |
| 2 | elétrico ou combustível, mesma massa embarcada | elétrico satura em 2,98 min |
| 3 | funil de seis famílias por oito filtros | 2 sobrevivem, 2 não julgadas |
| 4 | quanto atraso a arquitetura tolera | **o atraso não é o limitante** |
| 5 | turbinas reais contra a especificação | 4 de 8 requisitos não verificáveis |
| 6 | estrutura e ressonância, sem CAD | inércia estimada não é o gargalo |

O achado do experimento 4 reordena o projeto: a margem de autoridade de curto prazo é
**cinco a seis vezes menor** que a estática, o que limita a banda utilizável a cerca de
1,5 rad/s. A arquitetura tolera atraso porque é obrigada a ser lenta.

600 testes; o portão de lint e formatação cobre `src/`, `tests/`, `tools/` e `noxfile.py`,
e a sessão `resultados` do nox confere que `docs/resultados/` bate com o código.

## A pergunta

```
R = { (τ_atuador, τ_humano, K_humano, Ṫ_max, q_braços, m, r_cg) :
      estável sobre o envelope de cenários declarado }
```

E quais variáveis encolhem essa região até ela desaparecer. Descobrir que a região é estreita ou
vazia **é sucesso**: o projeto encontrou a barreira antes de alguém gastar dinheiro ou sobrancelhas.

## O que o marco 2 encontrou

Numa geometria de cinco propulsores **plausível, não medida**, sob pairado nivelado com geometria
congelada:

- A matriz de alocação tem **posto 4 de 6**, por duas causas distintas: nenhum bocal tem componente
  longitudinal, e os quatro bocais de braço compartilham a mesma razão entre momento de rolagem e
  força lateral.
- Um desvio lateral do centro de massa torna o equilíbrio **geometricamente** inatingível. Motor
  maior não resolve.
- Nenhuma perda única de propulsor admitiu trim naquele centro de massa.

O envelope escalar do marco 1 era **condição necessária de força vertical**, nunca previsão de
capacidade de voo.

### Experimento 1: nove de onze arquiteturas eliminadas

`python tools/sweep_geometry.py` varre onze variantes e mede posto, janela de centro de massa,
projeção vertical e tolerância a falha única.

O filtro decisivo é **rolagem pura**: um centro deslocado lateralmente exige momento de rolagem sem
força lateral, o que exige três graus de liberdade antissimétricos. Dois pares de bocais dão dois.

⚠ E contagem não basta: **três pares diferindo só em altura continuam falhando**. Precisam diferir
em envergadura, altura e inclinação. "Mais propulsores resolve" é falso; propulsores mais **diversos**
resolve.

Duas variantes sobrevivem, e aparece um conflito: a geometria de maior autoridade tolera **zero**
falhas, enquanto a de maior redundância não tem rolagem pura.

### Experimento 2: energia armazenada sob massa seca e geometria fixadas

`python tools/compare_energy_architectures.py` roda a mesma missão com a **mesma massa
embarcada**: mesma geometria, mesma massa seca, mesma reserva.

⚠ **Não é comparação entre arquiteturas completas.** Manter a massa seca igual é o que torna a
comparação controlada e é também o seu limite: motores, inversores e gerenciamento de bateria de
um lado, unidade de controle, tanques e linhas do outro, ainda não entraram no livro de massa. A
autonomia medida é tempo de pairado até a reserva, **sem** reserva de descida ou retorno.

| Massa embarcada | Combustão | Elétrico |
|---|---|---|
| 10 kg | 2,46 min | 0,50 min |
| 20 kg | 4,83 min | 1,07 min |
| 50 kg | 10,62 min | 2,21 min |

O ramo elétrico **fecha trim e voa**. O que o mata não é diâmetro de rotor, são dois tetos de
massa. O ótimo de bateria pede 190 kg; a geometria só equilibra até 208,1 kg brutos, ou 113,1 kg
de bateria; e exigir aceleração de subida corta o teto para 103,0 kg. Preso a isso, o melhor caso
elétrico é **2,98 min**, que a combustão alcança com **12,0 kg** de combustível.

⚠ Três afirmações anteriores deste repositório caíram aqui, e as três estão registradas no
ADR-008: "autonomia elétrica é função da área, não da bateria" era falsa; o empuxo por bocal que
eu tinha citado era massa dividida pelo número de bocais; e a eliminação do híbrido série
confundia energia com potência, e foi retirada.

E aparece um conflito que nenhuma das duas análises via sozinha: o trim de **menor consumo**
encosta um par de bocais no teto, então a folga superior de empuxo vai a zero exatamente.

⚠ Folga de empuxo não é margem de wrench. `min_upper_thrust_headroom_ratio` mede só a distância
ao teto do propulsor mais carregado. Zero ali é **evidência de saturação local**, e nada além:
não é suficiente para perda de autoridade, porque os outros bocais ainda podem subir, e nem
necessária, porque posto deficiente perde direções com todos os bocais longe do teto.

## Números de referência, e o que eles valem

⚠ **Nenhum dos números abaixo tem fonte arquivada com hash.** Eles entram como ordem de grandeza
para calibração, nunca como faixa validada do projeto.

| Grandeza | Valor citado | Estado da evidência |
|---|---|---|
| Empuxo sobre peso em trajes reais | 1,05 a 1,52 | derivado de massas e empuxos publicados, sem cópia arquivada |
| Atraso de atuador, degrau **grande** | 1 a 3 s na microturbina | catálogo de fabricante, sem cópia arquivada |
| Atraso de atuador, degrau **pequeno** | **desconhecido** | nenhum fabricante publica, e é o que decide estabilização |
| Eficiência de instalação vestível | **sem base** | não existe dado publicado para este arranjo |

A terceira linha é a mais importante do projeto. Ver
[`vault/08 - Dados/Deck de propulsao instalada - schema.md`](vault/08%20-%20Dados/).

## Resultados versionados, para auditar sem executar

⚠ As tabelas deste projeto **não vivem só no terminal de quem rodou.** As saídas dos experimentos
são geradas e versionadas em [`docs/resultados/`](docs/resultados/):

| Arquivo | O que traz |
|---|---|
| `geometria-detalhe.txt` | os sete bocais com posição, direção e limites; a matriz de alocação inteira; valores singulares; janela de centro de massa; e o trim nos dois objetivos, bocal a bocal |
| `experimento-1-geometria.txt` | as onze arquiteturas, com posto, janelas, rolagem pura e tolerância a falha |
| `experimento-2-energia.txt` | elétrico contra combustível por massa embarcada, tetos de massa e potência de barramento |

```bash
./.venv/Scripts/python.exe tools/refresh_results.py
```

Resultado que muda sem motivo declarado vira **diff visível** ao lado da mudança de código que o
causou, e não surpresa silenciosa.

## Resultados versionados, para auditar sem executar

⚠ As tabelas deste projeto **não vivem só no terminal de quem rodou.** As saídas dos experimentos
são geradas e versionadas em [`docs/resultados/`](docs/resultados/):

| Arquivo | O que traz |
|---|---|
| `geometria-detalhe.txt` | os sete bocais com posição, direção e limites; a matriz de alocação inteira; valores singulares; janela de centro de massa; e o trim nos dois objetivos, bocal a bocal |
| `experimento-1-geometria.txt` | as onze arquiteturas, com posto, janelas, rolagem pura e tolerância a falha única |
| `experimento-2-energia.txt` | elétrico contra combustível por massa embarcada, os dois tetos de massa e a potência de barramento |
| `experimento-3-funil.txt` | seis famílias de arquitetura por oito filtros, com o motivo de morte de cada uma |
| `experimento-4-atraso.txt` | fronteira de atraso e rampa, e as duas margens de autoridade medidas |
| `experimento-5-turbinas.txt` | três microturbinas de catálogo contra a especificação gerada |
| `experimento-6-estrutura.txt` | espectro de excitação, cargas de fixação e sensibilidade à inércia |
| `briefing-cad.txt` | o que modelar em CAD, com coordenadas em milímetros, e o que devolver ao simulador |

```bash
./.venv/Scripts/python.exe tools/refresh_results.py
```

Resultado que muda sem motivo declarado vira **diff visível** ao lado da mudança de código que o
causou, e não surpresa silenciosa.

## CAD conceitual, em dois processos

⚠ **FreeCAD não é dependência do projeto e não pode ser.** O núcleo importa apenas NumPy, SciPy e
pydantic, e há um motivo duro além do arquitetural: o FreeCAD 1.1 traz Python 3.11 enquanto o
projeto roda em 3.12, e `FreeCAD.pyd` é binário. Não há como importar um no outro.

A ponte é por arquivo, como todo deck do projeto:

```bash
# processo 1, no Python do FreeCAD: exporta propriedades de massa
"C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py modelo.FCStd docs/decks/traje.json --z-para-baixo

# processo 2, no Python do projeto: lê, converte unidade e agrega
./.venv/Scripts/python.exe -c "from hero_atlas.airframe.cad_deck import load_cad_deck; ..."
```

A conversão de unidade mora num lugar só, em [`cad_deck.py`](src/hero_atlas/airframe/cad_deck.py),
com teste contra solução analítica de caixa e de cilindro:

```
I_kg_m2 = I_freecad * (massa_kg / volume_mm3) * 1e-6
```

O FreeCAD calcula com **densidade unitária** e comprimento em milímetro. Esquecer o fator de
milhão é óbvio; esquecer a divisão pelo volume **não é**, e produz inércia errada por um fator da
ordem da densidade, que a simulação aceita sem reclamar.

O que modelar está em [`docs/resultados/briefing-cad.txt`](docs/resultados/).

## Como rodar

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
./.venv/Scripts/python.exe -m pytest
```

## Estrutura

```
src/hero_atlas/
  units.py                    SI no núcleo, dimensão e tipo semântico na fronteira
  verdict.py                  satisfeito, violado, indeterminado
  provenance.py               o que a fonte mede, declara, calcula ou infere
  model_status.py             carimbo que recusa saída condicional sem marca
  airframe/mass_properties    agregação com rotação de tensor e eixos paralelos
  airframe/geometry           bocais com posição, direção e limites próprios
  environment/atmosphere      atmosfera padrão sem dupla contagem
  analysis/envelope           força requerida separada de capacidade de entrega
  analysis/energy             turbina integrada; elétrico com máximo interior em bateria
  analysis/mission_energy     energia por missão, trim como porteiro da autonomia
  propulsion/actuator         atraso, constante de tempo, rampa, saturação e a recusa de inventar
  propulsion_family           ramos coexistem; "aprovado" não é expressável
  analysis/trim               equilíbrio vetorial com o momento do peso
  analysis/authority          posto, carga interna, janela de centro de massa
  analysis/requirements       o deck produz requisito, não estimativa
  sim/events                  agenda de eventos e limite de passo
  io/telemetry                evento de alocação com quatro modos de falha

tests/validation/             casos analíticos com solução fechada
vault/                        documentação em Obsidian: decisões, regras, física, diário
```

O núcleo importa **apenas** NumPy, SciPy e pydantic. Ferramentas pesadas produzem decks que o
núcleo consome por interface, verificado por varredura de árvore sintática em
[`test_core_isolation.py`](tests/validation/test_core_isolation.py).

## Por onde auditar

| O que verificar | Onde |
|---|---|
| Achados do marco 2, cada um com seu teste | `tests/validation/test_trim.py` |
| Agregação de massa com solução fechada | `tests/validation/test_mass_aggregation.py` |
| Evento agendado cai no instante certo | `tests/validation/test_event_alignment.py` |
| Calibração do envelope | `tests/validation/test_envelope.py` |
| Núcleo não importa biblioteca pesada | `tests/validation/test_core_isolation.py` |
| Forma fechada do atuador contra integração da própria lei | `tests/validation/test_actuator.py` |
| Missão numérica contra autonomia analítica de turbina | `tests/validation/test_mission_energy.py` |
| Seleção de tecnologia é indecidível por construção | `tests/validation/test_propulsion_family.py` |

A documentação é um cofre do Obsidian em [`vault/`](vault/). Comece por
`00 - Indice/MOC - Hero Atlas`. Decisões em `02 - Decisoes`, regras em `03 - Regras`, diário em
`07 - Diario`.

## Método

O plano passou por sete revisões de crítica técnica antes da primeira linha de código, e o trabalho
segue em rodadas de revisão externa. Cada rodada corrigiu erros do mesmo tipo: **redução silenciosa
de informação onde a informação importava.**

Somar tensores sem transladar. Ausência de evidência virando aprovação. Ausência virando reprovação.
Indecidível virando permitido. Lista manual perdendo item. Discrepância congelada perdendo o motivo.
Contar a mesma deficiência duas vezes.

Nenhuma quebra teste por si. Todas corrompem conclusão. O histórico está em
`vault/08 - Dados/Historico de revisoes.md`.

## Licença

MIT.
