async function openDirectChat(targetNodeId, targetUsername) {
    if (!targetNodeId) return;
    if (targetUsername === username) return;

    try {
        const res = await fetch("/api/direct/start", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                target_node_id: targetNodeId,
                target_username: targetUsername,
            }),
        });

        const data = await res.json();

        if (data.ok && data.chat) {
            activeTab = "dm";
            updateTabs();

            addDirectChat(data.chat);
            await selectDirectChat(data.chat);
        }
    } catch {
        alert("Не удалось открыть личный чат");
    }
}


function addDirectChat(dm) {
    if (!dm || !dm.chat_id) return;

    directChats.set(dm.chat_id, dm);
    renderRooms();
}


async function loadDirectChats() {
    try {
        const res = await fetch("/api/direct/chats");
        const list = await res.json();

        list.forEach(addDirectChat);
    } catch {}
}


async function selectDirectChat(dm) {
    if (!dm) return;

    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = dm.chat_id;

    roomTitle.textContent = dm.peer_name;
    directUnreadCounts.set(dm.chat_id, 0);

    typingUsers.clear();
    renderTypingStatus();

    rendered.clear();
    chat.innerHTML = "";

    try {
        const res = await fetch(
            `/api/direct/messages?chat_id=${encodeURIComponent(dm.chat_id)}`
        );

        const list = await res.json();
        list.forEach(addDirectMessage);
    } catch {}

    updateTabs();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}