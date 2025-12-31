from typing import List, Dict, Tuple
from itertools import combinations
import random
from .card import Card, Deck, SUITS, RANKS
from .poker_hand import PokerHandEvaluator


class WinProbabilityCalculator:
    """Monte Carlo simulation for calculating win probability."""

    @staticmethod
    def calculate_win_probability(
        hole_cards: List[Card],
        community_cards: List[Card],
        num_opponents: int,
        simulations: int = 1000
    ) -> Dict:
        """
        Calculate probability of winning using Monte Carlo simulation.
        Returns probabilities for win, tie, and loss.
        """
        if len(hole_cards) != 2:
            return {'win': 0, 'tie': 0, 'lose': 0, 'hand_odds': {}}

        wins = 0
        ties = 0
        losses = 0

        # Cards that are already in play
        used_cards = set()
        for card in hole_cards + community_cards:
            used_cards.add((card.rank, card.suit))

        # Create deck of remaining cards
        remaining_cards = []
        for suit in SUITS:
            for rank in RANKS:
                if (rank, suit) not in used_cards:
                    remaining_cards.append(Card(rank, suit))

        for _ in range(simulations):
            # Shuffle remaining cards
            deck = remaining_cards.copy()
            random.shuffle(deck)

            # Deal remaining community cards
            cards_needed = 5 - len(community_cards)
            sim_community = community_cards.copy()
            deck_index = 0

            for _ in range(cards_needed):
                sim_community.append(deck[deck_index])
                deck_index += 1

            # Deal opponent hands
            opponent_hands = []
            for _ in range(num_opponents):
                opponent_hand = [deck[deck_index], deck[deck_index + 1]]
                deck_index += 2
                opponent_hands.append(opponent_hand)

            # Evaluate our hand
            our_cards = hole_cards + sim_community
            _, our_rank, our_tiebreakers, _ = PokerHandEvaluator.best_hand(our_cards)

            # Evaluate opponent hands
            best_opponent_rank = 0
            best_opponent_tiebreakers = []

            for opp_hand in opponent_hands:
                opp_cards = opp_hand + sim_community
                _, opp_rank, opp_tiebreakers, _ = PokerHandEvaluator.best_hand(opp_cards)

                if opp_rank > best_opponent_rank or (
                    opp_rank == best_opponent_rank and opp_tiebreakers > best_opponent_tiebreakers
                ):
                    best_opponent_rank = opp_rank
                    best_opponent_tiebreakers = opp_tiebreakers

            # Compare
            if our_rank > best_opponent_rank:
                wins += 1
            elif our_rank < best_opponent_rank:
                losses += 1
            else:
                if our_tiebreakers > best_opponent_tiebreakers:
                    wins += 1
                elif our_tiebreakers < best_opponent_tiebreakers:
                    losses += 1
                else:
                    ties += 1

        total = simulations
        return {
            'win': round((wins / total) * 100, 1),
            'tie': round((ties / total) * 100, 1),
            'lose': round((losses / total) * 100, 1)
        }

    @staticmethod
    def calculate_hand_odds(hole_cards: List[Card], community_cards: List[Card]) -> Dict:
        """
        Calculate odds of making different hands by the river.
        """
        if len(hole_cards) != 2:
            return {}

        cards_to_come = 5 - len(community_cards)
        if cards_to_come <= 0:
            return {}

        # Cards that are already in play
        used_cards = set()
        for card in hole_cards + community_cards:
            used_cards.add((card.rank, card.suit))

        remaining_cards = []
        for suit in SUITS:
            for rank in RANKS:
                if (rank, suit) not in used_cards:
                    remaining_cards.append(Card(rank, suit))

        hand_counts = {
            'Royal Flush': 0,
            'Straight Flush': 0,
            'Four of a Kind': 0,
            'Full House': 0,
            'Flush': 0,
            'Straight': 0,
            'Three of a Kind': 0,
            'Two Pair': 0,
            'One Pair': 0,
            'High Card': 0
        }

        # Sample combinations
        simulations = min(1000, len(list(combinations(remaining_cards, cards_to_come))))
        sample_combos = random.sample(
            list(combinations(remaining_cards, cards_to_come)),
            min(simulations, len(list(combinations(remaining_cards, cards_to_come))))
        )

        for combo in sample_combos:
            all_cards = hole_cards + community_cards + list(combo)
            _, _, _, hand_name = PokerHandEvaluator.best_hand(all_cards)
            hand_counts[hand_name] += 1

        total = len(sample_combos)
        return {
            name: round((count / total) * 100, 1)
            for name, count in hand_counts.items()
            if count > 0
        }

    @staticmethod
    def get_outs(hole_cards: List[Card], community_cards: List[Card]) -> Dict:
        """
        Calculate outs for improving your hand.
        """
        if len(community_cards) < 3 or len(community_cards) >= 5:
            return {'outs': 0, 'odds': '0%', 'draws': []}

        all_cards = hole_cards + community_cards
        _, current_rank, _, current_name = PokerHandEvaluator.best_hand(all_cards)

        # Cards that are already in play
        used_cards = set()
        for card in all_cards:
            used_cards.add((card.rank, card.suit))

        remaining_cards = []
        for suit in SUITS:
            for rank in RANKS:
                if (rank, suit) not in used_cards:
                    remaining_cards.append(Card(rank, suit))

        outs = []
        draws = []

        for card in remaining_cards:
            test_cards = all_cards + [card]
            _, new_rank, _, new_name = PokerHandEvaluator.best_hand(test_cards)

            if new_rank > current_rank:
                outs.append(card)
                if new_name not in draws:
                    draws.append(new_name)

        num_outs = len(outs)
        cards_to_come = 5 - len(community_cards)

        # Calculate odds
        if cards_to_come == 2:  # After flop
            odds = round((1 - ((47 - num_outs) / 47 * (46 - num_outs) / 46)) * 100, 1)
        else:  # After turn
            odds = round((num_outs / (52 - len(all_cards))) * 100, 1)

        return {
            'outs': num_outs,
            'odds': f'{odds}%',
            'draws': draws,
            'current_hand': current_name
        }

    @staticmethod
    def get_hand_strength_label(win_probability: float) -> Tuple[str, str]:
        """
        Return a label and color for hand strength.
        """
        if win_probability >= 80:
            return ('Monster', '#00ff00')
        elif win_probability >= 65:
            return ('Strong', '#7fff00')
        elif win_probability >= 50:
            return ('Good', '#ffff00')
        elif win_probability >= 35:
            return ('Marginal', '#ffa500')
        elif win_probability >= 20:
            return ('Weak', '#ff6600')
        else:
            return ('Fold', '#ff0000')
