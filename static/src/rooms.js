function updateTabs() {
    groupsTab.classList.toggle("active", activeTab === "group");
    dmTab.classList.toggle("active", activeTab === "dm");

    createRoomBtn.style.display = activeTab === "group" ? "block" : "none";

    renderRooms();
}

groupsTab.onclick = () => {
    activeTab = "group";
    currentDirectChatId = null;

    const room = rooms.get(currentRoomId) || rooms.get("general");

    if (room) {
        selectRoom(room);
    } else {
        chat.innerHTML = "";
        roomTitle.textContent = "Комнаты";
        form.style.display = "none";
    }

    updateTabs();
};

dmTab.onclick = () => {
    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = null;

    rendered.clear();
    chat.innerHTML = "";
    roomTitle.textContent = "Личные сообщения";
    form.style.display = "none";

    updateTabs();
};


function addRoom(room) {
    if (!room || !room.room_id) {
        return;
    }

    if (room.room_id.startsWith("dm_") || room.room_id.startsWith("direct_")) {
        return;
    }

    const oldRoom = rooms.get(room.room_id);

    rooms.set(room.room_id, {
        ...oldRoom,
        ...room,
    });

    renderRooms();
}


async function selectRoom(room) {
    if (!room) {
        return;
    }

    activeTab = "group";
    currentDirectChatId = null;
    currentRoomId = room.room_id;

    roomTitle.textContent = room.name;

    rendered.clear();
    chat.innerHTML = "";

    if (room.is_joined === false) {
        form.style.display = "none";
        showJoinScreen(room);
        updateTabs();
        return;
    }

    form.style.display = "block";

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

    if (roomUniqueInput) {
        roomUniqueInput.value = "";
    }

    roomModal.classList.add("show");
    roomNameInput.focus();
};


cancelRoomBtn.onclick = () => {
    roomModal.classList.remove("show");
};


saveRoomBtn.onclick = async () => {
    const name = roomNameInput.value.trim();
    const unique_name = roomUniqueInput ? roomUniqueInput.value.trim() : "";

    if (!name) {
        return;
    }

    const res = await fetch("/api/rooms", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            name,
            unique_name,
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
};


roomNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        saveRoomBtn.click();
    }
});


if (roomUniqueInput) {
    roomUniqueInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            saveRoomBtn.click();
        }
    });
}


function renderRooms() {
    roomsList.innerHTML = "";

    if (activeTab === "group") {
        for (const room of rooms.values()) {
            const item = document.createElement("div");

            item.className =
                "room-item" +
                (room.room_id === currentRoomId ? " active" : "") +
                (room.is_joined === false ? " not-joined" : "");

            const joinMark = room.is_joined === false
                ? `<span class="join-mark">Вступить</span>`
                : "";

            item.innerHTML = `
                <div class="room-name">${escapeHtml(room.name)}</div>
                ${joinMark}
            `;

            item.onclick = () => selectRoom(room);
            roomsList.appendChild(item);
        }
    }

    if (activeTab === "dm") {
        for (const dm of directChats.values()) {
            const item = document.createElement("div");

            item.className =
                "room-item" +
                (dm.chat_id === currentDirectChatId ? " active" : "");

            item.innerHTML = `
                <div class="room-name">${escapeHtml(dm.peer_name)}</div>
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
}