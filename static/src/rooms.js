function updateTabs() {
    groupsTab.classList.toggle("active", activeTab === "group");
    dmTab.classList.toggle("active", activeTab === "dm");

    createRoomBtn.style.display = activeTab === "group" ? "block" : "none";

    renderRooms();
}


groupsTab.onclick = async () => {
    activeTab = "group";
    currentDirectChatId = null;

    const room = rooms.get(currentRoomId) || rooms.get("general");

    if (room) {
        await selectRoom(room);
    } else {
        rendered.clear();
        chat.innerHTML = "";
        roomTitle.textContent = "Комнаты";
        form.style.display = "none";
    }

    updateTabs();
};


dmTab.onclick = async () => {
    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = null;

    rendered.clear();
    chat.innerHTML = "";
    roomTitle.textContent = "Личные сообщения";
    form.style.display = "none";

    await loadDirectChats();

    updateTabs();
};


function addRoom(room, shouldRender = true, options = {}) {
    if (!room || !room.room_id) {
        return false;
    }

    if (room.room_id.startsWith("dm_") || room.room_id.startsWith("direct_")) {
        return false;
    }

    const oldRoom = rooms.get(room.room_id);

    const mergedRoom = {
        ...oldRoom,
        ...room,
    };

    const allowJoinedDowngrade = options.allowJoinedDowngrade === true;

    if (
        !allowJoinedDowngrade &&
        oldRoom &&
        oldRoom.is_joined === true &&
        room.is_joined === false
    ) {
        mergedRoom.is_joined = true;
    }

    if (
        oldRoom &&
        oldRoom.is_creator === true &&
        room.is_creator === false
    ) {
        mergedRoom.is_creator = true;
    }

    const oldJson = oldRoom ? JSON.stringify(oldRoom) : "";
    const newJson = JSON.stringify(mergedRoom);

    if (oldJson === newJson) {
        return false;
    }

    rooms.set(room.room_id, mergedRoom);

    if (shouldRender) {
        renderRooms();
    }

    return true;
}


async function selectRoom(room) {
    if (!room) {
        return;
    }

    const actualRoom = rooms.get(room.room_id) || room;

    activeTab = "group";
    currentDirectChatId = null;
    currentRoomId = actualRoom.room_id;

    roomTitle.textContent = actualRoom.name;

    rendered.clear();
    chat.innerHTML = "";

    if (actualRoom.is_joined === false) {
        form.style.display = "none";
        input.value = "";
        showJoinScreen(actualRoom);
        updateTabs();
        return;
    }

    form.style.display = "block";
    restoreDraftForCurrentChat();

    await loadHistory();

    updateTabs();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}


function showJoinScreen(room) {
    chat.innerHTML = `
        <div class="join-screen">
            <h2>${escapeHtml(room.name)}</h2>
            <p>Вы ещё не вступили в эту группу.</p>
            <button id="joinSelectedGroupBtn" type="button">Вступить в группу</button>
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
    try {
        const res = await fetch("/api/rooms");
        const list = await res.json();

        let changed = false;

        list.forEach((room) => {
            const didChange = addRoom(room, false);

            if (didChange) {
                changed = true;
            }
        });

        if (!rooms.has(currentRoomId)) {
            currentRoomId = "general";
        }

        if (changed) {
            renderRooms();
        }
    } catch {}
}


createRoomBtn.onclick = () => {
    roomNameInput.value = "";

    roomModal.classList.add("show");
    roomNameInput.focus();
};


cancelRoomBtn.onclick = () => {
    roomModal.classList.remove("show");
};


saveRoomBtn.onclick = async () => {
    const name = roomNameInput.value.trim();

    if (!name) {
        roomNameInput.focus();
        return;
    }

    try {
        const res = await fetch("/api/rooms", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                name,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            alert("Не удалось создать группу");
            return;
        }

        addRoom(data.room);

        roomModal.classList.remove("show");

        await selectRoom(data.room);
    } catch {
        alert("Ошибка создания группы");
    }
};


roomNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        saveRoomBtn.click();
    }
});


function renderRooms() {
    roomsList.innerHTML = "";

    if (activeTab === "group") {
        for (const room of rooms.values()) {
            const item = document.createElement("div");

            item.className =
                "room-item" +
                (room.room_id === currentRoomId ? " active" : "") +
                (room.is_joined === false ? " not-joined" : "");

            const muted = isChatMuted("group", room.room_id);

            const joinMark = room.is_joined === false
                ? `<span class="join-mark">Вступить</span>`
                : "";

            const muteIcon = muted ? "🔇" : "🔔";
            const muteTitle = muted ? "Включить звук" : "Отключить звук";

            item.innerHTML = `
                <div class="room-name">${escapeHtml(room.name)}</div>

                <div class="room-actions">
                    ${joinMark}
                    <button class="mute-btn" type="button" title="${muteTitle}">
                        ${muteIcon}
                    </button>
                </div>
            `;

            item.onclick = () => selectRoom(room);

            const muteBtn = item.querySelector(".mute-btn");

            if (muteBtn) {
                muteBtn.onclick = (e) => {
                    e.stopPropagation();
                    toggleChatMute("group", room.room_id);
                };
            }

            roomsList.appendChild(item);
        }
    }

    if (activeTab === "dm") {
        for (const dm of directChats.values()) {
            const item = document.createElement("div");

            item.className =
                "room-item" +
                (dm.chat_id === currentDirectChatId ? " active" : "");

            const muted = isChatMuted("dm", dm.chat_id);
            const muteIcon = muted ? "🔇" : "🔔";
            const muteTitle = muted ? "Включить звук" : "Отключить звук";

            item.innerHTML = `
                <div class="room-name">${escapeHtml(dm.peer_name)}</div>

                <div class="room-actions">
                    <button class="mute-btn" type="button" title="${muteTitle}">
                        ${muteIcon}
                    </button>
                </div>
            `;

            item.onclick = () => selectDirectChat(dm);

            const muteBtn = item.querySelector(".mute-btn");

            if (muteBtn) {
                muteBtn.onclick = (e) => {
                    e.stopPropagation();
                    toggleChatMute("dm", dm.chat_id);
                };
            }

            roomsList.appendChild(item);
        }
    }

    if (typeof applySmileys === "function") {
        applySmileys(roomsList);
    }
}


async function joinGroup(group) {
    if (!group || !group.room_id) {
        return;
    }

    try {
        const res = await fetch("/api/groups/join", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                room_id: group.room_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            alert("Не удалось вступить в группу");
            return;
        }

        addRoom(data.room);

        await selectRoom(data.room);
    } catch {
        alert("Ошибка вступления в группу");
    }
}