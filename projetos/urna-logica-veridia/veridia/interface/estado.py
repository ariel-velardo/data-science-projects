"""Estado da interface: uma ``SessaoJogo`` por navegador e o contexto de cada aba.

Cada navegador recebe de NiceGUI um identificador próprio
(``app.storage.browser["id"]``, guardado em cookie). O ``GerenciadorSessoes``
associa esse identificador a uma ``SessaoJogo`` em memória. Assim:

- jogadores diferentes nunca compartilham a mesma partida;
- navegar entre telas (ou recarregar a página) continua a mesma partida;
- "Sair" descarta apenas a partida daquele navegador, sem parar o servidor.

Não há banco de dados: reiniciar o servidor zera todas as partidas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from veridia.fases.base import ResultadoAcao
from veridia.jogo.sessao import SessaoJogo


class GerenciadorSessoes:
    """Registro em memória: id do navegador → SessaoJogo."""

    def __init__(self) -> None:
        self._sessoes: dict[str, SessaoJogo] = {}

    def obter(self, identificador: str) -> SessaoJogo:
        if not identificador:
            raise ValueError("identificador de sessão vazio")
        if identificador not in self._sessoes:
            self._sessoes[identificador] = SessaoJogo()
        return self._sessoes[identificador]

    def existe(self, identificador: str) -> bool:
        return identificador in self._sessoes

    def descartar(self, identificador: str) -> bool:
        """Encerra a partida deste navegador. Devolve False se não havia partida."""
        return self._sessoes.pop(identificador, None) is not None

    def __len__(self) -> int:
        return len(self._sessoes)


GERENCIADOR = GerenciadorSessoes()


@dataclass
class ContextoTela:
    """Contexto de uma aba aberta: identifica a sessão e guarda ganchos de atualização.

    ``ao_clicar_local`` é preenchido pela tela do mapa; o evento de clique no
    SVG é registrado UMA vez no layout e repassado para cá (evita handlers
    duplicados quando a tela é redesenhada).
    """

    identificador: str
    gerenciador: GerenciadorSessoes = field(default_factory=lambda: GERENCIADOR)
    atualizar_selos: Callable[[], None] = lambda: None
    ao_clicar_local: Callable[[str], None] | None = None
    memoria: dict[str, Any] = field(default_factory=dict)  # dados de tela (ex.: última busca do Resolver)

    @property
    def sessao(self) -> SessaoJogo:
        return self.gerenciador.obter(self.identificador)

    def agir(self, numero_fase: int, acao: str, *args: Any, **kwargs: Any) -> ResultadoAcao:
        """Executa uma ação de fase SEMPRE pela sessão (que é quem concede selos).

        A sessão age sobre ``fase_atual``; ao conceder um selo ela avança para a
        fase seguinte. Como o jogador continua vendo a tela da fase
        ``numero_fase``, a fase atual é reposicionada antes de cada ação.
        """
        sessao = self.sessao
        if sessao.fase_atual != numero_fase:
            entrada = sessao.ir_para_fase(numero_fase)
            if not entrada.sucesso:
                return entrada
        resultado = sessao.executar(acao, *args, **kwargs)
        self.atualizar_selos()
        return resultado
