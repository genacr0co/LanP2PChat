function connectUiSocket() {
    const ws = new WebSocket(`ws://${location.host}/ui/ws`);

    ws.onopen = () => {
        statusEl.textContent = "Онлайн";
    };

    ws.onmessage = (e) => {
        let packet = null;

        try {
            packet = JSON.parse(e.data);
        } catch {
            return;
        }

        if (packet.type === "room" || packet.type === "group") {
            handleIncomingGroup(packet.data);
            return;
        }

        if (packet.type === "message" || packet.type === "group_message") {
            handleIncomingGroupMessage(packet.data);
            return;
        }

        if (packet.type === "group_message_deleted") {
            handleIncomingGroupMessageDeleted(packet.data);
            return;
        }

        if (packet.type === "direct_chat") {
            addDirectChat(packet.data);
            return;
        }

        if (packet.type === "direct_chat_deleted") {
            handleDirectChatDeleted(packet.data);
            return;
        }

        if (packet.type === "direct_message") {
            handleIncomingDirectMessage(packet.data);
            return;
        }

        if (packet.type === "direct_message_deleted") {
            handleIncomingDirectMessageDeleted(packet.data);
            return;
        }
    };

    ws.onclose = () => {
        statusEl.textContent = "Переподключение...";
        setTimeout(connectUiSocket, 1000);
    };

    ws.onerror = () => {
        ws.close();
    };
}


function handleIncomingGroup(group) {
    if (!group || !group.room_id) {
        return;
    }

    addRoom(group);

    if (group.is_deleted === true && currentRoomId === group.room_id) {
        const generalRoom = rooms.get("general");

        if (generalRoom) {
            selectRoom(generalRoom);
        } else {
            currentRoomId = "general";
            rendered.clear();
            chat.innerHTML = "";
            roomTitle.textContent = "Общий чат";
            form.style.display = "none";
            renderRooms();
        }
    }
}


function handleIncomingGroupMessage(msg) {
    if (!msg || !msg.message_id || !msg.room_id) {
        return;
    }

    if (msg.is_deleted === true) {
        handleIncomingGroupMessageDeleted(msg);
        return;
    }

    const room = rooms.get(msg.room_id);

    if (!room || room.is_joined === false || room.is_deleted === true) {
        return;
    }

    const isMe = msg.sender_id === myNodeId;

    const isCurrent =
        activeTab === "group" &&
        msg.room_id === currentRoomId;

    if (!isMe && !notified.has(msg.message_id)) {
        notified.add(msg.message_id);
        playNotifySound("group", msg.room_id);
    }

    if (isCurrent) {
        addMessage(msg);
    }
}


function handleIncomingGroupMessageDeleted(msg) {
    if (!msg || !msg.message_id || !msg.room_id) {
        return;
    }

    const room = rooms.get(msg.room_id);

    if (!room || room.is_joined === false || room.is_deleted === true) {
        return;
    }

    const isCurrent =
        activeTab === "group" &&
        msg.room_id === currentRoomId;

    if (!isCurrent) {
        return;
    }

    handleGroupMessageDeleted(msg);
}


function handleIncomingDirectMessage(msg) {
    if (!msg || !msg.message_id || !msg.chat_id) {
        return;
    }

    if (msg.is_deleted === true) {
        handleIncomingDirectMessageDeleted(msg);
        return;
    }

    const isMe = msg.sender_id === myNodeId;

    const isCurrent =
        activeTab === "dm" &&
        msg.chat_id === currentDirectChatId;

    if (!isMe && !notified.has(msg.message_id)) {
        notified.add(msg.message_id);
        playNotifySound("dm", msg.chat_id);
    }

    if (isCurrent) {
        addDirectMessage(msg);
    }
}


function handleIncomingDirectMessageDeleted(msg) {
    if (!msg || !msg.message_id || !msg.chat_id) {
        return;
    }

    const isCurrent =
        activeTab === "dm" &&
        msg.chat_id === currentDirectChatId;

    if (!isCurrent) {
        return;
    }

    handleDirectMessageDeleted(msg);
}