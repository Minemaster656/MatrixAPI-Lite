let ws = null;
let currentLocationId = null;
let currentCharacterId = null;
let currentCharacterName = null;
let currentUsername = null;
let selectedCharacterId = null;
let isOocMode = false;

function getToken() {
    return localStorage.getItem('access_token');
}

function authFetch(url, options = {}) {
    const token = getToken();
    if (!token) return Promise.reject('No token');
    options.headers = options.headers || {};
    options.headers['Authorization'] = 'Bearer ' + token;
    return fetch(url, options);
}

async function init() {
    const token = getToken();
    
    if (!token) {
        document.getElementById('auth-required').classList.remove('hidden');
        return;
    }
    
    const meResponse = await authFetch('/auth/me');
    if (!meResponse.ok) {
        localStorage.removeItem('access_token');
        document.getElementById('auth-required').classList.remove('hidden');
        return;
    }
    
    const meData = await meResponse.json();
    currentUsername = meData.username;
    
    const preselectedCharId = localStorage.getItem('selected_character_id');
    const preselectedCharName = localStorage.getItem('selected_character_name');
    
    const charsResponse = await authFetch('/api/characters/');
    if (!charsResponse.ok) {
        document.getElementById('no-characters').classList.remove('hidden');
        return;
    }
    
    const characters = await charsResponse.json();
    
    if (characters.length === 0) {
        document.getElementById('no-characters').classList.remove('hidden');
        return;
    }
    
    if (preselectedCharId && characters.find(c => c.id === parseInt(preselectedCharId))) {
        selectedCharacterId = parseInt(preselectedCharId);
        currentCharacterName = preselectedCharName;
    }
    
    renderCharacterSelect(characters);
    await loadLocations();
    
    document.getElementById('setup-panel').classList.remove('hidden');
}

function renderCharacterSelect(characters) {
    const container = document.getElementById('character-select');
    container.innerHTML = characters.map(char => `
        <div class="character-option ${char.id === selectedCharacterId ? 'selected' : ''}" 
             onclick="selectCharacter(${char.id}, '${escapeHtml(char.name)}')">
            <img src="${char.avatar_url}" alt="${char.name}">
            <div>
                <div class="text-white font-medium">${escapeHtml(char.name)}</div>
                <div class="text-gray-400 text-sm truncate">${escapeHtml(char.description) || 'Без описания'}</div>
            </div>
        </div>
    `).join('');
}

function selectCharacter(id, name) {
    selectedCharacterId = id;
    currentCharacterName = name;
    document.querySelectorAll('.character-option').forEach(el => {
        el.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');
}

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
    const locationId = parseInt(document.getElementById('location-select').value);
    
    if (!selectedCharacterId) {
        alert('Выберите персонажа');
        return;
    }
    
    if (!locationId) {
        alert('Выберите локацию');
        return;
    }

    currentLocationId = locationId;
    currentCharacterId = selectedCharacterId;
    ws = new WebSocket(`ws://${window.location.host}/ws/chat`);

    ws.onopen = async () => {
        const locResponse = await fetch(`/api/locations/${locationId}`);
        const locationData = await locResponse.json();
        
        document.body.style.backgroundImage = `url('${locationData.background_url}')`;
        document.body.style.backgroundSize = 'cover';
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundAttachment = 'fixed';
        
        document.getElementById('location-name').textContent = locationData.name;
        
        ws.send(JSON.stringify({ type: 'set_character', character_id: currentCharacterId, character_name: currentCharacterName, username: currentUsername }));
        ws.send(JSON.stringify({ type: 'set_location', location_id: locationId }));
        
        const locationsResponse = await fetch('/api/locations');
        const locations = await locationsResponse.json();
        renderLocationsList(locations, locationId);
        
        await populateCharacterDropdown();
        
        document.getElementById('setup-panel').classList.add('hidden');
        document.getElementById('chat-panel').classList.remove('hidden');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'message') {
            addMessage(data);
        } else if (data.type === 'private_message') {
            addMessage(data, true);
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
        } else if (data.type === 'ooc_set') {
            isOocMode = data.is_ooc;
            const checkbox = document.getElementById('ooc-toggle');
            if (checkbox) checkbox.checked = isOocMode;
            const label = document.getElementById('ooc-label');
            const charSelect = document.getElementById('character-select');
            if (isOocMode) {
                if (label) label.classList.remove('hidden');
                if (charSelect) {
                    charSelect.disabled = true;
                    charSelect.classList.add('opacity-50');
                }
            } else {
                if (label) label.classList.add('hidden');
                if (charSelect) {
                    charSelect.disabled = false;
                    charSelect.classList.remove('opacity-50');
                }
            }
        }
    };

    ws.onclose = () => {
        clearBackground();
        document.getElementById('chat-panel').classList.add('hidden');
        document.getElementById('setup-panel').classList.remove('hidden');
        document.getElementById('messages').innerHTML = '';
    };
}

async function populateCharacterDropdown() {
    const response = await authFetch('/api/characters/');
    const characters = await response.json();
    const select = document.getElementById('character-select');
    select.innerHTML = characters.map(char => 
        `<option value="${char.id}" data-name="${escapeHtml(char.name)}" ${char.id === currentCharacterId ? 'selected' : ''}>${escapeHtml(char.name)}</option>`
    ).join('');
    
    select.onchange = () => {
        const selected = select.options[select.selectedIndex];
        currentCharacterId = parseInt(selected.value);
        currentCharacterName = selected.dataset.name;
        if (!isOocMode) {
            ws.send(JSON.stringify({ type: 'set_character', character_id: currentCharacterId, character_name: currentCharacterName, username: currentUsername }));
        }
    };
}

function toggleOocMode() {
    const checkbox = document.getElementById('ooc-toggle');
    isOocMode = checkbox.checked;
    const label = document.getElementById('ooc-label');
    const oocUserSelect = document.getElementById('ooc-user-select');
    const charSelect = document.getElementById('character-select');
    
    if (isOocMode) {
        label.classList.remove('hidden');
        oocUserSelect.classList.remove('hidden');
        charSelect.disabled = true;
        charSelect.classList.add('opacity-50');
        ws.send(JSON.stringify({ type: 'set_ooc', is_ooc: true }));
    } else {
        label.classList.add('hidden');
        oocUserSelect.classList.add('hidden');
        charSelect.disabled = false;
        charSelect.classList.remove('opacity-50');
        const selected = charSelect.options[charSelect.selectedIndex];
        currentCharacterId = parseInt(selected.value);
        currentCharacterName = selected.dataset.name;
        ws.send(JSON.stringify({ type: 'set_ooc', is_ooc: false }));
        ws.send(JSON.stringify({ type: 'set_character', character_id: currentCharacterId, character_name: currentCharacterName, username: currentUsername }));
    }
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
        
        const groupedByUser = {};
        users.forEach(user => {
            const userKey = user.username;
            if (!groupedByUser[userKey]) {
                groupedByUser[userKey] = {
                    username: user.username,
                    characters: []
                };
            }
            groupedByUser[userKey].characters.push(user);
        });
        
        Object.values(groupedByUser).forEach(userGroup => {
            const isMe = userGroup.characters.some(c => c.character_name === currentCharacterName);
            const div = document.createElement('div');
            div.className = `mb-2 ${isMe ? 'bg-blue-900/30 rounded-lg p-2' : ''}`;
            
            const charDivs = userGroup.characters.map(char => {
                const charIsMe = char.character_name === currentCharacterName;
                const avatarUrl = char.avatar_url || '/static/assets/img/builtin_avatars/mtrx_avatar_default1.png';
                return `
                    <div class="flex items-center gap-2 py-1 ${charIsMe ? 'text-blue-300' : 'text-gray-300'}">
                        <img src="${avatarUrl}" class="w-5 h-5 rounded-full object-cover">
                        <span class="truncate text-sm">${escapeHtml(char.character_name || char.username)}</span>
                        ${charIsMe ? '<span class="text-xs text-blue-400">(вы)</span>' : ''}
                    </div>
                `;
            }).join('');
            
            div.innerHTML = `
                <div class="text-xs text-gray-500 px-2 mb-1">${escapeHtml(userGroup.username)}${isMe ? ' <span class="text-blue-400">(вы)</span>' : ''}</div>
                ${charDivs}
            `;
            list.appendChild(div);
        });
        
        updateMessageTargetDropdown(users);
        updateOocUserDropdown(users);
    };
    renderTo('online-users');
    renderTo('online-users-mobile', true);
}

function updateMessageTargetDropdown(users) {
    const targetSelect = document.getElementById('message-target');
    if (!targetSelect) return;
    
    const currentValue = targetSelect.value;
    targetSelect.innerHTML = '<option value="">Всем</option>';
    
    users.forEach(user => {
        if (user.username !== 'Anonymous' && user.character_name !== currentCharacterName) {
            const option = document.createElement('option');
            option.value = user.username;
            option.textContent = `${user.character_name || user.username} (${user.username})`;
            targetSelect.appendChild(option);
        }
    });
    
    if (currentValue) {
        targetSelect.value = currentValue;
    }
}

function updateOocUserDropdown(users) {
    const oocSelect = document.getElementById('ooc-user-select');
    if (!oocSelect) return;
    
    oocSelect.innerHTML = '<option value="">От своего имени</option>';
    
    users.forEach(user => {
        if (user.username !== 'Anonymous' && user.username !== currentUsername) {
            const option = document.createElement('option');
            option.value = user.username;
            option.textContent = user.username;
            oocSelect.appendChild(option);
        }
    });
    
    oocSelect.onchange = () => {
        const selectedOocUser = oocSelect.value;
        ws.send(JSON.stringify({ type: 'set_ooc', is_ooc: true, ooc_username: selectedOocUser || null }));
    };
}

function clearBackground() {
    document.body.style.backgroundImage = '';
    document.body.style.backgroundSize = '';
    document.body.style.backgroundPosition = '';
    document.body.style.backgroundAttachment = '';
    document.body.style.background = '';
}

function addMessage(data, isPrivate = false) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    const isOoc = data.is_ooc === true || data.is_ooc === 'true';
    div.className = 'message' + (isPrivate ? ' private-message' : '') + (isOoc ? ' ooc-message' : '');
    
    const time = new Date(data.created_at).toLocaleTimeString();
    const renderedText = marked.parse(data.text);
    const avatarUrl = data.avatar_url || '/static/assets/img/builtin_avatars/mtrx_avatar_default1.png';
    
    let authorDisplay = escapeHtml(data.character_name);
    if (isOoc && data.sender_username) {
        authorDisplay = `${escapeHtml(data.sender_username)} [OOC]`;
    } else if (isOoc) {
        authorDisplay = `${escapeHtml(data.character_name)} [OOC]`;
    }
    
    div.innerHTML = `
        <img src="${avatarUrl}" alt="${escapeHtml(data.character_name)}" class="message-avatar">
        <div class="message-content">
            <div class="author">${authorDisplay}${isPrivate ? ' <span class="text-purple-400">(личное)</span>' : ''}</div>
            <div class="content">${renderedText}</div>
            <div class="time">${time}</div>
        </div>
    `;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendMessage() {
    const messageInput = document.getElementById('message');
    const text = messageInput.value.trim();
    const targetSelect = document.getElementById('message-target');
    const targetUsername = targetSelect.value;
    
    if (text && ws && ws.readyState === WebSocket.OPEN) {
        if (targetUsername) {
            ws.send(JSON.stringify({ type: 'private_message', text: text, target_username: targetUsername }));
        } else {
            ws.send(JSON.stringify({ type: 'message', text: text }));
        }
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

init();
