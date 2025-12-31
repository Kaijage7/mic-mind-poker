from typing import List, Optional
from .card import Card


class Player:
    def __init__(self, name: str, is_human: bool = True):
        self.name = name
        self.is_human = is_human
        self.hand: List[Card] = []
        self.seat_position = 0
        self.avatar = 'default'
        self.last_card_called = False  # For Last Card game
        self.wins = 0  # Track wins

    def receive_cards(self, cards: List[Card]) -> None:
        self.hand.extend(cards)

    def clear_hand(self) -> None:
        self.hand = []
        self.last_card_called = False

    def to_dict(self, hide_cards: bool = False) -> dict:
        return {
            'name': self.name,
            'is_human': self.is_human,
            'seat_position': self.seat_position,
            'avatar': self.avatar,
            'hand': [] if hide_cards else [card.to_dict() for card in self.hand],
            'card_count': len(self.hand),
            'last_card_called': self.last_card_called,
            'wins': self.wins
        }

    def __repr__(self) -> str:
        return f"Player('{self.name}', cards={len(self.hand)})"
