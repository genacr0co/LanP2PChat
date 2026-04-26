function connectUiSocket() {
    const ws = new WebSocket(`ws://${location.host}/ui/ws`);

    ws.onopen = () => {
        statusEl.textContent = "Онлайн";
    };

    ws.onmessage = (e) => {
        const packet = JSON.parse(e.data);

        if (packet.type === "room" || packet.type === "group") {
            addRoom(packet.data);
            return;
        }

        if (packet.type === "message") {
            handleIncomingGroupMessage(packet.data);
            return;
        }

        if (packet.type === "direct_chat") {
            addDirectChat(packet.data);
            return;
        }

        if (packet.type === "direct_message") {
            handleIncomingDirectMessage(packet.data);
            return;
        }

        // typing/search/unread больше не используем
    };

    ws.onclose = () => {
        statusEl.textContent = "Переподключение...";
        setTimeout(connectUiSocket, 1000);
    };

    ws.onerror = () => {
        ws.close();
    };
}


function handleIncomingGroupMessage(msg) {
    if (!msg || !msg.message_id || !msg.room_id) {
        return;
    }

    const room = rooms.get(msg.room_id);

    // Если мы не вступили в группу, не показываем и не уведомляем.
    if (!room || room.is_joined === false) {
        return;
    }

    const isMe = msg.username === username || msg.sender_id === myNodeId;
    const isCurrent =
        activeTab === "group" &&
        msg.room_id === currentRoomId;

    if (!isMe && !notified.has(msg.message_id)) {
        notified.add(msg.message_id);
        playNotifySound();
    }

    if (isCurrent) {
        addMessage(msg);
    }
}


function handleIncomingDirectMessage(msg) {
    if (!msg || !msg.message_id || !msg.chat_id) {
        return;
    }

    const isMe = msg.username === username || msg.sender_id === myNodeId;
    const isCurrent =
        activeTab === "dm" &&
        msg.chat_id === currentDirectChatId;

    if (!isMe && !notified.has(msg.message_id)) {
        notified.add(msg.message_id);
        playNotifySound();
    }

    if (isCurrent) {
        addDirectMessage(msg);
    }
}