# Hero Atlas

Laboratório virtual para descobrir quais limites físicos e de controle tornam um traje de
propulsão pessoal controlável, marginal ou inevitavelmente instável.

**Não é** "simular um Homem de Ferro". O entregável é o simulador e o estudo de viabilidade.
Sem hardware. Custo zero. Python.

## A pergunta

```
R = { (τ_atuador, τ_humano, K_humano, Ṫ_max, q_braços, m, r_cg) :
      estável sobre o envelope de cenários declarado }
```

E quais variáveis encolhem essa região até ela desaparecer. Descobrir que a região é estreita ou
vazia **é sucesso**, não fracasso: o projeto encontrou a barreira real antes de alguém gastar
dinheiro, combustível ou sobrancelhas.

## Os números que decidem

| Número | Traje real | Referência |
|---|---|---|
| Empuxo sobre peso | 1,05 a 1,52 | drone de corrida: 10 a 14 |
| Atraso do atuador | 1 a 3 s na microturbina | motor elétrico: 0,1 s |
| Autoridade de momento | inclusive com um propulsor apagado | — |
| Taxa máxima de empuxo | separada da constante de tempo | — |

A 1,1 de empuxo sobre peso a aceleração vertical disponível é 0,1 g. Para deter uma descida de
3 m/s são precisos cerca de 3 segundos e 4,5 m de altura. Voando a 2 m do solo não existe
recuperação.

## Como rodar

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
./.venv/Scripts/python.exe -m pytest
```

## Estrutura

```
src/hero_atlas/
  units.py                  SI no núcleo, dimensão explícita na fronteira
  provenance.py             o que a fonte mede, declara, calcula ou infere
  airframe/mass_properties  agregação com rotação de tensor e eixos paralelos
  sim/events.py             agenda de eventos e limite de passo do integrador
  io/telemetry.py           registro de evento de alocação e ativação de limite

tests/
  validation/               casos analíticos com solução fechada
  unit/                     testes isolados

vault/                      documentação em Obsidian: decisões, regras, física, diário
```

O núcleo importa **apenas** NumPy, SciPy e pydantic. Ferramentas pesadas produzem decks que o
núcleo consome por interface, e nunca são importadas por ele. O simulador roda no primeiro dia e
continua rodando se nada pesado for instalado.

## Documentação

O vault do Obsidian em [`vault/`](vault/) é a fonte de verdade do projeto. Abra a pasta no Obsidian
e comece por `00 - Indice/MOC - Hero Atlas`.

| Pasta | Conteúdo |
|---|---|
| `01 - Visao` | por que o projeto existe e o que ele responde |
| `02 - Decisoes` | ADRs, com motivo e consequência |
| `03 - Regras` | invariantes de projeto |
| `04 - Fisica` | equações implementadas e aproximações declaradas |
| `05 - Verificacao` | como saber que o simulador não está mentindo |
| `06 - Marcos` | cronograma e critério de sucesso de cada etapa |
| `07 - Diario` | registro diário |
| `08 - Dados` | procedência e números de referência |

## Estado

**Marco 0, fundação.** Unidades, procedência, agregação de massa, agenda de eventos, telemetria.

O plano passou por sete revisões de crítica técnica antes da primeira linha de código. Cada uma
corrigiu um erro real do mesmo tipo: uma frase intuitiva que, implementada literalmente, introduz
erro sistemático exatamente na análise mais sensível.

Somar tensores de inércia diretamente. Congelar buffer de atraso como regra geral. Dividir a força
requerida pelo derating atmosférico. Recalcular inércia sobre um centro que migra. Testar
conservação num modelo que declaradamente não tem os termos.

Todas pareciam certas. Nenhuma era. Ver `vault/08 - Dados/Historico de revisoes`.

## Licença

MIT.
