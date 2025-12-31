from typing import List, Optional
from .card import Card


class Player:
    def __init__(self, name: str, chips: int = 1000, is_human: bool = True):
        self.name = name
        self.chips = chips
        self.is_human = is_human
        self.hand: List[Card] = []
        self.current_bet = 0
        self.total_bet_this_round = 0
        self.is_folded = False
        self.is_all_in = False
        self.seat_position = 0

    def receive_cards(self, cards: List[Card]) -> None:
        self.hand.extend(cards)

    def clear_hand(self) -> None:
        self.hand = []
        self.current_bet = 0
        self.total_bet_this_round = 0
        self.is_folded = False
        self.is_all_in = False

    def bet(self, amount: int) -> int:
        actual_bet = min(amount, self.chips)
        self.chips -= actual_bet
        self.current_bet += actual_bet
        self.total_bet_this_round += actual_bet
        if self.chips == 0:
            self.is_all_in = True
        return actual_bet

    def fold(self) -> None:
        self.is_folded = True

    def win_pot(self, amount: int) -> None:
        self.chips += amount

    def reset_current_bet(self) -> None:
        self.current_bet = 0

    @property
    def is_active(self) -> bool:
        return not self.is_folded and self.chips > 0

    @property
    def can_act(self) -> bool:
        return self.is_active and not self.is_all_in

    def to_dict(self, hide_cards: bool = False) -> dict:
        return {
            'name': self.name,
            'chips': self.chips,
            'current_bet': self.current_bet,
            'total_bet': self.total_bet_this_round,
            'is_folded': self.is_folded,
            'is_all_in': self.is_all_in,
            'is_human': self.is_human,
            'seat_position': self.seat_position,
            'hand': [] if hide_cards else [card.to_dict() for card in self.hand],
            'card_count': len(self.hand)
        }

    def __repr__(self) -> str:
        return f"Player('{self.name}', chips={self.chips}, hand={self.hand})"
