"""Exceções compartilhadas pelas estruturas de dados."""


class EstruturaVaziaError(IndexError):
    """Operação de leitura/remoção solicitada em uma estrutura vazia."""
