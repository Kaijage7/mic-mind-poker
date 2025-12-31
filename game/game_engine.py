"""
Last Card / Crazy Eights Game Engine
"""
from enum import Enum
from typing import List, Dict, Optional, Tuple
from .card import Card, Deck
from .player import Player


class GamePhase(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    GAME_OVER = "game_over"


class LastCardGame:
    """
    Last Card game implementation (official rules).

    Rules:
    - Each player gets 5 cards
    - Match rank OR suit to play a card
    - Special cards:
      - Ace: Change suit (can be played anytime)
      - 2: Next player draws 2 cards (stackable)
      - 8: Skip next player
      - Jack: Free throw (play another card), can be played on any card
      - Joker: Wild + next player draws 6 cards + change suit
    - First to empty hand wins
    - Must call "Last Card" when at 1 card (penalty: draw 1)
    - Last Card cannot be a special card (A, 2, 8, J, Joker)
    """

    SPECIAL_CARDS = ['A', '2', '8', 'J', 'Joker']  # Cannot be last card

    CARDS_PER_PLAYER = 5
    MAX_PLAYERS = 8

    def __init__(self):
        self.players: List[Player] = []
        self.deck = Deck()
        self.discard_pile: List[Card] = []
        self.phase = GamePhase.WAITING
        self.current_player_index = 0
        self.direction = 1  # 1 = clockwise, -1 = counter-clockwise
        self.pending_draw = 0  # Stacked draw 2s or Joker
        self.current_suit: Optional[str] = None  # Override suit from Ace/Joker
        self.winner: Optional[str] = None
        self.action_log: List[str] = []
        self.round_number = 0
        self.last_played_by: Optional[str] = None
        self.free_throw_active = False  # Jack allows playing another card

    def add_player(self, player: Player) -> bool:
        """Add a player to the game."""
        if len(self.players) >= self.MAX_PLAYERS:
            return False
        if self.phase != GamePhase.WAITING:
            return False
        player.seat_position = len(self.players)
        self.players.append(player)
        return True

    def remove_player(self, player_name: str) -> bool:
        """Remove a player from the game."""
        for i, p in enumerate(self.players):
            if p.name == player_name:
                self.players.pop(i)
                # Reassign seat positions
                for j, player in enumerate(self.players):
                    player.seat_position = j
                return True
        return False

    def start_game(self) -> bool:
        """Start a new game - deal cards and flip first card."""
        if len(self.players) < 2:
            return False

        self.phase = GamePhase.PLAYING
        self.round_number += 1
        self.winner = None
        self.pending_draw = 0
        self.direction = 1
        self.current_suit = None
        self.action_log = []
        self.free_throw_active = False

        # Reset deck and shuffle
        self.deck.reset()
        self.deck.shuffle()
        self.discard_pile = []

        # Clear all hands
        for player in self.players:
            player.clear_hand()
            player.last_card_called = False

        # Deal cards to each player
        for _ in range(self.CARDS_PER_PLAYER):
            for player in self.players:
                card = self.deck.deal_one()
                if card:
                    player.receive_cards([card])

        # Flip first card to discard pile
        first_card = self.deck.deal_one()
        while first_card and (first_card.rank == '8' or first_card.rank == 'Joker'):
            # Don't start with a wild card (8 or Joker), put it back and draw another
            self.deck.cards.insert(0, first_card)
            self.deck.shuffle()
            first_card = self.deck.deal_one()

        if first_card:
            self.discard_pile.append(first_card)
            self.current_suit = first_card.suit

        # Random starting player
        import random
        self.current_player_index = random.randint(0, len(self.players) - 1)

        self._log_action(f"Game started! First card: {first_card}")
        self._log_action(f"{self.get_current_player().name}'s turn")

        return True

    def get_current_player(self) -> Optional[Player]:
        """Get the current player."""
        if not self.players:
            return None
        return self.players[self.current_player_index]

    def get_top_card(self) -> Optional[Card]:
        """Get the top card of the discard pile."""
        if not self.discard_pile:
            return None
        return self.discard_pile[-1]

    def get_active_suit(self) -> Optional[str]:
        """Get the currently active suit (may be overridden by wild 8)."""
        return self.current_suit

    def is_valid_play(self, card: Card) -> bool:
        """Check if a card can be played."""
        # Jokers can always be played (wild)
        if card.rank == 'Joker':
            return True

        # Ace can be played anytime (changes suit)
        if card.rank == 'A':
            return True

        # Jack can be played on any card (free throw)
        if card.rank == 'J':
            return True

        # If there are pending draws from 2s/Joker, only a 2 can be played (stacking)
        if self.pending_draw > 0:
            return card.rank == '2'

        top_card = self.get_top_card()
        if not top_card:
            return True

        active_suit = self.get_active_suit()

        # Match rank or suit
        return card.rank == top_card.rank or card.suit == active_suit

    def get_playable_cards(self, player: Player) -> List[int]:
        """Get indices of cards that can be played from player's hand."""
        playable = []
        for i, card in enumerate(player.hand):
            if self.is_valid_play(card):
                playable.append(i)
        return playable

    def get_matching_cards(self, player: Player, card_index: int) -> List[int]:
        """Get indices of all cards with the same rank as the selected card."""
        if card_index < 0 or card_index >= len(player.hand):
            return []
        selected_card = player.hand[card_index]
        matching = []
        for i, card in enumerate(player.hand):
            if card.rank == selected_card.rank:
                matching.append(i)
        return matching

    def play_cards(self, player_name: str, card_indices: List[int], suit_override: Optional[str] = None) -> Tuple[bool, str]:
        """
        Play multiple cards of the same rank at once.

        Args:
            player_name: Name of the player
            card_indices: List of card indices to play (must be same rank)
            suit_override: Suit choice for Ace/Joker

        Returns:
            Tuple of (success, message)
        """
        if not card_indices:
            return False, "No cards selected"

        # If only one card, use regular play_card method
        if len(card_indices) == 1:
            return self.play_card(player_name, card_indices[0], suit_override)

        player = self._get_player_by_name(player_name)
        if not player:
            return False, "Player not found"

        current = self.get_current_player()
        if not current or current.name != player_name:
            return False, "Not your turn"

        # Validate all indices
        for idx in card_indices:
            if idx < 0 or idx >= len(player.hand):
                return False, "Invalid card index"

        # Get all cards to be played
        cards_to_play = [player.hand[i] for i in card_indices]

        # Check that all cards have the same rank
        first_rank = cards_to_play[0].rank
        for card in cards_to_play:
            if card.rank != first_rank:
                return False, "All cards must be the same rank to play together"

        # Check if the first card is playable
        if not self.is_valid_play(cards_to_play[0]):
            return False, f"Cannot play {cards_to_play[0]}. Must match {self.get_active_suit()} or {self.get_top_card().rank}"

        # Check if trying to use special cards as last cards
        remaining_after = len(player.hand) - len(card_indices)
        if remaining_after == 0 and first_rank in self.SPECIAL_CARDS:
            return False, f"Cannot use {first_rank} as your last card!"

        # Check Last Card call penalty
        # Penalty applies if: will have 1 card left OR finishing (0 cards) from 2-3 cards
        needs_last_card_call = (remaining_after == 1) or (remaining_after == 0 and len(player.hand) in [2, 3])
        if needs_last_card_call and not player.last_card_called:
            self._draw_cards(player, 1)
            self._log_action(f"{player_name} forgot to call Last Card! Drew 1 penalty card.")
            player.last_card_called = False

        # Remove cards from hand (in reverse order to maintain indices)
        sorted_indices = sorted(card_indices, reverse=True)
        for idx in sorted_indices:
            player.hand.pop(idx)

        # Add all cards to discard pile
        for card in cards_to_play:
            self.discard_pile.append(card)

        self.last_played_by = player_name
        card_count = len(cards_to_play)
        self._log_action(f"{player_name} played {card_count}x {first_rank}!")

        # Reset last card called if more than 1 card left
        if len(player.hand) > 1:
            player.last_card_called = False

        # Check for win
        if len(player.hand) == 0:
            self.winner = player_name
            self.phase = GamePhase.GAME_OVER
            self._log_action(f"{player_name} wins!")
            return True, f"{player_name} wins with {card_count}x {first_rank}!"

        # Apply special effects for each card played
        played_jack = first_rank == 'J'
        for i, card in enumerate(cards_to_play):
            # Only use suit_override on the last card
            override = suit_override if i == len(cards_to_play) - 1 else None
            self._apply_special_effects(card, override)

        # Jack = free throw (still applies even with multiple Jacks)
        if played_jack:
            self.free_throw_active = True
            self._log_action(f"{player_name} gets a free throw!")
            return True, f"Played {card_count}x {first_rank} - Free throw!"

        # Move to next player
        self.free_throw_active = False
        self._advance_to_next_player()

        return True, f"Played {card_count}x {first_rank}"

    def play_card(self, player_name: str, card_index: int, suit_override: Optional[str] = None) -> Tuple[bool, str]:
        """
        Play a card from the player's hand.

        Args:
            player_name: Name of the player
            card_index: Index of the card in player's hand
            suit_override: Suit choice for wild 8s

        Returns:
            Tuple of (success, message)
        """
        player = self._get_player_by_name(player_name)
        if not player:
            return False, "Player not found"

        current = self.get_current_player()
        if not current or current.name != player_name:
            return False, "Not your turn"

        if card_index < 0 or card_index >= len(player.hand):
            return False, "Invalid card index"

        card = player.hand[card_index]

        if not self.is_valid_play(card):
            return False, f"Cannot play {card}. Must match {self.get_active_suit()} or {self.get_top_card().rank}"

        # Check if trying to use a special card as last card
        if len(player.hand) == 1 and card.rank in self.SPECIAL_CARDS:
            return False, f"Cannot use {card.rank} as your last card! Special cards (A, 2, 8, J, Joker) cannot be last."

        # Remove card from hand and add to discard pile
        player.hand.pop(card_index)
        self.discard_pile.append(card)
        self.last_played_by = player_name

        # Check if player should have called Last Card (now has 1 card)
        if len(player.hand) == 1 and not player.last_card_called:
            # Penalty: draw 1 card
            self._draw_cards(player, 1)
            self._log_action(f"{player_name} forgot to call Last Card! Drew 1 penalty card.")
            player.last_card_called = False

        # Reset last card called after playing (if more than 1 card left)
        if len(player.hand) > 1:
            player.last_card_called = False

        self._log_action(f"{player_name} played {card}")

        # Check for win
        if len(player.hand) == 0:
            self.winner = player_name
            self.phase = GamePhase.GAME_OVER
            self._log_action(f"{player_name} wins!")
            return True, f"{player_name} wins!"

        # Apply special card effects
        played_jack = card.rank == 'J'
        self._apply_special_effects(card, suit_override)

        # Jack = free throw, don't advance to next player
        if played_jack:
            self.free_throw_active = True
            self._log_action(f"{player_name} gets a free throw!")
            return True, f"Played {card} - Free throw!"

        # Move to next player (unless free throw)
        self.free_throw_active = False
        self._advance_to_next_player()

        return True, f"Played {card}"

    def draw_card(self, player_name: str) -> Tuple[bool, str]:
        """
        Draw a card from the deck.

        Returns:
            Tuple of (success, message)
        """
        player = self._get_player_by_name(player_name)
        if not player:
            return False, "Player not found"

        current = self.get_current_player()
        if not current or current.name != player_name:
            return False, "Not your turn"

        # Determine draw count
        if self.pending_draw > 0:
            draw_count = self.pending_draw
        else:
            draw_count = 1

        cards_drawn = self._draw_cards(player, draw_count)

        if self.pending_draw > 0:
            self._log_action(f"{player_name} drew {cards_drawn} cards (from 2s/Joker)")
            self.pending_draw = 0
        else:
            self._log_action(f"{player_name} drew a card")

        # Reset last card called
        player.last_card_called = False

        # Move to next player
        self._advance_to_next_player()

        return True, f"Drew {cards_drawn} card(s)"

    def call_last_card(self, player_name: str) -> Tuple[bool, str]:
        """
        Call "Last Card!" before playing cards that will leave you with 1 or 0 cards.
        - With 2 cards: Call before playing 1 (leaves 1) or 2 of same rank (wins)
        - With 3 cards: Call before playing 3 of same rank (wins)

        Returns:
            Tuple of (success, message)
        """
        player = self._get_player_by_name(player_name)
        if not player:
            return False, "Player not found"

        # Allow calling with 2 or 3 cards (for multi-card finishing plays)
        if len(player.hand) > 3:
            return False, "Can only call Last Card when you have 2-3 cards"

        if len(player.hand) < 2:
            return False, "Too late to call Last Card"

        if player.last_card_called:
            return False, "Already called Last Card"

        player.last_card_called = True
        self._log_action(f"{player_name} called Last Card!")

        return True, "Last Card called!"

    def _apply_special_effects(self, card: Card, suit_override: Optional[str] = None):
        """Apply special card effects according to official Last Card rules."""

        # Joker - Wild + next player draws 6 + change suit
        if card.rank == 'Joker':
            if suit_override and suit_override in ['hearts', 'diamonds', 'clubs', 'spades']:
                self.current_suit = suit_override
                self._log_action(f"Joker! Suit changed to {suit_override}")
            else:
                self.current_suit = 'hearts'  # Default suit for Joker
            self.pending_draw += 6
            self._log_action(f"Next player must draw {self.pending_draw} cards!")
            return  # Joker effect complete

        # Ace - Change suit (can be played anytime)
        if card.rank == 'A':
            if suit_override and suit_override in ['hearts', 'diamonds', 'clubs', 'spades']:
                self.current_suit = suit_override
                self._log_action(f"Ace! Suit changed to {suit_override}")
            else:
                self.current_suit = card.suit
            return  # Ace effect complete

        # Draw 2 (stackable) - "Terrible Two's"
        if card.rank == '2':
            self.pending_draw += 2
            self._log_action(f"Next player must draw {self.pending_draw} or play a 2")
            self.current_suit = card.suit
            return

        # Seven - Reverse direction (can be countered by another 7)
        if card.rank == '7':
            self.current_suit = card.suit
            self.direction *= -1
            direction_name = "clockwise" if self.direction == 1 else "counter-clockwise"
            self._log_action(f"Direction reversed to {direction_name}!")
            return

        # Eight - Reverse direction (can be countered by another 8)
        if card.rank == '8':
            self.current_suit = card.suit
            self.direction *= -1
            direction_name = "clockwise" if self.direction == 1 else "counter-clockwise"
            self._log_action(f"Direction reversed to {direction_name}!")
            return

        # Jack - Free throw (handled in play_card, but set suit here)
        if card.rank == 'J':
            self.current_suit = card.suit
            return

        # Normal cards - just update suit
        self.current_suit = card.suit

    def _advance_to_next_player(self):
        """Move to the next player in the current direction."""
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
        current = self.get_current_player()
        if current:
            self._log_action(f"{current.name}'s turn")

    def _draw_cards(self, player: Player, count: int) -> int:
        """Draw cards from deck to player's hand. Reshuffles discard if needed."""
        cards_drawn = 0

        for _ in range(count):
            # Reshuffle discard pile if deck is empty
            if len(self.deck.cards) == 0:
                self._reshuffle_discard()

            if len(self.deck.cards) > 0:
                card = self.deck.deal_one()
                if card:
                    player.receive_cards([card])
                    cards_drawn += 1

        return cards_drawn

    def _reshuffle_discard(self):
        """Reshuffle the discard pile back into the deck, keeping the top card."""
        if len(self.discard_pile) <= 1:
            return

        top_card = self.discard_pile.pop()
        self.deck.cards = self.discard_pile.copy()
        self.discard_pile = [top_card]
        self.deck.shuffle()
        self._log_action("Deck reshuffled from discard pile")

    def _get_player_by_name(self, name: str) -> Optional[Player]:
        """Find a player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None

    def _log_action(self, message: str):
        """Add an action to the log."""
        self.action_log.append(message)
        # Keep only last 20 actions
        if len(self.action_log) > 20:
            self.action_log = self.action_log[-20:]

    def get_valid_actions(self, player_name: str) -> List[str]:
        """Get list of valid actions for a player."""
        player = self._get_player_by_name(player_name)
        if not player:
            return []

        current = self.get_current_player()
        if not current or current.name != player_name:
            return []

        actions = []

        # Can always draw
        actions.append('draw_card')

        # Can play if has valid cards
        playable = self.get_playable_cards(player)
        if playable:
            actions.append('play_card')

        # Can call last card if has 2-3 cards and hasn't called yet
        # (allows for multi-card finishing plays)
        if len(player.hand) in [2, 3] and not player.last_card_called:
            actions.append('call_last_card')

        return actions

    def get_game_state(self, for_player: Optional[str] = None) -> Dict:
        """
        Get the current game state.

        Args:
            for_player: If specified, include that player's hand

        Returns:
            Dict with game state
        """
        top_card = self.get_top_card()

        players_data = []
        for player in self.players:
            player_data = {
                'name': player.name,
                'card_count': len(player.hand),
                'is_human': player.is_human,
                'avatar': player.avatar,
                'seat_position': player.seat_position,
                'last_card_called': player.last_card_called
            }

            # Only show hand to the requesting player
            if for_player and player.name == for_player:
                player_data['hand'] = [card.to_dict() for card in player.hand]
            else:
                player_data['hand'] = []

            players_data.append(player_data)

        current_player = self.get_current_player()

        state = {
            'phase': self.phase.value,
            'discard_pile_top': top_card.to_dict() if top_card else None,
            'current_suit': self.current_suit,
            'draw_pile_count': len(self.deck.cards),
            'direction': self.direction,
            'pending_draw': self.pending_draw,
            'free_throw_active': self.free_throw_active,
            'current_player': current_player.name if current_player else None,
            'players': players_data,
            'winner': self.winner,
            'action_log': self.action_log[-10:],
            'round_number': self.round_number
        }

        # Add valid actions and playable cards for requesting player
        if for_player:
            state['valid_actions'] = self.get_valid_actions(for_player)
            player = self._get_player_by_name(for_player)
            if player:
                state['playable_cards'] = self.get_playable_cards(player)
            else:
                state['playable_cards'] = []
        else:
            state['valid_actions'] = []
            state['playable_cards'] = []

        return state

    def new_round(self) -> bool:
        """Start a new round after a game ends."""
        if self.phase != GamePhase.GAME_OVER:
            return False
        return self.start_game()
