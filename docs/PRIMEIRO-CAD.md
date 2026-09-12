# Primeiro CAD — sua primeira hora no FreeCAD

**Para quem nunca modelou nada.** Estado em 2026-09-12.

Três exercícios, em ordem. No fim da primeira hora você terá um arquivo que o simulador
lê e confere sozinho. Depois disso, o [guia de modelagem](GUIA-MODELAGEM.md) faz sentido.

⚠ **Não instale outro programa.** O FreeCAD 1.1.3 já está instalado nesta máquina e é o
único que a ponte de exportação do projeto lê. Fusion 360 salva em `.f3d`, que o
exportador não abre, e a versão gratuita dele tem restrição de uso comercial.

---

## Antes de começar: três ajustes

Abra o FreeCAD e configure, em `Editar > Preferências > Geral > Unidades`:

| Campo | Valor |
|---|---|
| Sistema de unidades | Padrão (mm, kg, s, graus) |
| Número de decimais | **4** |

Quatro casas importa. Com duas, um vetor de direção `0,2506` aparece como `0,25` e você
não consegue conferir contra a tabela do projeto.

Depois, no seletor de bancada no topo da janela, escolha **Part**. Não é a Part Design.
A bancada Part tem sólidos prontos, que é tudo de que você precisa aqui.

---

## Exercício 1 — A caixa de calibração

**Por que uma caixa e não um motor.** Porque a caixa tem resposta conhecida. Se o número
que sai do seu modelo bater com a fórmula do livro, a cadeia inteira está correta: o
modelo, as unidades, a exportação e a leitura. Se você começar pelo motor, e o número
sair errado, você não vai saber em qual dos quatro passos está o erro.

### O que fazer

1. `Arquivo > Novo`.
2. Na bancada Part, clique no ícone da **caixa** (um cubo). Ela aparece na árvore, à
   esquerda, com o nome `Box`.
3. Clique em `Box` na árvore. O painel de propriedades aparece embaixo, na aba **Dados**.
4. Preencha:

| Propriedade | Valor |
|---|---:|
| Length | 100 mm |
| Width | 200 mm |
| Height | 300 mm |

5. Clique duas vezes devagar no nome `Box` na árvore para renomear. Chame de
   `caixa_de_calibracao`.
6. `Arquivo > Salvar como`, em `docs/decks/meu-primeiro.FCStd`.

### O arquivo de massa

O FreeCAD sabe o **volume** da sua caixa, mas não sabe a **massa**: isso depende do
material. O projeto exige que você declare, e o exportador **recusa** qualquer peça sem
massa ou densidade. Ele nunca chuta material, porque chutar produziria uma inércia
plausível e errada, que é o pior resultado possível.

Crie um arquivo `docs/decks/minhas-massas.json`:

```json
{
  "caixa_de_calibracao": { "mass_kg": 1.0, "material": "fictício, para calibração" }
}
```

### Exportar

```bash
cd "C:/Users/alanl/OneDrive/Desktop/Projetos/Hero_Atlas"

"C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py ^
    docs/decks/meu-primeiro.FCStd ^
    docs/decks/meu-primeiro.json ^
    --z-para-baixo ^
    --densidades docs/decks/minhas-massas.json
```

### Conferir

```bash
./.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); import numpy as np; from hero_atlas.airframe.cad_deck import load_cad_deck; c = load_cad_deck('docs/decks/meu-primeiro.json').to_mass_components()[0]; print(np.diag(c.inertia_about_own_cg_kg_m2).round(7))"
```

**Deve sair exatamente isto:**

```
[0.0108333 0.0083333 0.0041667]
```

Confira com a fórmula de caixa, que está em qualquer livro de mecânica:

```
I_xx = m(b² + c²)/12 = 1 × (0,200² + 0,300²)/12 = 0,0108333
I_yy = m(a² + c²)/12 = 1 × (0,100² + 0,300²)/12 = 0,0083333
I_zz = m(a² + b²)/12 = 1 × (0,100² + 0,200²)/12 = 0,0041667
```

**Se bateu, a cadeia inteira está correta e você pode confiar nela.** Guarde essa caixa:
ela é o teste que você refaz sempre que mexer no processo.

### O que deu errado, se deu

| Mensagem | Causa |
|---|---|
| "sem massa nem densidade declarada" | o nome no JSON não bate com o nome na árvore do FreeCAD |
| "deck exportado com z para cima" | faltou a marca `--z-para-baixo` |
| "volume precisa ser positivo" | o objeto não é um sólido fechado |
| números mil vezes maiores | você mudou as unidades para metro em algum lugar |

---

## Exercício 2 — O cilindro do propulsor

Agora sim, o "motor". Mas ele não é um motor: é o **envelope** dele. O simulador só
precisa saber que espaço ele ocupa, quanto pesa e para onde empurra. O compressor por
dentro não muda nenhum número.

### O que fazer

1. No mesmo documento, clique no ícone do **cilindro** na bancada Part.
2. Nas propriedades:

| Propriedade | Valor | Por quê |
|---|---:|---|
| Radius | 60 mm | metade de ⌀120, a Kingtech K-260G4 |
| Height | 299 mm | comprimento de catálogo |

3. Renomeie para `turbina_dorsal`.
4. Acrescente ao arquivo de massas:

```json
"turbina_dorsal": { "mass_kg": 2.20, "material": "Kingtech K-260G4" }
```

### Posicionar, que é a parte que importa

Um cilindro na origem não serve para nada. Ele precisa estar **onde o propulsor fica** e
apontando **para onde o propulsor empurra**.

O bocal dorsal é o mais fácil de todos, porque aponta reto para cima. Na tabela do
projeto ele tem:

| | Valor |
|---|---|
| Saída do bocal | (−150; 0; +100) mm |
| Direção de empuxo | (0; 0; −1) |

⚠ **Lembre que +z aponta para BAIXO.** Então `(0; 0; −1)` é para cima. E a saída em
`z = +100` está **abaixo** da origem, nas costas.

**Onde fica o centro do cilindro.** A base do cilindro fica na saída, e ele cresce no
sentido do empuxo, porque o corpo da turbina está a montante do bocal. O jato sai para
baixo; a turbina fica em cima.

```
centro = saída + (299/2) × direção
       = (−150; 0; +100) + 149,5 × (0; 0; −1)
       = (−150; 0; −49,5) mm
```

No FreeCAD, expanda a propriedade **Placement** do cilindro e preencha a posição da
**base**, não do centro:

| Campo | Valor |
|---|---:|
| Position x | −150 mm |
| Position y | 0 mm |
| Position z | +100 mm |
| Angle | 180° |
| Axis x | 1 |

A rotação de 180° em torno de x vira o cilindro, que por padrão cresce no +z, para
crescer no −z.

### Conferir

Exporte de novo e leia:

```bash
./.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); from hero_atlas.airframe.cad_deck import load_cad_deck; [print(f'{c.name:22} {(c.center_of_mass_body_m*1000).round(1)}') for c in load_cad_deck('docs/decks/meu-primeiro.json').to_mass_components()]"
```

O centro da turbina deve sair em `[-150. 0. -49.5]`.

⚠ **Se sair `[-150. 0. 249.5]`**, você girou o cilindro para o lado errado, ou não girou.
O centro ficou **abaixo** da saída, ou seja no caminho do jato. Esse é o erro de sinal
mais comum deste passo inteiro.

---

## Exercício 3 — Conferir contra o gabarito

O projeto tem um modelo de referência completo, gerado por script, com a caixa de
calibração e os sete propulsores nos lugares certos.

```bash
"C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_reference_model.py docs/decks/referencia
```

Isso cria `docs/decks/referencia/referencia.FCStd`. **Abra esse arquivo no FreeCAD** e
compare com o seu: clique em cada cilindro e olhe o Placement.

Depois exporte e leia:

```bash
"C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py ^
    docs/decks/referencia/referencia.FCStd ^
    docs/decks/referencia/referencia.json ^
    --z-para-baixo ^
    --densidades docs/decks/referencia/densidades.json
```

Resultado esperado: **8 componentes, 16,40 kg**, sendo 1,00 kg de caixa e 15,40 kg das
sete turbinas. O centro agregado das turbinas sai em (132,9; 0; −336,1) mm, ou seja
336 mm **acima** da origem, que é onde braço fica.

⚠ Use o gabarito para **conferir**, não para copiar. O valor do exercício está em você
errar o sinal do cilindro uma vez e descobrir sozinho, porque esse é o erro que vai
aparecer de novo quando você modelar os outros seis.

---

## O que você aprendeu, e o que ainda não

**Aprendeu:** criar sólidos, dar dimensão, posicionar com Placement, girar com eixo e
ângulo, declarar massa, exportar, e conferir contra solução analítica.

**Não aprendeu, e não precisa ainda:** esboço e extrusão, restrições paramétricas,
operações booleanas, montagem, desenho técnico, chanfro, filete. Nada disso é necessário
para o que o projeto pede, porque o simulador só consome massa, centro, inércia e
envelope.

Se depois você quiser aprender esboço e extrusão de verdade, a bancada é a **Part
Design**, e o caminho é diferente: croqui num plano, restrições, e só então o sólido.
Para este projeto, a bancada Part com sólidos prontos basta e erra menos.

---

## O que vem depois

O [guia de modelagem](GUIA-MODELAGEM.md), que tem as coordenadas dos sete propulsores, o
manequim do piloto em dez segmentos, o orçamento de massa e o **portão de envelope**: a
pergunta de se tudo isso cabe num corpo humano.

⚠ Esse portão pode reprovar. As coordenadas saíram de uma varredura que otimizou
autoridade de controle e nunca perguntou se um corpo acomoda o resultado. Se não couber,
pare e avise: a geometria muda e o trabalho de modelagem recomeça.

---

## Glossário mínimo

| Termo | O que é no FreeCAD |
|---|---|
| **Documento** | o arquivo `.FCStd`, que guarda tudo |
| **Árvore** | a lista à esquerda, com os objetos do documento |
| **Bancada** | o conjunto de ferramentas ativo; use **Part** |
| **Sólido** | forma fechada, com volume. Só sólidos exportam |
| **Placement** | posição mais rotação de um objeto |
| **Data** | a aba de propriedades numéricas, embaixo à esquerda |
| **Recompute** | recalcular o modelo depois de mudar algo |
