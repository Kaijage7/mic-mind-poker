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
    Last Card / Crazy Eights game implementation.

    Rules:
    - Each player gets 5 cards
    - Match rank OR suit to play a card
    - Special cards:
      - 8 (wild): Can be played anytime, player chooses next suit
      - 2: Next player draws 2 cards and skips turn (stackable)
      - 7: Next player must play a 7 or draw 1 card
      - Ace: Reverses play direction
      - Jack: Skips next player
      - Joker: Wild + next player draws 5 cards
    - First to empty hand wins
    - Must call "Last Card" when at 1 card (penalty: draw 1)
    """

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
        self.pending_seven = False  # Must play 7 or draw 1
        self.current_suit: Optional[str] = None  # Override suit from wild 8/Joker
        self.winner: Optional[str] = None
        self.action_log: List[str] = []
        self.round_number = 0
        self.last_played_by: Optional[str] = None

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
        self.pending_seven = False
        self.direction = 1
        self.current_suit = None
        self.action_log = []

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
        # Jokers and 8s (wilds) can always be played
        if card.rank == 'Joker' or card.rank == '8':
            return True

        # If there are pending draws from 2s, only a 2 can be played (stacking)
        if self.pending_draw > 0:
            return card.rank == '2'

        # If there's a pending 7, only a 7 can be played
        if self.pending_seven:
            return card.rank == '7'

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
        self._apply_special_effects(card, suit_override)

        # Move to next player
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
        elif self.pending_seven:
            draw_count = 1  # Seven only makes you draw 1
        else:
            draw_count = 1

        cards_drawn = self._draw_cards(player, draw_count)

        if self.pending_draw > 0:
            self._log_action(f"{player_name} drew {cards_drawn} cards (from 2s/Joker)")
            self.pending_draw = 0
        elif self.pending_seven:
            self._log_action(f"{player_name} drew 1 card (from 7)")
            self.pending_seven = False
        else:
            self._log_action(f"{player_name} drew a card")

        # Reset last card called
        player.last_card_called = False

        # Move to next player
        self._advance_to_next_player()

        return True, f"Drew {cards_drawn} card(s)"

    def call_last_card(self, player_name: str) -> Tuple[bool, str]:
        """
        Call "Last Card!" when player has 2 cards (before playing to get to 1).
        Must be called BEFORE playing the card that leaves you with 1 card.

        Returns:
            Tuple of (success, message)
        """
        player = self._get_player_by_name(player_name)
        if not player:
            return False, "Player not found"

        if len(player.hand) > 2:
            return False, "Can only call Last Card when you have 2 cards"

        if len(player.hand) < 2:
            return False, "Too late to call Last Card"

        if player.last_card_called:
            return False, "Already called Last Card"

        player.last_card_called = True
        self._log_action(f"{player_name} called Last Card!")

        return True, "Last Card called!"

    def _apply_special_effects(self, card: Card, suit_override: Optional[str] = None):
        """Apply special card effects."""

        # Clear pending seven when any card is played
        self.pending_seven = False

        # Joker - Wild + next player draws 5
        if card.rank == 'Joker':
            if suit_override and suit_override in ['hearts', 'diamonds', 'clubs', 'spades']:
                self.current_suit = suit_override
                self._log_action(f"Joker! Suit changed to {suit_override}")
            else:
                self.current_suit = 'hearts'  # Default suit for Joker
            self.pending_draw += 5
            self._log_action(f"Next player must draw {self.pending_draw} cards!")
            return  # Joker doesn't stack with other effects

        # Wild 8 - player chooses next suit
        if card.rank == '8':
            if suit_override and suit_override in ['hearts', 'diamonds', 'clubs', 'spades']:
                self.current_suit = suit_override
                self._log_action(f"Suit changed to {suit_override}")
            else:
                self.current_suit = card.suit
        else:
            self.current_suit = card.suit

        # Draw 2 (stackable)
        if card.rank == '2':
            self.pending_draw += 2
            self._log_action(f"Next player must draw {self.pending_draw} or play a 2")

        # Seven - next player must play 7 or draw 1
        if card.rank == '7':
            self.pending_seven = True
            self._log_action(f"Next player must play a 7 or draw 1 card")

        # Reverse (Ace)
        if card.rank == 'A':
            self.direction *= -1
            direction_name = "clockwise" if self.direction == 1 else "counter-clockwise"
            self._log_action(f"Direction reversed to {direction_name}")

        # Skip (Jack)
        if card.rank == 'J':
            self._advance_to_next_player()
            skipped = self.get_current_player()
            if skipped:
                self._log_action(f"{skipped.name} was skipped!")

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

        # Can call last card if has 2 cards and hasn't called yet
        if len(player.hand) == 2 and not player.last_card_called:
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
            'pending_seven': self.pending_seven,
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
