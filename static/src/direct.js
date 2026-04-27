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


function addDirectChat(dm, shouldRender = true) {
    if (!dm || !dm.chat_id) {
        return false;
    }

    const oldChat = directChats.get(dm.chat_id);

    const mergedChat = {
        ...oldChat,
        ...dm,
    };

    const oldJson = oldChat ? JSON.stringify(oldChat) : "";
    const newJson = JSON.stringify(mergedChat);

    if (oldJson === newJson) {
        return false;
    }

    directChats.set(dm.chat_id, mergedChat);

    if (shouldRender) {
        renderRooms();
    }

    return true;
}


async function loadDirectChats() {
    try {
        const res = await fetch("/api/direct/chats");
        const list = await res.json();

        let changed = false;

        list.forEach((dm) => {
            const didChange = addDirectChat(dm, false);

            if (didChange) {
                changed = true;
            }
        });

        if (changed) {
            renderRooms();
        }
    } catch {}
}


async function selectDirectChat(dm) {
    if (!dm) {
        return;
    }

    const actualDm = directChats.get(dm.chat_id) || dm;

    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = actualDm.chat_id;

    roomTitle.textContent = actualDm.peer_name;

    rendered.clear();
    chat.innerHTML = "";

    form.style.display = "block";
    restoreDraftForCurrentChat();

    try {
        const res = await fetch(
            `/api/direct/messages?chat_id=${encodeURIComponent(actualDm.chat_id)}`
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