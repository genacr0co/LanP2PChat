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
            addMessage(packet.data);
            return;
        }

        if (packet.type === "direct_chat") {
            addDirectChat(packet.data);
            return;
        }

        if (packet.type === "direct_message") {
            const msg = packet.data;
            if (!msg || !msg.chat_id) return;

            const isMe = msg.username === username;
            const isCurrent =
                activeTab === "dm" &&
                msg.chat_id === currentDirectChatId;

            if (!isMe && !notified.has(msg.message_id)) {
                notified.add(msg.message_id);
                playNotifySound();

                if (!isCurrent) {
                    const oldCount = directUnreadCounts.get(msg.chat_id) || 0;
                    directUnreadCounts.set(msg.chat_id, oldCount + 1);
                    renderRooms();
                }
            }

            if (isCurrent) {
                addDirectMessage(msg);
            }

            return;
        }

    };

    ws.onclose = () => {
        statusEl.textContent = "Переподключение...";
        setTimeout(connectUiSocket, 1000);
    };

    ws.onerror = () => ws.close();
}