import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import time
import random
import string

from game.card import Card
from game.player import Player
from game.ai_player import AIPlayer
from game.game_engine import LastCardGame, GamePhase

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lastcard_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Game rooms storage
games = {}
chat_history = {}

# Track socket sessions to player mappings
socket_to_player = {}
player_to_socket = {}
room_hosts = {}


def generate_room_code():
    """Generate a unique 6-character room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in games:
            return code


def get_or_create_game(room_id: str) -> LastCardGame:
    if room_id not in games:
        games[room_id] = LastCardGame()
        chat_history[room_id] = []
    return games[room_id]


def add_host_info_to_state(state: dict, room_id: str) -> dict:
    """Add host information to game state."""
    host_name = room_hosts.get(room_id)
    for player in state.get('players', []):
        player['is_host'] = player['name'] == host_name
    state['host'] = host_name
    return state


@app.route('/')
def index():
    return render_template('index.html')


# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'Connected to MIC MIND Last Card Server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle player disconnection."""
    socket_id = request.sid

    for room_id in list(socket_to_player.keys()):
        if socket_id in socket_to_player.get(room_id, {}):
            player_name = socket_to_player[room_id][socket_id]

            socketio.emit('player_disconnected', {
                'player_name': player_name,
                'message': f'{player_name} disconnected'
            }, room=room_id)

            if room_id in games and games[room_id].phase == GamePhase.WAITING:
                game = games[room_id]
                game.remove_player(player_name)

                del socket_to_player[room_id][socket_id]
                if player_name in player_to_socket.get(room_id, {}):
                    del player_to_socket[room_id][player_name]

                if room_hosts.get(room_id) == player_name:
                    human_players = [p for p in game.players if p.is_human]
                    if human_players:
                        room_hosts[room_id] = human_players[0].name
                        socketio.emit('host_changed', {
                            'new_host': human_players[0].name
                        }, room=room_id)
                    else:
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
    avatar = data.get('avatar', 'default')
    create_new = data.get('create_new', False)

    socket_id = request.sid

    if create_new:
        room_id = generate_room_code()
    elif room_id:
        if room_id not in games:
            emit('error', {'message': f'Room "{room_id}" not found.'})
            return
    else:
        emit('error', {'message': 'Please enter a room code or create a new room.'})
        return

    join_room(room_id)

    if room_id in games:
        game = games[room_id]
    else:
        game = get_or_create_game(room_id)

    # Check if game already started
    if game.phase != GamePhase.WAITING:
        if room_id in player_to_socket and player_name in player_to_socket[room_id]:
            old_socket = player_to_socket[room_id][player_name]
            if room_id in socket_to_player and old_socket in socket_to_player[room_id]:
                del socket_to_player[room_id][old_socket]
            socket_to_player.setdefault(room_id, {})[socket_id] = player_name
            player_to_socket[room_id][player_name] = socket_id
            emit('reconnected', {'room_id': room_id, 'player_name': player_name})
            state = game.get_game_state(for_player=player_name)
            add_host_info_to_state(state, room_id)
            emit('game_state', state)
            return
        else:
            emit('error', {'message': 'Game already in progress.'})
            return

    # Check if name exists
    existing_names = [p.name for p in game.players]
    if player_name in existing_names:
        if room_id in player_to_socket and player_name in player_to_socket[room_id]:
            old_socket = player_to_socket[room_id][player_name]
            if room_id in socket_to_player and old_socket in socket_to_player[room_id]:
                del socket_to_player[room_id][old_socket]
            socket_to_player.setdefault(room_id, {})[socket_id] = player_name
            player_to_socket[room_id][player_name] = socket_id
            emit('reconnected', {'room_id': room_id, 'player_name': player_name})
            state = game.get_game_state(for_player=player_name)
            add_host_info_to_state(state, room_id)
            emit('game_state', state)
            return
        else:
            emit('error', {'message': f'Name "{player_name}" is already taken'})
            return

    if is_human:
        player = Player(player_name)
        socket_to_player.setdefault(room_id, {})[socket_id] = player_name
        player_to_socket.setdefault(room_id, {})[player_name] = socket_id

        if room_id not in room_hosts:
            room_hosts[room_id] = player_name
    else:
        difficulty = data.get('difficulty', 'medium')
        player = AIPlayer(player_name, difficulty=difficulty)

    player.avatar = avatar

    if game.add_player(player):
        human_count = sum(1 for p in game.players if p.is_human)

        socketio.emit('player_joined', {
            'player_name': player_name,
            'is_human': is_human,
            'player_count': len(game.players),
            'human_count': human_count,
            'avatar': avatar,
            'room_id': room_id,
            'is_host': room_hosts.get(room_id) == player_name
        }, room=room_id)

        emit('chat_history', {'messages': chat_history.get(room_id, [])[-50:]})

        emit('joined_room', {
            'room_id': room_id,
            'player_name': player_name,
            'is_host': room_hosts.get(room_id) == player_name
        })

        broadcast_game_state(room_id, game)
    else:
        emit('error', {'message': 'Game is full (max 8 players)'})


@socketio.on('add_ai_player')
def handle_add_ai(data):
    room_id = data.get('room_id', 'default')
    ai_name = data.get('name', f'Bot_{len(games.get(room_id, LastCardGame()).players) + 1}')
    difficulty = data.get('difficulty', 'medium')

    game = get_or_create_game(room_id)

    ai_avatars = ['robot1', 'robot2', 'robot3', 'alien', 'ninja', 'pirate']
    avatar = ai_avatars[len(game.players) % len(ai_avatars)]

    ai_player = AIPlayer(ai_name, difficulty=difficulty)
    ai_player.avatar = avatar

    if game.add_player(ai_player):
        emit('player_joined', {
            'player_name': ai_name,
            'is_human': False,
            'player_count': len(game.players),
            'avatar': avatar,
            'difficulty': difficulty
        }, room=room_id)

        broadcast_game_state(room_id, game)
    else:
        emit('error', {'message': 'Game is full'})


@socketio.on('start_game')
def handle_start_game(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name', '')
    game = get_or_create_game(room_id)

    host = room_hosts.get(room_id)
    if host and player_name != host:
        emit('error', {'message': f'Only the host ({host}) can start the game'})
        return

    if len(game.players) < 2:
        emit('error', {'message': 'Need at least 2 players to start'})
        return

    if game.start_game():
        emit('game_started', {'message': 'Game started!'}, room=room_id)
        emit('sound_effect', {'sound': 'shuffle'}, room=room_id)
        broadcast_game_state(room_id, game)
        check_and_execute_ai_turn(room_id, game)
    else:
        emit('error', {'message': 'Could not start game'})


@socketio.on('play_card')
def handle_play_card(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    card_index = data.get('card_index')
    suit_override = data.get('suit_override')

    if room_id not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_id]

    current_player = game.get_current_player()
    if not current_player or current_player.name != player_name:
        emit('error', {'message': 'Not your turn'})
        return

    success, message = game.play_card(player_name, card_index, suit_override)

    if success:
        emit('sound_effect', {'sound': 'card'}, room=room_id)
        broadcast_game_state(room_id, game)

        if game.phase == GamePhase.GAME_OVER:
            socketio.emit('game_over', {
                'winner': game.winner,
                'message': f'{game.winner} wins!'
            }, room=room_id)
        else:
            check_and_execute_ai_turn(room_id, game)
    else:
        emit('error', {'message': message})


@socketio.on('draw_card')
def handle_draw_card(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    if room_id not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_id]

    current_player = game.get_current_player()
    if not current_player or current_player.name != player_name:
        emit('error', {'message': 'Not your turn'})
        return

    success, message = game.draw_card(player_name)

    if success:
        emit('sound_effect', {'sound': 'draw'}, room=room_id)
        broadcast_game_state(room_id, game)
        check_and_execute_ai_turn(room_id, game)
    else:
        emit('error', {'message': message})


@socketio.on('call_last_card')
def handle_call_last_card(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    if room_id not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_id]

    success, message = game.call_last_card(player_name)

    if success:
        socketio.emit('last_card_called', {
            'player_name': player_name,
            'message': f'{player_name} called Last Card!'
        }, room=room_id)
        emit('sound_effect', {'sound': 'lastcard'}, room=room_id)
        broadcast_game_state(room_id, game)
    else:
        emit('error', {'message': message})


@socketio.on('new_round')
def handle_new_round(data):
    room_id = data.get('room_id', 'default')

    if room_id not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_id]

    if game.new_round():
        emit('new_round_started', {'message': 'New round started!'}, room=room_id)
        emit('sound_effect', {'sound': 'shuffle'}, room=room_id)
        broadcast_game_state(room_id, game)
        check_and_execute_ai_turn(room_id, game)
    else:
        emit('error', {'message': 'Could not start new round'})


@socketio.on('get_game_state')
def handle_get_state(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')

    if room_id not in games:
        emit('error', {'message': 'Room not found'})
        return

    game = games[room_id]
    state = game.get_game_state(for_player=player_name)
    add_host_info_to_state(state, room_id)
    emit('game_state', state)


@socketio.on('chat_message')
def handle_chat(data):
    room_id = data.get('room_id', 'default')
    player_name = data.get('player_name')
    message = data.get('message', '')[:200]

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


def broadcast_game_state(room_id: str, game: LastCardGame):
    """Broadcast personalized game state to each player."""
    for player in game.players:
        if player.is_human:
            socket_id = player_to_socket.get(room_id, {}).get(player.name)
            if socket_id:
                state = game.get_game_state(for_player=player.name)
                state['your_name'] = player.name
                state['is_host'] = room_hosts.get(room_id) == player.name
                socketio.emit('game_state', state, to=socket_id)


def check_and_execute_ai_turn(room_id: str, game: LastCardGame):
    """Check if it's an AI's turn and execute their action."""
    if game.phase != GamePhase.PLAYING:
        return

    current_player = game.get_current_player()
    if not current_player:
        return

    if not current_player.is_human and isinstance(current_player, AIPlayer):
        socketio.sleep(1.0)

        socketio.emit('ai_thinking', {
            'player_name': current_player.name
        }, room=room_id)

        socketio.sleep(0.8)

        state = game.get_game_state(for_player=current_player.name)
        action, card_index, suit_override = current_player.decide_action(state)

        if action == 'call_last_card':
            game.call_last_card(current_player.name)
            socketio.emit('last_card_called', {
                'player_name': current_player.name,
                'message': f'{current_player.name} called Last Card!'
            }, room=room_id)
            broadcast_game_state(room_id, game)
            socketio.sleep(0.5)
            # After calling last card, AI needs to make another action
            state = game.get_game_state(for_player=current_player.name)
            action, card_index, suit_override = current_player.decide_action(state)

        if action == 'play_card' and card_index is not None:
            success, message = game.play_card(current_player.name, card_index, suit_override)
            if success:
                socketio.emit('ai_action', {
                    'player_name': current_player.name,
                    'action': 'played a card'
                }, room=room_id)
                socketio.emit('sound_effect', {'sound': 'card'}, room=room_id)
        elif action == 'draw_card':
            success, message = game.draw_card(current_player.name)
            if success:
                socketio.emit('ai_action', {
                    'player_name': current_player.name,
                    'action': 'drew a card'
                }, room=room_id)
                socketio.emit('sound_effect', {'sound': 'draw'}, room=room_id)

        broadcast_game_state(room_id, game)

        if game.phase == GamePhase.GAME_OVER:
            socketio.emit('game_over', {
                'winner': game.winner,
                'message': f'{game.winner} wins!'
            }, room=room_id)
        elif game.phase == GamePhase.PLAYING:
            check_and_execute_ai_turn(room_id, game)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    print("\n" + "="*50)
    print("  MIC MIND - LAST CARD SERVER")
    print(f"  Running on port {port}")
    print("="*50 + "\n")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
