"""Leitor do deck de CAD: propriedades de massa vindas de fora, sem importar CAD.

⚠ **Este modulo nao importa FreeCAD, e nao pode.** O nucleo importa apenas NumPy,
SciPy e pydantic, verificado por varredura de arvore sintatica. A ferramenta pesada
roda num processo separado, escreve um arquivo, e o nucleo le o arquivo. E a mesma
arquitetura declarada para todo deck do projeto.

E aqui ha uma razao dura alem da arquitetural: o FreeCAD 1.1 traz Python 3.11 e o
projeto roda em 3.12. O modulo ``FreeCAD.pyd`` e binario compilado para 3.11 e **nao
importa** em 3.12. Dois processos nao e preferencia, e a unica rota possivel.

Conversao de unidade, que e onde este deck pode mentir em silencio:

    O FreeCAD devolve o tensor de inercia para **densidade unitaria**, com
    comprimento em milimetro. O numero que sai tem grandeza de volume vezes area,
    nao de massa vezes area.

        I_kg_m2 = I_freecad * (massa_kg / volume_mm3) * 1e-6

    Esquecer o fator ``1e-6`` produz inercia um milhao de vezes maior, o que e
    obvio. Esquecer a divisao pelo volume produz inercia errada por um fator da
    ordem da densidade, o que **nao** e obvio e passa despercebido: a simulacao
    continua rodando e o veiculo so fica preguicoso demais.

Por isso a conversao mora aqui, com teste que a prende contra solucao analitica de
caixa e de cilindro, em vez de ficar espalhada no script de exportacao.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .mass_properties import MassComponent

__all__ = [
    "CadDeckError",
    "CadComponentRecord",
    "CadDeck",
    "inertia_from_freecad",
    "load_cad_deck",
]

DECK_SCHEMA_VERSION = 1
MM_TO_M = 1.0e-3
MM2_TO_M2 = 1.0e-6


class CadDeckError(ValueError):
    """Deck de CAD malformado, incoerente ou de versao desconhecida."""


def inertia_from_freecad(
    matrix_mm5: NDArray[np.float64] | list[list[float]],
    *,
    mass_kg: float,
    volume_mm3: float,
) -> NDArray[np.float64]:
    """Converte o tensor do FreeCAD para quilograma metro quadrado.

        I_kg_m2 = I_freecad * (massa_kg / volume_mm3) * 1e-6

    O FreeCAD calcula com densidade unitaria, entao o "massa" embutido no tensor e o
    **volume em milimetro cubico**. Dividir pelo volume remove essa massa ficticia; a
    massa real entra multiplicando; e ``1e-6`` leva milimetro quadrado a metro
    quadrado.

    ⚠ A conversao supoe **densidade uniforme** na peca. Uma peca com densidade
    variavel, por exemplo um tanque parcialmente cheio ou um motor com o rotor mais
    denso que a carcaca, precisa ser modelada como pecas separadas, cada uma
    uniforme. Escalar o tensor de uma peca heterogenea pela massa total da um
    resultado errado que nada neste modulo consegue detectar.
    """
    if not math.isfinite(mass_kg) or mass_kg <= 0.0:
        raise CadDeckError(f"massa precisa ser positiva e finita, recebeu {mass_kg!r}")
    if not math.isfinite(volume_mm3) or volume_mm3 <= 0.0:
        raise CadDeckError(
            f"volume precisa ser positivo e finito, recebeu {volume_mm3!r}. "
            "Volume nulo costuma significar solido aberto ou malha nao fechada no CAD."
        )

    tensor = np.asarray(matrix_mm5, dtype=np.float64)
    if tensor.shape != (3, 3):
        raise CadDeckError(f"tensor de inercia deve ter forma (3, 3), recebeu {tensor.shape}")

    return tensor * (mass_kg / volume_mm3) * MM2_TO_M2


@dataclass(frozen=True, slots=True)
class CadComponentRecord:
    """Uma peca exportada do CAD, ainda em milimetro e densidade unitaria."""

    name: str
    mass_kg: float
    volume_mm3: float
    center_of_mass_mm: NDArray[np.float64]
    inertia_matrix_freecad: NDArray[np.float64]
    orientation_body_from_component: NDArray[np.float64]
    material: str = "nao declarado"

    def to_mass_component(self) -> MassComponent:
        """Converte para a interface que o agregador consome.

        ⚠ O tensor sai **sobre o centro da propria peca**, que e o que o agregador
        espera. O FreeCAD tambem calcula sobre o centro da peca, entao nao ha
        translacao a desfazer aqui. Se algum dia a exportacao passar a dar o tensor
        sobre a origem do documento, esta funcao precisa **subtrair** os eixos
        paralelos, e nao apenas escalar.
        """
        return MassComponent(
            name=self.name,
            mass_kg=self.mass_kg,
            center_of_mass_body_m=np.asarray(self.center_of_mass_mm, dtype=np.float64) * MM_TO_M,
            inertia_about_own_cg_kg_m2=inertia_from_freecad(
                self.inertia_matrix_freecad,
                mass_kg=self.mass_kg,
                volume_mm3=self.volume_mm3,
            ),
            orientation_body_from_component=self.orientation_body_from_component,
        )


@dataclass(frozen=True, slots=True)
class CadDeck:
    """Um arquivo de propriedades de massa vindo do CAD.

    Attributes:
        source_document: nome do arquivo de CAD que gerou o deck.
        exported_at: quando. A reconciliacao precisa saber se o deck envelheceu.
        z_axis_down: se o documento ja estava na convencao do projeto. **Obrigatorio
            e verificado**: o projeto usa z para baixo e quase todo CAD usa z para
            cima, e um deck exportado sem espelhar produz sinal trocado em toda
            posicao vertical.
    """

    source_document: str
    exported_at: str
    z_axis_down: bool
    components: tuple[CadComponentRecord, ...]
    schema_version: int = DECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DECK_SCHEMA_VERSION:
            raise CadDeckError(
                f"deck de versao {self.schema_version}, esperada {DECK_SCHEMA_VERSION}"
            )
        if not self.components:
            raise CadDeckError("deck sem nenhum componente")
        if not self.z_axis_down:
            raise CadDeckError(
                "deck exportado com z para cima. O projeto usa z para BAIXO, conforme "
                "ADR-001, e importar sem espelhar troca o sinal de toda posicao "
                "vertical. Corrija na exportacao, nao na leitura: consertar aqui "
                "esconderia o problema de quem abrir o arquivo de CAD."
            )
        nomes = [c.name for c in self.components]
        repetidos = {n for n in nomes if nomes.count(n) > 1}
        if repetidos:
            raise CadDeckError(f"nomes de componente repetidos no deck: {sorted(repetidos)}")

    @property
    def total_mass_kg(self) -> float:
        return sum(c.mass_kg for c in self.components)

    def to_mass_components(self) -> tuple[MassComponent, ...]:
        return tuple(c.to_mass_component() for c in self.components)

    def reconcile(self, accounting_mass_kg: float, *, tolerance: float = 0.02) -> str | None:
        """Compara a massa do CAD com a massa contabil. Devolve aviso, ou ``None``.

        ⚠ A fonte de verdade e a **massa contabil**, nao o CAD. O CAD produz
        propriedades de uma geometria assumida: material errado, parede fina demais,
        peca faltando. Divergencia e sinal de que alguem precisa olhar, e o projeto
        prefere um aviso explicito a uma substituicao silenciosa.
        """
        if accounting_mass_kg <= 0.0:
            raise CadDeckError("massa contabil precisa ser positiva")
        diferenca = self.total_mass_kg - accounting_mass_kg
        relativa = abs(diferenca) / accounting_mass_kg
        if relativa <= tolerance:
            return None
        return (
            f"massa do CAD {self.total_mass_kg:.2f} kg contra massa contabil "
            f"{accounting_mass_kg:.2f} kg: diferenca de {diferenca:+.2f} kg, "
            f"{relativa:.1%}, acima da tolerancia de {tolerance:.0%}"
        )


def _vetor(dados: Any, nome: str) -> NDArray[np.float64]:
    arr = np.asarray(dados, dtype=np.float64)
    if arr.shape != (3,):
        raise CadDeckError(f"{nome} deve ter tres componentes, recebeu {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise CadDeckError(f"{nome} tem valor nao finito")
    return arr


def load_cad_deck(path: str | Path) -> CadDeck:
    """Le um deck escrito por ``tools/freecad_export.py``.

    Raises:
        CadDeckError: arquivo ausente, malformado, de versao errada, com componente
            repetido, com volume nulo ou exportado com z para cima.
    """
    caminho = Path(path)
    if not caminho.is_file():
        raise CadDeckError(f"deck nao encontrado: {caminho}")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise CadDeckError(f"deck {caminho} nao e JSON valido: {erro}") from erro

    try:
        componentes = tuple(
            CadComponentRecord(
                name=str(item["name"]),
                mass_kg=float(item["mass_kg"]),
                volume_mm3=float(item["volume_mm3"]),
                center_of_mass_mm=_vetor(item["center_of_mass_mm"], f"{item['name']}.centro"),
                inertia_matrix_freecad=np.asarray(item["inertia_matrix"], dtype=np.float64),
                orientation_body_from_component=np.asarray(
                    item.get("orientation", np.eye(3).tolist()), dtype=np.float64
                ),
                material=str(item.get("material", "nao declarado")),
            )
            for item in dados["components"]
        )
    except (KeyError, TypeError, ValueError) as erro:
        raise CadDeckError(f"deck {caminho} com componente malformado: {erro}") from erro

    return CadDeck(
        source_document=str(dados.get("source_document", "desconhecido")),
        exported_at=str(dados.get("exported_at", "desconhecido")),
        z_axis_down=bool(dados.get("z_axis_down", False)),
        components=componentes,
        schema_version=int(dados.get("schema_version", 0)),
    )
