function updateTabs() {
    groupsTab.classList.toggle("active", activeTab === "group");
    dmTab.classList.toggle("active", activeTab === "dm");

    createRoomBtn.style.display = activeTab === "group" ? "flex" : "none";

    updateGroupSettingsButton();
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

    closeGroupSettingsModal();

    await loadDirectChats();

    updateTabs();
};


function isDeletedRoom(room) {
    return !!(room && room.is_deleted === true);
}


function canEditRoom(room) {
    if (!room) {
        return false;
    }

    if (room.room_id === "general") {
        return false;
    }

    if (room.is_deleted === true) {
        return false;
    }

    return room.is_creator === true;
}


function canDeleteRoom(room) {
    return canEditRoom(room);
}


function canLeaveRoom(room) {
    if (!room) {
        return false;
    }

    if (room.room_id === "general") {
        return false;
    }

    if (room.is_deleted === true) {
        return false;
    }

    return room.is_joined === true;
}


function getCurrentGroupRoom() {
    if (activeTab !== "group") {
        return null;
    }

    if (!currentRoomId) {
        return null;
    }

    return rooms.get(currentRoomId) || null;
}


function updateGroupSettingsButton() {
    if (!groupSettingsBtn) {
        return;
    }

    if (activeTab === "group") {
        const room = getCurrentGroupRoom();

        if (!room || room.is_deleted === true) {
            groupSettingsBtn.style.display = "none";
            return;
        }

        groupSettingsBtn.style.display = "inline-flex";
        return;
    }

    if (activeTab === "dm") {
        const dm = getCurrentDirectChat();

        if (!dm || dm.is_deleted === true) {
            groupSettingsBtn.style.display = "none";
            return;
        }

        groupSettingsBtn.style.display = "inline-flex";
        return;
    }

    groupSettingsBtn.style.display = "none";
}


function removeRoomFromUi(roomId) {
    if (!roomId) {
        return;
    }

    rooms.delete(roomId);

    if (currentRoomId === roomId) {
        currentRoomId = "general";

        const generalRoom = rooms.get("general");

        if (generalRoom) {
            selectRoom(generalRoom);
        } else {
            rendered.clear();
            chat.innerHTML = "";
            roomTitle.textContent = "Общий чат";
            form.style.display = "none";
        }
    }

    closeGroupSettingsModal();
    renderRooms();
    updateGroupSettingsButton();
}


function addRoom(room, shouldRender = true, options = {}) {
    if (!room || !room.room_id) {
        return false;
    }

    if (room.room_id.startsWith("dm_") || room.room_id.startsWith("direct_")) {
        return false;
    }

    if (room.is_deleted === true) {
        const existed = rooms.has(room.room_id);

        rooms.delete(room.room_id);

        if (currentRoomId === room.room_id) {
            currentRoomId = "general";

            const generalRoom = rooms.get("general");

            if (generalRoom) {
                selectRoom(generalRoom);
            } else {
                rendered.clear();
                chat.innerHTML = "";
                roomTitle.textContent = "Общий чат";
                form.style.display = "none";
            }
        }

        closeGroupSettingsModal();

        if (shouldRender) {
            renderRooms();
        }

        updateGroupSettingsButton();

        return existed;
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

    updateGroupSettingsButton();

    return true;
}


async function selectRoom(room) {
    if (!room) {
        return;
    }

    if (isDeletedRoom(room)) {
        removeRoomFromUi(room.room_id);
        return;
    }

    const actualRoom = rooms.get(room.room_id) || room;

    if (isDeletedRoom(actualRoom)) {
        removeRoomFromUi(actualRoom.room_id);
        return;
    }

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

    form.style.display = "flex";
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

        for (const [roomId, room] of rooms.entries()) {
            if (roomId !== "general" && room.is_deleted === true) {
                rooms.delete(roomId);
                changed = true;
            }
        }

        if (!rooms.has(currentRoomId)) {
            currentRoomId = "general";
        }

        if (changed) {
            renderRooms();
        }

        updateGroupSettingsButton();
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
            if (room.is_deleted === true) {
                continue;
            }

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

                <div class="room-actions">
                    ${joinMark}
                </div>
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


async function leaveSelectedRoom(room) {
    if (!canLeaveRoom(room)) {
        return;
    }

    const confirmed = confirm(
        `Выйти из группы "${room.name}"?\n\n` +
        "Группа останется в списке, и вы сможете вступить снова."
    );

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/groups/leave", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                room_id: room.room_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "cannot_leave_general") {
                alert("Из общего чата выйти нельзя.");
                return;
            }

            if (data.error === "group_not_found") {
                alert("Группа не найдена.");
                return;
            }

            alert("Не удалось выйти из группы.");
            return;
        }

        if (data.room) {
            addRoom(data.room, true, {
                allowJoinedDowngrade: true,
            });

            closeGroupSettingsModal();

            if (currentRoomId === data.room.room_id) {
                await selectRoom(data.room);
            }
        }
    } catch {
        alert("Ошибка выхода из группы.");
    }
}


function openGroupSettingsModal() {
    const room = getCurrentGroupRoom();

    if (!room) {
        return;
    }

    if (groupSettingsTitle) {
        groupSettingsTitle.textContent = room.name;
    }

    updateGroupMuteButton(room);
    updateGroupLeaveButton(room);
    updateOwnerActions(room);
    hideGroupRenameForm();

    if (groupMembersList) {
        groupMembersList.textContent = "Список участников появится позже.";
    }

    groupSettingsModal.classList.add("show");
}


function closeGroupSettingsModal() {
    if (groupSettingsModal) {
        groupSettingsModal.classList.remove("show");
    }

    hideGroupRenameForm();
}


function updateGroupMuteButton(room) {
    if (!groupMuteBtn || !room) {
        return;
    }

    const muted = isChatMuted("group", room.room_id);

    groupMuteBtn.textContent = muted
        ? "🔔 Включить звук"
        : "🔕 Отключить звук";
}


function updateGroupLeaveButton(room) {
    if (!groupLeaveBtn) {
        return;
    }

    groupLeaveBtn.style.display = canLeaveRoom(room)
        ? "inline-flex"
        : "none";
}


function updateOwnerActions(room) {
    const canEdit = canEditRoom(room);

    if (groupRenameBtn) {
        groupRenameBtn.style.display = canEdit ? "inline-flex" : "none";
    }

    if (groupRenameForm) {
        groupRenameForm.classList.remove("show");
    }

    if (groupDeleteBtn) {
        groupDeleteBtn.style.display = canEdit ? "inline-flex" : "none";
    }
}


async function deleteSelectedRoom(room) {
    if (!canDeleteRoom(room)) {
        return;
    }

    const confirmed = confirm(
        `Удалить группу "${room.name}"?\n\n` +
        "Она исчезнет у вас и у других участников после синхронизации."
    );

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/groups/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                room_id: room.room_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_creator") {
                alert("Удалить группу может только её создатель.");
                return;
            }

            if (data.error === "cannot_delete_general") {
                alert("Общий чат удалить нельзя.");
                return;
            }

            alert("Не удалось удалить группу");
            return;
        }

        removeRoomFromUi(room.room_id);
    } catch {
        alert("Ошибка удаления группы");
    }
}


function showGroupRenameForm() {
    const room = getCurrentGroupRoom();

    if (!canEditRoom(room)) {
        return;
    }

    if (groupRenameInput) {
        groupRenameInput.value = room.name || "";
    }

    if (groupRenameForm) {
        groupRenameForm.classList.add("show");
    }

    setTimeout(() => {
        if (groupRenameInput) {
            groupRenameInput.focus();
            groupRenameInput.select();
        }
    }, 50);
}


function hideGroupRenameForm() {
    if (groupRenameForm) {
        groupRenameForm.classList.remove("show");
    }

    if (groupRenameInput) {
        groupRenameInput.value = "";
    }
}


async function saveGroupRename() {
    const room = getCurrentGroupRoom();

    if (!canEditRoom(room)) {
        return;
    }

    const newName = (groupRenameInput.value || "").trim();

    if (!newName) {
        groupRenameInput.focus();
        return;
    }

    if (newName === room.name) {
        hideGroupRenameForm();
        return;
    }

    try {
        const res = await fetch("/api/groups/rename", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                room_id: room.room_id,
                name: newName,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_creator") {
                alert("Переименовать группу может только её создатель.");
                return;
            }

            if (data.error === "cannot_rename_general") {
                alert("Общий чат переименовать нельзя.");
                return;
            }

            if (data.error === "empty_name") {
                alert("Название группы не может быть пустым.");
                return;
            }

            alert("Не удалось переименовать группу");
            return;
        }

        addRoom(data.room);

        currentRoomId = data.room.room_id;
        roomTitle.textContent = data.room.name;

        if (groupSettingsTitle) {
            groupSettingsTitle.textContent = data.room.name;
        }

        hideGroupRenameForm();
        renderRooms();
    } catch {
        alert("Ошибка переименования группы");
    }
}


if (groupSettingsBtn) {
    groupSettingsBtn.onclick = () => {
        if (activeTab === "group") {
            openGroupSettingsModal();
            return;
        }

        if (activeTab === "dm") {
            openDirectSettingsModal();
        }
    };
}


if (closeGroupSettingsBtn) {
    closeGroupSettingsBtn.onclick = () => {
        closeGroupSettingsModal();
    };
}


if (groupMuteBtn) {
    groupMuteBtn.onclick = () => {
        const room = getCurrentGroupRoom();

        if (!room) {
            return;
        }

        toggleChatMute("group", room.room_id);
        updateGroupMuteButton(room);
    };
}


if (groupLeaveBtn) {
    groupLeaveBtn.onclick = async () => {
        const room = getCurrentGroupRoom();

        if (!room) {
            return;
        }

        await leaveSelectedRoom(room);
    };
}


if (groupRenameBtn) {
    groupRenameBtn.onclick = () => {
        showGroupRenameForm();
    };
}


if (saveGroupRenameBtn) {
    saveGroupRenameBtn.onclick = saveGroupRename;
}


if (cancelGroupRenameBtn) {
    cancelGroupRenameBtn.onclick = () => {
        hideGroupRenameForm();
    };
}


if (groupRenameInput) {
    groupRenameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            saveGroupRename();
        }

        if (e.key === "Escape") {
            e.preventDefault();
            hideGroupRenameForm();
        }
    });
}


if (groupDeleteBtn) {
    groupDeleteBtn.onclick = async () => {
        const room = getCurrentGroupRoom();

        if (!room) {
            return;
        }

        await deleteSelectedRoom(room);
    };
}


if (groupSettingsModal) {
    groupSettingsModal.onclick = (e) => {
        if (e.target === groupSettingsModal) {
            closeGroupSettingsModal();
        }
    };
}