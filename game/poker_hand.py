from typing import List, Tuple
from itertools import combinations
from collections import Counter
from .card import Card


class HandRank:
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

    NAMES = {
        1: "High Card",
        2: "One Pair",
        3: "Two Pair",
        4: "Three of a Kind",
        5: "Straight",
        6: "Flush",
        7: "Full House",
        8: "Four of a Kind",
        9: "Straight Flush",
        10: "Royal Flush"
    }


class PokerHandEvaluator:
    @staticmethod
    def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int], str]:
        """
        Evaluate a 5-card poker hand.
        Returns: (hand_rank, tiebreaker_values, hand_name)
        """
        if len(cards) != 5:
            raise ValueError("Must evaluate exactly 5 cards")

        values = sorted([card.value for card in cards], reverse=True)
        suits = [card.suit for card in cards]
        value_counts = Counter(values)

        is_flush = len(set(suits)) == 1
        is_straight = PokerHandEvaluator._is_straight(values)

        # Check for wheel (A-2-3-4-5)
        is_wheel = set(values) == {14, 2, 3, 4, 5}
        if is_wheel:
            values = [5, 4, 3, 2, 1]  # Ace is low in wheel

        # Royal Flush
        if is_flush and is_straight and max(values) == 14 and min(values) == 10:
            return (HandRank.ROYAL_FLUSH, values, HandRank.NAMES[HandRank.ROYAL_FLUSH])

        # Straight Flush
        if is_flush and is_straight:
            return (HandRank.STRAIGHT_FLUSH, values, HandRank.NAMES[HandRank.STRAIGHT_FLUSH])

        # Four of a Kind
        if 4 in value_counts.values():
            quad = [v for v, c in value_counts.items() if c == 4][0]
            kicker = [v for v, c in value_counts.items() if c != 4][0]
            return (HandRank.FOUR_OF_A_KIND, [quad, kicker], HandRank.NAMES[HandRank.FOUR_OF_A_KIND])

        # Full House
        if 3 in value_counts.values() and 2 in value_counts.values():
            trips = [v for v, c in value_counts.items() if c == 3][0]
            pair = [v for v, c in value_counts.items() if c == 2][0]
            return (HandRank.FULL_HOUSE, [trips, pair], HandRank.NAMES[HandRank.FULL_HOUSE])

        # Flush
        if is_flush:
            return (HandRank.FLUSH, values, HandRank.NAMES[HandRank.FLUSH])

        # Straight
        if is_straight:
            return (HandRank.STRAIGHT, values, HandRank.NAMES[HandRank.STRAIGHT])

        # Three of a Kind
        if 3 in value_counts.values():
            trips = [v for v, c in value_counts.items() if c == 3][0]
            kickers = sorted([v for v, c in value_counts.items() if c != 3], reverse=True)
            return (HandRank.THREE_OF_A_KIND, [trips] + kickers, HandRank.NAMES[HandRank.THREE_OF_A_KIND])

        # Two Pair
        if list(value_counts.values()).count(2) == 2:
            pairs = sorted([v for v, c in value_counts.items() if c == 2], reverse=True)
            kicker = [v for v, c in value_counts.items() if c == 1][0]
            return (HandRank.TWO_PAIR, pairs + [kicker], HandRank.NAMES[HandRank.TWO_PAIR])

        # One Pair
        if 2 in value_counts.values():
            pair = [v for v, c in value_counts.items() if c == 2][0]
            kickers = sorted([v for v, c in value_counts.items() if c != 2], reverse=True)
            return (HandRank.ONE_PAIR, [pair] + kickers, HandRank.NAMES[HandRank.ONE_PAIR])

        # High Card
        return (HandRank.HIGH_CARD, values, HandRank.NAMES[HandRank.HIGH_CARD])

    @staticmethod
    def _is_straight(values: List[int]) -> bool:
        sorted_vals = sorted(values)
        # Normal straight
        if sorted_vals == list(range(min(sorted_vals), min(sorted_vals) + 5)):
            return True
        # Wheel (A-2-3-4-5)
        if set(values) == {14, 2, 3, 4, 5}:
            return True
        return False

    @staticmethod
    def best_hand(cards: List[Card]) -> Tuple[List[Card], int, List[int], str]:
        """
        Find the best 5-card hand from 7 cards (hole cards + community cards).
        Returns: (best_5_cards, hand_rank, tiebreaker_values, hand_name)
        """
        if len(cards) < 5:
            raise ValueError("Need at least 5 cards")

        best_hand = None
        best_rank = (0, [])
        best_name = ""

        for combo in combinations(cards, 5):
            hand = list(combo)
            rank, tiebreakers, name = PokerHandEvaluator.evaluate_hand(hand)
            current_rank = (rank, tiebreakers)

            if best_hand is None or PokerHandEvaluator._compare_hands(current_rank, best_rank) > 0:
                best_hand = hand
                best_rank = current_rank
                best_name = name

        return (best_hand, best_rank[0], best_rank[1], best_name)

    @staticmethod
    def _compare_hands(hand1: Tuple[int, List[int]], hand2: Tuple[int, List[int]]) -> int:
        """
        Compare two hands. Returns positive if hand1 > hand2, negative if hand1 < hand2, 0 if equal.
        """
        if hand1[0] != hand2[0]:
            return hand1[0] - hand2[0]

        for v1, v2 in zip(hand1[1], hand2[1]):
            if v1 != v2:
                return v1 - v2
        return 0

    @staticmethod
    def compare_players(players_cards: List[Tuple[str, List[Card]]]) -> List[Tuple[str, int, str]]:
        """
        Compare multiple players' hands and return rankings.
        Input: List of (player_name, 7_cards)
        Output: List of (player_name, rank_position, hand_name) sorted by winner first
        """
        evaluated = []
        for name, cards in players_cards:
            _, rank, tiebreakers, hand_name = PokerHandEvaluator.best_hand(cards)
            evaluated.append((name, rank, tiebreakers, hand_name))

        # Sort by rank (desc) then tiebreakers (desc)
        evaluated.sort(key=lambda x: (x[1], x[2]), reverse=True)

        results = []
        current_rank = 1
        prev_score = None

        for i, (name, rank, tiebreakers, hand_name) in enumerate(evaluated):
            current_score = (rank, tiebreakers)
            if prev_score is not None and current_score != prev_score:
                current_rank = i + 1
            results.append((name, current_rank, hand_name))
            prev_score = current_score

        return results
