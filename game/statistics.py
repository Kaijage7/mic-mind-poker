from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class PlayerStats:
    hands_played: int = 0
    hands_won: int = 0
    total_winnings: int = 0
    total_losses: int = 0
    biggest_pot_won: int = 0
    royal_flushes: int = 0
    straight_flushes: int = 0
    four_of_a_kind: int = 0
    full_houses: int = 0
    flushes: int = 0
    straights: int = 0
    three_of_a_kind: int = 0
    two_pairs: int = 0
    pairs: int = 0
    high_cards: int = 0
    bluffs_won: int = 0
    all_ins_won: int = 0
    all_ins_lost: int = 0
    tournaments_won: int = 0
    tournaments_played: int = 0
    current_streak: int = 0
    best_streak: int = 0
    achievements: List[str] = field(default_factory=list)

    def win_rate(self) -> float:
        if self.hands_played == 0:
            return 0
        return (self.hands_won / self.hands_played) * 100

    def net_profit(self) -> int:
        return self.total_winnings - self.total_losses

    def to_dict(self) -> Dict:
        return {
            'hands_played': self.hands_played,
            'hands_won': self.hands_won,
            'win_rate': round(self.win_rate(), 1),
            'total_winnings': self.total_winnings,
            'total_losses': self.total_losses,
            'net_profit': self.net_profit(),
            'biggest_pot_won': self.biggest_pot_won,
            'hand_types': {
                'royal_flush': self.royal_flushes,
                'straight_flush': self.straight_flushes,
                'four_of_a_kind': self.four_of_a_kind,
                'full_house': self.full_houses,
                'flush': self.flushes,
                'straight': self.straights,
                'three_of_a_kind': self.three_of_a_kind,
                'two_pair': self.two_pairs,
                'pair': self.pairs,
                'high_card': self.high_cards
            },
            'bluffs_won': self.bluffs_won,
            'all_ins': {'won': self.all_ins_won, 'lost': self.all_ins_lost},
            'tournaments': {'won': self.tournaments_won, 'played': self.tournaments_played},
            'streaks': {'current': self.current_streak, 'best': self.best_streak},
            'achievements': self.achievements
        }


ACHIEVEMENTS = {
    'first_win': {'name': 'First Blood', 'desc': 'Win your first hand', 'icon': '🏆'},
    'win_streak_5': {'name': 'Hot Streak', 'desc': 'Win 5 hands in a row', 'icon': '🔥'},
    'win_streak_10': {'name': 'Unstoppable', 'desc': 'Win 10 hands in a row', 'icon': '⚡'},
    'royal_flush': {'name': 'Royal Treatment', 'desc': 'Get a Royal Flush', 'icon': '👑'},
    'straight_flush': {'name': 'Flush Royalty', 'desc': 'Get a Straight Flush', 'icon': '💎'},
    'four_of_a_kind': {'name': 'Quad Squad', 'desc': 'Get Four of a Kind', 'icon': '4️⃣'},
    'big_bluff': {'name': 'Master Bluffer', 'desc': 'Win with a bluff (high card)', 'icon': '🎭'},
    'comeback': {'name': 'Comeback King', 'desc': 'Win after being down to 10% chips', 'icon': '🦅'},
    'dominator': {'name': 'Table Dominator', 'desc': 'Win 10 hands total', 'icon': '💪'},
    'high_roller': {'name': 'High Roller', 'desc': 'Win a pot over 1000 chips', 'icon': '💰'},
    'all_in_master': {'name': 'All-In Master', 'desc': 'Win 5 all-in showdowns', 'icon': '🎰'},
    'tournament_champ': {'name': 'Tournament Champion', 'desc': 'Win a tournament', 'icon': '🏅'},
    'hundred_hands': {'name': 'Veteran', 'desc': 'Play 100 hands', 'icon': '🎖️'},
    'millionaire': {'name': 'Millionaire', 'desc': 'Accumulate 10,000 in winnings', 'icon': '💵'},
}


class StatsManager:
    def __init__(self):
        self.player_stats: Dict[str, PlayerStats] = {}

    def get_stats(self, player_name: str) -> PlayerStats:
        if player_name not in self.player_stats:
            self.player_stats[player_name] = PlayerStats()
        return self.player_stats[player_name]

    def record_hand_played(self, player_name: str):
        stats = self.get_stats(player_name)
        stats.hands_played += 1
        self._check_achievements(player_name, 'hands_played')

    def record_win(self, player_name: str, amount: int, hand_rank: int, was_all_in: bool = False):
        stats = self.get_stats(player_name)
        stats.hands_won += 1
        stats.total_winnings += amount
        stats.current_streak += 1

        if amount > stats.biggest_pot_won:
            stats.biggest_pot_won = amount

        if stats.current_streak > stats.best_streak:
            stats.best_streak = stats.current_streak

        if was_all_in:
            stats.all_ins_won += 1

        # Record hand type
        self._record_hand_type(stats, hand_rank)

        # Check achievements
        self._check_achievements(player_name, 'win')

    def record_loss(self, player_name: str, amount: int, was_all_in: bool = False):
        stats = self.get_stats(player_name)
        stats.total_losses += amount
        stats.current_streak = 0

        if was_all_in:
            stats.all_ins_lost += 1

    def record_bluff_win(self, player_name: str):
        stats = self.get_stats(player_name)
        stats.bluffs_won += 1
        self._check_achievements(player_name, 'bluff')

    def record_tournament_result(self, player_name: str, won: bool):
        stats = self.get_stats(player_name)
        stats.tournaments_played += 1
        if won:
            stats.tournaments_won += 1
            self._check_achievements(player_name, 'tournament_win')

    def _record_hand_type(self, stats: PlayerStats, rank: int):
        rank_map = {
            10: 'royal_flushes',
            9: 'straight_flushes',
            8: 'four_of_a_kind',
            7: 'full_houses',
            6: 'flushes',
            5: 'straights',
            4: 'three_of_a_kind',
            3: 'two_pairs',
            2: 'pairs',
            1: 'high_cards'
        }
        attr = rank_map.get(rank)
        if attr:
            setattr(stats, attr, getattr(stats, attr) + 1)

    def _check_achievements(self, player_name: str, trigger: str) -> List[str]:
        stats = self.get_stats(player_name)
        new_achievements = []

        checks = {
            'first_win': stats.hands_won >= 1,
            'win_streak_5': stats.current_streak >= 5,
            'win_streak_10': stats.current_streak >= 10,
            'royal_flush': stats.royal_flushes >= 1,
            'straight_flush': stats.straight_flushes >= 1,
            'four_of_a_kind': stats.four_of_a_kind >= 1,
            'big_bluff': stats.bluffs_won >= 1,
            'dominator': stats.hands_won >= 10,
            'high_roller': stats.biggest_pot_won >= 1000,
            'all_in_master': stats.all_ins_won >= 5,
            'tournament_champ': stats.tournaments_won >= 1,
            'hundred_hands': stats.hands_played >= 100,
            'millionaire': stats.total_winnings >= 10000,
        }

        for achievement_id, condition in checks.items():
            if condition and achievement_id not in stats.achievements:
                stats.achievements.append(achievement_id)
                new_achievements.append(ACHIEVEMENTS[achievement_id])

        return new_achievements

    def get_leaderboard(self) -> List[Dict]:
        leaderboard = []
        for name, stats in self.player_stats.items():
            leaderboard.append({
                'name': name,
                'wins': stats.hands_won,
                'win_rate': stats.win_rate(),
                'net_profit': stats.net_profit(),
                'best_streak': stats.best_streak
            })
        leaderboard.sort(key=lambda x: (-x['wins'], -x['net_profit']))
        return leaderboard[:10]
