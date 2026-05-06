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

    closeDirectSettingsModal();

    const room = rooms.get(currentRoomId) || rooms.get("general");

    if (room) {
        await selectRoom(room);
        return;
    }

    rendered.clear();
    chat.innerHTML = "";
    roomTitle.textContent = "Комнаты";
    form.style.display = "none";

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


function roomNeedsPassword(room) {
    return !!(
        room &&
        room.has_password === true &&
        room.is_password_unlocked !== true
    );
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

    closeGroupSettingsModal();
    closeDirectSettingsModal();

    roomTitle.textContent = actualRoom.name;

    rendered.clear();
    chat.innerHTML = "";

    if (actualRoom.is_joined === false) {
        form.style.display = "none";
        input.value = "";

        showJoinScreen(actualRoom);
        updateTabs();

        if (roomNeedsPassword(actualRoom)) {
            openJoinGroupPasswordModal(actualRoom);
        }

        return;
    }

    form.style.display = "flex";
    restoreDraftForCurrentChat();

    updateTabs();

    await loadHistory();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}


function showJoinScreen(room) {
    rendered.clear();

    const isProtected = roomNeedsPassword(room);

    const description = isProtected
        ? "Эта группа защищена паролем. Нажмите кнопку и введите пароль, чтобы вступить."
        : "Вы ещё не вступили в эту группу.";

    const buttonText = isProtected
        ? "Ввести пароль и вступить"
        : "Вступить в группу";

    chat.innerHTML = `
        <div class="join-screen">
            <h2>${escapeHtml(room.name)}</h2>
            <p>${escapeHtml(description)}</p>
            <button id="joinSelectedGroupBtn" type="button">${escapeHtml(buttonText)}</button>
        </div>
    `;

    const btn = document.getElementById("joinSelectedGroupBtn");

    if (btn) {
        btn.onclick = async () => {
            if (roomNeedsPassword(room)) {
                openJoinGroupPasswordModal(room);
                return;
            }

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

    if (roomPasswordInput) {
        roomPasswordInput.value = "";
    }

    roomModal.classList.add("show");
    roomNameInput.focus();
};


cancelRoomBtn.onclick = () => {
    roomModal.classList.remove("show");
};


saveRoomBtn.onclick = async () => {
    const name = roomNameInput.value.trim();
    const password = roomPasswordInput ? roomPasswordInput.value : "";

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
                password,
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


if (roomPasswordInput) {
    roomPasswordInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            saveRoomBtn.click();
        }
    });
}


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

            const lockMark = room.has_password === true
                ? `<span class="room-lock-mark" title="Группа защищена паролем">🔒</span>`
                : "";

            const joinMark = room.is_joined === false
                ? `<span class="join-mark">Вступить</span>`
                : "";

            item.innerHTML = `
                <div class="room-name">${lockMark}${escapeHtml(room.name)}</div>

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
            if (dm.is_deleted === true) {
                continue;
            }

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


function setJoinGroupModalError(message) {
    if (joinGroupModalError) {
        joinGroupModalError.textContent = message || "";
    }
}


function openJoinGroupPasswordModal(room) {
    if (!room || !room.room_id) {
        return;
    }

    pendingJoinRoomId = room.room_id;

    if (joinGroupModalTitle) {
        joinGroupModalTitle.textContent = `Вступить в «${room.name}»`;
    }

    if (joinGroupModalText) {
        joinGroupModalText.textContent = "Эта группа защищена паролем. Введите пароль группы, чтобы вступить.";
    }

    if (joinGroupModalPasswordInput) {
        joinGroupModalPasswordInput.value = "";
    }

    setJoinGroupModalError("");

    if (joinGroupModal) {
        joinGroupModal.classList.add("show");
    }

    setTimeout(() => {
        if (joinGroupModalPasswordInput) {
            joinGroupModalPasswordInput.focus();
        }
    }, 50);
}


function closeJoinGroupPasswordModal() {
    pendingJoinRoomId = null;

    if (joinGroupModal) {
        joinGroupModal.classList.remove("show");
    }

    if (joinGroupModalPasswordInput) {
        joinGroupModalPasswordInput.value = "";
    }

    setJoinGroupModalError("");
}


async function submitJoinGroupPasswordModal() {
    if (!pendingJoinRoomId) {
        closeJoinGroupPasswordModal();
        return;
    }

    const room = rooms.get(pendingJoinRoomId);

    if (!room) {
        closeJoinGroupPasswordModal();
        return;
    }

    const password = joinGroupModalPasswordInput
        ? joinGroupModalPasswordInput.value
        : "";

    if (!password.trim()) {
        setJoinGroupModalError("Введите пароль группы.");

        if (joinGroupModalPasswordInput) {
            joinGroupModalPasswordInput.focus();
        }

        return;
    }

    await joinGroup(room, password, {
        errorTarget: "modal",
    });
}


async function joinGroup(group, passwordOverride = null, options = {}) {
    if (!group || !group.room_id) {
        return;
    }

    const useModalErrors = options.errorTarget === "modal";
    const passwordInput = document.getElementById("joinGroupPasswordInput");
    const passwordError = document.getElementById("joinGroupPasswordError");

    const password = passwordOverride !== null
        ? passwordOverride
        : (passwordInput ? passwordInput.value : "");

    if (passwordError) {
        passwordError.textContent = "";
    }

    if (useModalErrors) {
        setJoinGroupModalError("");
    }

    if (roomNeedsPassword(group) && !password.trim()) {
        if (useModalErrors) {
            setJoinGroupModalError("Введите пароль группы.");

            if (joinGroupModalPasswordInput) {
                joinGroupModalPasswordInput.focus();
            }

            return;
        }

        if (passwordError) {
            passwordError.textContent = "Введите пароль группы.";
        }

        if (passwordInput) {
            passwordInput.focus();
        }

        openJoinGroupPasswordModal(group);
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
                password,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "password_required") {
                if (useModalErrors) {
                    setJoinGroupModalError("Введите пароль группы.");

                    if (joinGroupModalPasswordInput) {
                        joinGroupModalPasswordInput.focus();
                    }

                    return;
                }

                if (passwordError) {
                    passwordError.textContent = "Введите пароль группы.";
                }

                if (passwordInput) {
                    passwordInput.focus();
                }

                openJoinGroupPasswordModal(group);
                return;
            }

            if (data.error === "wrong_password") {
                if (useModalErrors) {
                    setJoinGroupModalError("Неверный пароль.");

                    if (joinGroupModalPasswordInput) {
                        joinGroupModalPasswordInput.focus();
                        joinGroupModalPasswordInput.select();
                    }

                    return;
                }

                if (passwordError) {
                    passwordError.textContent = "Неверный пароль.";
                } else {
                    alert("Неверный пароль группы");
                }

                if (passwordInput) {
                    passwordInput.focus();
                    passwordInput.select();
                }

                openJoinGroupPasswordModal(group);
                return;
            }

            alert("Не удалось вступить в группу");
            return;
        }

        if (data.room) {
            addRoom(data.room);
            closeJoinGroupPasswordModal();
            await selectRoom(data.room);
            return;
        }

        const fallbackRoom = {
            ...group,
            is_joined: true,
            is_password_unlocked: true,
        };

        addRoom(fallbackRoom);
        closeJoinGroupPasswordModal();
        await selectRoom(fallbackRoom);
    } catch {
        if (useModalErrors) {
            setJoinGroupModalError("Ошибка вступления в группу.");
            return;
        }

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
    hideGroupPasswordForm();

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
    hideGroupPasswordForm();
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

    if (groupPasswordBtn) {
        groupPasswordBtn.style.display = canEdit ? "inline-flex" : "none";
        groupPasswordBtn.textContent = room && room.has_password
            ? "🔑 Изменить пароль группы"
            : "🔑 Поставить пароль группы";
    }

    if (groupRenameForm) {
        groupRenameForm.classList.remove("show");
    }

    if (groupPasswordForm) {
        groupPasswordForm.classList.remove("show");
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

    hideGroupPasswordForm();

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


function showGroupPasswordForm() {
    const room = getCurrentGroupRoom();

    if (!canEditRoom(room)) {
        return;
    }

    hideGroupRenameForm();

    if (groupPasswordInput) {
        groupPasswordInput.value = "";
        groupPasswordInput.placeholder = room.has_password
            ? "Новый пароль или пусто, чтобы убрать"
            : "Пароль группы";
    }

    if (groupPasswordHint) {
        groupPasswordHint.textContent = room.has_password
            ? "Оставьте поле пустым и нажмите сохранить, чтобы убрать пароль. После смены пароля участники введут его заново."
            : "После установки пароля новые участники должны будут ввести его при вступлении.";
    }

    if (groupPasswordForm) {
        groupPasswordForm.classList.add("show");
    }

    setTimeout(() => {
        if (groupPasswordInput) {
            groupPasswordInput.focus();
        }
    }, 50);
}


function hideGroupPasswordForm() {
    if (groupPasswordForm) {
        groupPasswordForm.classList.remove("show");
    }

    if (groupPasswordInput) {
        groupPasswordInput.value = "";
    }
}


async function saveGroupPassword() {
    const room = getCurrentGroupRoom();

    if (!canEditRoom(room)) {
        return;
    }

    const password = groupPasswordInput ? groupPasswordInput.value : "";

    if (!password.trim() && room.has_password !== true) {
        alert("Введите пароль или отмените действие.");
        if (groupPasswordInput) {
            groupPasswordInput.focus();
        }
        return;
    }

    if (!password.trim() && room.has_password === true) {
        const confirmed = confirm(
            `Убрать пароль у группы "${room.name}"?\n\n` +
            "После этого новые участники смогут вступать без пароля."
        );

        if (!confirmed) {
            return;
        }
    }

    try {
        const res = await fetch("/api/groups/password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                room_id: room.room_id,
                password,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_creator") {
                alert("Менять пароль может только создатель группы.");
                return;
            }

            if (data.error === "cannot_change_general_password") {
                alert("На общий чат нельзя поставить пароль.");
                return;
            }

            alert("Не удалось изменить пароль группы");
            return;
        }

        addRoom(data.room);
        hideGroupPasswordForm();
        updateOwnerActions(data.room);
        renderRooms();
    } catch {
        alert("Ошибка изменения пароля группы");
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


if (groupPasswordBtn) {
    groupPasswordBtn.onclick = () => {
        showGroupPasswordForm();
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


if (saveGroupPasswordBtn) {
    saveGroupPasswordBtn.onclick = saveGroupPassword;
}


if (cancelGroupPasswordBtn) {
    cancelGroupPasswordBtn.onclick = () => {
        hideGroupPasswordForm();
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


if (groupPasswordInput) {
    groupPasswordInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            saveGroupPassword();
        }

        if (e.key === "Escape") {
            e.preventDefault();
            hideGroupPasswordForm();
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


if (joinGroupModalSaveBtn) {
    joinGroupModalSaveBtn.onclick = () => {
        submitJoinGroupPasswordModal();
    };
}


if (joinGroupModalCancelBtn) {
    joinGroupModalCancelBtn.onclick = () => {
        closeJoinGroupPasswordModal();
    };
}


if (joinGroupModalPasswordInput) {
    joinGroupModalPasswordInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            submitJoinGroupPasswordModal();
        }

        if (e.key === "Escape") {
            e.preventDefault();
            closeJoinGroupPasswordModal();
        }
    });
}


if (joinGroupModal) {
    joinGroupModal.onclick = (e) => {
        if (e.target === joinGroupModal) {
            closeJoinGroupPasswordModal();
        }
    };
}
