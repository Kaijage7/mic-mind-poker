from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import json
import random
import string

from game.card import Card
from game.player import Player
from game.ai_player import AIPlayer
from game.game_engine import PokerGame, GamePhase, GameMode
from game.statistics import StatsManager, ACHIEVEMENTS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'poker_secret_key_2024_premium'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Game rooms storage
games = {}
stats_manager = StatsManager()
chat_history = {}

# Track socket sessions to player mappings
# Format: {room_id: {socket_id: player_name}}
socket_to_player = {}
# Format: {room_id: {player_name: socket_id}}
player_to_socket = {}
# Track room hosts (first human player to create the room)
room_hosts = {}


def generate_room_code():
    """Generate a unique 6-character room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in games:
            return code


def get_or_create_game(room_id: str, mode: str = "cash_game") -> PokerGame:
    if room_id not in games:
        games[room_id] = PokerGame(mode=mode)
        chat_history[room_id] = []
    return games[room_id]


def add_host_info_to_state(state: dict, room_id: str) -> dict:
    """Add host information to game state for lobby display."""
    host_name = room_hosts.get(room_id)
    for player in state.get('players', []):
        player['is_host'] = player['name'] == host_name
    state['host'] = host_name
    return state


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/achievements')
def get_achievements():
    return jsonify(ACHIEVEMENTS)


@app.route('/api/leaderboard')
def get_leaderboard():
    return jsonify(stats_manager.get_leaderboard())


# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'Connected to MIC MIND Server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle player disconnection."""
    socket_id = request.sid

    # Find which room and player this socket belonged to
    for room_id in list(socket_to_player.keys()):
        if socket_id in socket_to_player.get(room_id, {}):
            player_name = socket_to_player[room_id][socket_id]

            # Don't remove the mapping immediately - allow reconnection
            # Just notify other players
            socketio.emit('player_disconnected', {
                'player_name': player_name,
                'message': f'{player_name} disconnected'
            }, room=room_id)

            # If game is in waiting phase, remove the player
            if room_id in games and games[room_id].phase == GamePhase.WAITING:
                game = games[room_id]
                game.remove_player(player_name)

                # Clean up mappings
                del socket_to_player[room_id][socket_id]
                if player_name in player_to_socket.get(room_id, {}):
                    del player_to_socket[room_id][player_name]

                # If host left, assign new host
                if room_hosts.get(room_id) == player_name:
                    human_players = [p for p in game.players if p.is_human]
                    if human_players:
                        room_hosts[room_id] = human_players[0].name
                        socketio.emit('host_changed', {
                            'new_host': human_players[0].name
                        }, room=room_id)
                    else:
                        # No humans left, clean up room
                        del games[room_id]
                        if room_id in room_hosts:
                            del room_hosts[room_id]

                socketio.emit('player_left', {
                    'player_name': player_name,
                    'player_count': len(game.players) if room_id in games else 0
                }, room=room_id)

            break


@socketio.on('join_game')
def handle_join_game(data):
    room_id = data.get('room_id', '').strip().upper()
    player_name = data.get('player_name', 'Player').strip()
    is_human = data.get('is_human', True)
    mode = data.get('mode', 'cash_game')
    avatar = data.get('avatar', 'default')
    create_new = data.get('create_new', False)

    socket_id = request.sid

    # Generate room code if creating new room
    if create_new:
        room_id = generate_room_code()
    elif room_id:
        # Joining existing room - check if it exists
        if room_id not in games:
            emit('error', {'message': f'Room "{room_id}" not found. Check the code or create a new room.'})
            return
    else:
        # No room specified and not creating new - error
        emit('error', {'message': 'Please enter a room code or create a new room.'})
        return

    join_room(room_id)

    # For joining players, use existing game; for new rooms, create with specified mode
    if room_id in games:
        game = games[room_id]
    else:
        game = get_or_create_game(room_id, mode)

    # Check if game already started and player is trying to join
    if game.phase != GamePhase.WAITING:
        # Check if this is a reconnecting player
        if room_id in player_to_socket and player_name in player_to_socket[room_id]:
            # Update socket mapping for reconnecting player
            old_socket = player_to_socket[room_id][player_name]
            if room_id in socket_to_player and old_socket in socket_to_player[room_id]:
                del socket_to_player[room_id][old_socket]
            socket_to_player.setdefault(room_id, {})[socket_id] = player_name
            player_to_socket[room_id][player_name] = socket_id
            emit('reconnected', {'room_id': room_id, 'player_name': player_name})
            emit('game_state', game.get_game_state(for_player=player_name))
            return
        else:
            emit('error', {'message': 'Game already in progress. Wait for the next game.'})
            return

    # Check if player name already exists in this room
    existing_names = [p.name for p in game.players]
    if player_name in existing_names:
        # Check if it's a reconnection
        if room_id in player_to_socket and player_name in player_to_socket[room_id]:
            # Reconnection - update socket mapping
            old_socket = player_to_socket[room_id][player_name]
            if room_id in socket_to_player and old_socket in socket_to_player[room_id]:
                del socket_to_player[room_id][old_socket]
            socket_to_player.setdefault(room_id, {})[socket_id] = player_name
            player_to_socket[room_id][player_name] = socket_id
            emit('reconnected', {'room_id': room_id, 'player_name': player_name})
            emit('game_state', game.get_game_state(for_player=player_name))
            return
        else:
            emit('error', {'message': f'Name "{player_name}" is already taken in this room'})
            return

    if is_human:
        player = Player(player_name)
        # Track socket session for human players
        socket_to_player.setdefault(room_id, {})[socket_id] = player_name
        player_to_socket.setdefault(room_id, {})[player_name] = socket_id

        # First human player becomes the host
        if room_id not in room_hosts:
            room_hosts[room_id] = player_name
    else:
        difficulty = data.get('difficulty', 'medium')
        player = AIPlayer(player_name, difficulty=difficulty)

    player.avatar = avatar

    if game.add_player(player):
        # Get player stats
        player_stats = stats_manager.get_stats(player_name).to_dict()

        # Count human players
        human_count = sum(1 for p in game.players if p.is_human)

        emit('player_joined', {
            'player_name': player_name,
            'is_human': is_human,
            'player_count': len(game.players),
            'human_count': human_count,
            'avatar': avatar,
            'stats': player_stats,
            'room_id': room_id,
            'is_host': room_hosts.get(room_id) == player_name
        }, room=room_id)

        # Send chat history
        emit('chat_history', {'messages': chat_history.get(room_id, [])[-50:]})

        # Send personalized game state to the joining player
        emit('joined_room', {
            'room_id': room_id,
            'player_name': player_name,
            'is_host': room_hosts.get(room_id) == player_name
        })

        # Send game state with host info to the joining player
        state = game.get_game_state(for_player=player_name)
        add_host_info_to_state(state, room_id)
        emit('game_state', state)

        # Also update all other players in the room with the new player list
        for other_player in game.players:
            if other_player.name != player_name and other_player.is_human:
                other_socket = player_to_socket.get(room_id, {}).get(other_player.name)
                if other_socket:
                    other_state = game.get_game_state(for_player=other_player.name)
                    add_host_info_to_state(other_state, room_id)
                    socketio.emit('game_state', other_state, to=other_socket)
    else:
        emit('error', {'message': 'Game is full (max 8 players)'})


@socketio.on('add_ai_player')
def handle_add_ai(data):
    room_id = data.get('room_id', 'default')
    ai_name = data.get('name', f'Bot_{len(games.get(room_id, PokerGame()).players) + 1}')
    difficulty = data.get('difficulty', 'medium')
    personality = data.get('personality', 'balanced')

    game = get_or_create_game(room_id)

    # AI personalities with different avatars
    ai_avatars = ['robot1', 'robot2', 'robot3', 'alien', 'ninja', 'pirate']
    avatar = ai_avatars[len(game.players) % len(ai_avatars)]

    ai_player = AIPlayer(ai_name, difficulty=difficulty)
    ai_player.avatar = avatar
    ai_player.personality = personality

    if game.add_player(ai_player):
        emit('player_joined', {
            'player_name': ai_name,
            'is_human': False,
            'player_count': len(game.players),
            'avatar': avatar,
            'difficulty': difficulty
        }, room=room_id)

        emit('game_state', game.get_game_state(), room=room_id)
    else:
        emit('error', {'message': 'Game is full'})


@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name', '')
    game = get_or_create_game(room_id)

    # Only the host can start the game
    host = room_hosts.get(room_id)
    if host and player_name != host:
        emit('error', {'message': f'Only the host ({host}) can start the game'})
        return

    if len(game.players) < 2:
        emit('error', {'message': 'Need at least 2 players to start'})
        return

    state = game.start_new_hand()

    if 'error' in state:
        emit('error', {'message': state['error']})
    elif 'tournament_winner' in state:
        emit('tournament_complete', {
            'winner': state['tournament_winner'],
            'rankings': game.tournament_rankings
        }, room=room_id)
    else:
        emit('game_started', state, room=room_id)
        broadcast_game_state(room_id, game)
        emit('sound_effect', {'sound': 'shuffle'}, room=room_id)
        check_and_execute_ai_turn(room_id, game)


@socketio.on('player_action')
def handle_player_action(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    action = data.get('action')
    amount = data.get('amount', 0)

    game = get_or_create_game(room_id)

    current_player = game.get_current_player()
    if not current_player or current_player.name != player_name:
        emit('error', {'message': 'Not your turn'})
        return

    result = game.player_action(player_name, action, amount)

    if 'error' in result:
        emit('error', {'message': result['error']})
    else:
        # Play sound effect
        sound_map = {
            'fold': 'fold',
            'check': 'check',
            'call': 'chips',
            'raise': 'chips',
            'all_in': 'allin'
        }
        emit('sound_effect', {'sound': sound_map.get(action, 'click')}, room=room_id)

        broadcast_game_state(room_id, game)
        check_and_execute_ai_turn(room_id, game)


@socketio.on('new_hand')
def handle_new_hand(data):
    room_id = data.get('room_id', 'default')
    game = get_or_create_game(room_id)

    # Record stats for previous hand winners
    for winner in game.last_winners:
        stats_manager.record_win(
            winner['name'],
            winner['amount'],
            winner.get('hand_rank', 0)
        )

    # Record losses for non-winners
    for player in game.players:
        if player.name not in [w['name'] for w in game.last_winners]:
            stats_manager.record_hand_played(player.name)

    # Remove broke players
    broke_players = [p for p in game.players if p.chips <= 0]
    for p in broke_players:
        game.remove_player(p.name)
        emit('player_eliminated', {
            'player_name': p.name,
            'reason': 'out of chips',
            'final_position': len(game.players) + 1
        }, room=room_id)

    if len(game.players) < 2:
        if len(game.players) == 1:
            winner = game.players[0]
            if game.mode == GameMode.TOURNAMENT:
                stats_manager.record_tournament_result(winner.name, True)
            emit('game_over', {
                'winner': winner.name,
                'stats': stats_manager.get_stats(winner.name).to_dict()
            }, room=room_id)
        else:
            emit('error', {'message': 'Not enough players'})
        return

    state = game.start_new_hand()

    if 'tournament_winner' in state:
        stats_manager.record_tournament_result(state['tournament_winner'], True)
        emit('tournament_complete', {
            'winner': state['tournament_winner'],
            'rankings': game.tournament_rankings
        }, room=room_id)
    else:
        emit('new_hand_started', state, room=room_id)
        emit('sound_effect', {'sound': 'shuffle'}, room=room_id)
        broadcast_game_state(room_id, game)
        check_and_execute_ai_turn(room_id, game)


@socketio.on('surrender')
def handle_surrender(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    if room_id not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_id]

    # Find and remove the surrendering player
    player = next((p for p in game.players if p.name == player_name), None)
    if player:
        # Record surrender in stats
        stats_manager.record_hand_played(player_name)

        # Remove player from game
        game.remove_player(player_name)

        # Clean up socket mappings
        socket_id = player_to_socket.get(room_id, {}).get(player_name)
        if socket_id and room_id in socket_to_player:
            if socket_id in socket_to_player[room_id]:
                del socket_to_player[room_id][socket_id]
        if room_id in player_to_socket and player_name in player_to_socket[room_id]:
            del player_to_socket[room_id][player_name]

        # Notify all players
        socketio.emit('player_eliminated', {
            'player_name': player_name,
            'reason': 'surrendered',
            'final_position': len(game.players) + 1
        }, room=room_id)

        # If surrendering player was host, assign new host
        if room_hosts.get(room_id) == player_name:
            human_players = [p for p in game.players if p.is_human]
            if human_players:
                room_hosts[room_id] = human_players[0].name
                socketio.emit('host_changed', {
                    'new_host': human_players[0].name
                }, room=room_id)

        # Check if game should end
        if len(game.players) < 2:
            if len(game.players) == 1:
                winner = game.players[0]
                emit('game_over', {
                    'winner': winner.name,
                    'reason': 'All opponents surrendered'
                }, room=room_id)
            return

        broadcast_game_state(room_id, game)

        # If it was surrendering player's turn, move to next
        if game.phase not in [GamePhase.WAITING, GamePhase.HAND_COMPLETE, GamePhase.SHOWDOWN]:
            check_and_execute_ai_turn(room_id, game)


@socketio.on('accept_challenge')
def handle_accept_challenge(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    # For now, accepting a challenge just acknowledges it
    # This can be expanded for special challenge modes
    emit('challenge_accepted', {
        'player_name': player_name,
        'message': f'{player_name} accepted the challenge!'
    }, room=room_id)


@socketio.on('decline_challenge')
def handle_decline_challenge(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    emit('challenge_declined', {
        'player_name': player_name,
        'message': f'{player_name} declined the challenge'
    }, room=room_id)


@socketio.on('get_game_state')
def handle_get_state(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    game = get_or_create_game(room_id)
    emit('game_state', game.get_game_state(for_player=player_name))


@socketio.on('get_stats')
def handle_get_stats(data):
    player_name = data.get('player_name')
    stats = stats_manager.get_stats(player_name)
    emit('player_stats', stats.to_dict())


@socketio.on('chat_message')
def handle_chat(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    message = data.get('message', '')[:200]  # Limit message length

    if not message.strip():
        return

    chat_msg = {
        'player': player_name,
        'message': message,
        'timestamp': int(time.time() * 1000)
    }

    if room_id not in chat_history:
        chat_history[room_id] = []
    chat_history[room_id].append(chat_msg)

    # Keep only last 100 messages
    chat_history[room_id] = chat_history[room_id][-100:]

    emit('chat_message', chat_msg, room=room_id)


@socketio.on('emoji_reaction')
def handle_emoji(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    emoji = data.get('emoji')

    emit('emoji_reaction', {
        'player': player_name,
        'emoji': emoji
    }, room=room_id)


@socketio.on('request_tip')
def handle_tip_request(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    game = get_or_create_game(room_id)
    state = game.get_game_state(for_player=player_name)

    tip = generate_tip(state)
    emit('game_tip', {'tip': tip})


def generate_tip(state):
    """Generate a strategic tip based on game state."""
    win_prob = state.get('win_probability', {})
    pot_odds = state.get('pot_odds', {})
    phase = state.get('phase', '')

    if not win_prob:
        return "Wait for your cards to get strategic advice."

    win_pct = win_prob.get('win', 50)
    pot_odds_pct = pot_odds.get('pot_odds', 0)
    outs = win_prob.get('outs', {}).get('outs', 0)

    tips = []

    if win_pct >= 80:
        tips.append("You have a monster hand! Consider value betting.")
    elif win_pct >= 65:
        tips.append("Strong hand. Bet for value but watch for raises.")
    elif win_pct >= 50:
        tips.append("Decent hand. Play cautiously and control the pot.")
    elif win_pct >= 35:
        tips.append("Marginal hand. Check if possible, fold to big bets.")
    else:
        tips.append("Weak hand. Consider folding unless you can check.")

    if outs > 0:
        tips.append(f"You have {outs} outs to improve your hand.")

    if pot_odds_pct > 0 and pot_odds_pct < win_pct:
        tips.append("Pot odds favor a call.")
    elif pot_odds_pct > win_pct:
        tips.append("Pot odds don't favor calling.")

    return " ".join(tips)


def broadcast_game_state(room_id: str, game: PokerGame):
    """Broadcast personalized game state to each player."""
    # Send personalized state to each human player (they only see their own cards)
    for player in game.players:
        if player.is_human:
            # Get the socket ID for this player
            socket_id = player_to_socket.get(room_id, {}).get(player.name)
            if socket_id:
                state = game.get_game_state(for_player=player.name)
                state['your_name'] = player.name
                state['is_host'] = room_hosts.get(room_id) == player.name
                socketio.emit('game_state', state, to=socket_id)

    # Check for hand complete and play sounds
    if game.phase == GamePhase.HAND_COMPLETE:
        socketio.emit('sound_effect', {'sound': 'win'}, room=room_id)

    # Check for new achievements
    for winner in game.last_winners:
        achievements = stats_manager._check_achievements(winner['name'], 'win')
        if achievements:
            socketio.emit('achievement_unlocked', {
                'player': winner['name'],
                'achievements': achievements
            }, room=room_id)


def check_and_execute_ai_turn(room_id: str, game: PokerGame):
    """Check if it's an AI's turn and execute their action."""
    if game.phase in [GamePhase.WAITING, GamePhase.SHOWDOWN, GamePhase.HAND_COMPLETE]:
        return

    current_player = game.get_current_player()
    if not current_player:
        return

    if not current_player.is_human and isinstance(current_player, AIPlayer):
        # Add delay for better UX
        socketio.sleep(1.2)

        # Show thinking indicator
        socketio.emit('ai_thinking', {
            'player_name': current_player.name
        }, room=room_id)

        socketio.sleep(0.8)

        # Get game state for AI decision
        state = game.get_game_state(for_player=current_player.name)
        action, amount = current_player.decide_action(state)

        # Execute AI action
        result = game.player_action(current_player.name, action, amount)

        # Play sound
        sound_map = {
            'fold': 'fold',
            'check': 'check',
            'call': 'chips',
            'raise': 'chips',
            'all_in': 'allin'
        }
        socketio.emit('sound_effect', {'sound': sound_map.get(action, 'click')}, room=room_id)

        # Broadcast the action
        socketio.emit('ai_action', {
            'player_name': current_player.name,
            'action': action,
            'amount': amount
        }, room=room_id)

        broadcast_game_state(room_id, game)

        # Check for next AI turn (recursive)
        if game.phase not in [GamePhase.SHOWDOWN, GamePhase.HAND_COMPLETE]:
            check_and_execute_ai_turn(room_id, game)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  MIC MIND - PREMIUM POKER SERVER")
    print("  Open http://localhost:5000 in your browser")
    print("="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
