# Registro de fonte — Matsuo et al. (1995), inércia do corpo inteiro

**Tipo de registro:** transcrição do resumo, **não** cópia arquivada do artigo.

**Estado:** verificado no resumo indexado. É a **única** fonte de inércia humana deste
projeto com origem confirmada.

---

## Origem

| Campo | Valor |
|---|---|
| Título | Moment of inertia of whole body using an oscillating table in adolescent boys |
| Autores | Matsuo A, Ozawa H, Goda K, Fukunaga T |
| Periódico | Journal of Biomechanics |
| Ano, volume, páginas | 1995, 28, 219–223 |
| Identificador | PMID 7896864 |
| Como foi lido | resumo via API REST do Europe PMC, `EXT_ID:7896864 AND SRC:MED` |
| Data de consulta | 2026-09-13 |
| Tipo de fonte | `literature` |
| Classe de evidência | `measured`, mesa oscilante |

⚠ O PubMed recusou a leitura por exigir cookie. O resumo foi obtido pela API do Europe
PMC, que indexa o mesmo registro.

---

## Valores transcritos, verbatim do resumo

| Grandeza | Valor |
|---|---|
| Amostra | 117 rapazes, ensino fundamental e médio, 13 a 18 anos |
| Método | mesa oscilante |
| Faixa de Imx | 5,6 a 14,0 kg·m² |
| Faixa de Imy | 4,2 a 13,5 kg·m² |
| Erro de estimativa | ±5% |

```
Imx = 3.44 Ht2 + 0.144 W - 8.04   (R = 0.973)   postura supina
Imy = 3.52 Ht2 + 0.125 W - 7.78   (R = 0.972)   postura recumbente
```

`Ht` em metro, `W` em quilograma, momento em kg·m².

---

## O que esta fonte NÃO cobre, e todas as quatro importam aqui

| Lacuna | Consequência para o projeto |
|---|---|
| **Adolescentes**, não adultos | um piloto adulto de 80 kg é extrapolação da regressão |
| **Deitado**, não em pé | comparável ao corpo reto em pé, não à pose de pairado |
| **Braços junto ao corpo** | não diz nada sobre braços à frente |
| **Eixo longitudinal ausente** | só dois eixos transversais; nada para `Izz` |

⚠ **Mapeamento de eixos incerto.** O resumo nomeia `Imx` e `Imy` sem definir, no
texto disponível, qual é o eixo frontal e qual o sagital. O projeto compara os dois
momentos transversais do manequim contra os dois valores, sem afirmar a correspondência.

---

## Derivação feita pelo projeto

Para o piloto de referência, 1,75 m e 80 kg:

```
Imx = 3.44 × 1.75² + 0.144 × 80 − 8.04 = 14.02 kg·m²
Imy = 3.52 × 1.75² + 0.125 × 80 − 7.78 = 13.00 kg·m²
```

⚠ **Extrapolação.** Fora da população medida em idade e, provavelmente, na composição
corporal.

---

## Onde este registro é usado

- `tools/freecad_mannequin.py`, validação da pose anatômica
- `docs/sources/README.md`, índice de fontes
