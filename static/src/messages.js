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

    // Не показываем сообщения групп, куда пользователь не вступил
    if (room.is_joined === false) {
        return;
    }

    const isMe = msg.username === username || msg.sender_id === myNodeId;
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
    row.className = "message-row" + (isMe ? " me" : "");

    row.innerHTML = `
        <div class="bubble">
            <div class="name clickable-name"
                 data-sender-id="${escapeHtml(msg.sender_id)}"
                 data-username="${escapeHtml(msg.username)}">
                ${escapeHtml(msg.username)}
            </div>
            <div class="text">${escapeHtml(msg.message)}</div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    chat.appendChild(row);

    const nameEl = row.querySelector(".clickable-name");

    if (nameEl) {
        nameEl.onclick = () => {
            if (nameEl.dataset.senderId !== "system") {
                openDirectChat(
                    nameEl.dataset.senderId,
                    nameEl.dataset.username
                );
            }
        };
    }

    if (typeof applySmileys === "function") {
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

    const isMe = msg.username === username || msg.sender_id === myNodeId;

    const row = document.createElement("div");
    row.className = "message-row" + (isMe ? " me" : "");

    row.innerHTML = `
        <div class="bubble">
            <div class="name">${escapeHtml(msg.username)}</div>
            <div class="text">${escapeHtml(msg.message)}</div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    chat.appendChild(row);

    if (typeof applySmileys === "function") {
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

    // До вступления историю не грузим
    if (room.is_joined === false) {
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