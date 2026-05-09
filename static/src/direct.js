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

    if (dm.is_deleted === true) {
        const existed = directChats.has(dm.chat_id);

        directChats.delete(dm.chat_id);

        if (currentDirectChatId === dm.chat_id) {
            clearCurrentDirectChatView();
        }

        closeDirectSettingsModal();

        if (shouldRender) {
            renderRooms();
        }

        updateGroupSettingsButton();

        return existed;
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

    updateGroupSettingsButton();

    return true;
}


function getCurrentDirectChat() {
    if (activeTab !== "dm") {
        return null;
    }

    if (!currentDirectChatId) {
        return null;
    }

    return directChats.get(currentDirectChatId) || null;
}


function clearCurrentDirectChatView() {
    currentDirectChatId = null;
    rendered.clear();
    chat.innerHTML = "";
    roomTitle.textContent = "Личные сообщения";
    updateRoomDescription(null);
    form.style.display = "none";
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

        updateGroupSettingsButton();
    } catch {}
}


async function selectDirectChat(dm) {
    if (!dm) {
        return;
    }

    if (dm.is_deleted === true) {
        handleDirectChatDeleted(dm);
        return;
    }

    const actualDm = directChats.get(dm.chat_id) || dm;

    if (!actualDm || actualDm.is_deleted === true) {
        handleDirectChatDeleted(actualDm);
        return;
    }

    activeTab = "dm";
    currentRoomId = null;
    currentDirectChatId = actualDm.chat_id;

    closeGroupSettingsModal();
    closeDirectSettingsModal();

    roomTitle.textContent = actualDm.peer_name;
    updateRoomDescription(null);

    rendered.clear();
    chat.innerHTML = "";

    form.style.display = "flex";
    restoreDraftForCurrentChat();

    await loadDirectHistory(actualDm.chat_id);

    updateTabs();

    if (typeof applySmileys === "function") {
        applySmileys(roomTitle);
    }
}


function openDirectSettingsModal() {
    const dm = getCurrentDirectChat();

    if (!dm) {
        return;
    }

    if (directSettingsTitle) {
        directSettingsTitle.textContent = dm.peer_name || "Личный чат";
    }

    if (directInfoBox) {
        directInfoBox.textContent = "Удаление скроет этот личный чат у вас и у собеседника.";
    }

    updateDirectMuteButton(dm);

    if (directSettingsModal) {
        directSettingsModal.classList.add("show");
    }
}


function closeDirectSettingsModal() {
    if (directSettingsModal) {
        directSettingsModal.classList.remove("show");
    }
}


function updateDirectMuteButton(dm) {
    if (!directMuteBtn || !dm) {
        return;
    }

    const muted = isChatMuted("dm", dm.chat_id);

    directMuteBtn.textContent = muted
        ? "🔔 Включить звук"
        : "🔕 Отключить звук";
}


async function deleteCurrentDirectChat() {
    const dm = getCurrentDirectChat();

    if (!dm || !dm.chat_id || !dm.peer_id) {
        return;
    }

    const confirmed = confirm(
        `Удалить личный чат с "${dm.peer_name}"?\n\n` +
        "Он исчезнет у вас и у собеседника после синхронизации."
    );

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/direct/chats/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                chat_id: dm.chat_id,
                target_node_id: dm.peer_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            alert("Не удалось удалить личный чат.");
            return;
        }

        if (data.chat) {
            handleDirectChatDeleted(data.chat);
        }
    } catch {
        alert("Ошибка удаления личного чата.");
    }
}


function handleDirectChatDeleted(dm) {
    if (!dm || !dm.chat_id) {
        return;
    }

    directChats.delete(dm.chat_id);

    if (currentDirectChatId === dm.chat_id) {
        clearCurrentDirectChatView();
    }

    closeDirectSettingsModal();
    renderRooms();
    updateGroupSettingsButton();
}


if (closeDirectSettingsBtn) {
    closeDirectSettingsBtn.onclick = () => {
        closeDirectSettingsModal();
    };
}


if (directMuteBtn) {
    directMuteBtn.onclick = () => {
        const dm = getCurrentDirectChat();

        if (!dm) {
            return;
        }

        toggleChatMute("dm", dm.chat_id);
        updateDirectMuteButton(dm);
    };
}


if (directDeleteBtn) {
    directDeleteBtn.onclick = async () => {
        await deleteCurrentDirectChat();
    };
}


if (directSettingsModal) {
    directSettingsModal.onclick = (e) => {
        if (e.target === directSettingsModal) {
            closeDirectSettingsModal();
        }
    };
}