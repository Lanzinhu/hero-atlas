# Guia de modelagem — Hero Atlas, família A

**Para quem vai abrir o FreeCAD e modelar.** Estado em 2026-09-12.
Repositório: `https://github.com/Lanzinhu/hero-atlas`

Este documento é autocontido. Todos os números de que você precisa estão aqui, com a
origem de cada um. Não é preciso ler o código para executar o que está escrito.

---

## 0. O que você vai modelar, e por quê

Você **não** vai desenhar um traje. Você vai construir um modelo geométrico cujo único
propósito é devolver ao simulador quatro números que hoje são chute:

| Número | Hoje | Depois do CAD |
|---|---|---|
| Massa total | 115 kg, estimada em bloco | soma de peças |
| Centro de massa | 157,5 mm à frente da origem, **escolhido** | medido |
| Tensor de inércia | cilindro equivalente, diagonal | medido, com produtos fora da diagonal |
| Envelope | nunca verificado | **respondido, sim ou não** |

O quarto é o mais importante e é o único que pode **matar o projeto**. As posições dos
propulsores saíram de uma varredura que otimizou autoridade de controle e nunca
perguntou se um corpo humano acomoda o resultado.

⚠ **Modelar não valida nada.** O CAD pode reprovar a geometria. Se reprovar, isso é
resultado, e o caminho é voltar à varredura com restrição de envelope, não forçar o
desenho.

### O que este documento não cobre

Fabricação, materiais reais, processo, montagem, ensaio, operação. Nada aqui é
instrução de construção. O projeto tem escopo declarado de **simulação e engenharia
virtual, sem hardware**, e este guia serve a esse escopo.

---

## 1. Preparação

### 1.1 Ferramenta

FreeCAD 1.1.3, já instalado. Bancadas usadas: **Part** e **Part Design**. Não é preciso
nada além disso.

### 1.2 Unidades

Configure antes de começar, em `Editar > Preferências > Geral > Unidades`:

| Campo | Valor |
|---|---|
| Sistema de unidades | Padrão (mm, kg, s, graus) |
| Número de decimais | 4 |

⚠ Trabalhe **sempre em milímetro**. Todas as coordenadas deste documento estão em
milímetro. A conversão para metro acontece do lado do simulador, num lugar só, e já
tem teste.

### 1.3 O referencial, e este é o ponto onde mais gente erra

```
origem:  ponto de referência estrutural fixo no corpo
         NÃO é o centro de massa

  +x  →  para a FRENTE do piloto
  +y  →  para a DIREITA do piloto
  +z  →  para BAIXO
```

⚠ **O eixo z aponta para baixo.** Isso é convenção aeronáutica e é o contrário do que
quase todo CAD assume. Modelar com z para cima e espelhar na exportação é a fonte de
erro de sinal mais provável deste passo inteiro, e o simulador **recusa** um deck
exportado sem espelhar.

Duas rotas válidas, escolha uma e não misture:

- **Rota A, recomendada:** modele já com z para baixo. Estranho no começo, correto
  depois. O piloto fica "de cabeça para baixo" na tela, e tudo bem.
- **Rota B:** modele com z para cima, e aplique uma rotação de 180 graus em torno de x
  no objeto raiz antes de exportar. Exportar com a marca `--z-para-baixo` sem ter feito
  isso produz um modelo espelhado que o simulador aceita e que está errado.

### 1.4 Onde fica a origem no corpo

A origem é um ponto estrutural, não anatômico. A convenção deste projeto:

**Origem no centro do tronco, na altura do plexo solar**, ou seja aproximadamente
1250 mm acima do chão num piloto de 1750 mm, no plano médio, na metade da profundidade
do tronco.

Essa escolha vem do fato de que os propulsores se distribuem acima e abaixo dela, o que
mantém os números pequenos e os sinais legíveis.

---

## 2. Tabela mestra de coordenadas

**Esta é a tabela que define tudo.** Ela é saída do experimento de varredura de
geometria, não medida antropométrica.

### 2.1 Posição do centro de cada propulsor

| Bocal | x (mm) | y (mm) | z (mm) |
|---|---:|---:|---:|
| par0_esq | 320 | −300 | −150 |
| par0_dir | 320 | +300 | −150 |
| par1_esq | 200 | −400 | −260 |
| par1_dir | 200 | +400 | −260 |
| par2_esq | 20 | −350 | −370 |
| par2_dir | 20 | +350 | −370 |
| dorsal | −150 | 0 | +100 |

Lembre: z negativo é **acima** da origem. Então os pares de braço ficam de 150 a 370 mm
acima do plexo solar, e o dorsal fica 100 mm abaixo, atrás das costas.

### 2.2 Direção de empuxo de cada propulsor

A direção é para onde a **força** aponta. O jato sai no sentido contrário.

| Bocal | Vetor unitário (x, y, z) | Inclinação lateral | Inclinação longitudinal |
|---|---|---:|---:|
| par0_esq | (+0,2506; −0,2506; −0,9351) | 15° para fora | 14,5° para frente |
| par0_dir | (+0,2506; +0,2506; −0,9351) | 15° para fora | 14,5° para frente |
| par1_esq | (0; −0,5000; −0,8660) | 30° para fora | 0° |
| par1_dir | (0; +0,5000; −0,8660) | 30° para fora | 0° |
| par2_esq | (−0,2506; −0,6846; −0,6846) | 45° para fora | 14,5° para trás |
| par2_dir | (−0,2506; +0,6846; −0,6846) | 45° para fora | 14,5° para trás |
| dorsal | (0; 0; −1) | 0° | 0° |

**Como aplicar no FreeCAD.** Para cada cilindro de turbina, o eixo do cilindro deve
ficar alinhado com o vetor acima. Duas rotações, nesta ordem:

1. gire em torno de **y** pelo ângulo longitudinal (positivo = nariz para frente);
2. gire em torno de **x** pelo ângulo lateral (com o sinal do lado).

Ou, mais simples e menos sujeito a erro: use `Placement > Ângulo com eixo` e informe o
eixo e o ângulo diretamente. O eixo de rotação que leva `(0,0,−1)` até o vetor alvo é o
produto vetorial dos dois, e o ângulo é o arco cosseno do produto escalar.

⚠ **Confira sempre depois de posicionar.** Meça o vetor do eixo do cilindro no FreeCAD e
compare com a tabela, componente a componente, com quatro casas. Um sinal trocado em
`y` espelha o traje e o simulador não tem como saber.

---

## 3. Passo a passo

A ordem importa. O passo 3 é um **portão**: se ele reprovar, pare.

### Passo 1 — Manequim do piloto

**Propósito:** envelope e massa. Não precisa ser bonito, precisa ser do tamanho certo.

Modele como sólidos primitivos, um por segmento, porque o simulador quer propriedades
**por componente**:

| Segmento | Forma | Dimensões (mm) | Centro (x, y, z) mm | Massa (kg) |
|---|---|---|---|---:|
| cabeça e pescoço | cilindro | ⌀180 × 280 | (0; 0; −430) | 5,5 |
| tronco | caixa | 450 × 240 × 620 | (0; 0; −60) | 34,0 |
| braço superior esq | cilindro | ⌀100 × 300 | (0; −190; −250) | 2,5 |
| braço superior dir | cilindro | ⌀100 × 300 | (0; +190; −250) | 2,5 |
| antebraço e mão esq | cilindro | ⌀85 × 380 | (60; −220; +30) | 2,0 |
| antebraço e mão dir | cilindro | ⌀85 × 380 | (60; +220; +30) | 2,0 |
| coxa esq | cilindro | ⌀150 × 420 | (0; −95; +460) | 8,5 |
| coxa dir | cilindro | ⌀150 × 420 | (0; +95; +460) | 8,5 |
| perna e pé esq | cilindro | ⌀110 × 470 | (0; −95; +900) | 5,5 |
| perna e pé dir | cilindro | ⌀110 × 470 | (0; +95; +900) | 5,5 |
| **total** | | | | **76,5** |

⚠ Esses valores são **ordem de grandeza de percentil 50 masculino**, não medida sua.
A soma dá 76,5 kg contra os 80 kg do orçamento; a diferença cobre roupa, capacete e
proteção térmica, que você pode modelar separado ou embutir aumentando o tronco.

**Pose:** em pé, braços levemente abertos e à frente, como quem segura um guidão
invisível. É a pose de pairado.

### Passo 2 — Turbinas, como envelope

Modele cada uma como **cilindro simples**. Você não vai modelar o interior.

| Grandeza | Valor | Origem |
|---|---:|---|
| Diâmetro | 120 mm | Kingtech K-260G4, catálogo |
| Comprimento | 299 mm | catálogo |
| Massa | 2,20 kg | catálogo |

Registro da fonte em `docs/sources/kingtech-k210-k260-2026-09-12.md`.

⚠ **Some 30 mm de raio de folga** em torno de cada turbina para carcaça, isolamento e
fixação. Ou seja, para verificação de interferência use cilindro de ⌀180 mm, mas para
massa e inércia use o cilindro real de ⌀120 mm com 2,20 kg.

**Onde fica o centro do cilindro.** A tabela da seção 2.1 dá o ponto de aplicação do
empuxo, que fica na **saída do bocal**. O centro de massa da turbina fica recuado ao
longo do eixo, para dentro. Recue **150 mm** no sentido contrário ao vetor de empuxo.

Exemplo para `par0_dir`: ponto de empuxo em (320; 300; −150), vetor (+0,2506; +0,2506;
−0,9351). Centro do cilindro em:

```
(320; 300; −150) − 150 × (0,2506; 0,2506; −0,9351)
= (320 − 37,6; 300 − 37,6; −150 + 140,3)
= (282,4; 262,4; −9,7) mm
```

### Passo 3 — O PORTÃO: isto cabe?

**Pare aqui e verifique. Não continue modelando se reprovar.**

Rode a verificação de interferência do FreeCAD entre todos os pares de sólidos, com as
turbinas no envelope de ⌀180 mm.

Cinco perguntas, todas com resposta binária:

| # | Pergunta | Critério de reprovação |
|---|---|---|
| 1 | As turbinas invadem o corpo? | qualquer interseção com manequim |
| 2 | As turbinas invadem umas às outras? | qualquer interseção entre envelopes |
| 3 | O jato de um bocal atinge outro corpo sólido? | cone de 15° a partir da saída, comprimento 1000 mm, intersecta qualquer coisa |
| 4 | O par mais externo é alcançável? | eixo a 400 mm do plano médio; ombro está a 225 mm. Sobram 175 mm de braço ou estrutura |
| 5 | Sobra caminho para linha de combustível e cabo? | corredor livre de 40 mm da origem a cada turbina |

**Verificação preliminar já feita no simulador**, para você comparar:

| Par | Eixo a | Borda interna a | Linha do ombro | Resultado |
|---|---:|---:|---:|---|
| par0 | 300 mm | 240 mm | 225 mm | livre por 15 mm |
| par1 | 400 mm | 340 mm | 225 mm | livre por 115 mm |
| par2 | 350 mm | 290 mm | 225 mm | livre por 65 mm |

O par0 passa com **15 mm de folga**, o que é pouco. Confirme no modelo com o ombro
real, não com a caixa do tronco.

### Um segundo aperto, que não é de envelope

Com a turbina real, a folga de massa é **27,2 kg** antes de o trim deixar de fechar, e a
folga superior de empuxo em pairado é **17,6%**. Com a classe genérica de 35 kgf usada
nos experimentos, esses números eram 80,7 kg e 38,8%.

Ou seja: o orçamento de 12 kg de estrutura passa a ser o número que decide se fecha. Se
a estrutura real der 25 kg em vez de 12, ainda fecha; se der 40, não fecha.

⚠ **Se reprovar em qualquer uma das cinco, pare e avise.** A varredura de geometria
roda de novo com restrição de envelope, e as coordenadas mudam. Continuar modelando
uma geometria impossível desperdiça todo o trabalho seguinte.

### Passo 4 — Braços e berços

Só agora, e só se o passo 3 passou.

**Carga de dimensionamento.** Use o **teto** do propulsor, nunca o valor de pairado,
porque a alocação usa o teto em transitório e o piloto está do outro lado da alavanca.

⚠ **Dimensione pela turbina que você vai modelar, não pela classe dos experimentos.**
Os experimentos 1 a 4 usaram uma classe genérica de 35 kgf por bocal, que **nenhuma
turbina real da lista atinge**. A K-260G4 dá 26 kgf.

| Carga | Classe genérica 35 kgf | **K-260G4, use esta** |
|---|---:|---:|
| Empuxo por berço, no teto | 343 N | **255 N** |
| Empuxo por berço, em pairado | 209 N | 209 N |
| Maior momento de fixação, em flexão | 178 N·m | **132 N·m** |

Dimensionar pelos 178 N·m superdimensiona o modelo. Dimensionar pelos 132 N·m está
correto para a K-260G4 e fica **errado** se você trocar de turbina depois.

**Método de dimensionamento da viga**, ilustrativo:

```
módulo de seção necessário:  Z = M · FS / σ_adm

com M = 132 N·m, da K-260G4, e fator de segurança FS = 3:
  fibra de carbono, σ_adm = 300 MPa  →  Z = 1320 mm³
  alumínio 6061-T6, σ_adm = 240 MPa  →  Z = 1650 mm³
```

Módulo de seção de tubos redondos, para escolher:

| Tubo | Z (mm³) | Área (mm²) | 0,5 m em fibra |
|---|---:|---:|---:|
| ⌀40 × 2 mm | 2161 | 239 | 0,19 kg |
| ⌀40 × 3 mm | 3003 | 349 | 0,28 kg |
| ⌀50 × 2 mm | 3480 | 302 | 0,24 kg |
| ⌀50 × 3 mm | 4912 | 443 | 0,35 kg |
| ⌀60 × 3 mm | 7293 | 537 | 0,43 kg |

Um tubo de ⌀40 × 2 mm já atende com fator 3. Modele ⌀50 × 3 mm se quiser folga para
fixação e passagem de linha por dentro, e porque a seção real perde rigidez no furo do
berço.

⚠ Isto é **dimensionamento preliminar por tensão de flexão simples**. Não cobre
flambagem, fadiga, concentração de tensão no berço, junta colada, nem temperatura.
Serve para o modelo ter massa e inércia plausíveis, não para fabricar.

**Modele:** para cada par, um tubo da origem estrutural até o berço, mais um berço como
caixa de 150 × 150 × 40 mm na ponta.

### Passo 5 — Tanque de combustível

| Grandeza | Valor |
|---|---:|
| Massa de combustível | 20,0 kg |
| Densidade do querosene | 0,80 kg/L |
| Volume | 25,0 L = 25.000.000 mm³ |

Três formatos de mochila que fecham esse volume:

| Largura × altura | Profundidade |
|---|---:|
| 300 × 400 mm | 208 mm |
| 350 × 350 mm | 204 mm |
| 280 × 450 mm | 198 mm |

Posicione nas costas, centro aproximado em **(−220; 0; +50) mm**, atrás do tronco e
abaixo do bocal dorsal.

⚠ **Modele o tanque como duas peças:** o casco vazio, com a massa do material, e o
combustível, como sólido separado com 20,0 kg. O combustível queima e o casco não, e o
simulador precisa poder variar um sem o outro.

⚠ **Um tanque parcialmente cheio não tem densidade uniforme**, e a conversão de inércia
do simulador supõe uniformidade. Para o modelo conceitual, com tanque cheio, está
correto. Se for modelar tanque parcial, divida em sólidos separados.

### Passo 6 — Aviônica, linhas e fixação

Para fechar o orçamento de 12 kg de estrutura. Modele como blocos simples com massa
declarada:

| Item | Forma sugerida | Massa (kg) | Centro (x, y, z) mm |
|---|---|---:|---|
| unidade de controle e bateria | caixa 200 × 150 × 80 | 2,5 | (−180; 0; −120) |
| bomba e válvulas | cilindro ⌀90 × 140 | 1,5 | (−200; 0; +180) |
| linhas e cabeamento | 7 tubos ⌀12 | 1,8 | ao longo dos braços |
| cinto e arnês | caixa 420 × 230 × 30 | 2,4 | (0; 0; +200) |
| proteção térmica | cascas finas | 1,8 | junto às turbinas |
| berços e ferragem | incluído no passo 4 | 2,0 | nas pontas |
| **total** | | **12,0** | |

⚠ Esses 12 kg são **o número mais fraco do projeto inteiro**. A tabela acima é uma
decomposição plausível, não um levantamento. O valor do CAD é justamente substituí-la
por peças reais.

---

## 4. Materiais e densidades

O FreeCAD não sabe a massa de uma peça sem material atribuído. Duas rotas:

**Rota A, recomendada para o conceito:** declare a **massa** de cada peça diretamente
no arquivo de densidades. É o que as tabelas acima fazem.

**Rota B:** atribua densidade e deixe o volume calcular a massa.

| Material | Densidade (kg/m³) |
|---|---:|
| Alumínio 6061 | 2700 |
| Aço | 7850 |
| Titânio | 4500 |
| Fibra de carbono, laminado | 1600 |
| Querosene de aviação | 800 |

⚠ Ordem de grandeza para peça conceitual. Não substitui ficha de material.

**Formato do arquivo de densidades**, JSON, uma entrada por nome de objeto do FreeCAD:

```json
{
  "tronco":        { "mass_kg": 34.0, "material": "corpo humano" },
  "turbina_par0_dir": { "mass_kg": 2.20, "material": "Kingtech K-260G4" },
  "braco_par0_dir":   { "density_kg_m3": 1600, "material": "fibra de carbono" },
  "combustivel":      { "mass_kg": 20.0, "material": "querosene" }
}
```

O exportador **recusa** qualquer objeto que não tenha massa nem densidade declarada.
Ele não chuta material, porque chutar produziria inércia plausível e errada, que é o
pior resultado possível.

---

## 5. Exportação e verificação

### 5.1 Exportar

```bash
"C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py ^
    caminho/do/modelo.FCStd ^
    docs/decks/traje.json ^
    --z-para-baixo ^
    --densidades caminho/das/densidades.json
```

⚠ A marca `--z-para-baixo` afirma que o **documento já está** com z apontando para
baixo. Ela não converte nada. Usá-la num modelo com z para cima produz um deck
espelhado que o simulador aceita.

### 5.2 Verificar

```bash
./.venv/Scripts/python.exe -c "from hero_atlas.airframe.cad_deck import load_cad_deck; d = load_cad_deck('docs/decks/traje.json'); print(d.total_mass_kg); print(d.reconcile(127.4))"
```

O simulador **recusa** o deck se encontrar:

| Problema | Mensagem |
|---|---|
| z para cima | "deck exportado com z para cima" |
| volume nulo | sólido aberto ou malha não fechada no CAD |
| nome repetido | agregação silenciosamente errada |
| versão de esquema errada | deck antigo lido como novo |

E **avisa**, sem corrigir, se a massa do CAD divergir mais de 2% da massa contábil de
127,4 kg.

### 5.3 A conferência que você mesmo pode fazer

Antes de confiar no deck, modele **uma caixa de 100 × 200 × 300 mm com 1 kg** e exporte
só ela. A inércia sobre o próprio centro tem que dar:

```
I_xx = 1 × (0,200² + 0,300²) / 12 = 0,0108333 kg·m²
I_yy = 1 × (0,100² + 0,300²) / 12 = 0,0083333 kg·m²
I_zz = 1 × (0,100² + 0,200²) / 12 = 0,0041667 kg·m²
```

Se der isso, a cadeia está correta de ponta a ponta. Já existe um deck de demonstração
em `docs/decks/demo-caixa.json` que você pode comparar.

---

## 6. O que fazer quando não fecha

| Sintoma | Significado | Ação |
|---|---|---|
| Turbinas colidem com o corpo | geometria inviável | pare, volte à varredura com restrição de envelope |
| Massa total acima de 154,6 kg | o trim deixa de fechar com a K-260G4 | reduza estrutura ou combustível, ou suba de turbina |
| Centro de massa fora de 105 a 210 mm em x | trim não fecha | redistribua massa, ou a geometria muda |
| Inércia muito acima de diag(32; 32; 2,3) | veículo mais lento que o simulado | rode a varredura de atraso de novo com a inércia real |
| Jato atinge estrutura | perda de empuxo e dano térmico | reposicione, e o empuxo efetivo cai |

⚠ Os três primeiros são **reprovações**, não ajustes. Não mude a tabela de coordenadas
por conta própria: ela é saída de uma otimização de autoridade de controle, e mexer num
número quebra o resultado sem avisar.

---

## 7. Sobre construir a turbina

Você perguntou sobre um passo a passo de como construir um motor. Duas coisas separadas,
e a resposta é diferente para cada uma.

**Para o CAD, você não precisa de nenhuma.** A turbina entra no modelo como cilindro de
⌀120 × 299 mm com 2,20 kg e dois pontos de fixação. O interior dela não afeta massa,
centro, inércia nem envelope de forma que o simulador enxergue. Modelar o compressor
não muda nenhum número deste projeto.

**Para o projeto, construir não é o próximo passo, e não por prudência abstrata.** O
escopo que você declarou no início é simulação e engenharia virtual, sem hardware, e o
simulador acabou de mostrar que os quatro parâmetros que decidem a arquitetura **não
são publicados por nenhum fabricante**:

1. constante de tempo a degrau pequeno perto do ponto de operação;
2. taxa máxima de variação de empuxo, subindo e descendo;
3. atraso entre comando e início da resposta;
4. empuxo mínimo estável em voo, não em bancada.

Construir uma turbina não resolve nenhum dos quatro: resolver exige **medir**, em
bancada instrumentada, o que é outro projeto com outro orçamento e outro risco. Pedir
os quatro números a um fabricante custa um e-mail.

Se em algum momento o projeto for para hardware, a rota normal é **comprar** a
microturbina, como fazem Gravity, Zapata e JetPack Aviation. Nenhum deles fabrica o
motor.

---

## 8. Lista de verificação

Antes de exportar:

- [ ] unidades em milímetro, quatro decimais
- [ ] z apontando para baixo, ou rotação de 180° em x aplicada
- [ ] origem no plexo solar, plano médio, meia profundidade do tronco
- [ ] manequim completo, dez segmentos, 76,5 kg
- [ ] sete turbinas, ⌀120 × 299 mm, 2,20 kg cada, centro recuado 150 mm do bocal
- [ ] vetor de eixo de cada turbina conferido contra a tabela 2.2, quatro casas
- [ ] **portão do passo 3 passou**, cinco perguntas
- [ ] braços dimensionados para 178 N·m com fator 3
- [ ] tanque em duas peças, casco e combustível
- [ ] aviônica e fixação somando 12 kg
- [ ] arquivo de densidades cobrindo **todos** os objetos
- [ ] caixa de referência de 1 kg conferida contra a solução analítica

Depois de exportar:

- [ ] deck lido sem erro
- [ ] massa total entre 125 e 130 kg
- [ ] reconciliação sem aviso
- [ ] centro de massa em x entre 105 e 210 mm
- [ ] inércia comparada com diag(32,2; 32,2; 2,3)

---

## 9. Glossário, para quem for gerar o documento final

| Termo | Significado neste projeto |
|---|---|
| **Bocal** | propulsor, tratado como ponto de aplicação de força mais direção |
| **Trim** | o conjunto de empuxos que equilibra peso e momentos, sem acelerar |
| **Wrench** | o par força e momento, seis componentes, tratado como um vetor só |
| **Matriz de alocação** | mapeia empuxo de cada bocal para o wrench resultante |
| **Autoridade** | capacidade de produzir um momento pedido |
| **Margem estática** | o que seria atingível se os motores fossem instantâneos |
| **Margem de curto prazo** | o que é atingível dentro do horizonte, dado o limite de rampa |
| **Rampa** | taxa máxima de variação de empuxo, em newton por segundo |
| **Ponto de referência** | origem fixa no corpo, distinta do centro de massa |
| **Deck** | arquivo de dados que uma ferramenta pesada produz e o núcleo consome |
| **Envelope** | o espaço que uma peça ocupa, para verificação de interferência |

---

## 10. Números de referência, reunidos

Para conferência rápida enquanto modela.

| Grandeza | Valor |
|---|---:|
| Massa bruta alvo | 127,4 kg |
| Massa bruta máxima, com K-260G4 | 154,6 kg |
| Folga de massa | 27,2 kg |
| Piloto | 80,0 kg |
| Sete turbinas | 15,4 kg |
| Estrutura, tanques, aviônica | 12,0 kg |
| Combustível | 20,0 kg |
| Empuxo instalado, sete K-260G4 | 1785 N = 182 kgf |
| Empuxo por bocal no pairado | 209 N |
| Empuxo por bocal, teto da K-260G4 | 255 N |
| Momento de fixação, teto da K-260G4 | 132 N·m |
| Folga superior de empuxo a 127,4 kg | 17,6% |
| Centro de massa alvo, x | 105 a 210 mm |
| Inércia estimada | diag(32,2; 32,2; 2,3) kg·m² |
| Volume de combustível | 25,0 L |
| Turbina, envelope | ⌀120 × 299 mm |
| Turbina, envelope com folga | ⌀180 mm |
| Recuo do centro da turbina | 150 mm |
| Linha do ombro | 225 mm do plano médio |
| Banda de excitação a evitar | 550 a 1867 Hz |

⚠ **Nada aqui representa hardware.** A geometria é plausível e não medida, a massa é
estimada em bloco, o consumo é de catálogo extrapolado, e nenhuma tecnologia de
propulsão foi selecionada.
