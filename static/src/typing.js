// typing.js

function renderTypingStatus() {
    if (!typingStatus) return;

    if (activeTab !== "group") {
        typingStatus.textContent = "";
        return;
    }

    const names = [];

    for (const [, item] of typingUsers.entries()) {
        if (
            Date.now() - item.time < 3000 &&
            item.room_id === currentRoomId
        ) {
            names.push(item.username);
        }
    }

    typingStatus.textContent =
        names.length === 1
            ? `${names[0]} печатает...`
            : names.length > 1
                ? `${names.join(", ")} печатают...`
                : "";
}


function handleTyping(data) {
    if (!data || data.username === username) return;

    if (!data.room_id) return;

    // только для текущей комнаты
    if (data.room_id !== currentRoomId) return;

    if (data.is_typing) {
        typingUsers.set(data.sender_id, {
            username: data.username,
            room_id: data.room_id,
            time: Date.now(),
        });
    } else {
        typingUsers.delete(data.sender_id);
    }

    renderTypingStatus();
}


async function sendTypingSignal(isTyping = true) {
    if (activeTab !== "group" || !currentRoomId) return;

    try {
        await fetch("/api/typing", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                room_id: currentRoomId,
                is_typing: isTyping,
            }),
        });
    } catch {
        // игнор
    }
}