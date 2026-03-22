"""FreeCell rules and state (no GUI). Deals via pysol-cards (MS / PySol-compatible RNG)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

from pysol_cards.deal_game import Game as PysolDealGame
from pysol_cards.random_base import RandomBase

RANK_NAMES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUIT_SYMBOL = {0: "\u2660", 1: "\u2665", 2: "\u2666", 3: "\u2663"}


class Suit(IntEnum):
    SPADES, HEARTS, DIAMONDS, CLUBS = range(4)


# pysol_cards suits: C S H D (0..3) → our Suit
_PYSOL_TO_SUIT = (Suit.CLUBS, Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS)


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: int  # 0=Ace .. 12=King

    @property
    def color(self) -> str:
        return "red" if self.suit in (Suit.HEARTS, Suit.DIAMONDS) else "black"


def _from_pysol(pc) -> Card:
    return Card(_PYSOL_TO_SUIT[pc.suit], pc.rank - 1)


class FreeCellGame:
    def __init__(self) -> None:
        self.game_num: int = 0
        self.free_cells: List[Optional[Card]] = [None] * 4
        self.foundations: List[List[Card]] = [[] for _ in range(4)]
        self.tableau: List[List[Card]] = [[] for _ in range(8)]
        self.deal()

    def deal(self, game_num: Optional[int] = None) -> None:
        if game_num is None:
            game_num = random.randint(1, 999_999)
        self.game_num = game_num
        g = PysolDealGame(
            game_id="freecell",
            game_num=game_num,
            which_deals=RandomBase.DEALS_MS,
            max_rank=13,
        )
        g.deal()
        g.freecell()
        self.free_cells = [None] * 4
        self.foundations = [[] for _ in range(4)]
        self.tableau = [[] for _ in range(8)]
        for col_idx, col in enumerate(g.board.columns.cols):
            self.tableau[col_idx] = [_from_pysol(pc) for pc in col]

    def _empty_free(self) -> int:
        return sum(1 for c in self.free_cells if c is None)

    def _empty_tab_cols(self) -> int:
        return sum(1 for c in self.tableau if len(c) == 0)

    def max_movable(self, src_col: int, n: int) -> int:
        empty_free = self._empty_free()
        empty_cols = self._empty_tab_cols()
        if len(self.tableau[src_col]) == n:
            empty_cols += 1
        return (empty_free + 1) * (2**empty_cols)

    def valid_seq(self, cards: List[Card]) -> bool:
        if not cards:
            return False
        for a, b in zip(cards, cards[1:]):
            if a.color == b.color or a.rank != b.rank + 1:
                return False
        return True

    def can_foundation(self, c: Card) -> bool:
        p = self.foundations[int(c.suit)]
        return c.rank == 0 if not p else p[-1].rank + 1 == c.rank

    def can_tableau(self, bottom: Card, col: List[Card]) -> bool:
        return not col or (bottom.color != col[-1].color and bottom.rank == col[-1].rank - 1)

    def move_tab_tab(self, src: int, start: int, dst: int) -> bool:
        if src == dst:
            return False
        seq = self.tableau[src][start:]
        if not seq or not self.valid_seq(seq) or len(seq) > self.max_movable(src, len(seq)):
            return False
        if not self.can_tableau(seq[0], self.tableau[dst]):
            return False
        moving = self.tableau[src][start:]
        self.tableau[src] = self.tableau[src][:start]
        self.tableau[dst].extend(moving)
        return True

    def move_free_tab(self, fi: int, dst: int) -> bool:
        c = self.free_cells[fi]
        if c is None or not self.can_tableau(c, self.tableau[dst]):
            return False
        self.free_cells[fi] = None
        self.tableau[dst].append(c)
        return True

    def move_tab_free(self, src: int, fi: int) -> bool:
        if self.free_cells[fi] is not None or not self.tableau[src]:
            return False
        self.free_cells[fi], self.tableau[src] = self.tableau[src][-1], self.tableau[src][:-1]
        return True

    def move_free_found(self, fi: int) -> bool:
        c = self.free_cells[fi]
        if c is None or not self.can_foundation(c):
            return False
        self.free_cells[fi] = None
        self.foundations[int(c.suit)].append(c)
        return True

    def move_tab_found(self, src: int) -> bool:
        col = self.tableau[src]
        if not col or not self.can_foundation(col[-1]):
            return False
        c = col.pop()
        self.foundations[int(c.suit)].append(c)
        return True

    def won(self) -> bool:
        return all(len(p) == 13 for p in self.foundations)
