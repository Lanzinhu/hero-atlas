# Ferramentas do FreeCAD: o que já vem, o que instalar, e as macros do projeto

**Estado em 2026-09-12.** FreeCAD 1.1.3, instalado em `C:\Program Files\FreeCAD 1.1`.

---

## 1. O que eu consigo fazer no seu FreeCAD, e o que não

| Consigo | Não consigo |
|---|---|
| Rodar o Python do FreeCAD sem interface | Clicar na interface |
| Criar e salvar documentos `.FCStd` | Ver a sua tela |
| Ler um documento seu e medir tudo | Reagir ao que você faz na hora |
| Calcular massa, centro e inércia | Desenhar com o mouse |
| Instalar macros que viram comandos no seu menu | Instalar addons pela loja |

O jeito que funciona é este: eu escrevo macro ou script, instalo na sua pasta, e você
roda pelo menu **Macro**. Já instalei três, e elas estão descritas abaixo.

⚠ Não há integração ao vivo. Se você mexer no modelo, eu só vejo depois de você salvar
e eu abrir o arquivo.

---

## 2. As três macros, já instaladas

Em `C:\Users\alanl\AppData\Roaming\FreeCAD\v1-1\Macro\`. Aparecem em **Macro > Macros**.

### `HeroAtlas_Galeria`

Constrói cinco tipos de propulsor **no mesmo empuxo**, lado a lado, com uma silhueta do
piloto para escala. Serve para estudar o que você pediu: por que uns tipos servem e
outros não.

A física vem do próprio simulador. Nenhum número é digitado duas vezes.

| Tipo | Diâmetro | Massa | N/kg | Área de disco | Potência |
|---|---:|---:|---:|---:|---:|
| Microturbina | 120 mm | 2,20 kg | 116 | 0,011 m² | não comparável |
| Ventilador entubado | 250 mm | 3,60 kg | 71 | 0,049 m² | **19,1 kW** |
| Ventilador entubado | 400 mm | 6,50 kg | 39 | 0,126 m² | 11,9 kW |
| Rotor aberto | 700 mm | 4,20 kg | 61 | 0,385 m² | 6,8 kW |
| Rotor aberto | 1100 mm | 7,80 kg | 33 | 0,950 m² | **4,3 kW** |

**A lição está nas duas linhas em negrito.** Os dois fazem o mesmo empuxo, e um consome
4,4 vezes a potência do outro. A diferença é só área de disco.

A microturbina não tem coluna de potência porque a comparação não existe: ela queima
combustível, o rotor consome eletricidade. Entre as duas o que se compara é empuxo por
massa e por volume.

⚠ São **envelopes**, não motores. Sem compressor, pá, mancal ou combustível. As massas
dos rotores são ordem de grandeza; só a microturbina tem massa de fabricante.

### `HeroAtlas_Conferir`

Abre o seu modelo, compara contra as tabelas do projeto, e não modifica nada. Reporta
posição, direção do eixo, diâmetro e comprimento de cada propulsor.

Pega especificamente o erro mais provável do passo de CAD:

```
par0_dir         294 mm  159 graus         ok           ok
               EIXO INVERTIDO. O corpo da turbina ficou no caminho do jato.
               Gire 180 graus, ou lembre: centro = saida + (L/2) * direcao.
```

Testada dos dois lados: aprova o modelo de referência e reprova um modelo com três
erros plantados de propósito.

### `HeroAtlas_Exportar`

Exporta o deck sem sair do FreeCAD. Procura `massas.json` ao lado do seu `.FCStd`.

⚠ **Recusa exportar se faltar massa em qualquer peça**, e imprime o modelo pronto para
copiar. Ela não chuta densidade: material chutado produz inércia plausível e errada, e
a simulação roda lisa com o número errado.

---

## 3. O que já vem no FreeCAD 1.1, e é o que você vai precisar

Sua instalação tem estas bancadas, sem instalar nada:

| Bancada | Para quê, neste projeto |
|---|---|
| **Part** | sólidos prontos. É a que o guia usa |
| **Part Design** | esboço, extrusão, peça paramétrica de verdade |
| **Assembly** | montagem com juntas. Nova na versão 1.0 |
| **FEM** | análise estrutural e **modos de vibração** |
| **Material** | banco de materiais com densidade |
| **Measure** | medir distância, ângulo, interferência |
| **TechDraw** | desenho técnico 2D a partir do 3D |
| **Spreadsheet** | planilha que dirige dimensões |
| **Sketcher** | croqui com restrições |
| **CAM**, **Mesh**, **Surface**, **Draft**, **BIM** | não precisa agora |

**Duas delas importam muito para este projeto e você já tem.**

**FEM** resolve dois requisitos que o simulador levantou e não consegue responder
sozinho: se o braço aguenta os **132 N·m** de flexão, e onde estão os **modos naturais**
da estrutura, que precisam ficar fora da faixa de 550 a 1867 Hz varrida pelo eixo da
turbina.

**Assembly** é o que permite montar o traje com juntas em vez de posicionar cada peça a
mão, e é onde a pose do piloto vira parâmetro em vez de número fixo.

---

## 4. Addons que valem a pena, e os que não

Instalação por **Ferramentas > Addon Manager**, dentro do próprio FreeCAD.

### Provavelmente úteis

| Addon | Para quê |
|---|---|
| **Fasteners** | parafusos e porcas de norma, prontos. Poupa modelar fixação |
| **Curves** | superfícies avançadas, se as carenagens virarem assunto |
| **Sheet Metal** | chapa dobrada, para berços e suportes |
| **Manipulator** | mover e alinhar objetos com mais controle |

### Provavelmente não

| Addon | Por quê não |
|---|---|
| **A2plus**, **Assembly3**, **Assembly4** | a bancada Assembly nativa da 1.0 já resolve, e misturar sistemas de montagem cria conflito |
| **CfdOF** | integra OpenFOAM, que exige o Subsistema Windows para Linux, não instalado. E aerodinâmica é marco tardio |
| **Render** | render bonito não muda número nenhum |

⚠ **Não instale por instalar.** Cada addon é código de terceiro que roda dentro do
FreeCAD, e addon que conflita com a bancada nativa produz comportamento estranho e
difícil de diagnosticar. Instale quando tiver uma tarefa concreta que peça.

---

## 5. Sobre estudar motores no CAD

Você disse que quer usar o FreeCAD para estudar como funcionam os motores e quais tipos
servem. Vale separar duas coisas, porque elas pedem ferramentas diferentes.

**Estudar qual tipo serve** é comparação de envelope, massa, área e potência. O CAD é
ótimo para isso, e a macro `HeroAtlas_Galeria` faz exatamente isso. É o que decide
arquitetura, e é onde o projeto está.

**Estudar como um motor funciona por dentro** é outra coisa: compressor, câmara,
turbina, mancal, sistema de combustível. Modelar isso no CAD ensina a **forma** das
peças, mas não ensina o que elas fazem, porque o que elas fazem é termodinâmica e
aerodinâmica, que o CAD não calcula.

Se essa parte te interessa, o caminho útil é diferente do CAD: é ciclo de Brayton no
papel, com compressão, combustão e expansão, e aí sim um modelo de desempenho. O
simulador do projeto já tem o consumo específico entrando como parâmetro; o que falta é
justamente a **curva de carga parcial**, que nenhum fabricante publica.

⚠ E vale repetir o que já está na especificação: os quatro números que decidem esta
arquitetura não saem de modelar o motor. Saem de **medir** um motor real em bancada
instrumentada, ou de pedir ao fabricante.

---

## 6. Como eu atualizo as macros

As macros moram em duas cópias:

```
tools/macros/                                      no repositório, versionado
C:\Users\alanl\AppData\Roaming\FreeCAD\v1-1\Macro\  onde o FreeCAD lê
```

Quando eu mudar uma, copio de novo. Se você editar a sua cópia e quiser que eu veja,
me avise, porque eu leio a do repositório.

Reinstalar todas:

```bash
cp tools/macros/*.FCMacro "/c/Users/alanl/AppData/Roaming/FreeCAD/v1-1/Macro/"
```
