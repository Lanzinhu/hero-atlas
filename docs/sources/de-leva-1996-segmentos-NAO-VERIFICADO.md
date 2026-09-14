# Registro de fonte — de Leva (1996), segmentos corporais

**Estado: NÃO VERIFICADO.** Os valores usados pelo projeto **não** foram conferidos em
documento legível. Este registro existe para dizer isso, e para registrar como se
chegou até aqui.

---

## Referência

| Campo | Valor |
|---|---|
| Título | Adjustments to Zatsiorsky-Seluyanov's segment inertia parameters |
| Autor | Paolo de Leva |
| Periódico | Journal of Biomechanics |
| Ano, volume, páginas | 1996, 29, 1223–1230 |
| Data das tentativas | 2026-09-13 |

A referência bibliográfica em si está confirmada por várias fontes independentes. **Os
números da tabela não estão.**

---

## Valores usados, e o grau de confiança em cada um

Frações de massa para homens, usadas em `tools/freecad_mannequin.py`:

| Segmento | Fração | Confiança |
|---|---:|---|
| Cabeça e pescoço | 0,0694 | resumo automático de busca |
| Tronco | 0,4346 | resumo automático de busca |
| Braço | 0,0271 | resumo automático de busca |
| Antebraço | 0,0162 | resumo automático de busca |
| Mão | 0,0061 | resumo automático de busca |
| Coxa | 0,1416 | resumo automático de busca |
| Perna | 0,0433 | resumo automático de busca |
| Pé | 0,0137 | resumo automático de busca |

A soma, contando os dois lados dos membros, dá 1,000. Isso é **consistência interna**,
não verificação: uma tabela errada também pode somar um.

**Centro de massa por segmento e raio de giração não são usados.** O manequim tira os
dois da geometria de cada sólido primitivo, com densidade uniforme assumida.

---

## Todas as rotas tentadas, e por que falharam

| Rota | Resultado |
|---|---|
| PDF do artigo, espelho universitário | baixado, mas é **imagem escaneada**; extração de texto deu zero caracteres |
| Wiki do Visual3D, duas URLs | HTTP 500 |
| Wiki do Visual3D, exportação em PDF | HTTP 500 |
| Página de curso, Oregon State | HTTP 403 |
| Página de curso, Universidade de Delaware | HTTP 403 |
| ExRx | HTTP 403 |
| Artigo PMC6905426 | cita de Leva só como base de comparação, sem imprimir a tabela |
| Artigo PMC5430500 | cita de Leva para definir comprimentos, sem imprimir valores |
| Suplemento CDC | PDF de imagem, sem tabela legível |
| arXiv 1805.05330 | PDF sem texto extraível |

---

## ⚠ Incidente: números órfãos, descartados

Um resumo automático de busca apresentou estes valores de inércia do corpo inteiro,
para adultos de IMC normal em pé:

```
anteroposterior 11,99 ± 0,45 kg·m²
mediolateral    11,39 ± 0,53 kg·m²
longitudinal     1,30 ± 0,06 kg·m²
```

O resumo os atribuiu ao artigo **PMC6726190**. Lido diretamente, esse artigo **não
contém valor de inércia nenhum**: mede oscilação postural por plataforma de força. O
artigo **PMC11687818**, próximo nos resultados, também não os contém.

**Os três números foram descartados**, apesar de plausíveis e de terem sido repetidos
numa mensagem anterior. O padrão se repetiu numa busca seguinte, cujo resumo afirmou
que "perna 0,4395" coincidia com "44,59" na mesma frase.

A lição que o projeto registra: **resumo automático de busca não é fonte.** Ele serve
para achar o documento; o número só entra depois de lido no documento.

---

## Divergência entre tabelas aceitas

Três tabelas de uso corrente dão, para a fração de massa da coxa masculina:

| Tabela | Coxa |
|---|---:|
| Dempster (1955), via Winter | 0,100 |
| Dumas e Wojtusch (2018) | 0,123 |
| de Leva (1996) | 0,1416 |

⚠ Esses três valores também vieram de resumos de busca, **não verificados**. Mas a
divergência, em si, é consistente com o que um artigo aberto de fato afirma: comparadas
com densitometria em pessoas reais, previsões por tabela tiveram **erro médio de até
60%** por indivíduo (PMC6905426, lido diretamente).

É por isso que o manequim **não** é validado segmento a segmento, e sim no corpo
inteiro, contra a única fonte confirmada: [Matsuo et al. (1995)](matsuo-1995-inercia-corpo-inteiro.md).

---

## Para sair do estado não verificado

Uma destas basta:

1. obter o artigo por acesso institucional e transcrever a tabela 4;
2. achar reprodução da tabela em HTML ou PDF com texto;
3. trocar por uma tabela verificável, e registrar a troca.
