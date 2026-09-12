"""Regiao admissivel: a saida do deck e requisito, nao estimativa."""

from __future__ import annotations

import pytest

from hero_atlas.analysis.requirements import (
    ActuatorRequirement,
    AdmissibleRegion,
    Relation,
    Verdict,
)
from hero_atlas.model_status import PROPULSAO_INSTALADA_HOJE
from hero_atlas.units import UnitError

pytestmark = pytest.mark.unit

CONTEXTO = {
    "arm_pose": "symmetric_nominal",
    "thrust_margin": 1.25,
    "coupling_model": "fully_coupled_latent",
    "disturbance": "gust_1ms",
}


def req(parameter: str, relation: Relation, threshold: float, unit: str) -> ActuatorRequirement:
    return ActuatorRequirement(
        parameter=parameter,
        relation=relation,
        threshold=threshold,
        unit=unit,
        conditioned_on=CONTEXTO,
    )


def test_requisito_de_teto_e_de_piso():
    teto = req("tau_subida", Relation.AT_MOST, 0.30, "s")
    piso = req("Tdot_up_max", Relation.AT_LEAST, 900.0, "N/s")

    assert teto.satisfied_by(0.20) is True
    assert teto.satisfied_by(0.40) is False
    assert piso.satisfied_by(1200.0) is True
    assert piso.satisfied_by(500.0) is False


def test_limite_exato_satisfaz():
    assert req("tau_subida", Relation.AT_MOST, 0.30, "s").satisfied_by(0.30) is True


def test_texto_do_requisito_usa_o_simbolo_certo():
    assert req("tau_subida", Relation.AT_MOST, 0.3, "s").as_text() == "tau_subida <= 0.3 s"
    assert req("eta_inst", Relation.AT_LEAST, 0.8, "-").as_text() == "eta_inst >= 0.8 -"


def test_requisito_sem_contexto_e_recusado():
    """Uma condicao sem o contexto em que foi obtida nao e interpretavel."""
    with pytest.raises(ValueError, match="conditioned_on"):
        ActuatorRequirement(
            parameter="tau_subida",
            relation=Relation.AT_MOST,
            threshold=0.3,
            unit="s",
        )


def test_unidade_desconhecida_e_recusada():
    with pytest.raises(UnitError):
        ActuatorRequirement(
            parameter="tau_subida",
            relation=Relation.AT_MOST,
            threshold=0.3,
            unit="jiffies",
            conditioned_on=CONTEXTO,
        )


def test_regiao_admissivel_exige_todas_as_condicoes():
    regiao = AdmissibleRegion.of(
        [
            req("tau_subida", Relation.AT_MOST, 0.30, "s"),
            req("Tdot_up_max", Relation.AT_LEAST, 900.0, "N/s"),
            req("eta_inst", Relation.AT_LEAST, 0.80, "-"),
        ],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado_com_rajada",
    )

    bom = {"tau_subida": 0.20, "Tdot_up_max": 1200.0, "eta_inst": 0.88}
    ruim = {"tau_subida": 0.20, "Tdot_up_max": 400.0, "eta_inst": 0.88}

    assert regiao.satisfied_by(bom) is True
    assert regiao.satisfied_by(ruim) is False
    assert len(regiao) == 3


def test_parametro_ausente_conta_como_nao_satisfeito():
    """Silencio nao e aprovacao."""
    regiao = AdmissibleRegion.of(
        [req("tau_subida", Relation.AT_MOST, 0.30, "s")],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado",
    )

    assert regiao.satisfied_by({}) is False


def test_diagnostico_diz_qual_condicao_faltou():
    regiao = AdmissibleRegion.of(
        [
            req("tau_subida", Relation.AT_MOST, 0.30, "s"),
            req("Tdot_up_max", Relation.AT_LEAST, 900.0, "N/s"),
        ],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado",
    )

    faltando = regiao.unmet_by({"tau_subida": 0.20, "Tdot_up_max": 400.0})

    assert len(faltando) == 1
    assert faltando[0].parameter == "Tdot_up_max"


def test_regiao_vazia_e_recusada():
    with pytest.raises(ValueError, match="vazia"):
        AdmissibleRegion.of([], status=PROPULSAO_INSTALADA_HOJE, scenario="pairado")


def test_especificacao_sai_marcada():
    """A inversao fica visivel: o entregavel e especificacao para evidencia futura,
    nao estimativa apresentada como propriedade do veiculo.
    """
    regiao = AdmissibleRegion.of(
        [req("tau_subida", Relation.AT_MOST, 0.30, "s")],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado_com_rajada",
    )

    texto = regiao.as_specification()

    assert "precisa satisfazer" in texto
    assert "tau_subida <= 0.3 s" in texto
    assert "nao representa hardware" in texto


def test_o_estado_do_modelo_faz_parte_da_regiao():
    """Nao e metadado opcional: regiao derivada de deck nao validado e especificacao
    condicional, e o relatorio tem que dizer isso.
    """
    regiao = AdmissibleRegion.of(
        [req("eta_inst", Relation.AT_LEAST, 0.8, "-")],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado",
    )

    assert regiao.status.is_conditional is True


# --------------------------------------------------------------------------- #
# Veredito de tres valores: violado nao e o mesmo que indeterminado
# --------------------------------------------------------------------------- #


def regiao_tres() -> AdmissibleRegion:
    return AdmissibleRegion.of(
        [
            req("tau_subida", Relation.AT_MOST, 0.30, "s"),
            req("Tdot_up_max", Relation.AT_LEAST, 900.0, "N/s"),
            req("eta_inst", Relation.AT_LEAST, 0.80, "-"),
        ],
        status=PROPULSAO_INSTALADA_HOJE,
        scenario="pairado_com_rajada",
    )


def test_parametro_ausente_e_indeterminado_nao_violado():
    """A distincao que mais importa. Falta de parametro nao e reprovacao do conceito."""
    requisito = req("tau_subida", Relation.AT_MOST, 0.30, "s")

    assert requisito.evaluate({}) is Verdict.INDETERMINATE
    assert requisito.evaluate({"tau_subida": 0.90}) is Verdict.VIOLATED
    assert requisito.evaluate({"tau_subida": 0.20}) is Verdict.SATISFIED


def test_regiao_separa_violado_de_indeterminado():
    candidato = {"tau_subida": 0.20, "Tdot_up_max": 400.0}  # eta_inst ausente

    veredito = regiao_tres().evaluate(candidato)

    assert [r.parameter for r in veredito.satisfied] == ["tau_subida"]
    assert [r.parameter for r in veredito.violated] == ["Tdot_up_max"]
    assert [r.parameter for r in veredito.indeterminate] == ["eta_inst"]


def test_indeterminado_nao_conta_como_satisfeito():
    candidato = {"tau_subida": 0.20, "Tdot_up_max": 1200.0}  # eta_inst ausente

    veredito = regiao_tres().evaluate(candidato)

    assert veredito.is_satisfied is False
    assert veredito.is_demonstrable is False
    assert veredito.verdict is Verdict.INDETERMINATE


def test_candidato_completo_e_bom_e_demonstravel():
    veredito = regiao_tres().evaluate({"tau_subida": 0.20, "Tdot_up_max": 1200.0, "eta_inst": 0.88})

    assert veredito.is_satisfied is True
    assert veredito.is_demonstrable is True
    assert veredito.verdict is Verdict.SATISFIED


def test_violacao_tem_precedencia_sobre_indeterminacao():
    """Se ja ha condicao furada, o modelo diz nao mesmo com outra inavaliavel."""
    veredito = regiao_tres().evaluate({"tau_subida": 0.90})

    assert veredito.verdict is Verdict.VIOLATED
    assert veredito.is_demonstrable is False


def test_relatorio_preserva_a_distincao():
    """Fundir as duas faria lacuna de evidencia aparecer como reprovacao."""
    texto = regiao_tres().evaluate({"tau_subida": 0.90}).as_report()

    assert "Violadas, o modelo diz nao" in texto
    assert "NAO e reprovacao, e falta de evidencia" in texto
    assert "parametro ausente" in texto
    assert "nao representa hardware" in texto


def test_filtros_dedicados_por_classe():
    regiao = regiao_tres()
    candidato = {"tau_subida": 0.20, "Tdot_up_max": 400.0}

    assert [r.parameter for r in regiao.violated_by(candidato)] == ["Tdot_up_max"]
    assert [r.parameter for r in regiao.indeterminate_for(candidato)] == ["eta_inst"]
    assert len(regiao.unmet_by(candidato)) == 2


def test_refutado_e_rejeitado_sao_coisas_diferentes():
    """Rejeicao operacional pode tratar os dois igual. O relatorio, nunca.

    candidato_rejeitado = veredito em {violado, indeterminado}
    elegivel_como_conclusao = veredito em {satisfeito, violado}
    """
    so_indeterminado = regiao_tres().evaluate({"tau_subida": 0.20, "Tdot_up_max": 1200.0})
    com_violacao = regiao_tres().evaluate({"tau_subida": 0.90})

    # os dois bloqueiam o candidato
    assert so_indeterminado.is_rejected is True
    assert com_violacao.is_rejected is True

    # mas so um afirma falha do sistema
    assert so_indeterminado.is_refuted is False
    assert com_violacao.is_refuted is True


def test_veredito_sabe_se_e_conclusivo():
    assert Verdict.SATISFIED.is_conclusive is True
    assert Verdict.VIOLATED.is_conclusive is True
    assert Verdict.INDETERMINATE.is_conclusive is False


def test_veredito_sabe_se_bloqueia():
    assert Verdict.SATISFIED.rejects is False
    assert Verdict.VIOLATED.rejects is True
    assert Verdict.INDETERMINATE.rejects is True
