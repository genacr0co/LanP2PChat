function renderOnlineUsers(users) {
    if (!onlineList) {
        return;
    }

    onlineList.innerHTML = "";

    users.forEach((user) => {
        if (user.me) {
            return;
        }

        if (!user.node_id) {
            return;
        }

        const item = document.createElement("div");
        item.className = "online-user";

        item.innerHTML = `
            <span class="online-dot"></span>
            <span>${escapeHtml(user.username || "Аноним")}</span>
        `;

        item.onclick = () => {
            openDirectChat(user.node_id, user.username || "Аноним");
        };

        onlineList.appendChild(item);
    });

    if (typeof applySmileys === "function") {
        applySmileys(onlineList);
    }
}


async function updateStatus() {
    try {
        const res = await fetch("/api/me");
        const data = await res.json();

        if (data.node_id) {
            myNodeId = data.node_id;
        }

        statusEl.textContent =
            `Онлайн · узлов: ${data.peers} · сокетов: ${data.sockets}`;

        renderOnlineUsers(data.users || []);

        if (typeof applySmileys === "function") {
            applySmileys(statusEl);
        }
    } catch {
        statusEl.textContent = "Нет связи";
    }

    setTimeout(updateStatus, 1000);
}