// =========================
// DRAFTS
// =========================

function getCurrentDraftKey() {
    if (activeTab === "group" && currentRoomId) {
        return `group:${currentRoomId}`;
    }

    if (activeTab === "dm" && currentDirectChatId) {
        return `dm:${currentDirectChatId}`;
    }

    return null;
}


function saveCurrentDraft() {
    const key = getCurrentDraftKey();

    if (!key) {
        return;
    }

    messageDrafts.set(key, input.value);
}


function restoreDraftForCurrentChat() {
    const key = getCurrentDraftKey();

    if (!key) {
        input.value = "";
        return;
    }

    input.value = messageDrafts.get(key) || "";
}


function clearDraftForCurrentChat() {
    const key = getCurrentDraftKey();

    if (!key) {
        return;
    }

    messageDrafts.delete(key);
}


function restoreTextAfterFailedSend(text) {
    input.value = text;
    saveCurrentDraft();
    input.focus();
}


// =========================
// MUTE
// =========================

function loadMutedChats() {
    try {
        const raw = localStorage.getItem("mutedChats");
        const list = raw ? JSON.parse(raw) : [];

        mutedChats.clear();

        if (Array.isArray(list)) {
            list.forEach((key) => mutedChats.add(key));
        }
    } catch {}
}


function saveMutedChats() {
    try {
        localStorage.setItem(
            "mutedChats",
            JSON.stringify([...mutedChats])
        );
    } catch {}
}


function getMuteKey(type, id) {
    return `${type}:${id}`;
}


function isChatMuted(type, id) {
    if (!type || !id) {
        return false;
    }

    return mutedChats.has(getMuteKey(type, id));
}


function toggleChatMute(type, id) {
    if (!type || !id) {
        return;
    }

    const key = getMuteKey(type, id);

    if (mutedChats.has(key)) {
        mutedChats.delete(key);
    } else {
        mutedChats.add(key);
    }

    saveMutedChats();
    renderRooms();
}


// =========================
// INPUT DRAFT SAVE
// =========================

input.addEventListener("input", () => {
    saveCurrentDraft();
});


// =========================
// SEND MESSAGE
// =========================

form.onsubmit = async (e) => {
    e.preventDefault();

    const text = input.value.trim();

    if (!text || !username) {
        return;
    }

    input.value = "";

    // =========================
    // DIRECT MESSAGE
    // =========================
    if (activeTab === "dm" && currentDirectChatId) {
        const dm = directChats.get(currentDirectChatId);

        if (!dm) {
            restoreTextAfterFailedSend(text);
            return;
        }

        try {
            const res = await fetch("/api/direct/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    target_node_id: dm.peer_id,
                    target_username: dm.peer_name,
                    message: text,
                }),
            });

            const data = await res.json();

            if (!data.ok) {
                restoreTextAfterFailedSend(text);
                alert("Ошибка отправки");
                return;
            }

            if (data.chat) {
                addDirectChat(data.chat);
            }

            if (data.message) {
                addDirectMessage(data.message);
            }

            clearDraftForCurrentChat();
        } catch {
            restoreTextAfterFailedSend(text);
            alert("Не удалось отправить сообщение");
        }

        return;
    }

    // =========================
    // GROUP MESSAGE
    // =========================
    if (activeTab === "group" && currentRoomId) {
        const room = rooms.get(currentRoomId);

        if (!room) {
            restoreTextAfterFailedSend(text);
            alert("Группа не найдена");
            return;
        }

        if (room.is_joined === false) {
            restoreTextAfterFailedSend(text);
            alert("Сначала вступите в группу");
            showJoinScreen(room);
            return;
        }

        try {
            const res = await fetch("/api/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    room_id: currentRoomId,
                    username,
                    message: text,
                }),
            });

            const data = await res.json();

            if (!data.ok) {
                restoreTextAfterFailedSend(text);

                if (data.error === "not_joined") {
                    alert("Вы не участник этой группы");
                    showJoinScreen(room);
                } else {
                    alert("Ошибка отправки");
                }

                return;
            }

            if (data.message) {
                addMessage(data.message);
            }

            clearDraftForCurrentChat();
        } catch {
            restoreTextAfterFailedSend(text);
            alert("Ошибка отправки");
        }
    }
};


// =========================
// ENTER SEND
// =========================
// Enter = отправить
// Shift + Enter = перенос строки
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
    }
});


// =========================
// APP START
// =========================

async function startApp() {
    loadMutedChats();
    loadHideDeletedMessagesSetting();
    setupHideDeletedMessagesToggle();

    await loadAppVersion();
    await loadConfig();
    await loadRooms();
    await loadDirectChats();
    await loadEmojis();

    renderEmojiPicker();

    const general = rooms.get("general");

    if (general) {
        await selectRoom(general);
    } else {
        roomTitle.textContent = "Комнаты";
        chat.innerHTML = "";
        form.style.display = "none";
    }

    document.body.classList.remove("loading");

    connectUiSocket();
    updateStatus();
}


startApp();