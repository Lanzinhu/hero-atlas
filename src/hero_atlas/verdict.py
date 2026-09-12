"""Veredito de tres valores, compartilhado por todo o projeto.

Existe um so vocabulario porque a distincao e a mesma em toda parte:

    VIOLATED       o modelo diz **nao**, e isso e demonstravel
    INDETERMINATE  o modelo diz que **nao da para concluir**
    SATISFIED      o modelo diz **sim**, e isso e demonstravel

Fundir violado com indeterminado transforma lacuna de evidencia em veredito
negativo. Fundir indeterminado com satisfeito transforma lacuna de evidencia em
aprovacao. Os dois erros existem, sao simetricos, e os dois ja apareceram neste
projeto.

Rejeicao operacional e conclusao cientifica sao coisas diferentes:

    candidato_aceito    = veredito e SATISFIED
    candidato_rejeitado = veredito em {VIOLATED, INDETERMINATE}
    elegivel_como_conclusao = veredito em {SATISFIED, VIOLATED}

A rejeicao pode tratar os dois casos igual. **O dado e o relatorio, nunca.**
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Verdict"]


class Verdict(StrEnum):
    """Os tres valores. Ver o docstring do modulo para a semantica."""

    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INDETERMINATE = "indeterminate"

    @property
    def is_conclusive(self) -> bool:
        """Se o veredito e uma afirmacao sobre o objeto, e nao sobre a evidencia.

        ``INDETERMINATE`` nao diz nada sobre o sistema fisico. Diz que falta
        informacao para avaliar.
        """
        return self is not Verdict.INDETERMINATE

    @property
    def rejects(self) -> bool:
        """Se, operacionalmente, o candidato deve ser bloqueado.

        Verdadeiro tambem para ``INDETERMINATE``, porque nao demonstrado nao e
        aprovado. Mas isso **nao** o torna equivalente a ``VIOLATED``: use
        :attr:`is_conclusive` antes de escrever qualquer frase sobre o porque.
        """
        return self is not Verdict.SATISFIED
