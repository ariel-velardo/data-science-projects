import numpy as np
import pandas as pd
import pytest

from src.validacao import validar_folds_persistidos, comparar_linha


def test_validacao_detecta_cluster_em_dois_folds():
    with pytest.raises(ValueError,match='cluster'):
        validar_folds_persistidos(np.array([1,2,3,1]),np.ones(4),np.array(['a','a','b','c']))


def test_validacao_detecta_cobertura_incompleta():
    with pytest.raises(ValueError,match='cobertura'):
        validar_folds_persistidos(np.array([1,2,3]),np.array([1,0,1]))


def test_validacao_rejeita_estimativa_adulterada():
    psi=np.array([0.,1.,2.,3.]); g=np.array(['a','a','b','b'])
    row=dict(n=4,estimativa=0.,se_iid=np.std(psi,ddof=1)/2,se_cluster=1.)
    with pytest.raises(AssertionError):
        comparar_linha(row,psi,g)
