function updateTabs() {
    groupsTab.classList.toggle("active", activeTab === "group");
    dmTab.classList.toggle("active", activeTab === "dm");

    createRoomBtn.style.display = activeTab === "group" ? "block" : "none";

    if (groupSearchPanel) {
        groupSearchPanel.style.display = "none";
    }

    renderRooms();
}

groupsTab.onclick = () => {
    activeTab = "group";
    currentDirectChatId = null;

    const general = rooms.get(currentRoomId) || rooms.get("general");
    if (general) selectRoom(general);

    updateTabs();
};

dmTab.onclick = () => {
    activeTab = "dm";
    currentRoomId = null;
    rendered.clear();
    chat.innerHTML = "";
    roomTitle.textContent = "Личные сообщения";
    typingUsers.clear();
    renderTypingStatus();
    updateTabs();
};

function addRoom(room) {
    if (!room || !room.room_id) return;
    if (room.room_id.startsWith("dm_") || room.room_id.startsWith("direct_")) return;

    rooms.set(room.room_id, room);
    renderRooms();
}

async function selectRoom(room) {
    if (!room) return;

    activeTab = "group";
    currentDirectChatId = null;
    currentRoomId = room.room_id;

    roomTitle.textContent = room.name;
    unreadCounts.set(room.room_id, 0);

    typingUsers.clear();
    renderTypingStatus();

    rendered.clear();
    chat.innerHTML = "";

    if (room.is_joined === false) {
        showJoinScreen(room);
        updateTabs();
        return;
    }

    await loadHistory();
    updateTabs();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}

function showJoinScreen(room) {
    const lock = room.has_password ? "🔒 " : "";

    chat.innerHTML = `
        <div class="join-screen">
            <h2>${lock}${escapeHtml(room.name)}</h2>
            <p>Вы ещё не участник этой группы</p>
            <button id="joinSelectedGroupBtn" type="button">Вступить</button>
        </div>
    `;

    const btn = document.getElementById("joinSelectedGroupBtn");

    if (btn) {
        btn.onclick = async () => {
            await joinGroup(room);
        };
    }

    if (typeof applySmileys === "function") {
        applySmileys(chat);
    }
}

async function loadRooms() {
    const res = await fetch("/api/rooms");
    const list = await res.json();

    list.forEach(addRoom);

    if (!rooms.has(currentRoomId)) {
        currentRoomId = "general";
    }

    renderRooms();
}

createRoomBtn.onclick = () => {
    roomNameInput.value = "";
    roomPasswordInput.value = "";
    if (roomUniqueInput) roomUniqueInput.value = "";

    roomModal.classList.add("show");
    roomNameInput.focus();
};

cancelRoomBtn.onclick = () => {
    roomModal.classList.remove("show");
};

saveRoomBtn.onclick = async () => {
    const name = roomNameInput.value.trim();
    const password = roomPasswordInput.value.trim();
    const unique_name = roomUniqueInput ? roomUniqueInput.value.trim() : "";

    if (!name) return;

    const res = await fetch("/api/rooms", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name,
            password,
            unique_name,
        }),
    });

    const data = await res.json();

    if (!data.ok) return alert("Ошибка");

    addRoom(data.room);
    unlockedRooms.add(data.room.room_id);

    roomModal.classList.remove("show");
    await selectRoom(data.room);
};

roomNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") saveRoomBtn.click();
});

if (roomUniqueInput) {
    roomUniqueInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") saveRoomBtn.click();
    });
}

roomPasswordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") saveRoomBtn.click();
});

function renderRooms() {
    roomsList.innerHTML = "";

    if (activeTab === "group") {
        for (const room of rooms.values()) {
            const count = unreadCounts.get(room.room_id) || 0;

            const item = document.createElement("div");
            item.className =
                "room-item" +
                (room.room_id === currentRoomId ? " active" : "") +
                (count > 0 ? " unread" : "") +
                (room.is_joined === false ? " not-joined" : "");

            const lock = room.has_password ? "🔒 " : "";
            const joinMark = room.is_joined === false ? `<span class="join-mark">Вступить</span>` : "";
            const badge = count > 0 ? `<span class="unread-badge">${count}</span>` : "";

            item.innerHTML = `
                <div class="room-name">${lock}${escapeHtml(room.name)}</div>
                ${badge || joinMark}
            `;

            item.onclick = () => selectRoom(room);
            roomsList.appendChild(item);
        }
    }

    if (activeTab === "dm") {
        for (const dm of directChats.values()) {
            const count = directUnreadCounts.get(dm.chat_id) || 0;
            const badge = count > 0 ? `<span class="unread-badge">${count}</span>` : "";

            const item = document.createElement("div");
            item.className =
                "room-item" +
                (dm.chat_id === currentDirectChatId ? " active" : "") +
                (count > 0 ? " unread" : "");

            item.innerHTML = `
                <div class="room-name">${escapeHtml(dm.peer_name)}</div>
                ${badge}
            `;

            item.onclick = () => selectDirectChat(dm);
            roomsList.appendChild(item);
        }
    }

    if (typeof applySmileys === "function") {
        applySmileys(roomsList);
    }
}

async function joinGroup(group) {
    let password = "";

    if (group.has_password) {
        password = prompt(`Пароль для "${group.name}"`);
        if (password === null) return;
    }

    const res = await fetch("/api/groups/join", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            room_id: group.room_id,
            password,
            created_by: group.created_by,
        }),
    });

    const data = await res.json();

    if (!data.ok) {
        if (data.error === "wrong_password") {
            alert("Неверный пароль");
        } else {
            alert("Не удалось вступить в группу");
        }
        return;
    }

    addRoom(data.room);
    await selectRoom(data.room);
}