function isOwnMessage(msg) {
    if (!msg || !myNodeId) {
        return false;
    }

    return msg.sender_id === myNodeId;
}


function isDeletedMessage(msg) {
    return !!(msg && msg.is_deleted === true);
}


function getDeletedMessageText() {
    return "▒▒▒▒▒▒▒▒▒▒▒▒";
}


function setMessageText(row, text) {
    const textEl = row.querySelector(".text");

    if (!textEl) {
        return;
    }

    textEl.textContent = text || "";
}


function ensureMessageContextMenu() {
    let menu = document.getElementById("messageContextMenu");

    if (menu) {
        return menu;
    }

    menu = document.createElement("div");
    menu.id = "messageContextMenu";
    menu.className = "message-context-menu";
    menu.innerHTML = `
        <button id="copyMessageMenuBtn" type="button">Копировать сообщение</button>
        <button id="deleteMessageMenuBtn" type="button" class="danger">Удалить сообщение</button>
    `;

    document.body.appendChild(menu);

    return menu;
}


function hideMessageContextMenu() {
    const menu = document.getElementById("messageContextMenu");

    if (menu) {
        menu.classList.remove("show");
        menu.style.left = "0px";
        menu.style.top = "0px";
    }
}


function showMessageContextMenu(e, msg, type, row) {
    e.preventDefault();
    e.stopPropagation();

    if (!msg || !row) {
        return;
    }

    if (isDeletedMessage(msg)) {
        hideMessageContextMenu();
        return;
    }

    const menu = ensureMessageContextMenu();

    const copyBtn = document.getElementById("copyMessageMenuBtn");
    const deleteBtn = document.getElementById("deleteMessageMenuBtn");

    const canDelete =
        isOwnMessage(msg) &&
        !isDeletedMessage(msg) &&
        (type === "group" || type === "direct");

    if (copyBtn) {
        copyBtn.onclick = async (clickEvent) => {
            clickEvent.stopPropagation();
            await copyMessageText(msg);
            hideMessageContextMenu();
        };
    }

    if (deleteBtn) {
        deleteBtn.style.display = canDelete ? "flex" : "none";

        deleteBtn.onclick = async (clickEvent) => {
            clickEvent.stopPropagation();

            if (type === "group") {
                await deleteGroupMessage(msg);
            }

            if (type === "direct") {
                await deleteDirectMessage(msg);
            }

            hideMessageContextMenu();
        };
    }

    const menuWidth = 230;
    const menuHeight = canDelete ? 94 : 50;

    let x = e.clientX;
    let y = e.clientY;

    if (x + menuWidth > window.innerWidth) {
        x = window.innerWidth - menuWidth - 10;
    }

    if (y + menuHeight > window.innerHeight) {
        y = window.innerHeight - menuHeight - 10;
    }

    menu.style.left = `${Math.max(10, x)}px`;
    menu.style.top = `${Math.max(10, y)}px`;
    menu.classList.add("show");
}


async function copyMessageText(msg) {
    if (!msg || isDeletedMessage(msg)) {
        return;
    }

    const text = msg.message || "";

    if (!text.trim()) {
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
    } catch {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "-9999px";

        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            document.execCommand("copy");
        } catch {}

        textarea.remove();
    }
}


async function deleteGroupMessage(msg) {
    if (!msg || !msg.message_id || !msg.room_id) {
        return;
    }

    if (!isOwnMessage(msg) || isDeletedMessage(msg)) {
        return;
    }

    const confirmed = confirm("Удалить это сообщение?");

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/messages/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message_id: msg.message_id,
                room_id: msg.room_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_sender") {
                alert("Удалить можно только своё сообщение.");
                return;
            }

            if (data.error === "message_not_found") {
                alert("Сообщение не найдено.");
                return;
            }

            alert("Не удалось удалить сообщение.");
            return;
        }

        if (data.message) {
            handleGroupMessageDeleted(data.message);
        }
    } catch {
        alert("Ошибка удаления сообщения.");
    }
}


async function deleteDirectMessage(msg) {
    if (!msg || !msg.message_id || !msg.chat_id) {
        return;
    }

    if (!isOwnMessage(msg) || isDeletedMessage(msg)) {
        return;
    }

    const dm = getCurrentDirectChat();

    if (!dm || !dm.peer_id) {
        alert("Не удалось определить собеседника.");
        return;
    }

    const confirmed = confirm("Удалить это сообщение?");

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/direct/messages/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message_id: msg.message_id,
                chat_id: msg.chat_id,
                target_node_id: dm.peer_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_sender") {
                alert("Удалить можно только своё сообщение.");
                return;
            }

            if (data.error === "message_not_found") {
                alert("Сообщение не найдено.");
                return;
            }

            alert("Не удалось удалить сообщение.");
            return;
        }

        if (data.message) {
            handleDirectMessageDeleted(data.message);
        }
    } catch {
        alert("Ошибка удаления сообщения.");
    }
}


function applyDeletedMessageState(row, msg) {
    if (!row || !msg) {
        return;
    }

    const bubble = row.querySelector(".bubble");
    const textEl = row.querySelector(".text");

    row.classList.add("deleted-message-row");
    row.dataset.isDeleted = "true";

    if (bubble) {
        bubble.classList.add("deleted-message-bubble");
    }

    if (textEl) {
        textEl.textContent = msg.message || getDeletedMessageText();
        textEl.classList.add("deleted-message-text");
    }

    row.oncontextmenu = (e) => {
        e.preventDefault();
        e.stopPropagation();
        hideMessageContextMenu();
    };
}


function handleGroupMessageDeleted(msg) {
    if (!msg || !msg.message_id) {
        return;
    }

    const row = chat.querySelector(
        `.message-row[data-message-id="${CSS.escape(msg.message_id)}"]`
    );

    if (!row) {
        return;
    }

    const currentMsg = {
        ...msg,
        is_deleted: true,
        message: msg.message || getDeletedMessageText(),
    };

    applyDeletedMessageState(row, currentMsg);
}


function handleDirectMessageDeleted(msg) {
    if (!msg || !msg.message_id) {
        return;
    }

    const row = chat.querySelector(
        `.message-row[data-message-id="${CSS.escape(msg.message_id)}"]`
    );

    if (!row) {
        return;
    }

    const currentMsg = {
        ...msg,
        is_deleted: true,
        message: msg.message || getDeletedMessageText(),
    };

    applyDeletedMessageState(row, currentMsg);
}


function addMessage(msg) {
    if (!msg) {
        return;
    }

    if (!msg.room_id) {
        msg.room_id = "general";
    }

    if (msg.room_id.startsWith("dm_") || msg.room_id.startsWith("direct_")) {
        return;
    }

    const room = rooms.get(msg.room_id);

    if (!room) {
        return;
    }

    if (room.is_joined === false || room.is_deleted === true) {
        return;
    }

    const isMe = isOwnMessage(msg);
    const deleted = isDeletedMessage(msg);

    const isCurrent =
        activeTab === "group" &&
        msg.room_id === currentRoomId;

    if (!isCurrent) {
        return;
    }

    if (rendered.has(msg.message_id)) {
        return;
    }

    rendered.add(msg.message_id);

    const row = document.createElement("div");
    row.className =
        "message-row" +
        (isMe ? " me" : "") +
        (deleted ? " deleted-message-row" : "");

    row.dataset.messageId = msg.message_id;
    row.dataset.roomId = msg.room_id;
    row.dataset.senderId = msg.sender_id || "";
    row.dataset.isDeleted = deleted ? "true" : "false";

    const messageText = deleted
        ? (msg.message || getDeletedMessageText())
        : msg.message;

    row.innerHTML = `
        <div class="bubble${deleted ? " deleted-message-bubble" : ""}">
            <div class="name clickable-name"
                 data-sender-id="${escapeHtml(msg.sender_id)}"
                 data-username="${escapeHtml(msg.username)}">
                ${escapeHtml(msg.username)}
            </div>
            <div class="text${deleted ? " deleted-message-text" : ""}"></div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    setMessageText(row, messageText);

    chat.appendChild(row);

    const nameEl = row.querySelector(".clickable-name");

    if (nameEl && !deleted) {
        nameEl.onclick = () => {
            if (nameEl.dataset.senderId !== "system") {
                openDirectChat(
                    nameEl.dataset.senderId,
                    nameEl.dataset.username
                );
            }
        };
    }

    if (!deleted) {
        row.oncontextmenu = (e) => {
            showMessageContextMenu(e, msg, "group", row);
        };
    } else {
        applyDeletedMessageState(row, msg);
    }

    if (!deleted && typeof applySmileys === "function") {
        applySmileys(row);
    }

    chat.scrollTop = chat.scrollHeight;
}


function addDirectMessage(msg) {
    if (!msg) {
        return;
    }

    if (!msg.chat_id) {
        return;
    }

    if (rendered.has(msg.message_id)) {
        return;
    }

    rendered.add(msg.message_id);

    const isMe = isOwnMessage(msg);
    const deleted = isDeletedMessage(msg);

    const row = document.createElement("div");
    row.className =
        "message-row" +
        (isMe ? " me" : "") +
        (deleted ? " deleted-message-row" : "");

    row.dataset.messageId = msg.message_id;
    row.dataset.chatId = msg.chat_id;
    row.dataset.senderId = msg.sender_id || "";
    row.dataset.isDeleted = deleted ? "true" : "false";

    const messageText = deleted
        ? (msg.message || getDeletedMessageText())
        : msg.message;

    row.innerHTML = `
        <div class="bubble${deleted ? " deleted-message-bubble" : ""}">
            <div class="name">${escapeHtml(msg.username)}</div>
            <div class="text${deleted ? " deleted-message-text" : ""}"></div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    setMessageText(row, messageText);

    chat.appendChild(row);

    if (!deleted) {
        row.oncontextmenu = (e) => {
            showMessageContextMenu(e, msg, "direct", row);
        };
    } else {
        applyDeletedMessageState(row, msg);
    }

    if (!deleted && typeof applySmileys === "function") {
        applySmileys(row);
    }

    chat.scrollTop = chat.scrollHeight;
}


async function loadHistory() {
    if (!currentRoomId) {
        return;
    }

    const room = rooms.get(currentRoomId);

    if (!room) {
        return;
    }

    if (room.is_joined === false || room.is_deleted === true) {
        return;
    }

    const res = await fetch(
        `/api/messages?room_id=${encodeURIComponent(currentRoomId)}`
    );

    const list = await res.json();

    rendered.clear();
    chat.innerHTML = "";

    list.forEach(addMessage);
}


document.addEventListener("pointerdown", (e) => {
    const menu = document.getElementById("messageContextMenu");

    if (!menu || !menu.classList.contains("show")) {
        return;
    }

    if (menu.contains(e.target)) {
        return;
    }

    hideMessageContextMenu();
});


window.addEventListener("blur", () => {
    hideMessageContextMenu();
});