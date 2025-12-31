import random
from typing import Dict, List, Tuple
from .player import Player
from .card import Card
from .poker_hand import PokerHandEvaluator, HandRank


class AIPlayer(Player):
    def __init__(self, name: str, chips: int = 1000, difficulty: str = "medium"):
        super().__init__(name, chips, is_human=False)
        self.difficulty = difficulty  # easy, medium, hard

    def decide_action(self, game_state: Dict) -> Tuple[str, int]:
        """
        Decide what action to take based on game state.
        Returns: (action, amount)
        """
        valid_actions = game_state.get("valid_actions", [])
        if not valid_actions:
            return ("check", 0)

        # Get hand strength
        hand_strength = self._evaluate_hand_strength(game_state)
        pot_odds = self._calculate_pot_odds(game_state)
        position_factor = self._get_position_factor(game_state)

        # Adjust strength based on difficulty
        if self.difficulty == "easy":
            hand_strength *= random.uniform(0.7, 1.0)
        elif self.difficulty == "hard":
            hand_strength = hand_strength * 0.9 + position_factor * 0.1

        # Make decision
        return self._make_decision(valid_actions, hand_strength, pot_odds, game_state)

    def _evaluate_hand_strength(self, game_state: Dict) -> float:
        """
        Evaluate current hand strength on a scale of 0-1.
        """
        community_cards = self._parse_cards(game_state.get("community_cards", []))

        if not community_cards:
            # Pre-flop: evaluate hole cards
            return self._preflop_strength()
        else:
            # Post-flop: evaluate actual hand
            all_cards = self.hand + community_cards
            if len(all_cards) >= 5:
                _, rank, _, _ = PokerHandEvaluator.best_hand(all_cards)
                return self._rank_to_strength(rank)
            return self._preflop_strength()

    def _preflop_strength(self) -> float:
        """
        Evaluate pre-flop hand strength.
        """
        if len(self.hand) < 2:
            return 0.3

        card1, card2 = self.hand[0], self.hand[1]
        v1, v2 = card1.value, card2.value
        suited = card1.suit == card2.suit

        # Premium hands
        if v1 == v2:  # Pair
            if v1 >= 12:  # QQ+
                return 0.95
            elif v1 >= 9:  # 99-JJ
                return 0.85
            else:
                return 0.65 + (v1 / 14) * 0.15

        high = max(v1, v2)
        low = min(v1, v2)
        gap = high - low

        # High cards
        if high == 14:  # Ace
            if low >= 12:  # AK, AQ
                return 0.88 if suited else 0.85
            elif low >= 10:  # AJ, AT
                return 0.75 if suited else 0.70
            else:
                return 0.55 if suited else 0.45

        if high == 13:  # King
            if low >= 11:  # KQ, KJ
                return 0.70 if suited else 0.65
            elif low >= 9:
                return 0.55 if suited else 0.50

        # Suited connectors
        if suited and gap == 1 and low >= 6:
            return 0.55

        # Connected cards
        if gap == 1 and low >= 8:
            return 0.45

        # Suited
        if suited and high >= 10:
            return 0.40

        return 0.25 + (high / 14) * 0.1

    def _rank_to_strength(self, rank: int) -> float:
        """Convert hand rank to strength 0-1."""
        strength_map = {
            HandRank.HIGH_CARD: 0.20,
            HandRank.ONE_PAIR: 0.45,
            HandRank.TWO_PAIR: 0.65,
            HandRank.THREE_OF_A_KIND: 0.75,
            HandRank.STRAIGHT: 0.80,
            HandRank.FLUSH: 0.85,
            HandRank.FULL_HOUSE: 0.90,
            HandRank.FOUR_OF_A_KIND: 0.97,
            HandRank.STRAIGHT_FLUSH: 0.99,
            HandRank.ROYAL_FLUSH: 1.0
        }
        return strength_map.get(rank, 0.2)

    def _calculate_pot_odds(self, game_state: Dict) -> float:
        """Calculate pot odds."""
        pot = game_state.get("pot", 0)
        current_bet = game_state.get("current_bet", 0)
        call_amount = current_bet - self.current_bet

        if call_amount <= 0:
            return 1.0

        if pot + call_amount == 0:
            return 0.5

        return pot / (pot + call_amount)

    def _get_position_factor(self, game_state: Dict) -> float:
        """Get position advantage (late position = higher factor)."""
        players = game_state.get("players", [])
        dealer_pos = game_state.get("dealer_position", 0)
        my_pos = self.seat_position
        num_players = len(players)

        if num_players <= 1:
            return 0.5

        # Calculate relative position from dealer (0 = dealer, highest = early)
        relative_pos = (my_pos - dealer_pos) % num_players
        return relative_pos / num_players

    def _make_decision(self, valid_actions: List[Dict], strength: float,
                       pot_odds: float, game_state: Dict) -> Tuple[str, int]:
        """Make final decision based on calculations."""
        actions_map = {a["action"]: a for a in valid_actions}
        current_bet = game_state.get("current_bet", 0)
        pot = game_state.get("pot", 0)

        # Add randomness for unpredictability
        bluff_factor = random.random()
        if self.difficulty == "hard":
            bluff_threshold = 0.15
        elif self.difficulty == "medium":
            bluff_threshold = 0.08
        else:
            bluff_threshold = 0.03

        # Strong hand
        if strength >= 0.75:
            if "raise" in actions_map:
                raise_info = actions_map["raise"]
                raise_amount = self._calculate_raise_amount(raise_info, pot, strength)
                return ("raise", raise_amount)
            elif "call" in actions_map:
                return ("call", 0)
            return ("check", 0)

        # Medium hand
        elif strength >= 0.45:
            call_amount = actions_map.get("call", {}).get("amount", 0)

            # Good pot odds
            if pot_odds >= strength or call_amount == 0:
                if "check" in actions_map:
                    # Sometimes bet with medium hands
                    if random.random() < 0.3 and "raise" in actions_map:
                        raise_info = actions_map["raise"]
                        return ("raise", raise_info["min"])
                    return ("check", 0)
                return ("call", 0)

            # Bad pot odds but not too expensive
            if call_amount <= self.chips * 0.15:
                return ("call", 0)

            return ("fold", 0)

        # Weak hand
        else:
            # Check if possible
            if "check" in actions_map:
                # Occasional bluff
                if bluff_factor < bluff_threshold and "raise" in actions_map:
                    raise_info = actions_map["raise"]
                    return ("raise", raise_info["min"])
                return ("check", 0)

            # Consider calling small bets
            call_amount = actions_map.get("call", {}).get("amount", 0)
            if call_amount <= self.chips * 0.05 and pot_odds > 0.7:
                return ("call", 0)

            return ("fold", 0)

    def _calculate_raise_amount(self, raise_info: Dict, pot: int, strength: float) -> int:
        """Calculate optimal raise amount."""
        min_raise = raise_info.get("min", 0)
        max_raise = raise_info.get("max", min_raise)

        if self.difficulty == "easy":
            # Easy AI just min raises
            return min_raise

        # Value bet sizing based on strength
        if strength >= 0.9:
            # Very strong: bet big
            target = min(int(pot * 0.8), max_raise)
        elif strength >= 0.75:
            # Strong: bet 50-60% pot
            target = min(int(pot * 0.6), max_raise)
        else:
            # Medium: smaller bet
            target = min(int(pot * 0.4), max_raise)

        return max(min_raise, target)

    def _parse_cards(self, card_dicts: List[Dict]) -> List[Card]:
        """Convert card dictionaries to Card objects."""
        cards = []
        for cd in card_dicts:
            if isinstance(cd, dict):
                cards.append(Card(cd["rank"], cd["suit"]))
            elif isinstance(cd, Card):
                cards.append(cd)
        return cards
