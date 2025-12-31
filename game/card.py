import random
from dataclasses import dataclass
from typing import List


SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
SUIT_SYMBOLS = {'hearts': '\u2665', 'diamonds': '\u2666', 'clubs': '\u2663', 'spades': '\u2660'}
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS, 2)}


@dataclass
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    @property
    def symbol(self) -> str:
        return SUIT_SYMBOLS[self.suit]

    def __str__(self) -> str:
        return f"{self.rank}{self.symbol}"

    def __repr__(self) -> str:
        return f"Card('{self.rank}', '{self.suit}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    def __lt__(self, other) -> bool:
        return self.value < other.value

    def to_dict(self) -> dict:
        return {
            'rank': self.rank,
            'suit': self.suit,
            'value': self.value,
            'display': str(self)
        }


class Deck:
    def __init__(self):
        self.cards: List[Card] = []
        self.reset()

    def reset(self) -> None:
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, num: int = 1) -> List[Card]:
        if num > len(self.cards):
            raise ValueError(f"Cannot deal {num} cards, only {len(self.cards)} remaining")
        dealt = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt

    def deal_one(self) -> Card:
        return self.deal(1)[0]

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return f"Deck({len(self.cards)} cards)"
