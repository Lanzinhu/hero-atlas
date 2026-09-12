"""Procedencia: o que a fonte mede, declara, calcula ou infere."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from hero_atlas.provenance import (
    AcceptanceResult,
    EvidenceClass,
    FrozenComparison,
    Provenance,
    SourceType,
    TracedValue,
    Uncertainty,
    sha256_of_file,
    within_combined_uncertainty,
)
from hero_atlas.verdict import Verdict

pytestmark = pytest.mark.unit


def ficha_jetcat() -> Provenance:
    """Procedencia tipica de catalogo, ainda SEM copia arquivada."""
    return Provenance(
        source_type=SourceType.DATASHEET,
        evidence_class=EvidenceClass.DECLARED,
        retrieval_date=date(2026, 9, 11),
        source_uri="https://www.jetcat.de/en/productdetails/produkte/jetcat/produkte/Professionell/p400%20pro",
        applicability={
            "configuration": "static_test_stand",
            "altitude_m": 0.0,
            "atmosphere": "ISA",
            "installation": "bare_engine",
        },
        uncertainty=Uncertainty(type="bounded", unit="N", lower=390.0, upper=404.0),
    )


def test_valor_rastreado_converte_para_si():
    empuxo = TracedValue(value=40.5, unit="kgf", provenance=ficha_jetcat())
    assert empuxo.dimension == "force"
    assert empuxo.si == pytest.approx(397.17, abs=0.01)


def test_fonte_sem_hash_nao_esta_arquivada():
    """Regra do projeto: URL sem copia arquivada nao conta como procedencia."""
    proc = ficha_jetcat()
    assert proc.is_archived is False

    with pytest.raises(ValueError, match="copia arquivada"):
        proc.require_archived()


def test_fonte_com_hash_esta_arquivada():
    proc = ficha_jetcat().model_copy(update={"source_file_sha256": "a" * 64})
    assert proc.is_archived is True
    proc.require_archived()  # nao levanta


def test_hash_precisa_ter_64_caracteres():
    """Um hash truncado nao e procedencia, e um campo preenchido por engano."""
    with pytest.raises(ValidationError, match="source_file_sha256"):
        Provenance(
            source_type=SourceType.DATASHEET,
            evidence_class=EvidenceClass.DECLARED,
            source_file_sha256="abc",
        )


def test_imprensa_nao_pode_ser_medicao():
    """Bloqueia no schema que uma alegacao de marketing entre como medicao.

    Os "1.050 bhp" da Gravity e os "1.500 hp" da Zapata sao exatamente este caso:
    turbojato nao produz potencia de eixo.
    """
    with pytest.raises(ValidationError, match="measured"):
        Provenance(
            source_type=SourceType.PRESS,
            evidence_class=EvidenceClass.MEASURED,
        )


def test_estimativa_tambem_nao_pode_ser_medicao():
    with pytest.raises(ValidationError, match="measured"):
        Provenance(
            source_type=SourceType.ESTIMATE,
            evidence_class=EvidenceClass.MEASURED,
        )


def test_imprensa_pode_ser_declarada_ou_inferida():
    Provenance(source_type=SourceType.PRESS, evidence_class=EvidenceClass.DECLARED)
    Provenance(source_type=SourceType.PRESS, evidence_class=EvidenceClass.INFERRED)


def test_incerteza_limitada_exige_os_dois_extremos():
    with pytest.raises(ValidationError, match="lower e upper"):
        Uncertainty(type="bounded", lower=1.0)


def test_incerteza_limitada_recusa_faixa_invertida():
    with pytest.raises(ValidationError, match="maior que"):
        Uncertainty(type="bounded", lower=10.0, upper=1.0)


def test_incerteza_normal_exige_desvio():
    with pytest.raises(ValidationError, match="std"):
        Uncertainty(type="normal", mean=1.0)


def test_incerteza_desconhecida_e_inconclusiva_nao_aprovada():
    """Antes isto devolvia infinito e colapsava para aprovado.

    Isso invertia a regra central do projeto: um numero SEM procedencia virava
    irrefutavel por tolerancia infinita. O correto e inconclusivo.
    """
    desconhecida = Uncertainty()
    assert desconhecida.is_known is False
    assert desconhecida.half_width(100.0) is None

    proc = Provenance(source_type=SourceType.ESTIMATE, evidence_class=EvidenceClass.INFERRED)
    valor = TracedValue(value=100.0, unit="N", provenance=proc)

    resultado = valor.agrees_with(1e9)
    assert resultado.status is Verdict.INDETERMINATE
    assert resultado.numeric_comparison_performed is False
    assert resultado.eligible_for_regression is False
    assert "uncertainty_missing" in resultado.reason
    assert bool(resultado) is False


def test_incerteza_conhecida_permite_comparacao():
    unc = Uncertainty(type="bounded", unit="N", lower=390.0, upper=404.0)
    assert unc.is_known is True


def test_resultado_carrega_diferenca_e_orcamento():
    r = within_combined_uncertainty(10.0, 11.0, 0.4, 0.7)
    assert r.difference == pytest.approx(1.0)
    assert r.budget == pytest.approx(1.1)
    assert r.eligible_for_regression is True


def test_par_inconclusivo_nao_vira_teste_de_regressao():
    """Elegibilidade para quebrar o build exige comparacao conclusiva."""
    r = within_combined_uncertainty(10.0, 11.0, None, 0.5)
    assert r.eligible_for_regression is False
    assert isinstance(r, AcceptanceResult)


def test_meia_largura_de_faixa_assimetrica():
    unc = Uncertainty(type="bounded", unit="N", lower=390.0, upper=404.0)
    # nominal 397: 7 acima, 7 abaixo
    assert unc.half_width(397.0) == pytest.approx(7.0)
    # nominal 392: 12 acima, 2 abaixo, vale o maior
    assert unc.half_width(392.0) == pytest.approx(12.0)


def test_meia_largura_normal_usa_dois_desvios():
    assert Uncertainty(type="normal", std=1.5).half_width(0.0) == pytest.approx(3.0)


def test_criterio_de_incerteza_somada():
    """|y_modelo - y_ref| <= delta_ref + delta_modelo

    Substitui a tolerancia percentual fixa. Um catalogo pode dar massa com precisao
    de gramas e empuxo arredondado ao quilograma-forca na mesma pagina.
    """
    assert within_combined_uncertainty(10.0, 11.0, 0.4, 0.7).status is Verdict.SATISFIED
    assert within_combined_uncertainty(10.0, 11.0, 0.2, 0.3).status is Verdict.VIOLATED


def test_agrees_with_usa_a_unidade_declarada():
    empuxo = TracedValue(value=397.0, unit="N", provenance=ficha_jetcat())
    assert empuxo.agrees_with(400.0).status is Verdict.SATISFIED  # dentro dos 7 N
    assert empuxo.agrees_with(420.0).status is Verdict.VIOLATED


def test_unidade_invalida_falha_na_construcao():
    """O erro de unidade sobe embrulhado pelo pydantic, com o campo no contexto."""
    with pytest.raises(ValidationError, match="unidade desconhecida"):
        TracedValue(value=1.0, unit="nao_existe", provenance=ficha_jetcat())


def test_sha256_de_arquivo(tmp_path):
    arquivo = tmp_path / "fonte.txt"
    arquivo.write_bytes(b"hero atlas")
    digest = sha256_of_file(arquivo)
    assert len(digest) == 64
    assert digest == sha256_of_file(arquivo)


def test_procedencia_e_imutavel():
    proc = ficha_jetcat()
    with pytest.raises(ValidationError):
        proc.source_type = SourceType.TEST


def test_violado_e_congelavel_mas_nao_e_benchmark_aceito():
    """Congelar uma discordancia conhecida e teste legitimo. Nao e validacao.

    eligible_for_regression => comparacao feita e status != indeterminate
    accepted_as_benchmark   => status == satisfied
    """
    concorda = within_combined_uncertainty(10.0, 11.0, 0.4, 0.7)
    discorda = within_combined_uncertainty(10.0, 20.0, 0.4, 0.7)
    inconclusivo = within_combined_uncertainty(10.0, 11.0, None, 0.5)

    assert concorda.eligible_for_regression is True
    assert concorda.accepted_as_benchmark is True

    assert discorda.eligible_for_regression is True
    assert discorda.accepted_as_benchmark is False

    assert inconclusivo.eligible_for_regression is False
    assert inconclusivo.accepted_as_benchmark is False


def test_benchmark_aceito_implica_congelavel():
    """A implicacao vale nos tres casos, nunca o contrario."""
    for args in [(10.0, 11.0, 0.4, 0.7), (10.0, 20.0, 0.4, 0.7), (10.0, 11.0, None, 0.5)]:
        r = within_combined_uncertainty(*args)
        if r.accepted_as_benchmark:
            assert r.eligible_for_regression


# --------------------------------------------------------------------------- #
# Congelamento: preserva a discrepancia SEM perder a razao dela existir
# --------------------------------------------------------------------------- #


def ficha_arquivada() -> Provenance:
    return ficha_jetcat().model_copy(
        update={"source_file_sha256": "b" * 64, "source_revision": "rev B"}
    )


def test_congela_concordancia_sem_exigir_justificativa():
    resultado = within_combined_uncertainty(400.0, 397.0, 0.0, 7.0)

    congelado = FrozenComparison.freeze(
        resultado,
        reference=ficha_arquivada(),
        model_version="0.1.0",
        frozen_on=date(2026, 9, 12),
    )

    assert congelado.is_known_discrepancy is False
    assert congelado.result.accepted_as_benchmark is True


def test_congela_discordancia_conhecida_com_justificativa():
    """Fixa o comportamento atual e obriga decisao explicita quando algo evoluir."""
    resultado = within_combined_uncertainty(500.0, 397.0, 0.0, 7.0)

    congelado = FrozenComparison.freeze(
        resultado,
        reference=ficha_arquivada(),
        model_version="0.1.0",
        frozen_on=date(2026, 9, 12),
        justification="reingestao nao modelada; divergencia esperada ate o deck existir",
    )

    assert congelado.is_known_discrepancy is True
    assert congelado.result.accepted_as_benchmark is False
    assert "reingestao" in congelado.justification


def test_discordancia_sem_justificativa_e_recusada():
    """Sem o motivo, a suite preserva a discrepancia e perde a razao de ela existir."""
    resultado = within_combined_uncertainty(500.0, 397.0, 0.0, 7.0)

    with pytest.raises(ValueError, match="justificativa"):
        FrozenComparison.freeze(
            resultado,
            reference=ficha_arquivada(),
            model_version="0.1.0",
            frozen_on=date(2026, 9, 12),
        )


def test_indeterminado_nao_pode_ser_congelado():
    resultado = within_combined_uncertainty(400.0, 397.0, None, 7.0)

    with pytest.raises(ValueError, match="nao congelavel"):
        FrozenComparison.freeze(
            resultado,
            reference=ficha_arquivada(),
            model_version="0.1.0",
            frozen_on=date(2026, 9, 12),
            justification="qualquer",
        )


def test_registro_carrega_todo_o_contexto_do_congelamento():
    """Revisao, hash, versao do modelo, data, incerteza, aplicabilidade e motivo."""
    resultado = within_combined_uncertainty(500.0, 397.0, 0.0, 7.0)
    congelado = FrozenComparison.freeze(
        resultado,
        reference=ficha_arquivada(),
        model_version="0.1.0",
        frozen_on=date(2026, 9, 12),
        justification="divergencia conhecida",
    )

    registro = congelado.as_record()

    for campo in (
        "status",
        "difference",
        "budget",
        "accepted_as_benchmark",
        "is_known_discrepancy",
        "model_version",
        "frozen_on",
        "justification",
        "source_revision",
        "source_file_sha256",
        "source_archived",
        "uncertainty",
        "applicability",
    ):
        assert campo in registro, f"registro sem {campo}"

    assert registro["frozen_on"] == "2026-09-12"
    assert registro["source_revision"] == "rev B"
    assert registro["source_archived"] is True
