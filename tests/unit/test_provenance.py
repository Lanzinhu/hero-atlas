"""Procedencia: o que a fonte mede, declara, calcula ou infere."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from hero_atlas.provenance import (
    EvidenceClass,
    Provenance,
    SourceType,
    TracedValue,
    Uncertainty,
    sha256_of_file,
    within_combined_uncertainty,
)

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


def test_incerteza_desconhecida_nunca_reprova():
    """Um numero sem incerteza declarada nao pode reprovar nada."""
    desconhecida = Uncertainty()
    assert desconhecida.half_width(100.0) == float("inf")

    proc = Provenance(source_type=SourceType.ESTIMATE, evidence_class=EvidenceClass.INFERRED)
    valor = TracedValue(value=100.0, unit="N", provenance=proc)
    assert valor.agrees_with(1e9) is True


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
    assert within_combined_uncertainty(10.0, 11.0, 0.4, 0.7) is True  # 1,0 <= 1,1
    assert within_combined_uncertainty(10.0, 11.0, 0.2, 0.3) is False  # 1,0 > 0,5


def test_agrees_with_usa_a_unidade_declarada():
    empuxo = TracedValue(value=397.0, unit="N", provenance=ficha_jetcat())
    assert empuxo.agrees_with(400.0) is True  # dentro dos 7 N de faixa
    assert empuxo.agrees_with(420.0) is False


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
