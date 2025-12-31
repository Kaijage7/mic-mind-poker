"""
AI Player for Last Card / Crazy Eights
"""
import random
from typing import Dict, List, Tuple, Optional, Union
from .player import Player
from .card import Card


class AIPlayer(Player):
    """AI player for Last Card game."""

    def __init__(self, name: str, difficulty: str = "medium"):
        super().__init__(name, is_human=False)
        self.difficulty = difficulty  # easy, medium, hard

    def decide_action(self, game_state: Dict) -> Tuple[str, Optional[Union[int, List[int]]], Optional[str]]:
        """
        Decide what action to take based on game state.
        Returns: (action, card_index_or_indices, suit_override)
        - For single card: ("play_card", card_index, suit_override)
        - For multi-card: ("play_cards", [indices], suit_override)
        """
        valid_actions = game_state.get("valid_actions", [])
        playable_cards = game_state.get("playable_cards", [])
        pending_draw = game_state.get("pending_draw", 0)

        if not valid_actions:
            return ("draw_card", None, None)

        # First, check if we should call Last Card (with 2-3 cards for multi-card finish)
        if len(self.hand) in [2, 3] and not self.last_card_called and 'call_last_card' in valid_actions:
            # AI should call last card before playing
            return ("call_last_card", None, None)

        # If we must draw due to 2s/Joker, draw unless we have a 2
        if pending_draw > 0:
            twos = [i for i in playable_cards if self.hand[i].rank == '2']
            if twos:
                # For hard AI, try to play all 2s to stack
                if self.difficulty == "hard" and len(twos) > 1:
                    return self._play_cards(twos, game_state)
                return self._play_card(twos[0], game_state)
            else:
                return ("draw_card", None, None)

        # If we can play a card, decide which one (or multiple)
        if playable_cards and 'play_card' in valid_actions:
            return self._choose_cards_to_play(playable_cards, game_state)

        # Otherwise, draw
        return ("draw_card", None, None)

    def _get_matching_cards(self, playable_cards: List[int], rank: str) -> List[int]:
        """Get all playable cards with the same rank."""
        return [i for i in playable_cards if self.hand[i].rank == rank]

    def _choose_cards_to_play(self, playable_cards: List[int], game_state: Dict) -> Tuple[str, Union[int, List[int]], Optional[str]]:
        """
        Choose the best card(s) to play, potentially multiple of same rank or combos.
        Returns: (action, card_index_or_indices, suit_override)

        Valid combos:
        - Same rank: 2, 3, or 4 cards of same rank
        - Jack combo: Jack + any other card(s)
        - Joker + 2: Stack draw effects
        """
        # Easy AI always plays single cards
        if self.difficulty == "easy":
            card_index = random.choice(playable_cards)
            return self._play_card(card_index, game_state)

        # For medium/hard AI, consider combo plays
        card_index = self._choose_card_to_play(playable_cards, game_state)
        chosen_card = self.hand[card_index]

        # Check for Joker + 2 combo opportunity (hard AI)
        if self.difficulty == "hard":
            combo_indices = self._find_joker_two_combo(playable_cards)
            if combo_indices and len(combo_indices) > 1:
                return self._play_cards(combo_indices, game_state)

            # Check for Jack combo opportunity
            jack_combo = self._find_jack_combo(playable_cards)
            if jack_combo and len(jack_combo) > 1:
                return self._play_cards(jack_combo, game_state)

        # Find all matching cards of same rank
        matching_indices = self._get_matching_cards(playable_cards, chosen_card.rank)

        # Decide if we should play multiple cards
        should_play_multiple = False

        if len(matching_indices) > 1:
            # Hard AI: Always play multiple when advantageous
            if self.difficulty == "hard":
                # Play multiple 2s to stack damage
                if chosen_card.rank == '2':
                    should_play_multiple = True
                # Play multiple normal cards to get rid of them faster
                elif chosen_card.rank not in ['A', 'J', 'Joker']:
                    should_play_multiple = True
                # Play multiple Jacks for combo (free throw)
                elif chosen_card.rank == 'J':
                    should_play_multiple = True

            # Medium AI: Sometimes play multiple cards
            elif self.difficulty == "medium":
                # 50% chance to play multiple 2s
                if chosen_card.rank == '2' and random.random() > 0.5:
                    should_play_multiple = True
                # Play multiple normal cards if we have many cards
                elif len(self.hand) > 5 and chosen_card.rank not in ['A', 'J', 'Joker', '2']:
                    should_play_multiple = True
                # Medium AI: Sometimes use Jack combo
                if chosen_card.rank == 'J' and random.random() > 0.5:
                    jack_combo = self._find_jack_combo(playable_cards)
                    if jack_combo and len(jack_combo) > 1:
                        return self._play_cards(jack_combo, game_state)

        # Check if playing multiple would leave us with 1 card and it's a special card
        if should_play_multiple:
            remaining_after = len(self.hand) - len(matching_indices)
            if remaining_after == 1:
                # Check if the remaining card is a special card (can't be last)
                remaining_card = None
                for i, card in enumerate(self.hand):
                    if i not in matching_indices:
                        remaining_card = card
                        break
                if remaining_card and remaining_card.rank in ['A', '2', '8', 'J', 'Joker']:
                    # Can't play all - play fewer to avoid having special as last
                    should_play_multiple = False

            # Check if playing would end with 0 cards but last is special
            if remaining_after == 0 and chosen_card.rank in ['A', '2', '8', 'J', 'Joker']:
                should_play_multiple = False

        if should_play_multiple and len(matching_indices) > 1:
            return self._play_cards(matching_indices, game_state)

        return self._play_card(card_index, game_state)

    def _find_joker_two_combo(self, playable_cards: List[int]) -> List[int]:
        """Find Joker + 2 combo cards for maximum draw damage."""
        jokers = [i for i in range(len(self.hand)) if self.hand[i].rank == 'Joker']
        twos = [i for i in range(len(self.hand)) if self.hand[i].rank == '2']

        # Only combine if we have at least one Joker (Joker can always be played)
        if not jokers:
            return []

        # Combine Jokers and 2s
        combo = jokers + twos

        # Check remaining cards after combo
        remaining = len(self.hand) - len(combo)
        if remaining == 0:
            # Can't finish with special cards
            return []
        if remaining == 1:
            # Check if remaining card is special
            for i, card in enumerate(self.hand):
                if i not in combo:
                    if card.rank in ['A', '2', '8', 'J', 'Joker']:
                        return []  # Can't leave special as last

        return combo if len(combo) > 1 else []

    def _find_jack_combo(self, playable_cards: List[int]) -> List[int]:
        """Find Jack + other cards combo for playing multiple cards."""
        jacks = [i for i in playable_cards if self.hand[i].rank == 'J']
        if not jacks:
            return []

        # Jack can be combined with any other card
        # Find non-special cards to combine with Jack
        combo = list(jacks)
        for i in playable_cards:
            if i not in combo:
                card = self.hand[i]
                # Prefer adding non-special cards
                if card.rank not in ['A', '2', '8', 'J', 'Joker']:
                    combo.append(i)
                    break  # Just add one for Jack combo

        # Check remaining cards
        remaining = len(self.hand) - len(combo)
        if remaining == 0:
            # Check if last card in combo is special
            last_card = self.hand[combo[-1]]
            if last_card.rank in ['A', '2', '8', 'J', 'Joker']:
                return []
        if remaining == 1:
            for i, card in enumerate(self.hand):
                if i not in combo:
                    if card.rank in ['A', '2', '8', 'J', 'Joker']:
                        return []

        return combo if len(combo) > 1 else []

    def _choose_card_to_play(self, playable_cards: List[int], game_state: Dict) -> int:
        """Choose the best single card to play from playable options."""

        if self.difficulty == "easy":
            # Easy AI plays randomly
            return random.choice(playable_cards)

        # Categorize cards based on official Last Card rules
        special_cards = {
            'Joker': [],  # Wild + draw 6 - most powerful
            '2': [],      # Draw 2 - offensive (stackable)
            'A': [],      # Change suit - wild-like
            'J': [],      # Free throw - play another card
            '7': [],      # Reverse direction
            '8': [],      # Reverse direction
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
            for rank in ['7', '2', 'J', 'A']:
                if special_cards[rank]:
                    return special_cards[rank][0]

        # Play offensive cards (2s, Jacks, 7s, Jokers) when others have few cards
        players = game_state.get('players', [])
        opponent_low_cards = any(p['card_count'] <= 3 for p in players if p['name'] != self.name)

        if opponent_low_cards:
            # Attack with Joker (most powerful), 2s, 7s, or skips
            if special_cards['Joker']:
                return special_cards['Joker'][0]
            if special_cards['2']:
                return special_cards['2'][0]
            if special_cards['7']:
                return special_cards['7'][0]
            if special_cards['J']:
                return special_cards['J'][0]

        # Normal play - prefer normal cards, save wilds
        if normal_cards:
            return random.choice(normal_cards)

        # Play non-wild specials first
        for rank in ['7', 'A', 'J', '2']:
            if special_cards[rank]:
                return special_cards[rank][0]

        # Last resort: play wild 8 or Joker
        if special_cards['8']:
            return special_cards['8'][0]
        if special_cards['Joker']:
            return special_cards['Joker'][0]

        # Fallback
        return random.choice([i for cards in special_cards.values() for i in cards] + normal_cards)

    def _hard_ai_choice(self, special_cards: Dict, normal_cards: List[int], game_state: Dict) -> int:
        """Hard difficulty AI card selection - smarter strategy."""

        players = game_state.get('players', [])
        current_suit = game_state.get('current_suit', '')

        # Count suits in hand (exclude Jokers which have no meaningful suit)
        suit_counts = {}
        for card in self.hand:
            if card.rank != 'Joker':
                suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

        # Find most common suit
        most_common_suit = max(suit_counts.keys(), key=lambda s: suit_counts[s]) if suit_counts else None

        # Check if next player has few cards
        my_index = next((i for i, p in enumerate(players) if p['name'] == self.name), 0)
        direction = game_state.get('direction', 1)
        next_index = (my_index + direction) % len(players)
        next_player = players[next_index] if players else None
        next_has_few = next_player and next_player['card_count'] <= 2

        # If next player has few cards, attack aggressively!
        if next_has_few:
            # Use Joker for maximum damage
            if special_cards['Joker']:
                return special_cards['Joker'][0]
            if special_cards['2']:
                return special_cards['2'][0]
            if special_cards['7']:
                return special_cards['7'][0]
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
        for rank in ['7', 'A', 'J', '2']:
            if special_cards[rank]:
                return special_cards[rank][0]

        # Last resort: wild 8 or Joker
        if special_cards['8']:
            return special_cards['8'][0]
        if special_cards['Joker']:
            return special_cards['Joker'][0]

        return normal_cards[0] if normal_cards else list(special_cards.values())[0][0]

    def _play_card(self, card_index: int, game_state: Dict) -> Tuple[str, int, Optional[str]]:
        """Return play action with optional suit override for wilds."""
        card = self.hand[card_index]

        # If playing Ace or Joker (suit changers), choose the suit we have most of
        if card.rank == 'A' or card.rank == 'Joker':
            suit_override = self._choose_wild_suit()
            return ("play_card", card_index, suit_override)

        return ("play_card", card_index, None)

    def _play_cards(self, card_indices: List[int], game_state: Dict) -> Tuple[str, List[int], Optional[str]]:
        """Return play action for multiple cards with optional suit override."""
        if not card_indices:
            return ("draw_card", None, None)

        first_card = self.hand[card_indices[0]]

        # If playing Aces or Jokers (suit changers), choose the suit we have most of
        if first_card.rank == 'A' or first_card.rank == 'Joker':
            suit_override = self._choose_wild_suit()
            return ("play_cards", card_indices, suit_override)

        return ("play_cards", card_indices, None)

    def _choose_wild_suit(self) -> str:
        """Choose suit for wild card - pick the one we have most of."""
        suit_counts = {}
        for card in self.hand:
            # Don't count other suit changers (Aces and Jokers)
            if card.rank != 'A' and card.rank != 'Joker':
                suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

        if suit_counts:
            return max(suit_counts.keys(), key=lambda s: suit_counts[s])

        # If only suit changers left, pick randomly
        return random.choice(['hearts', 'diamonds', 'clubs', 'spades'])
