"""Ramos de tecnologia de propulsao, e a recusa estrutural de escolher um cedo demais.

Este modulo existe por causa de um erro concreto e registrado. Depois do experimento
1, com **zero** dinamica implementada, o projeto produziu a frase "recomendacao:
combustao". A revisao externa recusou, com razao:

    Os resultados atuais nao selecionam um motor nem aprovam uma tecnologia. Eles
    mostram que, sob as hipoteses de massa, energia e geometria avaliadas, certas
    metas de autonomia eletrica exigem area propulsiva potencialmente incompativel
    com a arquitetura vestivel de bracos vetorizados.

A diferenca entre as duas frases nao e de tom, e de conteudo. "Combustao aprovada"
exigiria que a familia de atraso e rampa sobrevivesse aos marcos 3 a 5, que ainda
nao estao prontos. Convencao nao segura essa distincao: ja falhou uma vez. Por isso
ela e **estrutural**, como em :mod:`hero_atlas.model_status`.

O mecanismo tem tres partes:

1. :class:`FamilyStatus` **nao tem** valor de aprovacao. Nao ha como escrever.
2. :class:`PropulsionFamily` recusa candidata sem incognita bloqueante declarada,
   porque candidata sem nada bloqueando e aprovacao com outro nome.
3. :func:`selection_verdict` so devolveria ``SATISFIED`` diante de uma candidata sem
   bloqueio, que o item 2 torna inconstruivel. Hoje ela devolve ``INDETERMINATE``
   **por construcao**, e o teste que fixa isso e parte da suite.

Quando os marcos 3 a 5 medirem atraso, rampa e saturacao, uma incognita bloqueante
sai da lista por evidencia, nao por decisao. Ai, e so ai, o veredito muda sozinho.

⚠ Eliminar aqui nunca e absoluto. ``INCOMPATIBLE_UNDER_HYPOTHESIS`` carrega a
hipotese que elimina: mudou a hipotese, o ramo volta para a mesa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .verdict import Verdict

__all__ = [
    "FamilyStatus",
    "PropulsionFamily",
    "FAMILIES",
    "TURBINA_COMPACTA",
    "ELETRICO_DISTRIBUIDO",
    "HIBRIDO_SERIE",
    "HIBRIDO_TURBINA_COM_BUFFER",
    "family_by_name",
    "selection_verdict",
    "blocking_unknowns_across",
]


class FamilyStatus(StrEnum):
    """Situacao de um ramo tecnologico perante a evidencia de hoje.

    ⚠ **Nao existe valor de aprovacao, e a ausencia e deliberada.** Aprovar uma
    familia de propulsao exigiria demonstrar estabilidade sobre o envelope declarado,
    o que depende de dinamica fechada, atraso medido e saturacao. Enquanto esses
    marcos nao existirem, o vocabulario nao deve permitir escrever a conclusao.
    """

    UNEVALUATED = "unevaluated"
    """Nenhuma analise ainda. Silencio, nao juizo."""

    CANDIDATE = "candidate"
    """Sobreviveu ao que foi testado. **Nao** quer dizer viavel: quer dizer nao
    eliminado, com as incognitas bloqueantes ainda em aberto."""

    INCOMPATIBLE_UNDER_HYPOTHESIS = "incompatible_under_hypothesis"
    """Eliminado **sob hipotese declarada**, que fica registrada junto."""


@dataclass(frozen=True, slots=True)
class PropulsionFamily:
    """Um ramo tecnologico, com a condicao de validade colada nele.

    Attributes:
        name: identificador curto e estavel.
        summary: o que caracteriza o ramo, em uma linha.
        status: ver :class:`FamilyStatus`.
        conditioned_on: hipoteses sob as quais o status vale. **Obrigatorio e nao
            vazio**: status sem condicao declarada e exatamente o defeito que este
            modulo existe para bloquear.
        blocking_unknowns: o que falta medir para o ramo poder ser concluido.
        eliminated_by: qual hipotese elimina o ramo. Obrigatorio, e so permitido,
            quando o status e ``INCOMPATIBLE_UNDER_HYPOTHESIS``.
    """

    name: str
    summary: str
    status: FamilyStatus
    conditioned_on: tuple[str, ...]
    blocking_unknowns: tuple[str, ...] = field(default=())
    eliminated_by: str | None = None

    def __post_init__(self) -> None:
        if not self.conditioned_on:
            raise ValueError(
                f"familia {self.name!r} sem 'conditioned_on'. Status de ramo "
                "tecnologico so tem sentido junto da hipotese que o sustenta; sem "
                "ela, a afirmacao vira recomendacao descontextualizada."
            )

        if self.status is FamilyStatus.CANDIDATE and not self.blocking_unknowns:
            raise ValueError(
                f"familia {self.name!r} marcada como candidata sem nenhuma incognita "
                "bloqueante. Candidata sem bloqueio e aprovacao com outro nome, e "
                "aprovacao nao e expressavel neste estagio do projeto."
            )

        eliminada = self.status is FamilyStatus.INCOMPATIBLE_UNDER_HYPOTHESIS
        if eliminada and not self.eliminated_by:
            raise ValueError(
                f"familia {self.name!r} eliminada sem dizer sob qual hipotese. "
                "Eliminacao sem hipotese registrada nao pode ser revisitada quando a "
                "hipotese mudar, e vira dogma."
            )
        if not eliminada and self.eliminated_by:
            raise ValueError(f"familia {self.name!r} declara 'eliminated_by' sem estar eliminada.")

    @property
    def is_open(self) -> bool:
        """Se o ramo ainda pode virar solucao.

        Eliminado sob hipotese conta como fechado **apenas enquanto a hipotese
        valer**, e a hipotese esta em :attr:`eliminated_by` para poder ser atacada.
        """
        return self.status is not FamilyStatus.INCOMPATIBLE_UNDER_HYPOTHESIS


TURBINA_COMPACTA = PropulsionFamily(
    name="turbina_compacta",
    summary="microturbinas nos bracos e dorsal, empuxo direto, vetorizado pelo corpo",
    status=FamilyStatus.CANDIDATE,
    conditioned_on=(
        "pairado nivelado, pose congelada, massa congelada",
        "geometria plausivel, nao medida",
        "consumo especifico de catalogo, medido perto do maximo, extrapolado a pairado",
    ),
    blocking_unknowns=(
        "atraso de degrau pequeno perto do trim: nenhum fabricante publica",
        "taxa maxima de variacao de empuxo sob comando pequeno",
        "perda de instalacao e interacao em arranjo vestivel: sem dado publicado",
        "consumo especifico em carga parcial",
    ),
)

HIBRIDO_TURBINA_COM_BUFFER = PropulsionFamily(
    name="hibrido_turbina_com_buffer",
    summary=(
        "turbinas sustentam, canal eletrico rapido e pequeno produz autoridade de "
        "controle: separa largura de banda de sustentacao"
    ),
    status=FamilyStatus.CANDIDATE,
    conditioned_on=(
        "pairado nivelado, pose congelada, massa congelada",
        "geometria plausivel, nao medida",
        "canal lento fixado no valor de trim, canal rapido livre dentro dos limites",
        "sustentacao continua saindo da turbina, nao do canal eletrico",
    ),
    blocking_unknowns=(
        "quanta autoridade rapida e necessaria: depende do atraso do canal lento, "
        "que e a incognita central do projeto",
        "atraso de degrau pequeno da turbina, que dimensiona o canal rapido",
        "potencia continua do gerador ou do barramento",
        "energia e potencia maxima do buffer eletrico",
        "penalidade de massa de gerador, eletronica de potencia, cabos e termico",
        "acoplamento aerodinamico entre jato de turbina e rotor proximo",
        "contingencia: perda de gerador, de buffer, de motor ou de propulsor",
    ),
)

ELETRICO_DISTRIBUIDO = PropulsionFamily(
    name="eletrico_distribuido",
    summary="rotores eletricos, autonomia limitada por area de disco e massa de bateria",
    status=FamilyStatus.INCOMPATIBLE_UNDER_HYPOTHESIS,
    conditioned_on=(
        "arquitetura vestivel de bracos vetorizados, com rotor preso ao braco",
        "energia especifica de pack de alta descarga, 180 Wh/kg, 85 por cento utilizavel",
        "figura de merito 0,70 e rendimento de motor 0,88",
        "massa de bateria no otimo, ou seja duas vezes a massa seca",
    ),
    blocking_unknowns=(
        "energia especifica de pack de alta descarga acima de 180 Wh/kg muda a conta",
        "figura de merito real de rotor pequeno e carenado junto ao corpo",
    ),
    eliminated_by=(
        "teto de autonomia por saturacao de massa, nao por geometria de rotor. Com 95 kg "
        "secos o otimo de bateria pede 190 kg, mas a maior massa bruta que a geometria "
        "equilibra em pairado e 208,1 kg, ou 113,1 kg de bateria, e exigir 0,5 m/s2 de "
        "aceleracao na saida do chao corta o teto para 103,0 kg. Preso a isso, o melhor "
        "caso eletrico e 2,98 min de pairado, que a combustao alcanca com 12,0 kg de "
        "combustivel: fator de 8,5 em massa embarcada. O ramo reabre se o alvo de missao "
        "cair abaixo de 3 min, se a area de disco crescer, ou se o empuxo instalado subir"
    ),
)

HIBRIDO_SERIE = PropulsionFamily(
    name="hibrido_serie",
    summary="motor a combustao move gerador, eletricidade move rotores que sustentam",
    status=FamilyStatus.CANDIDATE,
    conditioned_on=(
        "arquitetura vestivel de bracos vetorizados",
        "sustentacao produzida **integralmente** por rotores eletricos",
        "area de disco limitada pela envergadura do braco",
    ),
    blocking_unknowns=(
        "potencia especifica do conjunto gerador mais eletronica, em kW/kg: e o "
        "parametro que decide o ramo, porque a potencia de barramento exigida e alta",
        "gestao termica de um barramento dessa potencia junto ao corpo",
        "rendimento composto da cadeia geracao, eletronica, motor e helice",
        "modos de falha novos: gerador, conversor, cabo, barramento",
    ),
)
"""⚠ **Eliminacao retirada.** Uma versao anterior deste ramo estava marcada como
incompativel, com a justificativa de que "resolve energia, nao area". A frase
confundia **energia** com **potencia**.

A area de disco limita a *potencia* de pairado, e e verdade que o hibrido serie nao
a melhora. Mas a autonomia do ramo eletrico puro nao e limitada por potencia: e
limitada por **massa de bateria**, que satura contra o teto de trim. Trocar bateria
por gerador mais combustivel ataca exatamente essa saturacao, porque combustivel tem
energia especifica muito maior e a massa do sistema deixa de crescer com o tempo de
voo. O ramo volta para a mesa ate que a potencia especifica do gerador o feche ou o
abra por evidencia."""

FAMILIES: tuple[PropulsionFamily, ...] = (
    TURBINA_COMPACTA,
    HIBRIDO_TURBINA_COM_BUFFER,
    HIBRIDO_SERIE,
    ELETRICO_DISTRIBUIDO,
)
"""Todos os ramos considerados. Ordem: abertos primeiro."""


def family_by_name(name: str) -> PropulsionFamily:
    for familia in FAMILIES:
        if familia.name == name:
            return familia
    raise KeyError(f"familia de propulsao desconhecida: {name!r}")


def blocking_unknowns_across(
    families: tuple[PropulsionFamily, ...] = FAMILIES,
) -> tuple[str, ...]:
    """Incognitas que bloqueiam algum ramo ainda aberto, sem repeticao."""
    vistas: dict[str, None] = {}
    for familia in families:
        if familia.is_open:
            for incognita in familia.blocking_unknowns:
                vistas.setdefault(incognita, None)
    return tuple(vistas)


def selection_verdict(
    families: tuple[PropulsionFamily, ...] = FAMILIES,
) -> tuple[Verdict, str]:
    """Da para escolher uma tecnologia de propulsao com a evidencia de hoje?

    Devolve ``SATISFIED`` apenas se existir **exatamente uma** familia aberta e ela
    nao tiver nenhuma incognita bloqueante.

    ⚠ Hoje isso e inalcancavel **por construcao**, nao por acaso do estado atual:
    :class:`PropulsionFamily` recusa candidata sem incognita bloqueante. O caminho
    para ``SATISFIED`` passa obrigatoriamente por medir, e uma incognita so sai da
    lista quando um marco produzir o dado.
    """
    abertas = [f for f in families if f.is_open]

    if not abertas:
        return (
            Verdict.VIOLATED,
            "todos os ramos considerados foram eliminados sob as hipoteses declaradas; "
            "a arquitetura precisa mudar, nao o motor",
        )

    livres = [f for f in abertas if not f.blocking_unknowns]
    if len(abertas) == 1 and livres:
        return (
            Verdict.SATISFIED,
            f"ramo unico sobrevivente sem incognita bloqueante: {abertas[0].name}",
        )

    pendentes = blocking_unknowns_across(families)
    nomes = ", ".join(f.name for f in abertas)
    return (
        Verdict.INDETERMINATE,
        f"{len(abertas)} ramos abertos ({nomes}) e {len(pendentes)} incognitas "
        "bloqueantes em aberto; a evidencia de hoje restringe arquitetura, nao "
        "seleciona tecnologia",
    )
