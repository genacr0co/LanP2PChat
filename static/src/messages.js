const MESSAGE_PAGE_LIMIT = 40;
const MESSAGE_LOAD_SCROLL_EDGE = 120;
const MESSAGE_SCROLL_SUPPRESS_MS = 450;

const messagePagination = new Map();


function getMessagePaginationKey(type, id) {
    return `${type}:${id}`;
}


function createMessagePaginationState() {
    return {
        loading: false,
        initialLoading: false,
        hasMore: true,
        beforeCreatedAt: null,
        beforeMessageId: null,
        initialized: false,
        lastRequestCursor: "",
        suppressScrollUntil: 0,
    };
}


function getMessagePaginationState(type, id) {
    const key = getMessagePaginationKey(type, id);

    if (!messagePagination.has(key)) {
        messagePagination.set(key, createMessagePaginationState());
    }

    return messagePagination.get(key);
}


function resetMessagePagination(type, id) {
    const key = getMessagePaginationKey(type, id);
    messagePagination.set(key, createMessagePaginationState());
}


function updateMessagePaginationState(state, payload) {
    if (!state || !payload) {
        return;
    }

    state.hasMore = payload.has_more === true;
    state.beforeCreatedAt = payload.next_before_created_at || null;
    state.beforeMessageId = payload.next_before_message_id || null;
    state.initialized = true;
}


function getCurrentPaginationContext() {
    if (activeTab === "group" && currentRoomId) {
        return {
            type: "group",
            id: currentRoomId,
        };
    }

    if (activeTab === "dm" && currentDirectChatId) {
        return {
            type: "direct",
            id: currentDirectChatId,
        };
    }

    return null;
}


function waitForNextFrame() {
    return new Promise((resolve) => {
        requestAnimationFrame(() => {
            requestAnimationFrame(resolve);
        });
    });
}


async function scrollChatToBottom() {
    await waitForNextFrame();

    if (chat) {
        chat.scrollTop = chat.scrollHeight;
    }
}


function suppressPaginationScroll(type, id) {
    const state = getMessagePaginationState(type, id);
    state.suppressScrollUntil = Date.now() + MESSAGE_SCROLL_SUPPRESS_MS;
}


function isPaginationScrollSuppressed(state) {
    if (!state) {
        return true;
    }

    return Date.now() < state.suppressScrollUntil;
}


function isChatScrollable() {
    if (!chat) {
        return false;
    }

    return chat.scrollHeight > chat.clientHeight + 20;
}


function getFirstMessageRow() {
    if (!chat) {
        return null;
    }

    return chat.querySelector(".message-row");
}


function hasRenderedMessage(messageId) {
    if (!messageId) {
        return true;
    }

    if (rendered.has(messageId)) {
        return true;
    }

    return !!chat.querySelector(
        `.message-row[data-message-id="${CSS.escape(messageId)}"]`
    );
}


// Skeleton пока оставляем как функции, но не вставляем в поток сообщений.
// Позже можно сделать overlay, чтобы он не ломал порядок DOM.

function ensureMessagesSkeleton() {
    let skeleton = document.getElementById("messagesSkeleton");

    if (skeleton) {
        return skeleton;
    }

    skeleton = document.createElement("div");
    skeleton.id = "messagesSkeleton";
    skeleton.className = "messages-skeleton";
    skeleton.innerHTML = `
        <div class="skeleton-bubble"></div>
        <div class="skeleton-bubble short"></div>
        <div class="skeleton-bubble"></div>
    `;

    return skeleton;
}


function showMessagesSkeleton() {
    return;
}


function hideMessagesSkeleton() {
    const skeleton = document.getElementById("messagesSkeleton");

    if (skeleton) {
        skeleton.remove();
    }
}


function isOwnMessage(msg) {
    if (!msg || !myNodeId) {
        return false;
    }

    return msg.sender_id === myNodeId;
}


function isDeletedMessage(msg) {
    return !!(msg && msg.is_deleted === true);
}


function shouldHideDeletedMessages() {
    return hideDeletedMessages === true;
}


function loadHideDeletedMessagesSetting() {
    try {
        hideDeletedMessages = localStorage.getItem("hideDeletedMessages") === "true";
    } catch {
        hideDeletedMessages = false;
    }

    if (hideDeletedMessagesToggle) {
        hideDeletedMessagesToggle.checked = hideDeletedMessages;
    }
}


function saveHideDeletedMessagesSetting() {
    try {
        localStorage.setItem(
            "hideDeletedMessages",
            hideDeletedMessages ? "true" : "false"
        );
    } catch {}
}


async function reloadCurrentChatMessagesAfterFilterChange() {
    hideMessageContextMenu();

    if (activeTab === "group" && currentRoomId) {
        await loadHistory();
        return;
    }

    if (activeTab === "dm" && currentDirectChatId) {
        await loadDirectHistory(currentDirectChatId);
    }
}


function setupHideDeletedMessagesToggle() {
    if (!hideDeletedMessagesToggle) {
        return;
    }

    hideDeletedMessagesToggle.checked = hideDeletedMessages;

    hideDeletedMessagesToggle.onchange = async () => {
        hideDeletedMessages = hideDeletedMessagesToggle.checked === true;
        saveHideDeletedMessagesSetting();
        await reloadCurrentChatMessagesAfterFilterChange();
    };
}


function getDeletedMessageText() {
    return "▒▒▒▒▒▒▒▒▒▒▒▒";
}


function setMessageText(row, text) {
    const textEl = row.querySelector(".text");

    if (!textEl) {
        return;
    }

    textEl.textContent = text || "";
}


function ensureMessageContextMenu() {
    let menu = document.getElementById("messageContextMenu");

    if (menu) {
        return menu;
    }

    menu = document.createElement("div");
    menu.id = "messageContextMenu";
    menu.className = "message-context-menu";
    menu.innerHTML = `
        <button id="copyMessageMenuBtn" type="button">Копировать сообщение</button>
        <button id="deleteMessageMenuBtn" type="button" class="danger">Удалить сообщение</button>
    `;

    document.body.appendChild(menu);

    return menu;
}


function hideMessageContextMenu() {
    const menu = document.getElementById("messageContextMenu");

    if (menu) {
        menu.classList.remove("show");
        menu.style.left = "0px";
        menu.style.top = "0px";
    }
}


function showMessageContextMenu(e, msg, type, row) {
    e.preventDefault();
    e.stopPropagation();

    if (!msg || !row) {
        return;
    }

    if (isDeletedMessage(msg)) {
        hideMessageContextMenu();
        return;
    }

    const menu = ensureMessageContextMenu();

    const copyBtn = document.getElementById("copyMessageMenuBtn");
    const deleteBtn = document.getElementById("deleteMessageMenuBtn");

    const canDelete =
        isOwnMessage(msg) &&
        !isDeletedMessage(msg) &&
        (type === "group" || type === "direct");

    if (copyBtn) {
        copyBtn.onclick = async (clickEvent) => {
            clickEvent.stopPropagation();
            await copyMessageText(msg);
            hideMessageContextMenu();
        };
    }

    if (deleteBtn) {
        deleteBtn.style.display = canDelete ? "flex" : "none";

        deleteBtn.onclick = async (clickEvent) => {
            clickEvent.stopPropagation();

            if (type === "group") {
                await deleteGroupMessage(msg);
            }

            if (type === "direct") {
                await deleteDirectMessage(msg);
            }

            hideMessageContextMenu();
        };
    }

    const menuWidth = 230;
    const menuHeight = canDelete ? 94 : 50;

    let x = e.clientX;
    let y = e.clientY;

    if (x + menuWidth > window.innerWidth) {
        x = window.innerWidth - menuWidth - 10;
    }

    if (y + menuHeight > window.innerHeight) {
        y = window.innerHeight - menuHeight - 10;
    }

    menu.style.left = `${Math.max(10, x)}px`;
    menu.style.top = `${Math.max(10, y)}px`;
    menu.classList.add("show");
}


async function copyMessageText(msg) {
    if (!msg || isDeletedMessage(msg)) {
        return;
    }

    const text = msg.message || "";

    if (!text.trim()) {
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
    } catch {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "-9999px";

        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            document.execCommand("copy");
        } catch {}

        textarea.remove();
    }
}


async function deleteGroupMessage(msg) {
    if (!msg || !msg.message_id || !msg.room_id) {
        return;
    }

    if (!isOwnMessage(msg) || isDeletedMessage(msg)) {
        return;
    }

    const confirmed = confirm("Удалить это сообщение?");

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/messages/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message_id: msg.message_id,
                room_id: msg.room_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_sender") {
                alert("Удалить можно только своё сообщение.");
                return;
            }

            if (data.error === "message_not_found") {
                alert("Сообщение не найдено.");
                return;
            }

            alert("Не удалось удалить сообщение.");
            return;
        }

        if (data.message) {
            handleGroupMessageDeleted(data.message);
        }
    } catch {
        alert("Ошибка удаления сообщения.");
    }
}


async function deleteDirectMessage(msg) {
    if (!msg || !msg.message_id || !msg.chat_id) {
        return;
    }

    if (!isOwnMessage(msg) || isDeletedMessage(msg)) {
        return;
    }

    const dm = getCurrentDirectChat();

    if (!dm || !dm.peer_id) {
        alert("Не удалось определить собеседника.");
        return;
    }

    const confirmed = confirm("Удалить это сообщение?");

    if (!confirmed) {
        return;
    }

    try {
        const res = await fetch("/api/direct/messages/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message_id: msg.message_id,
                chat_id: msg.chat_id,
                target_node_id: dm.peer_id,
            }),
        });

        const data = await res.json();

        if (!data.ok) {
            if (data.error === "not_sender") {
                alert("Удалить можно только своё сообщение.");
                return;
            }

            if (data.error === "message_not_found") {
                alert("Сообщение не найдено.");
                return;
            }

            alert("Не удалось удалить сообщение.");
            return;
        }

        if (data.message) {
            handleDirectMessageDeleted(data.message);
        }
    } catch {
        alert("Ошибка удаления сообщения.");
    }
}


function applyDeletedMessageState(row, msg) {
    if (!row || !msg) {
        return;
    }

    const bubble = row.querySelector(".bubble");
    const textEl = row.querySelector(".text");

    if (shouldHideDeletedMessages()) {
        rendered.delete(msg.message_id);
        row.remove();
        return;
    }

    row.classList.add("deleted-message-row");
    row.dataset.isDeleted = "true";

    if (bubble) {
        bubble.classList.add("deleted-message-bubble");
    }

    if (textEl) {
        textEl.textContent = msg.message || getDeletedMessageText();
        textEl.classList.add("deleted-message-text");
    }

    row.oncontextmenu = (e) => {
        e.preventDefault();
        e.stopPropagation();
        hideMessageContextMenu();
    };
}


function handleGroupMessageDeleted(msg) {
    if (!msg || !msg.message_id) {
        return;
    }

    const row = chat.querySelector(
        `.message-row[data-message-id="${CSS.escape(msg.message_id)}"]`
    );

    if (!row) {
        return;
    }

    const currentMsg = {
        ...msg,
        is_deleted: true,
        message: msg.message || getDeletedMessageText(),
    };

    applyDeletedMessageState(row, currentMsg);
}


function handleDirectMessageDeleted(msg) {
    if (!msg || !msg.message_id) {
        return;
    }

    const row = chat.querySelector(
        `.message-row[data-message-id="${CSS.escape(msg.message_id)}"]`
    );

    if (!row) {
        return;
    }

    const currentMsg = {
        ...msg,
        is_deleted: true,
        message: msg.message || getDeletedMessageText(),
    };

    applyDeletedMessageState(row, currentMsg);
}


function createGroupMessageRow(msg) {
    if (!msg) {
        return null;
    }

    if (!msg.room_id) {
        msg.room_id = "general";
    }

    if (msg.room_id.startsWith("dm_") || msg.room_id.startsWith("direct_")) {
        return null;
    }

    const room = rooms.get(msg.room_id);

    if (!room) {
        return null;
    }

    if (room.is_joined === false || room.is_deleted === true) {
        return null;
    }

    if (hasRenderedMessage(msg.message_id)) {
        return null;
    }

    rendered.add(msg.message_id);

    const isMe = isOwnMessage(msg);
    const deleted = isDeletedMessage(msg);

    if (deleted && shouldHideDeletedMessages()) {
        return null;
    }

    const row = document.createElement("div");
    row.className =
        "message-row" +
        (isMe ? " me" : "") +
        (deleted ? " deleted-message-row" : "");

    row.dataset.messageId = msg.message_id;
    row.dataset.roomId = msg.room_id;
    row.dataset.senderId = msg.sender_id || "";
    row.dataset.isDeleted = deleted ? "true" : "false";

    const messageText = deleted
        ? (msg.message || getDeletedMessageText())
        : msg.message;

    row.innerHTML = `
        <div class="bubble${deleted ? " deleted-message-bubble" : ""}">
            <div class="name clickable-name"
                 data-sender-id="${escapeHtml(msg.sender_id)}"
                 data-username="${escapeHtml(msg.username)}">
                ${escapeHtml(msg.username)}
            </div>
            <div class="text${deleted ? " deleted-message-text" : ""}"></div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    setMessageText(row, messageText);

    const nameEl = row.querySelector(".clickable-name");

    if (nameEl && !deleted) {
        nameEl.onclick = () => {
            if (nameEl.dataset.senderId !== "system") {
                openDirectChat(
                    nameEl.dataset.senderId,
                    nameEl.dataset.username
                );
            }
        };
    }

    if (!deleted) {
        row.oncontextmenu = (e) => {
            showMessageContextMenu(e, msg, "group", row);
        };
    } else {
        applyDeletedMessageState(row, msg);
    }

    if (!deleted && typeof applySmileys === "function") {
        applySmileys(row);
    }

    return row;
}


function createDirectMessageRow(msg) {
    if (!msg) {
        return null;
    }

    if (!msg.chat_id) {
        return null;
    }

    if (hasRenderedMessage(msg.message_id)) {
        return null;
    }

    rendered.add(msg.message_id);

    const isMe = isOwnMessage(msg);
    const deleted = isDeletedMessage(msg);

    if (deleted && shouldHideDeletedMessages()) {
        return null;
    }

    const row = document.createElement("div");
    row.className =
        "message-row" +
        (isMe ? " me" : "") +
        (deleted ? " deleted-message-row" : "");

    row.dataset.messageId = msg.message_id;
    row.dataset.chatId = msg.chat_id;
    row.dataset.senderId = msg.sender_id || "";
    row.dataset.isDeleted = deleted ? "true" : "false";

    const messageText = deleted
        ? (msg.message || getDeletedMessageText())
        : msg.message;

    row.innerHTML = `
        <div class="bubble${deleted ? " deleted-message-bubble" : ""}">
            <div class="name">${escapeHtml(msg.username)}</div>
            <div class="text${deleted ? " deleted-message-text" : ""}"></div>
            <div class="time">${escapeHtml(msg.created_at)}</div>
        </div>
    `;

    setMessageText(row, messageText);

    if (!deleted) {
        row.oncontextmenu = (e) => {
            showMessageContextMenu(e, msg, "direct", row);
        };
    } else {
        applyDeletedMessageState(row, msg);
    }

    if (!deleted && typeof applySmileys === "function") {
        applySmileys(row);
    }

    return row;
}


function addMessage(msg, options = {}) {
    if (!msg) {
        return;
    }

    if (!msg.room_id) {
        msg.room_id = "general";
    }

    const isCurrent =
        activeTab === "group" &&
        msg.room_id === currentRoomId;

    if (!isCurrent) {
        return;
    }

    const row = createGroupMessageRow(msg);

    if (!row) {
        return;
    }

    chat.appendChild(row);

    if (options.scroll !== false) {
        chat.scrollTop = chat.scrollHeight;
    }
}


function addDirectMessage(msg, options = {}) {
    if (!msg) {
        return;
    }

    const isCurrent =
        activeTab === "dm" &&
        msg.chat_id === currentDirectChatId;

    if (!isCurrent) {
        return;
    }

    const row = createDirectMessageRow(msg);

    if (!row) {
        return;
    }

    chat.appendChild(row);

    if (options.scroll !== false) {
        chat.scrollTop = chat.scrollHeight;
    }
}


function prependGroupMessages(list) {
    if (!Array.isArray(list) || list.length === 0) {
        return 0;
    }

    const fragment = document.createDocumentFragment();
    let added = 0;

    list.forEach((msg) => {
        const row = createGroupMessageRow(msg);

        if (row) {
            fragment.appendChild(row);
            added += 1;
        }
    });

    if (added === 0) {
        return 0;
    }

    const firstMessageRow = getFirstMessageRow();

    if (firstMessageRow) {
        chat.insertBefore(fragment, firstMessageRow);
    } else {
        chat.appendChild(fragment);
    }

    return added;
}


function prependDirectMessages(list) {
    if (!Array.isArray(list) || list.length === 0) {
        return 0;
    }

    const fragment = document.createDocumentFragment();
    let added = 0;

    list.forEach((msg) => {
        const row = createDirectMessageRow(msg);

        if (row) {
            fragment.appendChild(row);
            added += 1;
        }
    });

    if (added === 0) {
        return 0;
    }

    const firstMessageRow = getFirstMessageRow();

    if (firstMessageRow) {
        chat.insertBefore(fragment, firstMessageRow);
    } else {
        chat.appendChild(fragment);
    }

    return added;
}


async function loadHistory() {
    if (!currentRoomId) {
        return;
    }

    const room = rooms.get(currentRoomId);

    if (!room) {
        return;
    }

    if (room.is_joined === false || room.is_deleted === true) {
        return;
    }

    const loadRoomId = currentRoomId;

    resetMessagePagination("group", loadRoomId);

    const state = getMessagePaginationState("group", loadRoomId);

    rendered.clear();
    chat.innerHTML = "";

    try {
        state.loading = true;
        state.initialLoading = true;

        const url =
            `/api/messages?room_id=${encodeURIComponent(loadRoomId)}` +
            `&page=1&limit=${MESSAGE_PAGE_LIMIT}`;

        const res = await fetch(url);
        const payload = await res.json();

        if (activeTab !== "group" || currentRoomId !== loadRoomId) {
            return;
        }

        const items = Array.isArray(payload.items)
            ? payload.items
            : [];

        items.forEach((msg) => {
            addMessage(msg, {
                scroll: false,
            });
        });

        updateMessagePaginationState(state, payload);

        await scrollChatToBottom();

        suppressPaginationScroll("group", loadRoomId);
    } catch {
        state.hasMore = false;
    } finally {
        state.loading = false;
        state.initialLoading = false;
    }
}


async function loadDirectHistory(chatId) {
    if (!chatId) {
        return;
    }

    const loadChatId = chatId;

    resetMessagePagination("direct", loadChatId);

    const state = getMessagePaginationState("direct", loadChatId);

    rendered.clear();
    chat.innerHTML = "";

    try {
        state.loading = true;
        state.initialLoading = true;

        const url =
            `/api/direct/messages?chat_id=${encodeURIComponent(loadChatId)}` +
            `&page=1&limit=${MESSAGE_PAGE_LIMIT}`;

        const res = await fetch(url);
        const payload = await res.json();

        if (activeTab !== "dm" || currentDirectChatId !== loadChatId) {
            return;
        }

        const items = Array.isArray(payload.items)
            ? payload.items
            : [];

        items.forEach((msg) => {
            addDirectMessage(msg, {
                scroll: false,
            });
        });

        updateMessagePaginationState(state, payload);

        await scrollChatToBottom();

        suppressPaginationScroll("direct", loadChatId);
    } catch {
        state.hasMore = false;
    } finally {
        state.loading = false;
        state.initialLoading = false;
    }
}


async function loadOlderGroupMessages() {
    if (activeTab !== "group" || !currentRoomId) {
        return;
    }

    const loadRoomId = currentRoomId;
    const state = getMessagePaginationState("group", loadRoomId);

    if (state.loading || state.initialLoading || !state.hasMore) {
        return;
    }

    if (isPaginationScrollSuppressed(state)) {
        return;
    }

    if (!state.beforeCreatedAt || !state.beforeMessageId) {
        return;
    }

    const cursorKey = `${state.beforeCreatedAt}|${state.beforeMessageId}`;

    if (state.lastRequestCursor === cursorKey) {
        return;
    }

    try {
        state.loading = true;
        state.lastRequestCursor = cursorKey;

        const url =
            `/api/messages?room_id=${encodeURIComponent(loadRoomId)}` +
            `&page=1&limit=${MESSAGE_PAGE_LIMIT}` +
            `&before_created_at=${encodeURIComponent(state.beforeCreatedAt)}` +
            `&before_message_id=${encodeURIComponent(state.beforeMessageId)}`;

        const res = await fetch(url);
        const payload = await res.json();

        if (activeTab !== "group" || currentRoomId !== loadRoomId) {
            return;
        }

        const items = Array.isArray(payload.items)
            ? payload.items
            : [];

        const oldScrollHeight = chat.scrollHeight;
        const oldScrollTop = chat.scrollTop;

        const added = prependGroupMessages(items);

        if (added > 0) {
            const newScrollHeight = chat.scrollHeight;
            chat.scrollTop = oldScrollTop + (newScrollHeight - oldScrollHeight);
        }

        updateMessagePaginationState(state, payload);

        if (items.length === 0) {
            state.hasMore = false;
        }
    } catch {
        state.lastRequestCursor = "";
    } finally {
        state.loading = false;
    }
}


async function loadOlderDirectMessages() {
    if (activeTab !== "dm" || !currentDirectChatId) {
        return;
    }

    const loadChatId = currentDirectChatId;
    const state = getMessagePaginationState("direct", loadChatId);

    if (state.loading || state.initialLoading || !state.hasMore) {
        return;
    }

    if (isPaginationScrollSuppressed(state)) {
        return;
    }

    if (!state.beforeCreatedAt || !state.beforeMessageId) {
        return;
    }

    const cursorKey = `${state.beforeCreatedAt}|${state.beforeMessageId}`;

    if (state.lastRequestCursor === cursorKey) {
        return;
    }

    try {
        state.loading = true;
        state.lastRequestCursor = cursorKey;

        const url =
            `/api/direct/messages?chat_id=${encodeURIComponent(loadChatId)}` +
            `&page=1&limit=${MESSAGE_PAGE_LIMIT}` +
            `&before_created_at=${encodeURIComponent(state.beforeCreatedAt)}` +
            `&before_message_id=${encodeURIComponent(state.beforeMessageId)}`;

        const res = await fetch(url);
        const payload = await res.json();

        if (activeTab !== "dm" || currentDirectChatId !== loadChatId) {
            return;
        }

        const items = Array.isArray(payload.items)
            ? payload.items
            : [];

        const oldScrollHeight = chat.scrollHeight;
        const oldScrollTop = chat.scrollTop;

        const added = prependDirectMessages(items);

        if (added > 0) {
            const newScrollHeight = chat.scrollHeight;
            chat.scrollTop = oldScrollTop + (newScrollHeight - oldScrollHeight);
        }

        updateMessagePaginationState(state, payload);

        if (items.length === 0) {
            state.hasMore = false;
        }
    } catch {
        state.lastRequestCursor = "";
    } finally {
        state.loading = false;
    }
}


async function handleChatPaginationScroll() {
    if (!chat) {
        return;
    }

    if (!isChatScrollable()) {
        return;
    }

    const context = getCurrentPaginationContext();

    if (!context) {
        return;
    }

    const state = getMessagePaginationState(context.type, context.id);

    if (!state.initialized || state.initialLoading || state.loading) {
        return;
    }

    if (isPaginationScrollSuppressed(state)) {
        return;
    }

    if (chat.scrollTop > MESSAGE_LOAD_SCROLL_EDGE) {
        return;
    }

    if (context.type === "group") {
        await loadOlderGroupMessages();
        return;
    }

    if (context.type === "direct") {
        await loadOlderDirectMessages();
    }
}


if (chat) {
    chat.addEventListener("scroll", () => {
        handleChatPaginationScroll();
    });
}


document.addEventListener("pointerdown", (e) => {
    const menu = document.getElementById("messageContextMenu");

    if (!menu || !menu.classList.contains("show")) {
        return;
    }

    if (menu.contains(e.target)) {
        return;
    }

    hideMessageContextMenu();
});


window.addEventListener("blur", () => {
    hideMessageContextMenu();
});