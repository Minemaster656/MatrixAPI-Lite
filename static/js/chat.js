let ws = null;
let currentLocationId = null;
let currentCharacterName = null;

async function loadLocations() {
    const response = await fetch('/api/locations');
    const locations = await response.json();
    const select = document.getElementById('location-select');
    locations.forEach(loc => {
        const option = document.createElement('option');
        option.value = loc.id;
        option.textContent = loc.name;
        select.appendChild(option);
    });
}

function joinChat() {
    const characterName = document.getElementById('character-name').value.trim();
    const locationId = parseInt(document.getElementById('location-select').value);
    const locationName = document.getElementById('location-select').options[document.getElementById('location-select').selectedIndex].text;
    
    if (!characterName || !locationId) {
        alert('Введите имя персонажа и выберите локацию');
        return;
    }

    currentLocationId = locationId;
    ws = new WebSocket(`ws://${window.location.host}/ws/chat`);

    ws.onopen = async () => {
        const locResponse = await fetch(`/api/locations/${locationId}`);
        const locationData = await locResponse.json();
        
        document.body.style.backgroundImage = `url('${locationData.background_url}')`;
        document.body.style.backgroundSize = 'cover';
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundAttachment = 'fixed';
        
        document.getElementById('location-name').textContent = locationData.name;
        
        ws.send(JSON.stringify({ type: 'set_character', character_name: characterName }));
        ws.send(JSON.stringify({ type: 'set_location', location_id: locationId }));
        
        const locationsResponse = await fetch('/api/locations');
        const locations = await locationsResponse.json();
        renderLocationsList(locations, locationId);
        
        currentCharacterName = characterName;
        
        document.getElementById('setup-panel').classList.add('hidden');
        document.getElementById('chat-panel').classList.remove('hidden');
        document.getElementById('character-name-display').value = characterName;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'message') {
            addMessage(data);
        } else if (data.type === 'location_set') {
            document.getElementById('messages').innerHTML = '';
            currentLocationId = data.location_id;
            if (data.location_name) {
                document.body.style.backgroundImage = `url('${data.background_url}')`;
                document.body.style.backgroundSize = 'cover';
                document.body.style.backgroundPosition = 'center';
                document.body.style.backgroundAttachment = 'fixed';
                document.getElementById('location-name').textContent = data.location_name;
            }
            data.messages.forEach(addMessage);
            document.getElementById('messages').style.opacity = '1';
        } else if (data.type === 'locations_list') {
            renderLocationsList(data.locations, currentLocationId);
        } else if (data.type === 'online_users') {
            renderOnlineUsers(data.users);
        } else if (data.type === 'error') {
            alert(data.message);
        }
    };

    ws.onclose = () => {
        clearBackground();
        document.getElementById('chat-panel').classList.add('hidden');
        document.getElementById('setup-panel').classList.remove('hidden');
        document.getElementById('messages').innerHTML = '';
    };
}

function leaveChat() {
    if (ws) {
        ws.close();
    }
    clearBackground();
    document.getElementById('messages').innerHTML = '';
    document.getElementById('locations-list').innerHTML = '';
    document.getElementById('online-users').innerHTML = '';
    document.getElementById('locations-list-mobile').innerHTML = '';
    document.getElementById('online-users-mobile').innerHTML = '';
    currentCharacterName = null;
}

function toggleSidebar(panel) {
    const panelEl = document.getElementById('panel-' + panel);
    const overlayEl = document.getElementById('overlay-' + panel);
    
    if (panelEl.classList.contains('hidden')) {
        panelEl.classList.remove('hidden');
        setTimeout(() => {
            panelEl.classList.remove('-translate-x-full', 'translate-x-full');
            overlayEl.classList.remove('hidden');
        }, 10);
    } else {
        panelEl.classList.add('-translate-x-full', 'translate-x-full');
        overlayEl.classList.add('hidden');
        setTimeout(() => {
            panelEl.classList.add('hidden');
        }, 200);
    }
}

function renderLocationsList(locations, currentId) {
    const renderTo = (containerId, isMobile = false) => {
        const list = document.getElementById(containerId);
        if (!list) return;
        list.innerHTML = '';
        locations.forEach(loc => {
            const div = document.createElement('div');
            const isActive = loc.id === currentId;
            div.className = `p-2 rounded cursor-pointer flex items-center gap-2 text-sm ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`;
            div.innerHTML = `<span class="truncate">${escapeHtml(loc.name)}</span>`;
            if (!isActive) {
                div.onclick = () => {
                    if (isMobile) toggleSidebar('locations');
                    switchLocation(loc.id);
                };
            }
            list.appendChild(div);
        });
    };
    renderTo('locations-list');
    renderTo('locations-list-mobile', true);
}

function switchLocation(locationId) {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.style.opacity = '0';
    setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'set_location', location_id: locationId }));
        }
    }, 200);
}

function renderOnlineUsers(users) {
    const renderTo = (containerId, isMobile = false) => {
        const list = document.getElementById(containerId);
        if (!list) return;
        list.innerHTML = '';
        if (users.length === 0) {
            list.innerHTML = '<div class="text-gray-500 text-sm px-2">Нет онлайн</div>';
            return;
        }
        users.forEach(user => {
            const div = document.createElement('div');
            const isMe = user.character_name === currentCharacterName;
            div.className = `p-2 rounded text-sm flex items-center gap-2 ${isMe ? 'bg-blue-900 text-blue-200' : 'text-gray-300 hover:bg-gray-700'}`;
            div.innerHTML = `<span class="w-2 h-2 bg-green-500 rounded-full flex-shrink-0"></span><span class="truncate">${escapeHtml(user.character_name || user.username)}${isMe ? ' (вы)' : ''}</span>`;
            list.appendChild(div);
        });
    };
    renderTo('online-users');
    renderTo('online-users-mobile', true);
}

function clearBackground() {
    document.body.style.backgroundImage = '';
    document.body.style.backgroundSize = '';
    document.body.style.backgroundPosition = '';
    document.body.style.backgroundAttachment = '';
    document.body.style.background = '';
}

function addMessage(data) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message';
    
    const time = new Date(data.created_at).toLocaleTimeString();
    const renderedText = marked.parse(data.text);
    
    div.innerHTML = `
        <div class="author">${escapeHtml(data.character_name)}</div>
        <div class="content">${renderedText}</div>
        <div class="time">${time}</div>
    `;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendMessage() {
    const messageInput = document.getElementById('message');
    const text = messageInput.value.trim();
    
    if (text && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'message', text: text }));
        messageInput.value = '';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById('message')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

loadLocations();
