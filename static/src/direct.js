async function openDirectChat(targetNodeId, targetUsername) {
    if (!targetNodeId) {
        return;
    }

    if (targetNodeId === myNodeId) {
        return;
    }

    if (targetUsername === username) {
        return;
    }

    try {
        const res = await fetch("/api/direct/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                target_node_id: targetNodeId,
                target_username: targetUsername,
            }),
        });

        const data = await res.json();

        if (data.ok && data.chat) {
            activeTab = "dm";

            addDirectChat(data.chat);
            await selectDirectChat(data.chat);

            updateTabs();
        }
    } catch {
        alert("Не удалось открыть личный чат");
    }
}


function addDirectChat(dm) {
    if (!dm || !dm.chat_id) {
        return;
    }

    const oldChat = directChats.get(dm.chat_id);

    directChats.set(dm.chat_id, {
        ...oldChat,
        ...dm,
    });

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
    if (!dm) {
        return;
    }

    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = dm.chat_id;

    roomTitle.textContent = dm.peer_name;

    rendered.clear();
    chat.innerHTML = "";

    form.style.display = "block";

    try {
        const res = await fetch(
            `/api/direct/messages?chat_id=${encodeURIComponent(dm.chat_id)}`
        );

        const list = await res.json();

        rendered.clear();
        chat.innerHTML = "";

        list.forEach(addDirectMessage);
    } catch {}

    updateTabs();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}