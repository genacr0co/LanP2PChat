form.onsubmit = async (e) => {
    e.preventDefault();

    const text = input.value.trim();
    if (!text || !username) return;

    input.value = "";

    // =========================
    // DIRECT
    // =========================
    if (activeTab === "dm" && currentDirectChatId) {
        const dm = directChats.get(currentDirectChatId);
        if (!dm) return;

        try {
            const res = await fetch("/api/direct/send", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    target_node_id: dm.peer_id,
                    target_username: dm.peer_name,
                    message: text,
                }),
            });

            const data = await res.json();

            if (data.ok) {
                if (data.chat) addDirectChat(data.chat);
                if (data.message) addDirectMessage(data.message);
            } else {
                alert("Ошибка отправки");
            }
        } catch {
            alert("Не удалось отправить сообщение");
        }

        return;
    }

    // =========================
    // GROUP
    // =========================
    if (activeTab === "group" && currentRoomId) {
        try {
            const res = await fetch("/api/send", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    room_id: currentRoomId,
                    username,
                    message: text,
                }),
            });

            const data = await res.json();

            if (data.ok && data.message) {
                addMessage(data.message);
            }

            if (!data.ok && data.error === "not_joined") {
                alert("Вы не участник этой группы");
            }
        } catch {
            alert("Ошибка отправки");
        }
    }
};


// =========================
// ENTER SEND
// =========================
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.ctrlKey) {
        e.preventDefault();
        form.requestSubmit();
    }
});


// =========================
// APP START
// =========================
async function startApp() {
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
    }

    document.body.classList.remove("loading");

    connectUiSocket();
    updateStatus();

    // =========================
    // ЛЁГКИЙ POLLING
    // =========================

    // список групп
    setInterval(loadRooms, 3000);

    // список личек
    setInterval(loadDirectChats, 3000);

    // статус уже сам обновляется внутри updateStatus()
}

startApp();