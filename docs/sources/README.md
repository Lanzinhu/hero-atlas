# Fontes externas

Todo número que entra no projeto vindo de fora tem um registro aqui, com origem, data
de consulta e o que a fonte **não** publica.

## Índice e hashes

Os hashes abaixo são do **registro**, não do documento original. Eles detectam alteração
do registro, não alteração da página de origem.

| Registro | SHA-256 |
|---|---|
| `anny-naver-2025-corpo-parametrico.md` | `b20db8b35a3f0559a7d46c48e785b8a6a7cd83a02192cb8ae0cce06ac97a4421` |
| `de-leva-1996-segmentos-NAO-VERIFICADO.md` | `4f2aea7e6a436632b1c40fe6ce9207e7ea707dbfab5f8ed7d213481a3d8da094` |
| `jetcat-p400-pro-ln-2026-09-12.md` | `d7cf1cb7a5a109697a4e0d16c587484198f154eb66d087d9603903491a6b234e` |
| `kingtech-k210-k260-2026-09-12.md` | `a9e2c8e1e096fae07dba085f3a769fa8b7687500cb5f40313f80653e58f7a373` |
| `matsuo-1995-inercia-corpo-inteiro.md` | `edde82b4de7439736347cc4f8b80893ad28dacde308e2c0868b16d845c9bd54b` |

Recalcular:

```bash
sha256sum docs/sources/*.md
```

## ⚠ Esta pasta ainda não satisfaz o ADR-007

O regime de procedência do projeto pede **cópia do documento original** com hash do
arquivo copiado. O que existe aqui são **transcrições**: os valores lidos, a origem e a
data.

A diferença importa. Com uma cópia arquivada, uma alteração silenciosa na página do
fabricante seria detectável. Com transcrição, não é: o registro diz apenas o que foi
lido e quando.

Escalonando por força de evidência, do mais fraco ao mais forte:

| Nível | O que é | Estado |
|---|---|---|
| 1 | número citado em texto, sem origem | eliminado do projeto |
| 2 | transcrição com origem e data | **onde estamos** |
| 3 | cópia do documento com hash | pendente |
| 4 | medição própria em bancada | fora do escopo, sem hardware |

## O padrão que os registros seguem

Cada registro traz, obrigatoriamente:

1. **tipo de registro**, dizendo se é cópia ou transcrição;
2. origem, data e tipo de fonte;
3. valores transcritos, com unidade, sem conversão;
4. derivações feitas pelo projeto, com a fórmula;
5. **o que a fonte não publica**, que costuma ser a parte mais útil;
6. onde o registro é consumido no código.

O item cinco existe porque a lacuna é resultado. No caso das microturbinas, o que falta
nas fichas é exatamente o que decide a dinâmica da arquitetura.
