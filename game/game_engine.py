from typing import List, Dict, Optional, Tuple
from enum import Enum
from .card import Card, Deck
from .player import Player
from .poker_hand import PokerHandEvaluator, HandRank
from .probability import WinProbabilityCalculator


class GamePhase(Enum):
    WAITING = "waiting"
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    HAND_COMPLETE = "hand_complete"


class GameMode(Enum):
    CASH_GAME = "cash_game"
    TOURNAMENT = "tournament"
    SIT_N_GO = "sit_n_go"


class PokerGame:
    def __init__(self, small_blind: int = 10, big_blind: int = 20, mode: str = "cash_game"):
        self.players: List[Player] = []
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0
        self.side_pots: List[Dict] = []
        self.current_bet = 0
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.initial_small_blind = small_blind
        self.initial_big_blind = big_blind
        self.dealer_position = -1
        self.current_player_index = 0
        self.phase = GamePhase.WAITING
        self.min_raise = big_blind
        self.last_raiser_index = -1
        self.action_log: List[str] = []
        self.hand_number = 0
        self.mode = GameMode(mode)

        # Tournament specific
        self.blind_level = 1
        self.hands_until_blind_increase = 10
        self.tournament_finished = False
        self.tournament_rankings: List[Dict] = []

        # Hand history for replay
        self.hand_history: List[Dict] = []
        self.current_hand_actions: List[Dict] = []

        # Winner info for last hand
        self.last_winners: List[Dict] = []
        self.last_hand_rankings: List[Dict] = []

    def add_player(self, player: Player) -> bool:
        if len(self.players) >= 8:  # Increased to 8 players
            return False
        player.seat_position = len(self.players)
        self.players.append(player)
        return True

    def remove_player(self, player_name: str) -> bool:
        for i, p in enumerate(self.players):
            if p.name == player_name:
                if self.mode == GameMode.TOURNAMENT:
                    self.tournament_rankings.insert(0, {
                        'name': p.name,
                        'position': len([pl for pl in self.players if pl.chips > 0]),
                        'eliminated_hand': self.hand_number
                    })
                self.players.pop(i)
                for j, pl in enumerate(self.players):
                    pl.seat_position = j
                return True
        return False

    def start_new_hand(self) -> Dict:
        if len(self.players) < 2:
            return {"error": "Need at least 2 players"}

        active_players = [p for p in self.players if p.chips > 0]
        if len(active_players) < 2:
            if self.mode == GameMode.TOURNAMENT and len(active_players) == 1:
                self.tournament_finished = True
                return {"tournament_winner": active_players[0].name}
            return {"error": "Not enough players with chips"}

        # Tournament blind increase
        if self.mode == GameMode.TOURNAMENT:
            self.hands_until_blind_increase -= 1
            if self.hands_until_blind_increase <= 0:
                self._increase_blinds()

        # Save previous hand
        if self.current_hand_actions:
            self.hand_history.append({
                'hand_number': self.hand_number,
                'actions': self.current_hand_actions.copy(),
                'winners': self.last_winners.copy()
            })

        # Reset game state
        self.hand_number += 1
        self.deck.reset()
        self.community_cards = []
        self.pot = 0
        self.side_pots = []
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.action_log = []
        self.current_hand_actions = []
        self.last_winners = []
        self.last_hand_rankings = []

        # Reset players
        for player in self.players:
            player.clear_hand()

        # Move dealer button
        self.dealer_position = self._get_next_active_position(self.dealer_position)

        # Deal hole cards
        for _ in range(2):
            for player in self.players:
                if player.chips > 0:
                    player.receive_cards(self.deck.deal(1))

        # Post blinds
        self._post_blinds()

        # Set phase and current player
        self.phase = GamePhase.PRE_FLOP
        self.current_player_index = self._get_utg_position()
        self.last_raiser_index = self._get_big_blind_position()

        self._log_action("hand_start", None, {"hand_number": self.hand_number})

        return self.get_game_state()

    def _increase_blinds(self):
        self.blind_level += 1
        self.small_blind = self.initial_small_blind * self.blind_level
        self.big_blind = self.initial_big_blind * self.blind_level
        self.min_raise = self.big_blind
        self.hands_until_blind_increase = 10
        self.action_log.append(f"*** BLINDS INCREASED: {self.small_blind}/{self.big_blind} ***")

    def _get_next_active_position(self, current: int) -> int:
        for i in range(len(self.players)):
            pos = (current + 1 + i) % len(self.players)
            if self.players[pos].chips > 0:
                return pos
        return 0

    def _post_blinds(self) -> None:
        sb_pos = self._get_small_blind_position()
        bb_pos = self._get_big_blind_position()

        sb_player = self.players[sb_pos]
        bb_player = self.players[bb_pos]

        sb_amount = sb_player.bet(min(self.small_blind, sb_player.chips))
        bb_amount = bb_player.bet(min(self.big_blind, bb_player.chips))

        self.pot = sb_amount + bb_amount
        self.current_bet = self.big_blind

        self.action_log.append(f"{sb_player.name} posts small blind ${sb_amount}")
        self.action_log.append(f"{bb_player.name} posts big blind ${bb_amount}")

    def _get_small_blind_position(self) -> int:
        if len([p for p in self.players if p.chips > 0]) == 2:
            return self.dealer_position
        return self._get_next_active_position(self.dealer_position)

    def _get_big_blind_position(self) -> int:
        sb_pos = self._get_small_blind_position()
        if len([p for p in self.players if p.chips > 0]) == 2:
            return self._get_next_active_position(self.dealer_position)
        return self._get_next_active_position(sb_pos)

    def _get_utg_position(self) -> int:
        bb_pos = self._get_big_blind_position()
        return self._get_next_active_position(bb_pos)

    def _get_first_to_act_postflop(self) -> int:
        for i in range(len(self.players)):
            idx = (self.dealer_position + 1 + i) % len(self.players)
            if self.players[idx].can_act:
                return idx
        return self.dealer_position

    def get_current_player(self) -> Optional[Player]:
        if self.phase in [GamePhase.WAITING, GamePhase.SHOWDOWN, GamePhase.HAND_COMPLETE]:
            return None
        if not self.players:
            return None
        return self.players[self.current_player_index]

    def _log_action(self, action: str, player: Optional[Player], data: Dict = None):
        self.current_hand_actions.append({
            'action': action,
            'player': player.name if player else None,
            'data': data or {},
            'pot': self.pot,
            'phase': self.phase.value
        })

    def player_action(self, player_name: str, action: str, amount: int = 0) -> Dict:
        player = self.get_current_player()
        if not player or player.name != player_name:
            return {"error": "Not your turn"}

        result = None
        if action == "fold":
            result = self._handle_fold(player)
        elif action == "check":
            result = self._handle_check(player)
        elif action == "call":
            result = self._handle_call(player)
        elif action == "raise":
            result = self._handle_raise(player, amount)
        elif action == "all_in":
            result = self._handle_all_in(player)
        else:
            return {"error": "Invalid action"}

        self._log_action(action, player, {'amount': amount})
        return result

    def _handle_fold(self, player: Player) -> Dict:
        player.fold()
        self.action_log.append(f"{player.name} folds")

        active_players = [p for p in self.players if not p.is_folded]
        if len(active_players) == 1:
            return self._end_hand_single_winner(active_players[0])

        self._advance_to_next_player()
        return self.get_game_state()

    def _handle_check(self, player: Player) -> Dict:
        if player.current_bet < self.current_bet:
            return {"error": "Cannot check, must call or raise"}

        self.action_log.append(f"{player.name} checks")
        self._advance_to_next_player()
        return self.get_game_state()

    def _handle_call(self, player: Player) -> Dict:
        call_amount = self.current_bet - player.current_bet
        if call_amount <= 0:
            return {"error": "Nothing to call"}

        actual_bet = player.bet(call_amount)
        self.pot += actual_bet

        if actual_bet < call_amount:
            self.action_log.append(f"{player.name} calls ${actual_bet} (all-in)")
        else:
            self.action_log.append(f"{player.name} calls ${actual_bet}")

        self._advance_to_next_player()
        return self.get_game_state()

    def _handle_raise(self, player: Player, amount: int) -> Dict:
        raise_amount = amount - self.current_bet
        if raise_amount < self.min_raise and amount < player.chips + player.current_bet:
            return {"error": f"Minimum raise is ${self.min_raise}"}

        bet_needed = amount - player.current_bet
        actual_bet = player.bet(bet_needed)
        self.pot += actual_bet

        if player.is_all_in:
            self.action_log.append(f"{player.name} raises to ${player.current_bet} (all-in)")
        else:
            self.action_log.append(f"{player.name} raises to ${amount}")

        self.min_raise = raise_amount
        self.current_bet = player.current_bet
        self.last_raiser_index = self.current_player_index

        self._advance_to_next_player()
        return self.get_game_state()

    def _handle_all_in(self, player: Player) -> Dict:
        amount = player.chips
        actual_bet = player.bet(amount)
        self.pot += actual_bet

        self.action_log.append(f"{player.name} goes all-in for ${actual_bet}")

        if player.current_bet > self.current_bet:
            self.current_bet = player.current_bet
            self.last_raiser_index = self.current_player_index

        self._advance_to_next_player()
        return self.get_game_state()

    def _advance_to_next_player(self) -> None:
        start_index = self.current_player_index
        for i in range(len(self.players)):
            next_index = (start_index + 1 + i) % len(self.players)
            player = self.players[next_index]

            if player.can_act:
                if next_index == self.last_raiser_index:
                    self._end_betting_round()
                    return
                if self._is_betting_round_complete():
                    self._end_betting_round()
                    return

                self.current_player_index = next_index
                return

        self._end_betting_round()

    def _is_betting_round_complete(self) -> bool:
        active_players = [p for p in self.players if p.can_act]
        if not active_players:
            return True

        bets = [p.current_bet for p in self.players if not p.is_folded]
        return len(set(bets)) == 1

    def _end_betting_round(self) -> None:
        for player in self.players:
            player.reset_current_bet()
        self.current_bet = 0
        self.min_raise = self.big_blind

        active_players = [p for p in self.players if not p.is_folded]
        if len(active_players) == 1:
            self._end_hand_single_winner(active_players[0])
            return

        players_who_can_act = [p for p in self.players if p.can_act]
        if len(players_who_can_act) <= 1:
            self._run_out_board()
            return

        if self.phase == GamePhase.PRE_FLOP:
            self._deal_flop()
        elif self.phase == GamePhase.FLOP:
            self._deal_turn()
        elif self.phase == GamePhase.TURN:
            self._deal_river()
        elif self.phase == GamePhase.RIVER:
            self._showdown()

    def _deal_flop(self) -> None:
        self.deck.deal(1)
        self.community_cards.extend(self.deck.deal(3))
        self.phase = GamePhase.FLOP
        self.current_player_index = self._get_first_to_act_postflop()
        self.last_raiser_index = self.current_player_index
        self.action_log.append("*** FLOP ***")

    def _deal_turn(self) -> None:
        self.deck.deal(1)
        self.community_cards.extend(self.deck.deal(1))
        self.phase = GamePhase.TURN
        self.current_player_index = self._get_first_to_act_postflop()
        self.last_raiser_index = self.current_player_index
        self.action_log.append("*** TURN ***")

    def _deal_river(self) -> None:
        self.deck.deal(1)
        self.community_cards.extend(self.deck.deal(1))
        self.phase = GamePhase.RIVER
        self.current_player_index = self._get_first_to_act_postflop()
        self.last_raiser_index = self.current_player_index
        self.action_log.append("*** RIVER ***")

    def _run_out_board(self) -> None:
        while len(self.community_cards) < 5:
            self.deck.deal(1)
            self.community_cards.extend(self.deck.deal(1))
        self._showdown()

    def _showdown(self) -> None:
        self.phase = GamePhase.SHOWDOWN

        active_players = [p for p in self.players if not p.is_folded]
        if len(active_players) == 1:
            self._end_hand_single_winner(active_players[0])
            return

        player_hands = []
        hand_details = {}
        for player in active_players:
            all_cards = player.hand + self.community_cards
            best_hand, rank, tiebreakers, hand_name = PokerHandEvaluator.best_hand(all_cards)
            player_hands.append((player.name, all_cards))
            hand_details[player.name] = {
                'rank': rank,
                'hand_name': hand_name,
                'best_cards': [c.to_dict() for c in best_hand]
            }

        rankings = PokerHandEvaluator.compare_players(player_hands)
        self.action_log.append("*** SHOWDOWN ***")
        self.last_hand_rankings = []

        winners = [name for name, rank, hand_name in rankings if rank == 1]

        for name, rank, hand_name in rankings:
            player = next(p for p in self.players if p.name == name)
            cards_str = " ".join(str(c) for c in player.hand)
            self.action_log.append(f"{name} shows [{cards_str}] - {hand_name}")
            self.last_hand_rankings.append({
                'name': name,
                'rank': rank,
                'hand_name': hand_name,
                'hand_details': hand_details.get(name, {})
            })

        pot_per_winner = self.pot // len(winners)
        remainder = self.pot % len(winners)

        for winner_name in winners:
            winner = next(p for p in self.players if p.name == winner_name)
            amount = pot_per_winner + (remainder if winners.index(winner_name) == 0 else 0)
            winner.win_pot(amount)
            self.action_log.append(f"{winner_name} wins ${amount}")

            winner_detail = hand_details.get(winner_name, {})
            self.last_winners.append({
                'name': winner_name,
                'amount': amount,
                'hand_name': winner_detail.get('hand_name', ''),
                'hand_rank': winner_detail.get('rank', 0)
            })

        self.pot = 0
        self.phase = GamePhase.HAND_COMPLETE

    def _end_hand_single_winner(self, winner: Player) -> Dict:
        winner.win_pot(self.pot)
        self.action_log.append(f"{winner.name} wins ${self.pot}")
        self.last_winners = [{
            'name': winner.name,
            'amount': self.pot,
            'hand_name': 'Uncalled',
            'hand_rank': 0
        }]
        self.pot = 0
        self.phase = GamePhase.HAND_COMPLETE
        return self.get_game_state()

    def get_valid_actions(self, player_name: str) -> List[Dict]:
        player = self.get_current_player()
        if not player or player.name != player_name:
            return []

        actions = []
        actions.append({"action": "fold"})

        call_amount = self.current_bet - player.current_bet
        if call_amount == 0:
            actions.append({"action": "check"})
        else:
            actions.append({"action": "call", "amount": call_amount})

        if player.chips > call_amount:
            min_raise_to = self.current_bet + self.min_raise
            max_raise_to = player.chips + player.current_bet
            actions.append({
                "action": "raise",
                "min": min_raise_to,
                "max": max_raise_to
            })

        if player.chips > 0:
            actions.append({"action": "all_in", "amount": player.chips})

        return actions

    def get_win_probability(self, player_name: str) -> Dict:
        player = next((p for p in self.players if p.name == player_name), None)
        if not player or not player.hand:
            return {}

        num_opponents = len([p for p in self.players if not p.is_folded and p.name != player_name])
        if num_opponents == 0:
            return {'win': 100, 'tie': 0, 'lose': 0}

        prob = WinProbabilityCalculator.calculate_win_probability(
            player.hand,
            self.community_cards,
            num_opponents,
            simulations=500
        )

        outs = WinProbabilityCalculator.get_outs(player.hand, self.community_cards)
        label, color = WinProbabilityCalculator.get_hand_strength_label(prob['win'])

        return {
            **prob,
            'outs': outs,
            'strength_label': label,
            'strength_color': color
        }

    def get_pot_odds(self, player_name: str) -> Dict:
        player = next((p for p in self.players if p.name == player_name), None)
        if not player:
            return {}

        call_amount = self.current_bet - player.current_bet
        if call_amount <= 0:
            return {'pot_odds': 0, 'call_amount': 0, 'pot': self.pot}

        pot_odds = round((call_amount / (self.pot + call_amount)) * 100, 1)
        return {
            'pot_odds': pot_odds,
            'call_amount': call_amount,
            'pot': self.pot,
            'ratio': f"{self.pot}:{call_amount}"
        }

    def get_game_state(self, for_player: str = None) -> Dict:
        current_player = self.get_current_player()

        state = {
            "phase": self.phase.value,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "community_cards": [card.to_dict() for card in self.community_cards],
            "dealer_position": self.dealer_position,
            "current_player": current_player.name if current_player else None,
            "players": [],
            "action_log": self.action_log[-15:],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "hand_number": self.hand_number,
            "mode": self.mode.value,
            "blind_level": self.blind_level if self.mode == GameMode.TOURNAMENT else None,
            "hands_until_blind_increase": self.hands_until_blind_increase if self.mode == GameMode.TOURNAMENT else None,
            "last_winners": self.last_winners,
            "last_hand_rankings": self.last_hand_rankings,
            "tournament_finished": self.tournament_finished if self.mode == GameMode.TOURNAMENT else False,
            "tournament_rankings": self.tournament_rankings if self.mode == GameMode.TOURNAMENT else []
        }

        for player in self.players:
            hide_cards = for_player is not None and player.name != for_player
            if self.phase == GamePhase.SHOWDOWN and not player.is_folded:
                hide_cards = False
            state["players"].append(player.to_dict(hide_cards=hide_cards))

        if for_player:
            if current_player and current_player.name == for_player:
                state["valid_actions"] = self.get_valid_actions(for_player)

            if self.phase not in [GamePhase.WAITING, GamePhase.HAND_COMPLETE]:
                state["win_probability"] = self.get_win_probability(for_player)
                state["pot_odds"] = self.get_pot_odds(for_player)

        return state

    def get_hand_replay(self, hand_number: int) -> Optional[Dict]:
        for hand in self.hand_history:
            if hand['hand_number'] == hand_number:
                return hand
        return None
