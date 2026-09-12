"""Marco 3: casos analiticos da dinamica de corpo rigido.

Ver vault/05 - Verificacao/Tres classes de teste.md e Casos analiticos.md

**Classe A**: ordem do integrador em casos suaves e sem evento.
Dois testes aqui sao decisivos porque pegam erro de sinal e de convencao, que
produzem trajetoria suave e completamente falsa sem quebrar nenhum teste de forma:

- instabilidade do eixo intermediario, o efeito Dzhanibekov
- equivariancia sob rotacao do referencial
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from hero_atlas.dynamics.integrators import euler_step, integrate_fixed_step, rk4_step
from hero_atlas.dynamics.quaternion import (
    conjugate,
    from_axis_angle,
    hamilton,
    normalize,
    rotate_body_to_inertial,
    rotation_matrix_ib,
)
from hero_atlas.dynamics.rigid_body import (
    BodyWrench,
    PlantState,
    RigidBodyProperties,
    angular_momentum_inertial,
    kinetic_energy_J,
    state_derivative,
)
from hero_atlas.units import G0

pytestmark = pytest.mark.validation

SEM_GRAVIDADE = (0.0, 0.0, 0.0)


def corpo(
    inertia=(8.0, 12.0, 6.0), mass_kg: float = 100.0, cg_offset=(0.0, 0.0, 0.0)
) -> RigidBodyProperties:
    return RigidBodyProperties(
        mass_kg=mass_kg,
        inertia_about_cg_kg_m2=np.diag(inertia),
        cg_offset_from_reference_m=np.array(cg_offset),
    )


def derivada(body: RigidBodyProperties, wrench: BodyWrench, gravity=(0.0, 0.0, G0)):
    def f(_t, x):
        return state_derivative(PlantState.from_vector(x), body, wrench, gravity_I_m_s2=gravity)

    return f


# --------------------------------------------------------------------------- #
# Casos com solucao fechada
# --------------------------------------------------------------------------- #


def test_queda_livre_reproduz_meio_g_t_quadrado():
    """Sem empuxo e sem arrasto: z = g t^2 / 2, exato."""
    body = corpo()
    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero()),
        PlantState.at_rest(),
        t_final_s=2.0,
        dt_s=0.001,
    )

    assert traj[-1].position_O_I_m[2] == pytest.approx(0.5 * G0 * 4.0, abs=1e-9)
    assert traj[-1].velocity_O_I_m_s[2] == pytest.approx(G0 * 2.0, abs=1e-9)


def test_binario_puro_nao_move_o_centro():
    """Momento sem forca: rotaciona e nao translada. omega_dot = M / I, exato."""
    body = corpo(inertia=(8.0, 8.0, 8.0))
    momento = np.array([0.0, 0.0, 4.0])
    wrench = BodyWrench(force_N=np.zeros(3), moment_about_cg_Nm=momento)

    _t, traj = integrate_fixed_step(
        derivada(body, wrench, gravity=SEM_GRAVIDADE),
        PlantState.at_rest(),
        t_final_s=1.0,
        dt_s=0.001,
    )
    final = traj[-1]

    np.testing.assert_allclose(final.position_O_I_m, 0.0, atol=1e-12)
    np.testing.assert_allclose(final.velocity_O_I_m_s, 0.0, atol=1e-12)
    assert final.omega_B_rad_s[2] == pytest.approx(4.0 / 8.0, abs=1e-9)


def test_energia_mecanica_conservada_em_balistico():
    """Sem propulsao e sem dissipacao, energia se conserva.

    ⚠ A invariante vale **neste caso**. Com propulsao, arrasto ou combustivel o
    sistema nao conserva energia, e testar conservacao ali reprovaria fisica
    correta. Ver vault/05 - Verificacao/Invariantes por caso.md
    """
    body = corpo()
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.array([5.0, 0.0, -20.0]),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.zeros(3),
    )

    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero()), inicial, t_final_s=3.0, dt_s=0.001
    )

    def energia(s: PlantState) -> float:
        altura = -s.position_O_I_m[2]  # z para baixo
        return kinetic_energy_J(s, body) + body.mass_kg * G0 * altura

    e0, ef = energia(traj[0]), energia(traj[-1])
    assert abs(ef - e0) / abs(e0) < 1e-10


def test_corpo_livre_de_torque_conserva_momento_angular_no_inercial():
    """⚠ A avaliacao e no **inercial**.

    Verificar componentes no corpo seria incorreto: o proprio referencial gira, e
    elas mudam mesmo com o momento angular conservado.
    """
    body = corpo(inertia=(1.0, 2.0, 3.0))
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([1.2, 0.7, 2.1]),
    )

    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero(), gravity=SEM_GRAVIDADE),
        inicial,
        t_final_s=6.0,
        dt_s=0.001,
    )

    h0 = angular_momentum_inertial(traj[0], body)
    hf = angular_momentum_inertial(traj[-1], body)
    np.testing.assert_allclose(hf, h0, atol=1e-8)

    # e a energia de rotacao tambem
    assert kinetic_energy_J(traj[-1], body) == pytest.approx(
        kinetic_energy_J(traj[0], body), rel=1e-10
    )


def test_momento_angular_no_corpo_de_fato_varia():
    """Guarda contra o teste anterior passar por motivo errado.

    Se as componentes no corpo ficassem constantes, a conservacao no inercial
    estaria sendo verificada de forma trivial e o teste nao provaria nada.
    """
    body = corpo(inertia=(1.0, 2.0, 3.0))
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([1.2, 0.7, 2.1]),
    )

    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero(), gravity=SEM_GRAVIDADE),
        inicial,
        t_final_s=2.0,
        dt_s=0.001,
    )

    h_corpo_inicial = body.inertia_about_cg_kg_m2 @ traj[0].omega_B_rad_s
    h_corpo_final = body.inertia_about_cg_kg_m2 @ traj[-1].omega_B_rad_s

    assert not np.allclose(h_corpo_inicial, h_corpo_final, atol=1e-3)


# --------------------------------------------------------------------------- #
# Os dois testes decisivos de sinal e convencao
# --------------------------------------------------------------------------- #


def test_instabilidade_do_eixo_intermediario():
    """⚠ Efeito Dzhanibekov. O teste mais sensivel a erro de sinal que existe.

    Com tres momentos principais distintos, giro em torno do eixo **intermediario**
    e instavel, e o corpo capota periodicamente. Um sinal trocado na equacao de
    Euler ou na propagacao do quaternion produz um giro estavel e plausivel, e nada
    mais no modelo acusa.

    Com I = (1, 2, 3), o eixo 2 e o intermediario.
    """
    body = corpo(inertia=(1.0, 2.0, 3.0))
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([0.02, 5.0, 0.0]),  # giro em y, perturbacao pequena em x
    )

    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero(), gravity=SEM_GRAVIDADE),
        inicial,
        t_final_s=4.0,
        dt_s=0.002,
    )

    omega_y = np.array([s.omega_B_rad_s[1] for s in traj])

    assert omega_y.min() < -1.0, "o eixo intermediario tem que inverter o sinal"
    assert omega_y.max() > 1.0


def test_eixos_extremos_sao_estaveis():
    """Contraprova: giro no eixo de menor e de maior inercia **nao** capota.

    Sem isto, o teste anterior poderia passar com uma dinamica que simplesmente
    oscila tudo.

    Mesmo horizonte do teste de instabilidade, que e o que torna a comparacao
    justa: na janela em que o eixo intermediario inverte, os extremos nao se movem.
    """
    body = corpo(inertia=(1.0, 2.0, 3.0))

    for eixo, rotulo in ((0, "menor"), (2, "maior")):
        omega0 = np.zeros(3)
        omega0[eixo] = 5.0
        omega0[(eixo + 1) % 3] = 0.02

        inicial = PlantState(
            position_O_I_m=np.zeros(3),
            velocity_O_I_m_s=np.zeros(3),
            quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
            omega_B_rad_s=omega0,
        )
        _t, traj = integrate_fixed_step(
            derivada(body, BodyWrench.zero(), gravity=SEM_GRAVIDADE),
            inicial,
            t_final_s=12.0,
            dt_s=0.0005,
        )
        componente = np.array([s.omega_B_rad_s[eixo] for s in traj])

        assert componente.min() > 4.0, f"o eixo {rotulo} deveria ser estavel"


def test_equivariancia_sob_rotacao_do_referencial():
    """⚠ Rodar todo o problema por R tem que rodar a trajetoria por R.

    Pega confusao entre matriz de rotacao e sua transposta, e entre multiplicar o
    quaternion pela esquerda ou pela direita. Erros desses produzem trajetoria
    suave e errada que nenhum teste de conservacao detecta.
    """
    body = corpo(inertia=(4.0, 7.0, 5.0), cg_offset=(0.12, 0.0, -0.05))
    wrench = BodyWrench(
        force_N=np.array([10.0, -5.0, -900.0]), moment_about_cg_Nm=np.array([2.0, 1.5, -0.8])
    )
    gravidade = np.array([0.0, 0.0, G0])

    inicial = PlantState(
        position_O_I_m=np.array([1.0, -2.0, 0.5]),
        velocity_O_I_m_s=np.array([3.0, 0.0, -1.0]),
        quaternion_ib=from_axis_angle([0.3, 0.5, 0.81], 0.4),
        omega_B_rad_s=np.array([0.4, -0.2, 0.9]),
    )

    _t, original = integrate_fixed_step(
        derivada(body, wrench, gravity=gravidade), inicial, t_final_s=2.0, dt_s=0.002
    )

    # rotacao aplicada do lado inercial
    q_rot = from_axis_angle([0.2, -0.7, 0.68], 1.1)
    R = rotation_matrix_ib(q_rot)

    girado = PlantState(
        position_O_I_m=R @ inicial.position_O_I_m,
        velocity_O_I_m_s=R @ inicial.velocity_O_I_m_s,
        quaternion_ib=hamilton(q_rot, inicial.quaternion_ib),
        omega_B_rad_s=inicial.omega_B_rad_s,  # esta no corpo, nao muda
    )

    _t2, rodado = integrate_fixed_step(
        derivada(body, wrench, gravity=R @ gravidade), girado, t_final_s=2.0, dt_s=0.002
    )

    esperada = R @ original[-1].position_O_I_m
    np.testing.assert_allclose(rodado[-1].position_O_I_m, esperada, atol=1e-9)
    np.testing.assert_allclose(
        rodado[-1].velocity_O_I_m_s, R @ original[-1].velocity_O_I_m_s, atol=1e-9
    )
    np.testing.assert_allclose(rodado[-1].omega_B_rad_s, original[-1].omega_B_rad_s, atol=1e-9)


# --------------------------------------------------------------------------- #
# Integridade numerica
# --------------------------------------------------------------------------- #


def test_norma_do_quaternion_sobrevive_a_muitos_passos():
    """Um quaternion nao unitario deixa de representar rotacao e passa a escalar."""
    body = corpo(inertia=(1.0, 2.0, 3.0))
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([1.0, 2.0, 0.5]),
    )

    _t, traj = integrate_fixed_step(
        derivada(body, BodyWrench.zero(), gravity=SEM_GRAVIDADE),
        inicial,
        t_final_s=8.0,
        dt_s=0.0005,
    )

    normas = np.array([np.linalg.norm(s.quaternion_ib) for s in traj])
    assert np.max(np.abs(normas - 1.0)) < 1e-12


@pytest.mark.parametrize(
    ("stepper", "ordem_esperada"),
    [(rk4_step, 4.0), (euler_step, 1.0)],
)
def test_ordem_de_convergencia_em_caso_suave(stepper, ordem_esperada: float):
    """⚠ Classe A: ordem do integrador, **so** em caso suave e sem evento.

    Quarta ordem do integrador nao implica quarta ordem do sistema hibrido: com
    saturacao, retencao e evento a ordem observada cai mesmo com o integrador
    correto. Ali vale a classe B, de convergencia de metrica.

    Estimativa por **extrapolacao de Richardson**, comparando halvings sucessivos
    entre si:

        ordem = log2( |x(dt) - x(dt/2)| / |x(dt/2) - x(dt/4)| )

    Dispensa solucao de referencia fina, que custaria centenas de milhares de
    passos para dar a mesma informacao.
    """
    body = corpo(inertia=(4.0, 7.0, 5.0))
    wrench = BodyWrench(
        force_N=np.array([30.0, -10.0, -50.0]),
        moment_about_cg_Nm=np.array([1.0, 0.5, -0.3]),
    )
    f = derivada(body, wrench)
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.array([1.0, 0.0, 0.0]),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([0.2, -0.1, 0.3]),
    )
    horizonte = 1.0

    def final(dt: float) -> np.ndarray:
        _t, traj = integrate_fixed_step(f, inicial, t_final_s=horizonte, dt_s=dt, stepper=stepper)
        return traj[-1].to_vector()

    dt0 = 0.04 if stepper is rk4_step else 0.004
    x0, x1, x2 = final(dt0), final(dt0 / 2), final(dt0 / 4)

    d1 = float(np.linalg.norm(x1 - x0))
    d2 = float(np.linalg.norm(x2 - x1))
    ordem = math.log2(d1 / d2)

    assert ordem == pytest.approx(ordem_esperada, abs=0.3), (
        f"ordem estimada {ordem:.2f}, esperada {ordem_esperada}"
    )


def test_rk4_e_muito_mais_preciso_que_euler():
    """Guarda de sanidade do proprio teste de ordem."""
    body = corpo()
    f = derivada(body, BodyWrench.zero())
    inicial = PlantState.at_rest()

    _t, com_rk4 = integrate_fixed_step(f, inicial, t_final_s=2.0, dt_s=0.05, stepper=rk4_step)
    _t, com_euler = integrate_fixed_step(f, inicial, t_final_s=2.0, dt_s=0.05, stepper=euler_step)

    exato = 0.5 * G0 * 4.0
    erro_rk4 = abs(com_rk4[-1].position_O_I_m[2] - exato)
    erro_euler = abs(com_euler[-1].position_O_I_m[2] - exato)

    assert erro_rk4 < erro_euler


# --------------------------------------------------------------------------- #
# O ponto de referencia e o centro de massa
# --------------------------------------------------------------------------- #


def test_o_centro_de_massa_e_derivado_nao_integrado():
    """ADR-001: o estado carrega o ponto de referencia; o centro sai da atitude."""
    body = corpo(cg_offset=(0.2, 0.0, -0.1))
    estado = PlantState(
        position_O_I_m=np.array([1.0, 2.0, 3.0]),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=from_axis_angle([0.0, 0.0, 1.0], math.pi / 2),
        omega_B_rad_s=np.zeros(3),
    )

    centro = estado.center_of_mass_position_I_m(body)
    esperado = estado.position_O_I_m + rotate_body_to_inertial(
        estado.quaternion_ib, body.cg_offset_from_reference_m
    )

    np.testing.assert_allclose(centro, esperado, atol=1e-12)
    # girado 90 graus em z, o deslocamento longitudinal vira lateral
    np.testing.assert_allclose(centro, [1.0, 2.2, 2.9], atol=1e-9)


def test_com_centro_deslocado_a_rotacao_acelera_o_ponto_de_referencia():
    """Termo de transporte: com d nao nulo, girar move ``O`` mesmo sem forca liquida.

    E o termo centripeto que a formulacao sobre o centro so recupera ao transportar.
    """
    body = corpo(inertia=(8.0, 8.0, 8.0), cg_offset=(0.5, 0.0, 0.0))
    inicial = PlantState(
        position_O_I_m=np.zeros(3),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_B_rad_s=np.array([0.0, 0.0, 3.0]),
    )

    derivada_inicial = state_derivative(
        inicial, body, BodyWrench.zero(), gravity_I_m_s2=SEM_GRAVIDADE
    )
    aceleracao_O = derivada_inicial[3:6]

    # a_O = -omega x (omega x d) = +omega^2 * d, para d perpendicular a omega
    esperado = 3.0**2 * np.array([0.5, 0.0, 0.0])
    np.testing.assert_allclose(aceleracao_O, esperado, atol=1e-12)


def test_sem_deslocamento_o_ponto_de_referencia_e_o_centro():
    body = corpo(cg_offset=(0.0, 0.0, 0.0))
    estado = PlantState.at_rest([1.0, 2.0, 3.0])

    np.testing.assert_allclose(
        estado.center_of_mass_position_I_m(body), estado.position_O_I_m, atol=1e-12
    )


# --------------------------------------------------------------------------- #
# Algebra de quaternion
# --------------------------------------------------------------------------- #


def test_produto_de_hamilton_nao_e_comutativo():
    p = from_axis_angle([1.0, 0.0, 0.0], 0.7)
    q = from_axis_angle([0.0, 1.0, 0.0], 1.1)

    assert not np.allclose(hamilton(p, q), hamilton(q, p))


def test_quaternion_vezes_conjugado_da_identidade():
    q = from_axis_angle([0.3, -0.5, 0.81], 1.3)
    np.testing.assert_allclose(hamilton(q, conjugate(q)), [1.0, 0.0, 0.0, 0.0], atol=1e-12)


def test_matriz_de_rotacao_e_ortogonal_com_determinante_positivo():
    q = from_axis_angle([0.2, 0.9, -0.38], 2.1)
    R = rotation_matrix_ib(q)

    np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-12)


def test_rotacao_de_90_graus_em_z_leva_x_para_y():
    """Fixa o **sentido** da convencao, nao so a forma."""
    q = from_axis_angle([0.0, 0.0, 1.0], math.pi / 2)

    np.testing.assert_allclose(
        rotate_body_to_inertial(q, [1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1e-12
    )


def test_composicao_de_rotacoes_segue_a_ordem_do_produto():
    a = from_axis_angle([0.0, 0.0, 1.0], math.pi / 2)
    b = from_axis_angle([1.0, 0.0, 0.0], math.pi / 2)

    composta = hamilton(a, b)
    np.testing.assert_allclose(
        rotation_matrix_ib(composta), rotation_matrix_ib(a) @ rotation_matrix_ib(b), atol=1e-12
    )


def test_normalizar_recusa_quaternion_nulo():
    with pytest.raises(ValueError, match="norma nula"):
        normalize([0.0, 0.0, 0.0, 0.0])
