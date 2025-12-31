// MIC MIND - Last Card / Crazy Eights - JavaScript

const SUIT_SYMBOLS = {
    'hearts': '\u2665',
    'diamonds': '\u2666',
    'clubs': '\u2663',
    'spades': '\u2660'
};

const SUIT_COLORS = {
    'hearts': '#e74c3c',
    'diamonds': '#e74c3c',
    'clubs': '#2c3e50',
    'spades': '#2c3e50'
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
    currentState: null,
    aiCount: 0,
    soundEnabled: true,
    isHost: false,
    players: [],
    selectedCardIndex: null,
    playableCards: []
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
            'card_play': { freq: 600, duration: 0.1, type: 'sine' },
            'card_draw': { freq: 300, duration: 0.15, type: 'sine' },
            'lastcard': { freq: 800, duration: 0.3, type: 'square' },
            'win': { freq: 523.25, duration: 0.5, type: 'sine' },
            'click': { freq: 400, duration: 0.05, type: 'sine' },
            'error': { freq: 200, duration: 0.2, type: 'sawtooth' },
            'reverse': { freq: 500, duration: 0.2, type: 'triangle' },
            'skip': { freq: 700, duration: 0.15, type: 'sine' }
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
    GameState.socket.on('card_played', handleCardPlayed);
    GameState.socket.on('card_drawn', handleCardDrawn);
    GameState.socket.on('last_card_called', handleLastCardCalled);
    GameState.socket.on('ai_action', handleAIAction);
    GameState.socket.on('ai_thinking', handleAIThinking);
    GameState.socket.on('player_removed', handlePlayerRemoved);
    GameState.socket.on('player_disconnected', handlePlayerDisconnected);
    GameState.socket.on('player_left', handlePlayerLeft);
    GameState.socket.on('host_changed', handleHostChanged);
    GameState.socket.on('reconnected', handleReconnected);
    GameState.socket.on('game_over', handleGameOver);
    GameState.socket.on('error', handleError);
    GameState.socket.on('sound_effect', (data) => SoundManager.play(data.sound));
    GameState.socket.on('chat_message', handleChatMessage);
    GameState.socket.on('chat_history', handleChatHistory);
    GameState.socket.on('emoji_reaction', handleEmojiReaction);
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

    // Lobby buttons
    document.getElementById('create-room-btn').addEventListener('click', createRoom);
    document.getElementById('join-btn').addEventListener('click', joinRoom);
    document.getElementById('add-ai-btn').addEventListener('click', addAIPlayer);
    document.getElementById('start-game-btn').addEventListener('click', startGame);
    document.getElementById('copy-room-code').addEventListener('click', copyRoomCode);
    document.getElementById('copy-share-link').addEventListener('click', copyShareLink);
    document.getElementById('leave-room-btn').addEventListener('click', leaveRoom);

    // Game actions
    document.getElementById('draw-btn').addEventListener('click', drawCard);
    document.getElementById('play-btn').addEventListener('click', playSelectedCard);
    document.getElementById('lastcard-btn').addEventListener('click', callLastCard);
    document.getElementById('new-round-btn').addEventListener('click', newRound);

    // Suit selector buttons
    document.querySelectorAll('.suit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const suit = btn.dataset.suit;
            selectSuitAndPlay(suit);
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

    // Top bar buttons
    document.getElementById('sound-toggle').addEventListener('click', toggleSound);
    document.getElementById('help-btn').addEventListener('click', showHelp);

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboard);

    // Enter key for joining
    document.getElementById('player-name').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const roomCode = document.getElementById('room-id').value.trim();
            if (roomCode) {
                joinRoom();
            } else {
                createRoom();
            }
        }
    });
}

// Keyboard shortcuts
function handleKeyboard(e) {
    if (document.activeElement.tagName === 'INPUT') return;

    const isMyTurn = GameState.currentState?.current_player === GameState.playerName;

    switch(e.key.toLowerCase()) {
        case 'd':
            if (isMyTurn) drawCard();
            break;
        case ' ':
        case 'enter':
            if (isMyTurn && GameState.selectedCardIndex !== null) {
                e.preventDefault();
                playSelectedCard();
            }
            break;
        case 'l':
            callLastCard();
            break;
        case 'arrowleft':
            selectPreviousCard();
            break;
        case 'arrowright':
            selectNextCard();
            break;
    }
}

function selectPreviousCard() {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand || myPlayer.hand.length === 0) return;

    if (GameState.selectedCardIndex === null) {
        GameState.selectedCardIndex = myPlayer.hand.length - 1;
    } else {
        GameState.selectedCardIndex = (GameState.selectedCardIndex - 1 + myPlayer.hand.length) % myPlayer.hand.length;
    }
    updateMyHand(GameState.currentState.players);
}

function selectNextCard() {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand || myPlayer.hand.length === 0) return;

    if (GameState.selectedCardIndex === null) {
        GameState.selectedCardIndex = 0;
    } else {
        GameState.selectedCardIndex = (GameState.selectedCardIndex + 1) % myPlayer.hand.length;
    }
    updateMyHand(GameState.currentState.players);
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
function drawCard() {
    if (GameState.currentState?.current_player !== GameState.playerName) {
        showNotification("It's not your turn!", 'error');
        return;
    }

    GameState.socket.emit('draw_card', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });

    SoundManager.play('card_draw');
}

function playSelectedCard() {
    if (GameState.selectedCardIndex === null) {
        showNotification('Select a card first!', 'error');
        return;
    }

    if (GameState.currentState?.current_player !== GameState.playerName) {
        showNotification("It's not your turn!", 'error');
        return;
    }

    const myPlayer = GameState.currentState.players.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand) return;

    const card = myPlayer.hand[GameState.selectedCardIndex];

    // Check if card is playable
    if (!GameState.playableCards.includes(GameState.selectedCardIndex)) {
        showNotification('That card cannot be played!', 'error');
        SoundManager.play('error');
        return;
    }

    // If it's a wild 8, show suit selector
    if (card.rank === '8') {
        showSuitSelector();
        return;
    }

    // Play the card
    GameState.socket.emit('play_card', {
        room_id: GameState.roomId,
        player_name: GameState.playerName,
        card_index: GameState.selectedCardIndex,
        suit_override: null
    });

    GameState.selectedCardIndex = null;
    SoundManager.play('card_play');
}

function showSuitSelector() {
    document.getElementById('suit-modal').style.display = 'flex';
}

function hideSuitSelector() {
    document.getElementById('suit-modal').style.display = 'none';
}

function selectSuitAndPlay(suit) {
    hideSuitSelector();

    GameState.socket.emit('play_card', {
        room_id: GameState.roomId,
        player_name: GameState.playerName,
        card_index: GameState.selectedCardIndex,
        suit_override: suit
    });

    GameState.selectedCardIndex = null;
    SoundManager.play('card_play');
}

function callLastCard() {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer) return;

    if (myPlayer.hand?.length !== 2) {
        showNotification('You can only call Last Card when you have 2 cards!', 'error');
        return;
    }

    if (myPlayer.last_card_called) {
        showNotification('You already called Last Card!', 'info');
        return;
    }

    GameState.socket.emit('call_last_card', {
        room_id: GameState.roomId,
        player_name: GameState.playerName
    });

    SoundManager.play('lastcard');
}

function newRound() {
    GameState.socket.emit('new_round', {
        room_id: GameState.roomId
    });
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

function showHelp() {
    showNotification('Match rank OR suit. 8=Wild, 2=Draw 2, A=Reverse, J=Skip. Call Last Card when you have 2 cards!', 'info');
}

// Socket Event Handlers
function handleJoinedRoom(data) {
    console.log('Joined room:', data);
    GameState.roomId = data.room_id;
    GameState.isHost = data.is_host;

    document.getElementById('join-section').style.display = 'none';
    document.getElementById('player-setup').style.display = 'block';

    document.getElementById('room-code-value').textContent = data.room_id;
    updateShareLink(data.room_id);
    updateHostControls();

    showNotification(`Joined room ${data.room_id}!`, 'success');
}

function handlePlayerJoined(data) {
    document.getElementById('player-count-badge').textContent = `(${data.player_count}/8)`;

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

    if (data.player_name !== GameState.playerName) {
        showNotification(`${data.player_name} joined the room!`, 'info');
    }

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
    GameState.playableCards = state.playable_cards || [];

    if (state.phase === 'waiting') {
        updateLobbyPlayerListUI(state.players);
    } else {
        updateGameUI(state);
    }
}

function updateLobbyPlayerListUI(players) {
    const container = document.getElementById('players-list');
    container.innerHTML = '';

    GameState.players = players;

    const hostPlayer = players.find(p => p.is_host) || players.find(p => p.is_human);
    const hostName = hostPlayer ? hostPlayer.name : null;

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

    document.getElementById('player-count-badge').textContent = `(${players.length}/8)`;

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
    GameState.selectedCardIndex = null;
    updateGameUI(state);
}

function handleCardPlayed(data) {
    showNotification(`${data.player_name} played ${data.card.rank}${SUIT_SYMBOLS[data.card.suit]}`, 'info');
    SoundManager.play('card_play');
}

function handleCardDrawn(data) {
    if (data.player_name !== GameState.playerName) {
        showNotification(`${data.player_name} drew ${data.count} card(s)`, 'info');
    }
}

function handleLastCardCalled(data) {
    showNotification(`${data.player_name} called LAST CARD!`, 'warning');
    SoundManager.play('lastcard');
    showFloatingEmoji('\u{1F4E2}');
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

function handleGameOver(data) {
    showNotification(`Game Over! ${data.winner} wins!`, 'success');
    SoundManager.play('win');
}

function handleError(data) {
    showNotification(data.message, 'error');
    SoundManager.play('error');
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

// UI Update Functions
function updateGameUI(state) {
    updateTopBar(state);
    updateDiscardPile(state);
    updateDrawPile(state);
    updatePlayers(state.players, state.current_player);
    updateSidePanelPlayers(state.players, state.current_player);
    updateMyHand(state.players);
    updateActionPanel(state);
    updateActionLog(state.action_log);

    if (state.phase === 'game_over') {
        showGameOver(state);
    }
}

function updateTopBar(state) {
    const directionIndicator = document.getElementById('direction-indicator');
    if (state.direction === 1) {
        directionIndicator.innerHTML = '&#8635; Clockwise';
    } else {
        directionIndicator.innerHTML = '&#8634; Counter-clockwise';
    }

    const pendingDrawIndicator = document.getElementById('pending-draw-indicator');
    if (state.pending_draw > 0) {
        pendingDrawIndicator.style.display = 'inline';
        document.getElementById('pending-draw-count').textContent = state.pending_draw;
    } else {
        pendingDrawIndicator.style.display = 'none';
    }
}

function updateDiscardPile(state) {
    const discardCard = document.getElementById('discard-card');
    const suitIndicator = document.getElementById('current-suit-indicator');

    if (state.discard_pile_top) {
        const card = state.discard_pile_top;
        discardCard.className = `card ${card.suit}`;
        discardCard.innerHTML = `
            <span class="rank">${card.rank}</span>
            <span class="suit">${SUIT_SYMBOLS[card.suit]}</span>
        `;
    }

    // Show current suit indicator (especially for wild 8s)
    if (state.current_suit) {
        suitIndicator.innerHTML = `<span class="suit-${state.current_suit}">${SUIT_SYMBOLS[state.current_suit]}</span>`;
        suitIndicator.style.color = SUIT_COLORS[state.current_suit];
        suitIndicator.style.display = 'block';
    } else {
        suitIndicator.style.display = 'none';
    }

    // Update phase badge
    const phaseNames = {
        'waiting': 'Waiting',
        'playing': 'Playing',
        'game_over': 'Game Over'
    };
    document.getElementById('game-phase').textContent = phaseNames[state.phase] || state.phase;
}

function updateDrawPile(state) {
    document.getElementById('draw-pile-count').textContent = state.draw_pile_count || 0;
}

function updatePlayers(players, currentPlayer) {
    // Clear all seats first
    for (let i = 0; i < 8; i++) {
        document.getElementById(`seat-${i}`).innerHTML = '';
    }

    players.forEach((player, index) => {
        const seat = document.getElementById(`seat-${index}`);
        if (!seat) return;

        const isActive = player.name === currentPlayer;
        const isMe = player.name === GameState.playerName;

        let classes = 'player-box';
        if (isActive) classes += ' active';
        if (player.last_card_called) classes += ' last-card';

        let badges = '';
        if (player.last_card_called) badges += '<span class="player-badge lastcard">LAST!</span>';
        if (!player.is_human) badges += '<span class="player-badge bot">BOT</span>';

        // Show card backs for other players
        let cardsHtml = '';
        if (!isMe && player.card_count > 0) {
            cardsHtml = '<div class="player-cards-mini">';
            const displayCount = Math.min(player.card_count, 5);
            for (let i = 0; i < displayCount; i++) {
                cardsHtml += '<div class="mini-card hidden">?</div>';
            }
            if (player.card_count > 5) {
                cardsHtml += `<span class="more-cards">+${player.card_count - 5}</span>`;
            }
            cardsHtml += '</div>';
        }

        seat.innerHTML = `
            <div class="${classes}" data-player="${player.name}">
                <div class="player-avatar">${AVATAR_ICONS[player.avatar] || AVATAR_ICONS['default']}</div>
                <div class="player-name">${player.name}${!player.is_human ? ' \u{1F916}' : ''}</div>
                <div class="player-card-count">${player.card_count} cards</div>
                ${badges}
                ${cardsHtml}
            </div>
        `;
    });
}

function updateSidePanelPlayers(players, currentPlayer) {
    const container = document.getElementById('game-players-list');
    if (!container) return;

    container.innerHTML = '';

    players.forEach(player => {
        const isActive = player.name === currentPlayer;
        const isHuman = player.is_human;

        const item = document.createElement('div');
        item.className = 'game-player-item';
        if (isHuman) item.classList.add('is-human');
        else item.classList.add('is-bot');
        if (isActive) item.classList.add('is-active');
        if (player.last_card_called) item.classList.add('last-card-called');

        item.innerHTML = `
            <span class="player-avatar">${AVATAR_ICONS[player.avatar] || AVATAR_ICONS['default']}</span>
            <div class="player-info">
                <div class="player-name">${player.name}${isActive ? ' \u{23F3}' : ''}${player.last_card_called ? ' \u{1F4E2}' : ''}</div>
                <div class="player-type">${isHuman ? 'Human' : 'Bot'}</div>
            </div>
            <div class="player-card-count">${player.card_count} cards</div>
        `;

        container.appendChild(item);
    });
}

function updateMyHand(players) {
    const myPlayer = players.find(p => p.name === GameState.playerName);
    const container = document.getElementById('my-cards');
    container.innerHTML = '';

    document.getElementById('my-card-count').textContent = myPlayer?.hand?.length || 0;

    if (myPlayer && myPlayer.hand) {
        myPlayer.hand.forEach((card, index) => {
            const cardEl = createCardElement(card, index);

            // Mark playable cards
            if (GameState.playableCards.includes(index)) {
                cardEl.classList.add('playable');
            }

            // Mark selected card
            if (index === GameState.selectedCardIndex) {
                cardEl.classList.add('selected');
            }

            // Click to select
            cardEl.addEventListener('click', () => selectCard(index));

            container.appendChild(cardEl);
        });

        // Show/hide Last Card button
        const lastCardBtn = document.getElementById('lastcard-btn');
        if (myPlayer.hand.length === 2 && !myPlayer.last_card_called) {
            lastCardBtn.style.display = 'flex';
        } else {
            lastCardBtn.style.display = 'none';
        }
    }
}

function selectCard(index) {
    if (GameState.selectedCardIndex === index) {
        // Double click to play
        if (GameState.playableCards.includes(index)) {
            playSelectedCard();
        }
        return;
    }

    GameState.selectedCardIndex = index;
    updateMyHand(GameState.currentState.players);

    // Update play button state
    const playBtn = document.getElementById('play-btn');
    playBtn.disabled = !GameState.playableCards.includes(index);

    SoundManager.play('click');
}

function updateActionPanel(state) {
    const actionButtons = document.getElementById('action-buttons');
    const waitingMessage = document.getElementById('waiting-message');
    const gameOverPanel = document.getElementById('game-over-panel');

    const isMyTurn = state.current_player === GameState.playerName;

    if (state.phase === 'game_over') {
        actionButtons.style.display = 'none';
        waitingMessage.style.display = 'none';
        gameOverPanel.style.display = 'block';
        return;
    }

    gameOverPanel.style.display = 'none';

    if (!isMyTurn) {
        actionButtons.style.display = 'none';
        waitingMessage.style.display = 'flex';
        document.getElementById('current-player-name').textContent = state.current_player || 'Next player';
        return;
    }

    actionButtons.style.display = 'flex';
    waitingMessage.style.display = 'none';

    // Update play button state based on selection
    const playBtn = document.getElementById('play-btn');
    playBtn.disabled = GameState.selectedCardIndex === null ||
                       !GameState.playableCards.includes(GameState.selectedCardIndex);

    // Update draw button text if there's pending draw
    const drawBtn = document.getElementById('draw-btn');
    if (state.pending_draw > 0) {
        drawBtn.querySelector('.btn-text').textContent = `Draw ${state.pending_draw}`;
    } else {
        drawBtn.querySelector('.btn-text').textContent = 'Draw Card';
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

function showGameOver(state) {
    document.getElementById('action-buttons').style.display = 'none';
    document.getElementById('waiting-message').style.display = 'none';
    document.getElementById('game-over-panel').style.display = 'block';

    const winnerMsg = state.winner ? `${state.winner} Wins!` : 'Game Over!';
    document.getElementById('winner-message').textContent = winnerMsg;

    SoundManager.play('win');
    showFloatingEmoji('\u{1F3C6}');
}

// Card Element Creation
function createCardElement(card, index = 0) {
    const el = document.createElement('div');
    el.className = `card ${card.suit}`;
    el.dataset.index = index;
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
