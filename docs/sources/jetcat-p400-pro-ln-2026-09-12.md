# Registro de fonte — JetCat P400-PRO-LN

**Tipo de registro:** transcrição, **não** cópia arquivada do original.

⚠ **Isto é evidência mais fraca do que o ADR-007 exige.** O regime de procedência do
projeto pede cópia do documento original com hash do arquivo. O que existe aqui é uma
transcrição dos valores lidos, com a origem e a data. Se a página mudar, este registro
não permite detectar a mudança; permite apenas dizer o que foi lido e quando.

---

## Origem

| Campo | Valor |
|---|---|
| URL | `https://www.jetcat.de/en/productdetails/produkte/jetcat/produkte/Professionell/p400 pro` |
| Fabricante | JetCat / Ingenieurbüro CAT M. Zipperer GmbH |
| Data de consulta | 2026-09-12 |
| Tipo de fonte | `manufacturer_datasheet` |
| Classe de evidência | `declared_specification` |
| Aplicabilidade | bancada de ensaio estática, nível do mar, atmosfera não declarada |

---

## Valores transcritos

| Grandeza | Valor | Unidade |
|---|---:|---|
| Empuxo máximo | 425 | N |
| Empuxo em marcha lenta | 14 | N |
| Massa | 4010 | g |
| Rotação em marcha lenta | 30000 | 1/min |
| Rotação máxima | 98000 | 1/min |
| Consumo a plena carga | 1392 | ml/min |
| Consumo em marcha lenta | 200 | ml/min |
| Consumo específico no máximo | 0,157 | kg/(N·h) |
| Temperatura de gases de escape | 480 a 750 | °C |
| Diâmetro | 148,4 | mm |
| Comprimento | 390 | mm |
| Razão de pressão | 3,8 | — |
| Vazão mássica | 0,67 | kg/s |
| Velocidade dos gases | 2122 | km/h |
| Potência dos gases | 116,4 | kW |

## Derivações feitas pelo projeto

| Grandeza | Valor | Como |
|---|---:|---|
| Consumo específico em SI | 4,361e-5 kg/(N·s) | `0,157 / 3600` |
| Empuxo por massa | 106 N/kg | `425 / 4,010` |
| Frequência de eixo | 500 a 1633 Hz | `rpm / 60` |
| Fração de marcha lenta | 0,033 | `14 / 425` |

⚠ A densidade do querosene de 0,80 kg/L usada para converter mililitros por minuto em
quilogramas por segundo **não vem desta fonte**. É valor de ordem de grandeza.

---

## O que esta fonte NÃO publica

Verificado explicitamente na página em 2026-09-12. **Nenhuma** das grandezas abaixo
aparece, e todas decidem o comportamento dinâmico:

- constante de tempo a degrau pequeno perto do ponto de operação;
- constante de tempo a degrau grande;
- taxa máxima de variação de empuxo, subindo ou descendo;
- atraso entre comando e início da resposta;
- tempo de aceleração de marcha lenta a máximo;
- empuxo mínimo estável em voo, distinto do de bancada;
- consumo específico em carga parcial;
- contagem de pás do compressor.

---

## Onde este registro é usado

- `tools/turbine_match.py`, entrada `JetCat P400-PRO-LN`
- `tools/structure_screen.py`, faixa de rotação para o espectro de excitação
- `docs/ESPECIFICACAO.md`, seção 6, experimentos 5 e 6
