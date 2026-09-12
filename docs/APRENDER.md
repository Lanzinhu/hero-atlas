# Trilha de aprendizado — a física deste projeto, no código que já existe

**Para quem quer entender o simulador por dentro.** Estado em 2026-09-12.

Onze paradas, de força e massa até a fronteira de atraso. Cada uma tem o conceito, onde
ele mora no código real, um número que o projeto já produziu, e um exercício que roda.

⚠ **Nenhum exercício aqui pede para você reescrever o que já existe.** Aprender
duplicando constante física é como aprender a somar mantendo duas calculadoras: parece
inofensivo até as duas discordarem.

Este projeto já viveu isso. A densidade do ar ao nível do mar estava escrita como
`1.225` num lugar e calculada como `p/(R·T)` noutro. As duas divergiam em nove partes
por milhão, o que bastou para um cenário de referência não dar exatamente 1,0. A
correção foi apagar a cópia e **derivar** o valor. Existe **um** `G0` no projeto, em
`units.py`, usado em 31 lugares.

---

## Como usar

```bash
cd "C:/Users/alanl/OneDrive/Desktop/Projetos/Hero_Atlas"
./.venv/Scripts/python.exe
```

Cada exercício é um bloco que roda no interpretador. Nenhum cria arquivo novo.

---

## Parada 1 — Força, massa e peso

**O conceito.** Força é o que muda o movimento. Massa é a resistência a essa mudança.

```
F = m · a
```

Peso é um caso particular: a força com que a gravidade puxa uma massa.

```
P = m · g        com  g = 9,80665 m/s²
```

**Massa e peso não são a mesma grandeza.** Massa é propriedade do corpo; peso é força, e
depende de onde você está. Um quilograma-força é a força que a gravidade exerce sobre um
quilograma, ou seja 9,80665 newton. Essa distinção é a origem de metade dos erros de
unidade em engenharia.

**Onde mora:** `src/hero_atlas/units.py`

```python
from hero_atlas.units import G0, to_si, dimension_of

print(G0)                        # 9.80665
print(to_si(35.0, "kgf"))        # 343.2 N
print(dimension_of("kgf"))       # force
```

⚠ Repare que `to_si` faz a conversão. Você **não** escreve `35 * 9.80665` espalhado pelo
código: a conversão mora num lugar, com a dimensão declarada, e o sistema recusa somar
grandezas de dimensões diferentes.

**Exercício.** O traje pesa 127,4 kg. Quantos newtons de empuxo o conjunto precisa
produzir só para não cair?

```python
from hero_atlas.units import G0
print(127.4 * G0)                # 1249.4 N
```

**O que isto ainda não diz:** nada sobre se o traje voa. Empuxo vertical suficiente é
condição necessária e está muito longe de suficiente. As paradas 4 e 5 mostram por quê.

---

## Parada 2 — Massa distribuída, e por que tensores não se somam

**O conceito.** Um corpo não tem só massa: tem massa **espalhada**. A resistência a
girar depende de onde a massa está, não só de quanta é. Isso é o tensor de inércia.

```
I_j,ref = R_j · I_j,cg · R_jᵀ  +  m_j (‖d_j‖² I₃ − d_j d_jᵀ)
          ↑ rotação                ↑ eixos paralelos
```

⚠ **Somar tensores de inércia diretamente é errado.** Cada peça tem o tensor sobre o
próprio centro e nos próprios eixos. Antes de somar é preciso **rotacionar** para os
eixos comuns e **transladar** para o ponto comum. Esquecer a translação foi o primeiro
erro sério que este projeto cometeu e corrigiu.

**Onde mora:** `src/hero_atlas/airframe/mass_properties.py`

```python
import numpy as np
from hero_atlas.airframe.mass_properties import MassComponent, aggregate_mass_properties

esq = MassComponent("esq", 2.0, np.array([0, -0.5, 0]), np.eye(3) * 0.01, np.eye(3))
dir = MassComponent("dir", 2.0, np.array([0, +0.5, 0]), np.eye(3) * 0.01, np.eye(3))
r = aggregate_mass_properties((esq, dir))
print(r.mass_kg)                      # 4.0
print(r.center_of_mass_body_m)        # [0, 0, 0]
print(r.inertia_about_cg_kg_m2[0, 0]) # 1.02, não 0.02
```

O `1,02` contra `0,02` é a translação. Duas peças de 2 kg a meio metro do centro
contribuem `2 × 2 × 0,5² = 1,0` que a soma ingênua perderia.

---

## Parada 3 — Empuxo vetorial e a matriz de alocação

**O conceito.** Cada propulsor produz uma força numa direção, num ponto. Força fora do
centro produz **momento**. Sete propulsores produzem seis números: três de força, três
de momento.

```
W = [ n̂ᵢ ; (rᵢ − r_O) × n̂ᵢ + cᵢ·n̂ᵢ ]       matriz 6 × N
```

O termo `cᵢ·n̂ᵢ` é o torque de **reação**: zero num jato, não zero num rotor. Foi a
ausência dele que fez quatro arquiteturas de rotor serem eliminadas por engano.

**Onde mora:** `src/hero_atlas/airframe/geometry.py`

```python
import math
from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, allocation_matrix, parametric_layout
from hero_atlas.units import to_si

t15 = math.radians(15.0)
geo = parametric_layout(
    pairs=[ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
           ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
           ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15)],
    axial=[AxialNozzleSpec("dorsal", forward_m=-0.15, height_m=0.10)],
    thrust_max_N=to_si(35.0, "kgf"), idle_fraction=0.10)

W = allocation_matrix(geo)
print(W.shape)          # (6, 7)
print(W[2, :].round(3)) # a linha Fz: quanto cada bocal levanta
```

**Exercício.** Olhe a linha `Fz`. Nenhum bocal dá `−1,000` a não ser o dorsal. Por quê?
Porque os de braço estão inclinados para fora, e a inclinação **cobra o cosseno**: parte
do empuxo vira força lateral em vez de sustentação. É o preço da autoridade de controle.

---

## Parada 4 — Equilíbrio, e por que peso produz momento

**O conceito.** Pairar é achar empuxos que zerem **força e momento ao mesmo tempo**.

```
Σ Tᵢ n̂ᵢ + m R g = 0                              força
Σ (rᵢ − r_O) × Tᵢ n̂ᵢ + r_C/O × (m R g) = 0        momento
T_min ≤ Tᵢ ≤ T_max                                limites
```

⚠ **O segundo termo do momento é o que quase todo mundo esquece.** A gravidade age no
centro de massa. Sobre o centro ela não produz momento nenhum, por definição. Mas o
projeto integra um **ponto de referência estrutural**, não o centro, e sobre esse ponto
o peso produz momento sim. Toda vez que o piloto levanta um braço, esse termo muda.

**Onde mora:** `src/hero_atlas/analysis/trim.py`

```python
from hero_atlas.analysis.trim import TrimObjective, solve_trim
from hero_atlas.units import G0

s = solve_trim(geo, mass_kg=115.0, center_of_mass_body_m=[0.1575, 0, 0],
               objective=TrimObjective.MAX_MARGIN)
print(s.feasible)                                # True
print((s.thrusts_N / G0).round(2))               # kgf por bocal
print(s.vertical_thrust_projection_ratio)        # 0.8522
```

**Exercício.** A razão de projeção é 0,8525. Confira que ela explica a soma:

```python
print(115.0 / 0.8522, s.total_thrust_N / G0)     # 134,9 e 134,9
```

Quinze por cento do empuxo é gasto em cancelamento mútuo. É o custo de ter os bocais
inclinados, e sem essa inclinação não haveria controle.

---

## Parada 5 — Autoridade, e o posto da matriz

**O conceito.** A matriz tem seis linhas. Se o **posto** for menor que seis, existem
direções de força ou momento que nenhuma combinação de empuxos produz. Motor maior não
resolve: é geometria.

**Onde mora:** `src/hero_atlas/analysis/authority.py`

```python
from hero_atlas.analysis.authority import analyse_authority
m = analyse_authority(geo)
print(m.rank, "de 6")
print(m.singular_values.round(4))
```

Valores singulares pequenos são direções **fracas**: existem no papel e custam muito
empuxo. O menor aqui é cerca de 0,055 contra 2,3 do maior, uma razão de 42.

**O achado desta parada.** Das onze geometrias varridas, nove foram eliminadas. O filtro
decisivo foi **rolagem pura**: equilibrar um centro de massa deslocado de lado exige
momento de rolagem **sem** força lateral, e isso exige três graus de liberdade
antissimétricos. Dois pares de bocais dão dois.

⚠ Contar propulsores não basta. Três pares que diferem **só em altura** continuam
falhando. Precisam diferir em inclinação.

---

## Parada 6 — Energia, e as duas leis diferentes

**O conceito.** Turbina e elétrico não obedecem à mesma lei, e a diferença é o resultado
mais interessante do projeto.

```
Turbina:   ṁ = TSFC · ΣTᵢ        a massa CAI enquanto queima
           t = ln(m₀/(m₀ − combustível)) / k

Elétrico:  P = Σ Tᵢ^1,5 / √(2ρAᵢ) / (FM·η)   a massa NÃO cai
           E = m_bat · e · DoD
```

**Onde mora:** `src/hero_atlas/analysis/energy.py` e `mission_energy.py`

```python
from hero_atlas.analysis.energy import optimal_battery_mass_kg, turbine_endurance_s
from hero_atlas.units import to_si

print(optimal_battery_mass_kg(95.0))   # 190.0 kg, o dobro da massa seca
t = turbine_endurance_s(gross_kg=115.0, usable_fuel_kg=16.0,
                        tsfc_kg_per_N_s=to_si(1.54, "kg/(kgf*h)"))
print(t.endurance_min)                 # minutos
```

**O achado.** A autonomia elétrica tem **máximo interior**: a bateria ótima é exatamente
o dobro da massa seca, e passar disso **reduz** a autonomia, porque o quilo a mais não
paga o próprio transporte. E esse ótimo costuma ficar fora do que a geometria equilibra.

⚠ Essa forma fechada supõe potência auxiliar nula, sem teto de trim e sem aceleração.
Com carga auxiliar o ótimo sobe; com teto de trim ele desce.

---

## Parada 7 — Rotação, e por que quaternion

**O conceito.** Descrever orientação com três ângulos tem um defeito: em certas atitudes
dois eixos se alinham e um grau de liberdade some. Quaternion não tem esse problema.

```
q = [w, x, y, z]              escalar primeiro
v_I = R(q) · v_B              leva do corpo para o inercial
q̇ = ½ q ⊗ (0, ω_B)            cinemática
```

⚠ **Convenção trocada produz trajetória suave e completamente falsa**, e não quebra
nenhum teste ingênuo. Por isso o projeto fixa a convenção num lugar e a verifica por
**equivariância**: girar o referencial e girar o resultado têm que dar a mesma coisa.

**Onde mora:** `src/hero_atlas/dynamics/quaternion.py`

```python
import numpy as np
from hero_atlas.dynamics.quaternion import from_axis_angle, rotation_matrix_ib

q = from_axis_angle([0, 0, 1], np.radians(90))
print((rotation_matrix_ib(q) @ [1, 0, 0]).round(6))   # [0, 1, 0]
```

---

## Parada 8 — Dinâmica de corpo rígido

**O conceito.** Duas equações, uma para translação e outra para rotação.

```
m a_C = F                                    Newton, no centro de massa
I ω̇ + ω × (I ω) = M                          Euler, no centro de massa
```

O termo `ω × (I ω)` é o que produz o efeito Dzhanibekov: um corpo girando em torno do
eixo de inércia **intermediária** vira sozinho, periodicamente, sem força nenhuma. O
projeto usa isso como teste, porque um sinal trocado no produto vetorial mata o efeito.

**Onde mora:** `src/hero_atlas/dynamics/rigid_body.py`

```python
import numpy as np
from hero_atlas.dynamics.rigid_body import PlantState, RigidBodyProperties, angular_momentum_inertial

corpo = RigidBodyProperties(115.0, np.diag([32.2, 32.2, 2.3]), np.array([0.1575, 0, 0]))
print(corpo.inertia_inverse.diagonal().round(4))
```

⚠ O momento angular é conferido **no referencial inercial**. Verificar as componentes no
corpo seria errado, porque o próprio referencial gira: elas mudam mesmo com o momento
conservado.

---

## Parada 9 — O atuador, e a incógnita central do projeto

**O conceito.** Comando não vira empuxo. A cadeia é:

```
u(t) → u(t − T_d) → T_ss saturado → T(t) por equação diferencial → força
```

```
Ṫ = clip( (T_ss − T)/τ , −Ṫ↓max , +Ṫ↑max )
```

**Onde mora:** `src/hero_atlas/propulsion/actuator.py`

```python
from hero_atlas.propulsion.actuator import ActuatorEnvelope, step_response_time_s, small_step_response_time_s

env = ActuatorEnvelope(34.0, 343.0, tau_up_s=0.35, tau_down_s=0.30,
                       rate_up_max_N_s=120.0, rate_down_max_N_s=150.0)
print(step_response_time_s(initial_N=34, commanded_N=343, envelope=env))  # 2.33 s
small_step_response_time_s(thrust_N=190.0, envelope=env)                   # levanta erro
```

**A última linha levanta um erro de propósito.** O catálogo publica resposta a degrau
**grande**, de marcha lenta ao máximo. O que decide estabilização é a resposta a degrau
**pequeno** perto do pairado, e **nenhum fabricante publica isso**. Verifiquei na página
da JetCat: não há nenhuma especificação de tempo.

O código **recusa** inventar o número. Essa recusa é o resultado mais importante do
projeto.

---

## Parada 10 — Controle e alocação

**O conceito.** Duas camadas separadas:

```
erro de atitude  →  wrench desejado    (controlador)
wrench desejado  →  comando por bocal  (alocador)
```

⚠ O alocador só pode pedir o que a **rampa alcança no horizonte**, não o que a caixa
física permite:

```
Tᵢ(t + Ha) ∈ [ max(T_min, Tᵢ − Ṫ↓·Ha) , min(T_max, Tᵢ + Ṫ↑·Ha) ]
```

A diferença entre essas duas caixas é a **margem dinâmica**, e ela é o achado do passo 5.

**Onde mora:** `src/hero_atlas/control/`

```python
from hero_atlas.analysis.control_budget import moment_budget
envs = tuple(env for _ in geo.available)
orc = moment_budget(geo, thrust_trim_N=s.thrusts_N, envelopes=envs, horizon_s=0.20)
for nome, est, hor, raz in orc.as_rows():
    print(f"{nome:6} estático {est:7.1f} N·m | horizonte {hor:6.1f} N·m | {raz:.1f}× menor")
```

Resultado: **a margem de curto prazo é cinco a seis vezes menor que a estática.** Empuxo
máximo excelente não implica autoridade de curto prazo.

---

## Parada 11 — O laço fechado, e a conclusão

**O conceito.** Tudo junto, na ordem certa: evento, tique do controlador, alocação,
comando empilhado, integração com o comando **atrasado e retido**, projeção do empuxo.

**Onde mora:** `src/hero_atlas/sim/closed_loop.py`

```bash
./.venv/Scripts/python.exe tools/delay_sweep.py
```

**O resultado final do projeto até aqui:**

| Banda exigida | Período | Maior atraso tolerado |
|---:|---:|---:|
| 1,05 rad/s | 6,0 s | 0,40 s |
| 2,00 rad/s | 3,1 s | 0,15 s |
| 3,00 rad/s | 2,1 s | 0,02 s |
| 4,50 rad/s | 1,4 s | nenhum |

**A arquitetura tolera atraso porque é obrigada a ser lenta.** A autoridade de curto
prazo limita a banda a cerca de 1,5 rad/s. O parâmetro limitante não é o atraso: é o
momento disponível no horizonte.

---

## O que a trilha não ensina

Aerodinâmica do corpo com jatos ao lado. Piloto humano no laço. Falha de propulsor em
voo, que esta geometria **não tolera**. Estrutura, fadiga, térmica. Fabricação.

E, principalmente: **nada aqui diz que a arquitetura funciona.** Toda conclusão é
condicional a geometria plausível e não medida, massa estimada, consumo de catálogo
extrapolado e dinâmica reduzida.

---

## Por que não há exercício de reimplementar

Se em algum momento aparecer a sugestão de criar um módulo novo com uma constante
própria de gravidade, ou uma função própria de conversão de peso, a resposta é **não**,
e o motivo é concreto:

| Defeito | O que acontece |
|---|---|
| Duas cópias de uma constante | divergem, e a divergência não quebra teste nenhum |
| Conversão fora de `units.py` | some a dimensão declarada, e somar newton com kgf passa |
| Módulo fora da árvore | o teste de isolamento do núcleo não o cobre |

O projeto tem 629 testes justamente para que esse tipo de coisa seja detectável. Estudar
o código existente ensina a mesma física e mantém o sistema íntegro.
