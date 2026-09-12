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
> **A dinâmica ainda não foi implementada.** Os resultados atuais pertencem ao trim **estático** de
> uma geometria parametrizada. Nada aqui diz respeito a estabilidade, resposta ou pilotabilidade.
>
> Isso não é ressalva de rodapé: é o resultado principal do levantamento de evidência até agora, e
> está codificado em [`model_status.py`](src/hero_atlas/model_status.py), que **recusa** emitir
> resultado condicional sem carimbo.

## Estado do projeto

**Marco 2 entregue:** trim vetorial e autoridade estática.
**Marco 3 em andamento:** dinâmica de corpo rígido e suíte analítica.
**Próximo:** dinâmica reduzida, propulsão paramétrica e eventos.

| Marco | Entrega | Estado |
|---|---|---|
| 0 | Unidades, procedência, agregação de massa, eventos, telemetria | entregue |
| 1 | Envelope de massa e empuxo, autonomia | entregue |
| 2 | Trim com momento do peso, mapa de autoridade | entregue |
| 3 | Dinâmica seis graus de liberdade | núcleo e suíte analítica prontos |

411 testes, lint limpo.

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
  analysis/energy             autonomia de turbina integrada, elétrica por disco atuador
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
