"""
AI Player for Last Card / Crazy Eights
"""
import random
from typing import Dict, List, Tuple, Optional
from .player import Player
from .card import Card


class AIPlayer(Player):
    """AI player for Last Card game."""

    def __init__(self, name: str, difficulty: str = "medium"):
        super().__init__(name, is_human=False)
        self.difficulty = difficulty  # easy, medium, hard

    def decide_action(self, game_state: Dict) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Decide what action to take based on game state.
        Returns: (action, card_index, suit_override)
        """
        valid_actions = game_state.get("valid_actions", [])
        playable_cards = game_state.get("playable_cards", [])
        pending_draw = game_state.get("pending_draw", 0)

        if not valid_actions:
            return ("draw_card", None, None)

        # First, check if we should call Last Card
        if len(self.hand) == 2 and not self.last_card_called and 'call_last_card' in valid_actions:
            # AI should call last card before playing
            return ("call_last_card", None, None)

        # If we must draw due to 2s, draw unless we have a 2
        if pending_draw > 0:
            twos = [i for i in playable_cards if self.hand[i].rank == '2']
            if twos:
                return self._play_card(twos[0], game_state)
            else:
                return ("draw_card", None, None)

        # If we can play a card, decide which one
        if playable_cards and 'play_card' in valid_actions:
            card_index = self._choose_card_to_play(playable_cards, game_state)
            return self._play_card(card_index, game_state)

        # Otherwise, draw
        return ("draw_card", None, None)

    def _choose_card_to_play(self, playable_cards: List[int], game_state: Dict) -> int:
        """Choose the best card to play from playable options."""

        if self.difficulty == "easy":
            # Easy AI plays randomly
            return random.choice(playable_cards)

        # Categorize cards
        special_cards = {
            '2': [],   # Draw 2 - offensive
            'J': [],   # Skip - offensive
            'A': [],   # Reverse
            '8': [],   # Wild - save for emergencies
        }
        normal_cards = []

        for i in playable_cards:
            card = self.hand[i]
            if card.rank in special_cards:
                special_cards[card.rank].append(i)
            else:
                normal_cards.append(i)

        # Strategy based on difficulty
        if self.difficulty == "hard":
            return self._hard_ai_choice(special_cards, normal_cards, game_state)
        else:
            return self._medium_ai_choice(special_cards, normal_cards, game_state)

    def _medium_ai_choice(self, special_cards: Dict, normal_cards: List[int], game_state: Dict) -> int:
        """Medium difficulty AI card selection."""

        # If few cards left, prioritize getting rid of non-wilds
        if len(self.hand) <= 3:
            # Play normal cards first to save specials
            if normal_cards:
                return random.choice(normal_cards)
            # Play offensive cards
            for rank in ['2', 'J', 'A']:
                if special_cards[rank]:
                    return special_cards[rank][0]

        # Play offensive cards (2s, Jacks) when others have few cards
        players = game_state.get('players', [])
        opponent_low_cards = any(p['card_count'] <= 3 for p in players if p['name'] != self.name)

        if opponent_low_cards:
            # Attack with 2s or skips
            if special_cards['2']:
                return special_cards['2'][0]
            if special_cards['J']:
                return special_cards['J'][0]

        # Normal play - prefer normal cards, save wilds
        if normal_cards:
            return random.choice(normal_cards)

        # Play reverses/skips
        for rank in ['A', 'J', '2']:
            if special_cards[rank]:
                return special_cards[rank][0]

        # Last resort: play wild 8
        if special_cards['8']:
            return special_cards['8'][0]

        # Fallback
        return random.choice([i for cards in special_cards.values() for i in cards] + normal_cards)

    def _hard_ai_choice(self, special_cards: Dict, normal_cards: List[int], game_state: Dict) -> int:
        """Hard difficulty AI card selection - smarter strategy."""

        players = game_state.get('players', [])
        current_suit = game_state.get('current_suit', '')

        # Count suits in hand
        suit_counts = {}
        for card in self.hand:
            suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

        # Find most common suit
        most_common_suit = max(suit_counts.keys(), key=lambda s: suit_counts[s]) if suit_counts else None

        # Check if next player has few cards
        my_index = next((i for i, p in enumerate(players) if p['name'] == self.name), 0)
        direction = game_state.get('direction', 1)
        next_index = (my_index + direction) % len(players)
        next_player = players[next_index] if players else None
        next_has_few = next_player and next_player['card_count'] <= 2

        # If next player has few cards, attack!
        if next_has_few:
            if special_cards['2']:
                return special_cards['2'][0]
            if special_cards['J']:
                return special_cards['J'][0]

        # If we have few cards, play safe
        if len(self.hand) <= 2:
            # Avoid playing wilds if we have other options
            if normal_cards:
                # Play card that matches our most common suit
                matching = [i for i in normal_cards if self.hand[i].suit == most_common_suit]
                if matching:
                    return matching[0]
                return normal_cards[0]

        # Try to change to our most common suit
        if most_common_suit and most_common_suit != current_suit:
            # Look for cards that change to our suit
            suit_changers = [i for i in normal_cards if self.hand[i].suit == most_common_suit]
            if suit_changers:
                return suit_changers[0]

        # Play normal cards
        if normal_cards:
            return random.choice(normal_cards)

        # Play non-wild specials
        for rank in ['A', 'J', '2']:
            if special_cards[rank]:
                return special_cards[rank][0]

        # Last resort: wild
        if special_cards['8']:
            return special_cards['8'][0]

        return normal_cards[0] if normal_cards else list(special_cards.values())[0][0]

    def _play_card(self, card_index: int, game_state: Dict) -> Tuple[str, int, Optional[str]]:
        """Return play action with optional suit override for wilds."""
        card = self.hand[card_index]

        # If playing a wild 8, choose the suit we have most of
        if card.rank == '8':
            suit_override = self._choose_wild_suit()
            return ("play_card", card_index, suit_override)

        return ("play_card", card_index, None)

    def _choose_wild_suit(self) -> str:
        """Choose suit for wild 8 - pick the one we have most of."""
        suit_counts = {}
        for card in self.hand:
            if card.rank != '8':  # Don't count other wilds
                suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

        if suit_counts:
            return max(suit_counts.keys(), key=lambda s: suit_counts[s])

        # If only wilds left, pick randomly
        return random.choice(['hearts', 'diamonds', 'clubs', 'spades'])
