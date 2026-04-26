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
            input.value = text;
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
                input.value = text;
                alert("Ошибка отправки");
                return;
            }

            if (data.chat) {
                addDirectChat(data.chat);
            }

            if (data.message) {
                addDirectMessage(data.message);
            }
        } catch {
            input.value = text;
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
            input.value = text;
            alert("Группа не найдена");
            return;
        }

        if (room.is_joined === false) {
            input.value = text;
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
                input.value = text;

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
        } catch {
            input.value = text;
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
        form.style.display = "none";
    }

    document.body.classList.remove("loading");

    connectUiSocket();
    updateStatus();
}


startApp();