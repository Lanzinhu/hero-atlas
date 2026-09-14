# Registro de fonte — Anny, modelo paramétrico de corpo humano (NAVER Labs, 2025)

**Tipo de registro:** registro de **software**, não de número medido. O projeto consome
uma malha gerada, não um valor publicado.

**Estado:** instalado e executado localmente. O que está abaixo foi **lido no código
instalado** ou **medido na saída**, não tirado de resumo de busca.

---

## Origem

| Campo | Valor |
|---|---|
| Nome | Anny |
| Autores | Brégier R, Fiche G, Bravo-Sánchez L, Lucas T, Armando M, Weinzaepfel P, Rogez G, Baradel F |
| Artigo | Human Mesh Modeling for Anny Body, arXiv 2511.03589, 2025 |
| Código | https://github.com/naver/anny |
| Versão instalada | `0.6.1.dev1+g81ca83e20`, instalada do repositório em 2026-09-13 |
| Licença do código | Apache 2.0 |
| Licença da malha | CC0 1.0, ativos do MakeHuman adaptados do MPFB2 |
| Tipo de fonte | `derived`, modelo gerador |
| Classe de evidência | `inferred` para forma e massa |

---

## O que foi lido no código instalado

| Item | Valor | Onde |
|---|---|---|
| Massa | volume × **980 kg/m³**, constante | `anny/anthropometry.py`, `mass()` |
| Altura | extensão vertical da malha em repouso | `anny/anthropometry.py`, `height()` |
| Parâmetros de fenótipo | `gender, age, muscle, weight, height, proportions`, em [0, 1] | `model.phenotype_labels` |
| Esqueleto padrão | 104 ossos | `model.bone_labels` |
| Topologia padrão | 13 718 vértices, 27 420 triângulos | `model.template_vertices`, `model.faces` |
| Referencial | metros, z para cima, frente em −y, esquerda do sujeito em +x | medido na saída: dedos do pé em y < 0, ossos `.L` em x > 0 |

## O que foi medido na saída

| Medida | Valor |
|---|---|
| `gender = 0` | homem: mais alto, mais pesado, ombros mais largos. **O tutorial do Anny chama `gender = 1` de mulher**; conferido por imagem e por medida |
| `weight` acima de 1 | satura: 1,5 dá a mesma massa que 1,0 |
| Massa máxima a 1750 mm, `weight = muscle = 1` | 78,67 kg, abaixo dos 80 kg do manequim de primitivos |
| Malhas geradas nas duas poses | fechadas, `trimesh.is_watertight` verdadeiro |

---

## O que a fonte não publica

1. **Nenhuma distribuição de densidade.** A massa sai de volume por densidade uniforme.
   Centro e inércia calculados sobre a malha são de um sólido homogêneo, não de um corpo.
2. **Nenhuma população medida por trás de cada parâmetro.** Os próprios autores escrevem,
   no tutorial de forma, que os fenótipos são baseados em preconceitos de artistas do
   MakeHuman sobre traços humanos. O artigo menciona calibração por dados antropométricos
   da OMS; **isso não foi conferido** neste projeto.
3. **Nenhum percentil.** Não há como pedir "homem percentil 50" diretamente.
4. **Nenhuma deformação de tecido por carga**, como arnês apertando o tronco.

---

## Onde é consumido

| Arquivo | Uso |
|---|---|
| `tools/corpo_anny.py` | gera `docs/decks/corpo/`, em ambiente separado `.venv-corpo` |
| `tools/freecad_envelope_gate.py` | com argumento STL, mede folga e invasão contra a malha |

⚠ **Não entra no núcleo.** O núcleo continua importando só numpy, scipy e pydantic. As
propriedades de massa do projeto continuam vindo do manequim de segmentos; a malha
serve para **forma** e, no máximo, para conferir ordem de grandeza da inércia.
