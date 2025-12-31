// MIC MIND - Last Card / Crazy Eights - JavaScript

const SUIT_SYMBOLS = {
    'hearts': '\u2665',
    'diamonds': '\u2666',
    'clubs': '\u2663',
    'spades': '\u2660',
    'joker': '\u2605'  // Star symbol for Joker
};

const SUIT_COLORS = {
    'hearts': '#e74c3c',
    'diamonds': '#e74c3c',
    'clubs': '#2c3e50',
    'spades': '#2c3e50',
    'joker': '#9b59b6'  // Purple for Joker
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
    selectedCardIndices: [],  // For multi-card selection
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
    GameState.socket.on('game_update', handleGameUpdate);
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
            if (isMyTurn && GameState.selectedCardIndices.length > 0) {
                e.preventDefault();
                playSelectedCard();
            }
            break;
        case 'l':
            callLastCard();
            break;
        case 'a':
            // Select all cards of same rank as currently selected
            if (GameState.selectedCardIndex !== null) {
                selectAllSameRank(GameState.selectedCardIndex);
            }
            break;
        case 'c':
            // Auto-select best combo cards
            if (GameState.selectedCardIndex !== null) {
                selectComboCards(GameState.selectedCardIndex);
            }
            break;
        case 'escape':
            // Clear selection
            GameState.selectedCardIndex = null;
            GameState.selectedCardIndices = [];
            if (GameState.currentState) {
                updateMyHand(GameState.currentState.players);
            }
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
    GameState.selectedCardIndices = [GameState.selectedCardIndex];
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
    GameState.selectedCardIndices = [GameState.selectedCardIndex];
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
    if (GameState.selectedCardIndices.length === 0) {
        showNotification('Select a card first!', 'error');
        return;
    }

    if (GameState.currentState?.current_player !== GameState.playerName) {
        showNotification("It's not your turn!", 'error');
        return;
    }

    const myPlayer = GameState.currentState.players.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand) return;

    // Validate combo if multiple cards selected
    if (GameState.selectedCardIndices.length > 1) {
        if (!isValidCombo(myPlayer.hand, GameState.selectedCardIndices)) {
            showNotification('Invalid combo! Use same rank, Jack+card, or Joker+2', 'error');
            SoundManager.play('error');
            return;
        }
    }

    // Check if at least first card is playable (combos may include non-playable cards)
    const firstIndex = GameState.selectedCardIndices[0];
    const hasPlayableCard = GameState.selectedCardIndices.some(i => GameState.playableCards.includes(i));
    if (!hasPlayableCard) {
        showNotification('At least one selected card must be playable!', 'error');
        SoundManager.play('error');
        return;
    }

    // Check if any card in combo needs suit selector (Ace or Joker)
    const selectedCards = GameState.selectedCardIndices.map(i => myPlayer.hand[i]);
    const needsSuitSelector = selectedCards.some(c => c.rank === 'A' || c.rank === 'Joker');

    if (needsSuitSelector) {
        showSuitSelector();
        return;
    }

    // Play the card(s)
    if (GameState.selectedCardIndices.length === 1) {
        // Single card play
        GameState.socket.emit('play_card', {
            room_id: GameState.roomId,
            player_name: GameState.playerName,
            card_index: GameState.selectedCardIndices[0],
            suit_override: null
        });
    } else {
        // Multi-card play (combo)
        GameState.socket.emit('play_cards', {
            room_id: GameState.roomId,
            player_name: GameState.playerName,
            card_indices: GameState.selectedCardIndices,
            suit_override: null
        });
    }

    GameState.selectedCardIndex = null;
    GameState.selectedCardIndices = [];
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

    if (GameState.selectedCardIndices.length === 1) {
        // Single card play
        GameState.socket.emit('play_card', {
            room_id: GameState.roomId,
            player_name: GameState.playerName,
            card_index: GameState.selectedCardIndices[0],
            suit_override: suit
        });
    } else {
        // Multi-card play
        GameState.socket.emit('play_cards', {
            room_id: GameState.roomId,
            player_name: GameState.playerName,
            card_indices: GameState.selectedCardIndices,
            suit_override: suit
        });
    }

    GameState.selectedCardIndex = null;
    GameState.selectedCardIndices = [];
    SoundManager.play('card_play');
}

function callLastCard() {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer) return;

    // Allow calling with 2-3 cards (for multi-card finishing plays)
    if (myPlayer.hand?.length < 2 || myPlayer.hand?.length > 3) {
        showNotification('You can only call Last Card when you have 2-3 cards!', 'error');
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
    showNotification('COMBOS: Ctrl+click or [C] key! Jack+any, Joker+2, same rank. Keys: [A]=same rank, [C]=combo, [D]=draw, [L]=last card, [ESC]=clear. Special: A=suit, 2=+2, 7/8=reverse, J=free throw, Joker=+6', 'info');
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

function handleGameUpdate(data) {
    // Handle general game updates for synchronization
    console.log('Game update:', data);
    // Request fresh state if needed
    if (GameState.currentState && data.phase !== GameState.currentState.phase) {
        updateLobbyPlayerList();
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
    GameState.selectedCardIndices = [];
    updateGameUI(state);
}

function handleCardPlayed(data) {
    let cardDisplay;
    if (data.card.rank === 'Joker') {
        cardDisplay = 'Joker\u2605';
    } else {
        cardDisplay = `${data.card.rank}${SUIT_SYMBOLS[data.card.suit]}`;
    }
    showNotification(`${data.player_name} played ${cardDisplay}`, 'info');
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
        const oldCard = discardCard.dataset.card;
        const newCard = `${card.rank}-${card.suit}`;

        // Handle Joker display
        if (card.rank === 'Joker') {
            discardCard.className = 'card joker';
            discardCard.innerHTML = `
                <span class="rank">&#9733;</span>
                <span class="suit">JOKER</span>
            `;
        } else {
            discardCard.className = `card ${card.suit}`;
            discardCard.innerHTML = `
                <span class="rank">${card.rank}</span>
                <span class="suit">${SUIT_SYMBOLS[card.suit]}</span>
            `;
        }

        // Trigger animation if card changed
        if (oldCard !== newCard) {
            discardCard.classList.add('card-played');
            discardCard.dataset.card = newCard;
            setTimeout(() => discardCard.classList.remove('card-played'), 400);
        }
    }

    // Show current suit indicator (especially for wild 8s and Jokers)
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
    const oldCount = container.children.length;
    container.innerHTML = '';

    document.getElementById('my-card-count').textContent = myPlayer?.hand?.length || 0;

    if (myPlayer && myPlayer.hand) {
        const newCount = myPlayer.hand.length;

        // Find cards of same rank for grouping indicator
        const rankCounts = {};
        myPlayer.hand.forEach((card, i) => {
            if (!rankCounts[card.rank]) rankCounts[card.rank] = [];
            rankCounts[card.rank].push(i);
        });

        // Find combo-eligible cards based on current selection
        const comboEligible = getComboEligibleCards(myPlayer.hand);

        myPlayer.hand.forEach((card, index) => {
            const cardEl = createCardElement(card, index);

            // Mark playable cards
            if (GameState.playableCards.includes(index)) {
                cardEl.classList.add('playable');
            }

            // Mark selected cards (multi-selection)
            if (GameState.selectedCardIndices.includes(index)) {
                cardEl.classList.add('selected');
            }

            // Mark combo-eligible cards (can be added to current selection)
            if (comboEligible.includes(index) && !GameState.selectedCardIndices.includes(index)) {
                cardEl.classList.add('combo-eligible');
            }

            // Show indicator for cards with same rank (can be played together)
            if (rankCounts[card.rank].length > 1) {
                cardEl.classList.add('has-matching');
                const matchBadge = document.createElement('span');
                matchBadge.className = 'match-badge';
                matchBadge.textContent = rankCounts[card.rank].length;
                matchBadge.title = `${rankCounts[card.rank].length} cards of same rank - Double-click to select all`;
                cardEl.appendChild(matchBadge);
            }

            // Show combo indicator for special cards
            if (card.rank === 'J' || card.rank === 'Joker' || card.rank === '2') {
                cardEl.classList.add('combo-card');
            }

            // Animate new cards (if hand grew)
            if (newCount > oldCount && index >= oldCount) {
                cardEl.classList.add('card-drawn');
                setTimeout(() => cardEl.classList.remove('card-drawn'), 300);
            }

            // Click to select (pass event for Ctrl/Shift detection)
            cardEl.addEventListener('click', (e) => selectCard(index, e));

            // Double-click to select all cards of same rank
            cardEl.addEventListener('dblclick', (e) => {
                e.preventDefault();
                selectAllSameRank(index);
            });

            container.appendChild(cardEl);
        });

        // Show/hide Last Card button (show for 2-3 cards for multi-card finishing plays)
        const lastCardBtn = document.getElementById('lastcard-btn');
        if ((myPlayer.hand.length === 2 || myPlayer.hand.length === 3) && !myPlayer.last_card_called) {
            lastCardBtn.style.display = 'flex';
        } else {
            lastCardBtn.style.display = 'none';
        }
    }
}

// Get cards that can be added to current selection for a valid combo
function getComboEligibleCards(hand) {
    if (GameState.selectedCardIndices.length === 0) return [];

    const selectedCards = GameState.selectedCardIndices.map(i => hand[i]);
    const selectedRanks = selectedCards.map(c => c.rank);
    const eligible = [];

    hand.forEach((card, index) => {
        if (GameState.selectedCardIndices.includes(index)) return; // Already selected

        // Check if adding this card would make a valid combo
        const testIndices = [...GameState.selectedCardIndices, index];
        if (isValidCombo(hand, testIndices)) {
            eligible.push(index);
        }
    });

    return eligible;
}

function selectCard(index, event) {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand) return;

    const clickedCard = myPlayer.hand[index];

    // Double click to play (only if single card selected and playable)
    if (GameState.selectedCardIndex === index && !event?.ctrlKey && !event?.shiftKey) {
        if (GameState.selectedCardIndices.length === 1 && GameState.playableCards.includes(index)) {
            playSelectedCard();
        } else if (GameState.selectedCardIndices.length > 1 && canPlayCombo(myPlayer.hand)) {
            playSelectedCard();
        }
        return;
    }

    // Ctrl+click or Shift+click: Toggle multi-selection for combo plays
    if (event?.ctrlKey || event?.shiftKey) {
        if (GameState.selectedCardIndices.includes(index)) {
            // Remove from selection
            GameState.selectedCardIndices = GameState.selectedCardIndices.filter(i => i !== index);
            if (GameState.selectedCardIndices.length === 0) {
                GameState.selectedCardIndex = null;
            } else {
                GameState.selectedCardIndex = GameState.selectedCardIndices[0];
            }
        } else {
            // Add to selection - allow any card for combo plays
            const testIndices = [...GameState.selectedCardIndices, index];
            if (isValidCombo(myPlayer.hand, testIndices)) {
                GameState.selectedCardIndices.push(index);
                if (GameState.selectedCardIndex === null) {
                    GameState.selectedCardIndex = index;
                }
            } else {
                showNotification('Invalid combo! Use same rank, Jack+card, or Joker+2', 'error');
            }
        }
    } else {
        // Regular click - single selection
        GameState.selectedCardIndex = index;
        GameState.selectedCardIndices = [index];
    }

    updateMyHand(GameState.currentState.players);

    // Update play button state
    const playBtn = document.getElementById('play-btn');
    const canPlay = GameState.selectedCardIndices.length > 0 && canPlayCombo(myPlayer.hand);
    playBtn.disabled = !canPlay;

    SoundManager.play('click');
}

// Check if a combo selection is valid
function isValidCombo(hand, indices) {
    if (indices.length <= 1) return true;

    const cards = indices.map(i => hand[i]);
    const ranks = cards.map(c => c.rank);

    // Same rank - always valid
    if (ranks.every(r => r === ranks[0])) return true;

    // Jack combo - Jack + any cards (free throw allows playing more)
    if (ranks.includes('J')) return true;

    // Joker + 2 combo - stacking draw effects
    if (ranks.includes('Joker') && ranks.includes('2')) {
        // All cards must be Joker or 2
        if (ranks.every(r => r === 'Joker' || r === '2')) return true;
    }

    // Joker + Joker
    if (ranks.every(r => r === 'Joker')) return true;

    return false;
}

// Check if the current selection can be played
function canPlayCombo(hand) {
    if (GameState.selectedCardIndices.length === 0) return false;

    const cards = GameState.selectedCardIndices.map(i => hand[i]);
    const ranks = cards.map(c => c.rank);

    // Single card - must be playable
    if (GameState.selectedCardIndices.length === 1) {
        return GameState.playableCards.includes(GameState.selectedCardIndices[0]);
    }

    // Validate combo type
    if (!isValidCombo(hand, GameState.selectedCardIndices)) return false;

    // For combos, check if a valid starter card is playable
    // Jack combo - Jack can always be played (it's always in playable cards)
    if (ranks.includes('J')) {
        const jackIndices = GameState.selectedCardIndices.filter(i => hand[i].rank === 'J');
        if (jackIndices.some(i => GameState.playableCards.includes(i))) {
            return true;
        }
    }

    // Joker+2 combo - Joker can always be played
    if (ranks.includes('Joker')) {
        const jokerIndices = GameState.selectedCardIndices.filter(i => hand[i].rank === 'Joker');
        if (jokerIndices.some(i => GameState.playableCards.includes(i))) {
            return true;
        }
    }

    // Same rank combo - at least one card must be playable
    if (ranks.every(r => r === ranks[0])) {
        return GameState.selectedCardIndices.some(i => GameState.playableCards.includes(i));
    }

    // Default: at least one card must be playable
    return GameState.selectedCardIndices.some(i => GameState.playableCards.includes(i));
}

// Select all cards of the same rank as the clicked card
function selectAllSameRank(index) {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand) return;

    const clickedCard = myPlayer.hand[index];
    const sameRankIndices = [];

    myPlayer.hand.forEach((card, i) => {
        if (card.rank === clickedCard.rank) {
            sameRankIndices.push(i);
        }
    });

    GameState.selectedCardIndex = index;
    GameState.selectedCardIndices = sameRankIndices;

    updateMyHand(GameState.currentState.players);

    // Update play button state
    const playBtn = document.getElementById('play-btn');
    playBtn.disabled = !canPlayCombo(myPlayer.hand);

    SoundManager.play('click');
}

// Select combo cards (Jack + others, Joker + 2s)
function selectComboCards(startIndex) {
    const myPlayer = GameState.currentState?.players?.find(p => p.name === GameState.playerName);
    if (!myPlayer || !myPlayer.hand) return;

    const startCard = myPlayer.hand[startIndex];
    const comboIndices = [startIndex];

    // For Jack - add all Jacks and suggest adding other playable cards
    if (startCard.rank === 'J') {
        myPlayer.hand.forEach((card, i) => {
            if (i !== startIndex && card.rank === 'J') {
                comboIndices.push(i);
            }
        });
    }
    // For Joker - add all Jokers and 2s for maximum damage
    else if (startCard.rank === 'Joker') {
        myPlayer.hand.forEach((card, i) => {
            if (i !== startIndex && (card.rank === 'Joker' || card.rank === '2')) {
                comboIndices.push(i);
            }
        });
    }
    // For 2 - add all 2s and Jokers
    else if (startCard.rank === '2') {
        myPlayer.hand.forEach((card, i) => {
            if (i !== startIndex && (card.rank === '2' || card.rank === 'Joker')) {
                comboIndices.push(i);
            }
        });
    }
    // For other cards - add same rank
    else {
        myPlayer.hand.forEach((card, i) => {
            if (i !== startIndex && card.rank === startCard.rank) {
                comboIndices.push(i);
            }
        });
    }

    GameState.selectedCardIndex = startIndex;
    GameState.selectedCardIndices = comboIndices;

    updateMyHand(GameState.currentState.players);

    const playBtn = document.getElementById('play-btn');
    playBtn.disabled = !canPlayCombo(myPlayer.hand);

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

    // Get my player's hand for combo checking
    const myPlayer = state.players.find(p => p.name === GameState.playerName);

    // Update play button state based on selection (combo support)
    const playBtn = document.getElementById('play-btn');
    let canPlay = false;

    if (GameState.selectedCardIndices.length > 0 && myPlayer && myPlayer.hand) {
        // Check if at least one card is playable
        const hasPlayable = GameState.selectedCardIndices.some(i => GameState.playableCards.includes(i));
        // Check if combo is valid
        const validCombo = GameState.selectedCardIndices.length === 1 ||
                          isValidCombo(myPlayer.hand, GameState.selectedCardIndices);
        canPlay = hasPlayable && validCombo;
    }

    playBtn.disabled = !canPlay;

    // Update play button text to show card count and combo type
    const playBtnText = playBtn.querySelector('.btn-text');
    if (GameState.selectedCardIndices.length > 1 && myPlayer && myPlayer.hand) {
        const cards = GameState.selectedCardIndices.map(i => myPlayer.hand[i]);
        const ranks = cards.map(c => c.rank);

        // Determine combo type for display
        if (ranks.every(r => r === ranks[0])) {
            playBtnText.textContent = `Play ${GameState.selectedCardIndices.length}x ${ranks[0]}`;
        } else if (ranks.includes('J')) {
            playBtnText.textContent = 'Play Jack Combo';
        } else if (ranks.includes('Joker') && ranks.includes('2')) {
            playBtnText.textContent = 'Play Joker+2 Combo';
        } else {
            playBtnText.textContent = `Play ${GameState.selectedCardIndices.length} Cards`;
        }
    } else {
        playBtnText.textContent = 'Play Card';
    }

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

    // Handle Joker cards specially
    if (card.rank === 'Joker') {
        el.className = 'card joker';
        el.dataset.index = index;
        el.innerHTML = `
            <span class="rank">&#9733;</span>
            <span class="suit">JOKER</span>
        `;
    } else {
        el.className = `card ${card.suit}`;
        el.dataset.index = index;
        el.innerHTML = `
            <span class="rank">${card.rank}</span>
            <span class="suit">${SUIT_SYMBOLS[card.suit]}</span>
        `;
    }
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
