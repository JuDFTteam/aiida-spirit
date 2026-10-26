# -*- coding: utf-8 -*-
"""Tests for the split of the full exchange tensor into J, D and K"""
import numpy as np
from aiida_spirit.calculations import _split_exchange_tensor

# two-spin case measured with spirit develop b3b94c2a (jij-prediction spirit relay, note 06):
# one bond listed once, random non-collinear state; spirit total energy -1.2017343304 meV
J = 1.7
D = np.array([0.3, -0.5, 0.8])
K = np.array([[-0.4, 0.05, -0.15], [0.05, 0.1, 0.25], [-0.15, 0.25, 0.3]])
E_SPIRIT = -1.2017343304


def _cross_matrix(vec):
    """Matrix [v]_x with [v]_x w = v x w"""
    return np.array([[0, -vec[2], vec[1]], [vec[2], 0, -vec[0]], [-vec[1], vec[0], 0]])


def test_split_exchange_tensor():
    """Splitting Jtensor = J 1 + K + [D]_x^T gives back J, D, K, and -n1^T Jtensor n2
    equals spirit's energy for the same bond."""
    tensor = J * np.eye(3) + K + _cross_matrix(D).T
    jij, dij, kij = _split_exchange_tensor(tensor[None])
    assert np.allclose(jij, [J])
    assert np.allclose(dij, [D])
    assert np.allclose(kij, [K])
    # D_x = (Jtensor_yz - Jtensor_zy) / 2 (jij-prediction convention, half of aiida-kkr's JijData)
    assert np.isclose(dij[0, 0], (tensor[1, 2] - tensor[2, 1]) / 2)

    rng = np.random.default_rng(0)
    n1, n2 = (v / np.linalg.norm(v) for v in rng.normal(size=(2, 3)))
    e_hand = -J * n1 @ n2 - D @ np.cross(n1, n2) - n1 @ K @ n2
    assert np.isclose(-n1 @ tensor @ n2, e_hand)
    assert np.isclose(e_hand, E_SPIRIT, atol=1e-9)
