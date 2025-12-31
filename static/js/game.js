// Premium Texas Hold'em Poker - JavaScript

const SUIT_SYMBOLS = {
    'hearts': '\u2665',
    'diamonds': '\u2666',
    'clubs': '\u2663',
    'spades': '\u2660'
};

const AVATAR_ICONS = {
    'player1': '\u{1F464}',
    'player2': '\u{1F60E}',
    'player3': '\u{1F920}',
    'player4': '\u{1F680}',
    'player5': '\u{2B50}',
    'player6': '\u{1F48E}',
    'robot1': '\u{1F916}',
    'robot2': '\u{1F47E}',
    'robot3': '\u{1F47D}',
    'alien': '\u{1F47D}',
    'ninja': '\u{1F977}',
    'pirate': '\u{1F3F4}',
    'default': '\u{1F464}'
};

// Game State
const GameState = {
    socket: null,
    roomId: null,
    playerName: null,
    selectedAvatar: 'player1',
    selectedMode: 'cash_game',
    currentState: null,
    aiCount: 0,
    soundEnabled: true,
    myStats: null,
    isHost: false,
    players: []
};

// Sound effects
const SoundManager = {
    context: null,

    init() {
        try {
            this.context = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.log('Web Audio not supported');
        }
    },

    play(type) {
        if (!GameState.soundEnabled || !this.context) return;

        const oscillator = this.context.createOscillator();
        const gainNode = this.context.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.context.destination);

        const sounds = {
            'shuffle': { freq: 200, duration: 0.3, type: 'sawtooth' },
            'chips': { freq: 800, duration: 0.1, type: 'sine' },
            'fold': { freq: 150, duration: 0.2, type: 'sine' },
            'check': { freq: 600, duration: 0.1, type: 'sine' },
            'allin': { freq: 1000, duration: 0.3, type: 'square' },
            'win': { freq: 523.25, duration: 0.5, type: 'sine' },
            'click': { freq: 400, duration: 0.05, type: 'sine' }
        };

        const sound = sounds[type] || sounds['click'];
        oscillator.type = sound.type;
        oscillator.frequency.value = sound.freq;
        gainNode.gain.setValueAtTime(0.1, this.context.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.context.currentTime + sound.duration);

        oscillator.start(this.context.currentTime);
        oscillator.stop(this.context.currentTime + sound.duration);
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    SoundManager.init();
    initSocket();
    initEventListeners();
    checkShareLink();
});

// Check if user came from a share link
function checkShareLink() {
    const urlParams = new URLSearchParams(window.location.search);
    const roomCode = urlParams.get('room');
    if (roomCode) {
        document.getElementById('room-id').value = roomCode.toUpperCase();
        showNotification('Room code loaded from link! Enter your name and click Join.', 'info');
    }
}

function initSocket() {
    GameState.socket = io();

    GameState.socket.on('connect', () => {
        console.log('Connected to server');
        showNotification('Connected to server', 'success');
    });
    GameState.socket.on('disconnect', () => {
        console.log('Disconnected from server');
        showNotification('Disconnected from server', 'error');
    });
    GameState.socket.on('connected', (data) => console.log(data.status));

    GameState.socket.on('player_joined', handlePlayerJoined);
    GameState.socket.on('joined_room', handleJoinedRoom);
    GameState.socket.on('game_state', handleGameState);
    GameState.socket.on('game_started', handleGameStarted);
    GameState.socket.on('new_hand_started', handleNewHand);
    GameState.socket.on('ai_action', handleAIAction);
    GameState.socket.on('ai_thinking', handleAIThinking);
    GameState.socket.on('player_removed', handlePlayerRemoved);
    GameState.socket.on('player_eliminated', handlePlayerEliminated);
    GameState.socket.on('player_disconnected', handlePlayerDisconnected);
    GameState.socket.on('player_left', handlePlayerLeft);
    GameState.socket.on('host_changed', handleHostChanged);
    GameState.socket.on('reconnected', handleReconnected);
    GameState.socket.on('game_over', handleGameOver);
    GameState.socket.on('tournament_complete', handleTournamentComplete);
    GameState.socket.on('error', handleError);
    GameState.socket.on('sound_effect', (data) => SoundManager.play(data.sound));
    GameState.socket.on('chat_message', handleChatMessage);
    GameState.socket.on('chat_history', handleChatHistory);
    GameState.socket.on('emoji_reaction', handleEmojiReaction);
    GameState.socket.on('achievement_unlocked', handleAchievement);
    GameState.socket.on('player_stats', handlePlayerStats);
    GameState.socket.on('game_tip', handleGameTip);
}

function initEventListeners() {
    // Avatar selection
    document.querySelectorAll('.avatar-option').forEach(opt => {
        opt.addEventListener('click', () => {
            document.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            GameState.selectedAvatar = opt.dataset.avatar;
        });
    });

    // Mode selection
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            GameState.selectedMode = btn.dataset.mode;
        });
    });

    // Lobby buttons
    document.getElementById('create-room-btn').addEventListener('click', createRoom);
    document.getElementById('join-btn').addEventListener('click', joinRoom);
    document.getElementById('add-ai-btn').addEventListener('click', addAIPlayer);
    document.getElementById('start-game-btn').addEventListener('click', startGame);
    document.getElementById('copy-room-code').addEventListener('click', copyRoomCode);
    document.getElementById('copy-share-link').addEventListener('click', copyShareLink);
    document.getElementById('leave-room-btn').addEventListener('click', leaveRoom);

    // Game actions
    document.getElementById('fold-btn').addEventListener('click', () => playerAction('fold'));
    document.getElementById('check-btn').addEventListener('click', () => playerAction('check'));
    document.getElementById('call-btn').addEventListener('click', () => playerAction('call'));
    document.getElementById('raise-btn').addEventListener('click', handleRaise);
    document.getElementById('allin-btn').addEventListener('click', () => playerAction('all_in'));
    document.getElementById('surrender-btn').addEventListener('click', surrenderGame);
    document.getElementById('new-hand-btn').addEventListener('click', newHand);

    // Challenge buttons
    document.getElementById('accept-challenge-btn').addEventListener('click', acceptChallenge);
    document.getElementById('decline-challenge-btn').addEventListener('click', declineChallenge);

    // Raise slider and presets
    document.getElementById('raise-slider').addEventListener('input', updateRaiseDisplay);
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const multiplier = parseFloat(btn.dataset.multiplier);
            const pot = GameState.currentState?.pot || 0;
            const slider = document.getElementById('raise-slider');
            const value = Math.min(parseInt(slider.max), Math.max(parseInt(slider.min), Math.floor(pot * multiplier)));
            slider.value = value;
            updateRaiseDisplay();
        });
    });

    // Chat
    document.getElementById('send-chat').addEventListener('click', sendChat);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChat();
    });

    // Emoji buttons
    document.querySelectorAll('.emoji-btn').forEach(btn => {
        btn.addEventListener('click', () => sendEmoji(btn.dataset.emoji));
    });

    // Quick chat phrases
    document.querySelectorAll('.phrase-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('chat-input').value = btn.dataset.phrase;
            sendChat();
        });
    });

    // Top bar buttons
    document.getElementById('sound-toggle').addEventListener('click', toggleSound);
    document.getElementById('stats-btn').addEventListener('click', showStats);
    document.getElementById('help-btn').addEventListener('click', requestTip);
    document.getElementById('close-stats').addEventListener('click', () => {
        document.getElementById('stats-modal').style.display = 'none';
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);

    // Enter key for joining
    document.getElementById('player-name').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') joinGame();
    });
}

// Keyboard shortcuts
function handleKeyboard(e) {
    if (document.activeElement.tagName === 'INPUT') return;

    const isMyTurn = GameState.currentState?.current_player === GameState.playerName;
    if (!isMyTurn) return;

    switch(e.key.toLowerCase()) {
        case 'f': playerAction('fold'); break;
        case 'c':
            const checkBtn = document.getElementById('check-btn');
            if (checkBtn.style.display !== 'none') {
                playerAction('check');
            } else {
                playerAction('call');
            }
            break;
        case 'r': handleRaise(); break;
        case 'a': playerAction('all_in'); break;
    }
}

// Lobby Functions
function createRoom() {
    const playerName = document.getElementById('player-name').value.trim();
    if (!playerName) {
        showNotification('Please enter your name', 'error');
        return;
    }

    if (!GameState.socket || !GameState.socket.connected) {
        showNotification('Not connected to server. Please refresh the page.', 'error');
        return;
    }

    GameState.playerName = playerName;
    console.log('Creating room for player:', playerName);

    GameState.socket.emit('join_game', {
        room_id: '',
        player_name: playerName,
        is_human: true,
        mode: GameState.selectedMode,
        avatar: GameState.selectedAvatar,
        create_new: true
    });

    showNotification('Creating room...', 'info');
}

function joinRoom() {
    const playerName = document.getElementById('player-name').value.trim();
    if (!playerName) {
        showNotification('Please enter your name', 'error');
        return;
    }

    const roomCode = document.getElementById('room-id').value.trim().toUpperCase();
    if (!roomCode) {
        showNotification('Please enter a room code', 'error');
        return;
    }

    if (!GameState.socket || !GameState.socket.connected) {
        showNotification('Not connected to server. Please refresh the page.', 'error');
        return;
    }

    GameState.playerName = playerName;
    GameState.roomId = roomCode;
    console.log('Joining room:', roomCode, 'as player:', playerName);

    GameState.socket.emit('join_game', {
        room_id: roomCode,
        player_name: playerName,
        is_human: true,
        mode: GameState.selectedMode,
        avatar: GameState.selectedAvatar,
        create_new: false
    });

    showNotification('Joining room...', 'info');
}

function copyRoomCode() {
    const roomCode = document.getElementById('room-code-value').textContent;
    navigator.clipboard.writeText(roomCode).then(() => {
        showNotification('Room code copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = roomCode;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Room code copied!', 'success');
    });
}

function copyShareLink() {
    const shareLink = document.getElementById('share-link-input').value;
    navigator.clipboard.writeText(shareLink).then(() => {
        showNotification('Share link copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const input = document.getElementById('share-link-input');
        input.select();
        document.execCommand('copy');
        showNotification('Share link copied!', 'success');
    });
}

function updateShareLink(roomId) {
    const baseUrl = window.location.origin;
    const shareLink = `${baseUrl}?room=${roomId}`;
    document.getElementById('share-link-input').value = shareLink;
}

function leaveRoom() {
    // Reload the page to leave the room
    window.location.reload();
}

function addAIPlayer() {
    GameState.aiCount++;
    const difficulty = document.getElementById('ai-difficulty').value;

    GameState.socket.emit('add_ai_player', {
        room_id: GameState.roomId,
        name: `Bot_${GameState.aiCount}`,
        difficulty: difficulty
    });
}

function startGame() {
    GameState.socket.emit('start_game', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });
}

// Game Actions
function playerAction(action, amount = 0) {
    GameState.socket.emit('player_action', {
        room_id: GameState.roomId,
        player_name: GameState.playerName,
        action: action,
        amount: amount
    });
}

function handleRaise() {
    const amount = parseInt(document.getElementById('raise-slider').value);
    playerAction('raise', amount);
}

function newHand() {
    GameState.socket.emit('new_hand', {
        room_id: GameState.roomId
    });
}

function surrenderGame() {
    if (confirm('Are you sure you want to surrender? You will lose your remaining chips and exit the game.')) {
        GameState.socket.emit('surrender', {
            room_id: GameState.roomId,
            player_name: GameState.playerName
        });
        showNotification('You surrendered the game', 'warning');
    }
}

function acceptChallenge() {
    GameState.socket.emit('accept_challenge', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });
    document.getElementById('challenge-panel').style.display = 'none';
    showNotification('Challenge accepted!', 'success');
}

function declineChallenge() {
    GameState.socket.emit('decline_challenge', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });
    document.getElementById('challenge-panel').style.display = 'none';
    showNotification('Challenge declined', 'info');
}

function updateRaiseDisplay() {
    const value = document.getElementById('raise-slider').value;
    document.getElementById('raise-display').textContent = `$${value}`;
}

// Chat Functions
function sendChat() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    GameState.socket.emit('chat_message', {
        room_id: GameState.roomId,
        player_name: GameState.playerName,
        message: message
    });

    input.value = '';
}

function sendEmoji(emoji) {
    GameState.socket.emit('emoji_reaction', {
        room_id: GameState.roomId,
        player_name: GameState.playerName,
        emoji: emoji
    });
}

// Top Bar Functions
function toggleSound() {
    GameState.soundEnabled = !GameState.soundEnabled;
    const btn = document.getElementById('sound-toggle');
    btn.innerHTML = GameState.soundEnabled ? '&#128266;' : '&#128263;';
}

function showStats() {
    GameState.socket.emit('get_stats', {
        player_name: GameState.playerName
    });
    document.getElementById('stats-modal').style.display = 'flex';
}

function requestTip() {
    GameState.socket.emit('request_tip', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });
}

// Socket Event Handlers
function handleJoinedRoom(data) {
    console.log('Joined room:', data);
    GameState.roomId = data.room_id;
    GameState.isHost = data.is_host;

    // Show the player setup section, hide the join section
    document.getElementById('join-section').style.display = 'none';
    document.getElementById('player-setup').style.display = 'block';

    // Update room code display
    document.getElementById('room-code-value').textContent = data.room_id;

    // Update share link
    updateShareLink(data.room_id);

    // Show/hide host-only controls
    updateHostControls();

    const modeDisplay = document.getElementById('game-mode-display');
    modeDisplay.textContent = GameState.selectedMode === 'tournament' ?
        '\u{1F3C6} Tournament Mode' : '\u{1F4B0} Cash Game';

    showNotification(`Joined room ${data.room_id}!`, 'success');
}

function handlePlayerJoined(data) {
    // Update player count badge
    document.getElementById('player-count-badge').textContent = `(${data.player_count}/8)`;

    // Update start button
    const btn = document.getElementById('start-game-btn');
    btn.disabled = data.player_count < 2 || !GameState.isHost;

    if (!GameState.isHost) {
        document.getElementById('player-count-text').textContent = '';
        document.getElementById('waiting-for-host').style.display = 'block';
    } else {
        document.getElementById('waiting-for-host').style.display = 'none';
        document.getElementById('player-count-text').textContent =
            data.player_count >= 2 ? '' : `Need ${2 - data.player_count} more`;
    }

    // Show notification for new player
    if (data.player_name !== GameState.playerName) {
        showNotification(`${data.player_name} joined the room!`, 'info');
    }

    // Refresh the player list
    updateLobbyPlayerList();
}

function handlePlayerDisconnected(data) {
    showNotification(data.message, 'warning');
}

function handlePlayerLeft(data) {
    showNotification(`${data.player_name} left the room`, 'info');
    document.getElementById('player-count-badge').textContent = `(${data.player_count}/8)`;

    const btn = document.getElementById('start-game-btn');
    btn.disabled = data.player_count < 2 || !GameState.isHost;

    updateLobbyPlayerList();
}

function handleHostChanged(data) {
    if (data.new_host === GameState.playerName) {
        GameState.isHost = true;
        showNotification('You are now the host!', 'success');
    } else {
        showNotification(`${data.new_host} is now the host`, 'info');
    }
    updateHostControls();
    updateLobbyPlayerList();
}

function handleReconnected(data) {
    GameState.roomId = data.room_id;
    showNotification('Reconnected to game!', 'success');
}

function updateHostControls() {
    const startBtn = document.getElementById('start-game-btn');
    const addAiSection = document.getElementById('add-ai-section');
    const waitingMsg = document.getElementById('waiting-for-host');

    if (GameState.isHost) {
        startBtn.style.display = 'block';
        addAiSection.style.display = 'block';
        waitingMsg.style.display = 'none';
    } else {
        startBtn.style.display = 'none';
        addAiSection.style.display = 'none';
        waitingMsg.style.display = 'block';
    }
}

function updateLobbyPlayerList() {
    GameState.socket.emit('get_game_state', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });
}

function handleGameState(state) {
    GameState.currentState = state;

    if (state.phase === 'waiting') {
        updateLobbyPlayerListUI(state.players);
    } else {
        updateGameUI(state);
    }
}

function updateLobbyPlayerListUI(players) {
    const container = document.getElementById('players-list');
    container.innerHTML = '';

    // Store players in game state
    GameState.players = players;

    // Find the host (first human player or check is_host flag)
    const hostPlayer = players.find(p => p.is_host) || players.find(p => p.is_human);
    const hostName = hostPlayer ? hostPlayer.name : null;

    // Update isHost if server sent the info
    if (players.some(p => p.name === GameState.playerName && p.is_host)) {
        GameState.isHost = true;
    }

    players.forEach(player => {
        const isYou = player.name === GameState.playerName;
        const isHost = player.name === hostName || player.is_host;

        const card = document.createElement('div');
        card.className = 'player-card';
        if (isYou) card.classList.add('is-you');
        if (isHost) card.classList.add('is-host');

        let badges = '';
        if (isYou) badges += '<span class="you-badge">YOU</span>';
        if (isHost) badges += '<span class="host-badge">HOST</span>';

        card.innerHTML = `
            <div class="avatar">${AVATAR_ICONS[player.avatar] || AVATAR_ICONS['default']}</div>
            <div class="name">${player.name}${badges}</div>
            <span class="type ${player.is_human ? '' : 'ai'}">${player.is_human ? 'Human' : 'AI'}</span>
        `;
        container.appendChild(card);
    });

    // Update player count badge
    document.getElementById('player-count-badge').textContent = `(${players.length}/8)`;

    // Update start button
    const btn = document.getElementById('start-game-btn');
    btn.disabled = players.length < 2 || !GameState.isHost;

    if (GameState.isHost) {
        document.getElementById('player-count-text').textContent =
            players.length >= 2 ? '' : `Need ${2 - players.length} more`;
    }
}

function handleGameStarted(state) {
    document.getElementById('lobby').classList.remove('active');
    document.getElementById('game').classList.add('active');
    updateGameUI(state);
}

function handleNewHand(state) {
    document.getElementById('hand-complete-panel').style.display = 'none';
    document.getElementById('action-panel').style.display = 'block';
    updateGameUI(state);
}

function handleAIAction(data) {
    document.querySelectorAll('.thinking-indicator').forEach(el => el.remove());
}

function handleAIThinking(data) {
    const playerBox = document.querySelector(`[data-player="${data.player_name}"]`);
    if (playerBox && !playerBox.querySelector('.thinking-indicator')) {
        const indicator = document.createElement('div');
        indicator.className = 'thinking-indicator';
        indicator.textContent = '\u{1F914}';
        playerBox.appendChild(indicator);
    }
}

function handlePlayerRemoved(data) {
    console.log('Player removed:', data);
}

function handlePlayerEliminated(data) {
    showNotification(`${data.player_name} eliminated! Position: #${data.final_position}`);
}

function handleGameOver(data) {
    showNotification(`Game Over! Winner: ${data.winner}`, 'success');
}

function handleTournamentComplete(data) {
    let message = `Tournament Complete!\n\nWinner: ${data.winner}\n\nFinal Rankings:\n`;
    data.rankings.forEach((r, i) => {
        message += `${i + 1}. ${r.name}\n`;
    });
    alert(message);
}

function handleError(data) {
    showNotification(data.message, 'error');
}

function handleChatMessage(data) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = 'chat-msg';
    msg.innerHTML = `<span class="sender">${data.player}:</span> <span class="text">${escapeHtml(data.message)}</span>`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

function handleChatHistory(data) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    data.messages.forEach(msg => {
        const el = document.createElement('div');
        el.className = 'chat-msg';
        el.innerHTML = `<span class="sender">${msg.player}:</span> <span class="text">${escapeHtml(msg.message)}</span>`;
        container.appendChild(el);
    });
    container.scrollTop = container.scrollHeight;
}

function handleEmojiReaction(data) {
    showFloatingEmoji(data.emoji);
}

function handleAchievement(data) {
    data.achievements.forEach(ach => {
        showAchievement(ach);
    });
}

function handlePlayerStats(stats) {
    const content = document.getElementById('stats-content');
    content.innerHTML = `
        <div class="stat-row"><span class="stat-label">Hands Played</span><span class="stat-value">${stats.hands_played}</span></div>
        <div class="stat-row"><span class="stat-label">Hands Won</span><span class="stat-value">${stats.hands_won}</span></div>
        <div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value">${stats.win_rate}%</span></div>
        <div class="stat-row"><span class="stat-label">Net Profit</span><span class="stat-value" style="color: ${stats.net_profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)'}">$${stats.net_profit}</span></div>
        <div class="stat-row"><span class="stat-label">Biggest Pot Won</span><span class="stat-value">$${stats.biggest_pot_won}</span></div>
        <div class="stat-row"><span class="stat-label">Best Streak</span><span class="stat-value">${stats.streaks.best}</span></div>
        <div class="stat-row"><span class="stat-label">All-Ins Won/Lost</span><span class="stat-value">${stats.all_ins.won}/${stats.all_ins.lost}</span></div>
        <h3 style="margin-top: 20px; color: var(--primary-color);">Achievements (${stats.achievements.length})</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">
            ${stats.achievements.map(a => `<span style="background: var(--glass-bg); padding: 5px 10px; border-radius: 5px;">${a}</span>`).join('')}
        </div>
    `;
}

function handleGameTip(data) {
    showNotification(data.tip, 'info');
}

// UI Update Functions
function updateGameUI(state) {
    updateTopBar(state);
    updatePot(state.pot);
    updatePhase(state.phase);
    updateCommunityCards(state.community_cards);
    updatePlayers(state.players, state.dealer_position, state.current_player, state.last_winners);
    updateSidePanelPlayers(state.players, state.current_player);
    updateMyHand(state.players);
    updateProbability(state.win_probability, state.pot_odds);
    updateActionPanel(state);
    updateActionLog(state.action_log);

    if (state.phase === 'hand_complete' || state.phase === 'showdown') {
        showHandComplete(state);
    }
}

function updateSidePanelPlayers(players, currentPlayer) {
    const container = document.getElementById('game-players-list');
    if (!container) return;

    container.innerHTML = '';

    players.forEach(player => {
        const isActive = player.name === currentPlayer;
        const isFolded = player.folded;
        const isHuman = player.is_human;

        const item = document.createElement('div');
        item.className = 'game-player-item';
        if (isHuman) item.classList.add('is-human');
        else item.classList.add('is-bot');
        if (isActive) item.classList.add('is-active');
        if (isFolded) item.classList.add('is-folded');

        item.innerHTML = `
            <span class="player-avatar">${AVATAR_ICONS[player.avatar] || AVATAR_ICONS['default']}</span>
            <div class="player-info">
                <div class="player-name">${player.name}${isActive ? ' ⏳' : ''}${isFolded ? ' (Folded)' : ''}</div>
                <div class="player-type">${isHuman ? 'Human' : 'Bot'}</div>
            </div>
            <div class="player-chips">$${player.chips}</div>
        `;

        container.appendChild(item);
    });
}

function updateTopBar(state) {
    document.getElementById('hand-num').textContent = state.hand_number || 1;
    document.getElementById('sb-amount').textContent = state.small_blind;
    document.getElementById('bb-amount').textContent = state.big_blind;

    const tournamentInfo = document.getElementById('tournament-info');
    if (state.mode === 'tournament' && state.blind_level) {
        tournamentInfo.style.display = 'inline';
        document.getElementById('blind-level').textContent = state.blind_level;
        document.getElementById('hands-to-blind').textContent = state.hands_until_blind_increase;
    } else {
        tournamentInfo.style.display = 'none';
    }
}

function updatePot(pot) {
    document.getElementById('pot-amount').textContent = pot;
}

function updatePhase(phase) {
    const phaseNames = {
        'waiting': 'Waiting',
        'pre_flop': 'Pre-Flop',
        'flop': 'Flop',
        'turn': 'Turn',
        'river': 'River',
        'showdown': 'Showdown',
        'hand_complete': 'Complete'
    };
    document.getElementById('game-phase').textContent = phaseNames[phase] || phase;
}

function updateCommunityCards(cards) {
    const container = document.getElementById('community-cards');
    container.innerHTML = '';

    cards.forEach((card, i) => {
        const cardEl = createCardElement(card);
        cardEl.style.animationDelay = `${i * 0.1}s`;
        container.appendChild(cardEl);
    });

    for (let i = cards.length; i < 5; i++) {
        const placeholder = document.createElement('div');
        placeholder.className = 'card placeholder';
        container.appendChild(placeholder);
    }
}

function updatePlayers(players, dealerPos, currentPlayer, lastWinners) {
    const winnerNames = (lastWinners || []).map(w => w.name);

    for (let i = 0; i < 8; i++) {
        document.getElementById(`seat-${i}`).innerHTML = '';
    }

    players.forEach((player, index) => {
        const seat = document.getElementById(`seat-${index}`);
        if (!seat) return;

        const isActive = player.name === currentPlayer;
        const isWinner = winnerNames.includes(player.name);
        const isMe = player.name === GameState.playerName;

        let classes = 'player-box';
        if (isActive) classes += ' active';
        if (player.is_folded) classes += ' folded';
        if (isWinner) classes += ' winner';

        let badges = '';
        if (index === dealerPos) badges += '<span class="player-badge dealer">D</span>';
        if (player.is_all_in) badges += '<span class="player-badge allin">ALL IN</span>';

        let cardsHtml = '';
        if (!isMe && !player.is_folded) {
            cardsHtml = '<div class="player-cards-mini">';
            if (player.hand && player.hand.length > 0) {
                player.hand.forEach(card => {
                    cardsHtml += `<div class="mini-card ${card.suit}"><span>${card.rank}</span><span>${SUIT_SYMBOLS[card.suit]}</span></div>`;
                });
            } else if (player.card_count > 0) {
                for (let i = 0; i < player.card_count; i++) {
                    cardsHtml += '<div class="mini-card hidden">?</div>';
                }
            }
            cardsHtml += '</div>';
        }

        seat.innerHTML = `
            <div class="${classes}" data-player="${player.name}">
                <div class="player-avatar">${AVATAR_ICONS[player.avatar] || AVATAR_ICONS['default']}</div>
                <div class="player-name">${player.name}${!player.is_human ? ' \u{1F916}' : ''}</div>
                <div class="player-chips">$${player.chips}</div>
                ${player.total_bet > 0 ? `<div class="player-bet">Bet: $${player.total_bet}</div>` : ''}
                ${badges}
                ${cardsHtml}
            </div>
        `;
    });
}

function updateMyHand(players) {
    const myPlayer = players.find(p => p.name === GameState.playerName);
    const container = document.getElementById('my-cards');
    container.innerHTML = '';

    if (myPlayer && myPlayer.hand) {
        myPlayer.hand.forEach(card => {
            container.appendChild(createCardElement(card));
        });
    }
}

function updateProbability(winProb, potOdds) {
    if (!winProb || Object.keys(winProb).length === 0) {
        document.getElementById('win-prob').textContent = '--';
        document.getElementById('prob-fill').style.width = '0%';
        document.getElementById('strength-label').textContent = '--';
        document.getElementById('outs-count').textContent = '0';
        document.getElementById('pot-odds').textContent = '--';
        return;
    }

    const winPct = winProb.win || 0;
    document.getElementById('win-prob').textContent = winPct;
    document.getElementById('prob-fill').style.width = `${winPct}%`;

    const label = document.getElementById('strength-label');
    label.textContent = winProb.strength_label || '--';
    label.style.background = winProb.strength_color || 'gray';

    const outs = winProb.outs || {};
    document.getElementById('outs-count').textContent = outs.outs || 0;
    document.getElementById('outs-odds').textContent = outs.odds || '';

    if (potOdds) {
        document.getElementById('pot-odds').textContent =
            potOdds.pot_odds > 0 ? `${potOdds.pot_odds}% (${potOdds.ratio})` : '--';
    }
}

function updateActionPanel(state) {
    const actionPanel = document.getElementById('action-panel');
    const actionButtons = document.getElementById('action-buttons');
    const waitingMessage = document.getElementById('waiting-message');
    const handCompletePanel = document.getElementById('hand-complete-panel');

    const isMyTurn = state.current_player === GameState.playerName;
    const validActions = state.valid_actions || [];

    if (state.phase === 'hand_complete' || state.phase === 'showdown') {
        actionPanel.style.display = 'none';
        return;
    }

    actionPanel.style.display = 'block';
    handCompletePanel.style.display = 'none';

    if (!isMyTurn) {
        actionButtons.style.display = 'none';
        waitingMessage.style.display = 'flex';
        document.getElementById('current-player-name').textContent = state.current_player || 'Next player';
        return;
    }

    actionButtons.style.display = 'flex';
    waitingMessage.style.display = 'none';

    const actions = validActions.map(a => a.action);

    document.getElementById('check-btn').style.display = actions.includes('check') ? 'flex' : 'none';
    document.getElementById('call-btn').style.display = actions.includes('call') ? 'flex' : 'none';

    const callAction = validActions.find(a => a.action === 'call');
    if (callAction) {
        document.getElementById('call-amount').textContent = callAction.amount;
    }

    const raiseAction = validActions.find(a => a.action === 'raise');
    const raiseSection = document.querySelector('.raise-section');
    if (raiseAction) {
        raiseSection.style.display = 'flex';
        const slider = document.getElementById('raise-slider');
        slider.min = raiseAction.min;
        slider.max = raiseAction.max;
        slider.value = raiseAction.min;
        document.getElementById('min-raise-label').textContent = `$${raiseAction.min}`;
        document.getElementById('max-raise-label').textContent = `$${raiseAction.max}`;
        updateRaiseDisplay();
    } else {
        raiseSection.style.display = 'none';
    }

    const allinAction = validActions.find(a => a.action === 'all_in');
    if (allinAction) {
        document.getElementById('allin-amount').textContent = allinAction.amount;
    }
}

function updateActionLog(log) {
    const ul = document.getElementById('action-log-list');
    ul.innerHTML = '';

    if (log) {
        log.forEach(entry => {
            const li = document.createElement('li');
            li.textContent = entry;
            ul.appendChild(li);
        });
    }
    ul.scrollTop = ul.scrollHeight;
}

function showHandComplete(state) {
    document.getElementById('action-panel').style.display = 'none';
    const panel = document.getElementById('hand-complete-panel');
    panel.style.display = 'block';

    const winners = state.last_winners || [];
    const winnerMsg = winners.map(w => `${w.name}`).join(' & ');
    document.getElementById('winner-message').textContent = winnerMsg ? `${winnerMsg} Wins!` : 'Hand complete!';

    const handName = winners.length > 0 ? winners[0].hand_name : '';
    document.getElementById('winning-hand').textContent = handName;

    // Show pot won amount
    const totalWon = winners.reduce((sum, w) => sum + w.amount, 0);
    document.getElementById('pot-won').textContent = totalWon > 0 ? `+$${totalWon}` : '';

    // Show winning cards if available
    const winningCardsContainer = document.getElementById('winning-cards');
    winningCardsContainer.innerHTML = '';

    // Find winner's cards from players
    if (winners.length > 0) {
        const winnerPlayer = state.players.find(p => p.name === winners[0].name);
        if (winnerPlayer && winnerPlayer.hand) {
            winnerPlayer.hand.forEach((card, i) => {
                const cardEl = createCardElement(card);
                cardEl.style.animationDelay = `${i * 0.2}s`;
                winningCardsContainer.appendChild(cardEl);
            });
        }
    }

    // Create confetti celebration
    createConfetti();
}

function createConfetti() {
    const container = document.getElementById('confetti-container');
    container.innerHTML = '';

    const colors = ['#ffd700', '#ff4757', '#00ff88', '#00d4ff', '#ff6b81', '#7bed9f'];

    for (let i = 0; i < 50; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.left = `${Math.random() * 100}%`;
        confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.animationDelay = `${Math.random() * 2}s`;
        confetti.style.animationDuration = `${2 + Math.random() * 2}s`;

        // Random shapes
        if (Math.random() > 0.5) {
            confetti.style.borderRadius = '50%';
        }

        container.appendChild(confetti);
    }

    // Clear confetti after animation
    setTimeout(() => {
        container.innerHTML = '';
    }, 4000);
}

// Card Element Creation
function createCardElement(card) {
    const el = document.createElement('div');
    el.className = `card ${card.suit}`;
    el.innerHTML = `
        <span class="rank">${card.rank}</span>
        <span class="suit">${SUIT_SYMBOLS[card.suit]}</span>
    `;
    return el;
}

// UI Effects
function showFloatingEmoji(emoji) {
    const container = document.getElementById('floating-emojis');
    const el = document.createElement('div');
    el.className = 'floating-emoji';
    el.textContent = emoji;
    el.style.left = `${Math.random() * 80 + 10}%`;
    el.style.top = `${Math.random() * 50 + 25}%`;
    container.appendChild(el);

    setTimeout(() => el.remove(), 2000);
}

function showAchievement(achievement) {
    const toast = document.getElementById('achievement-toast');
    document.getElementById('achievement-icon').textContent = achievement.icon;
    document.getElementById('achievement-title').textContent = achievement.name;
    document.getElementById('achievement-desc').textContent = achievement.desc;

    toast.style.display = 'flex';
    SoundManager.play('win');

    setTimeout(() => {
        toast.style.display = 'none';
    }, 4000);
}

function showNotification(message, type = 'info') {
    const colors = {
        'info': '#00d4ff',
        'success': '#00ff88',
        'error': '#ff4757',
        'warning': '#ffa502'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: ${colors[type]};
        color: #0a0a1a;
        padding: 15px 30px;
        border-radius: 10px;
        font-weight: 600;
        z-index: 1002;
        animation: slideIn 0.5s ease;
        max-width: 80%;
        text-align: center;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => notification.remove(), 4000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
