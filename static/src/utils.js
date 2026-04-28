function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
}


function playNotifySound(type = null, id = null) {
    /*
        Защита на нижнем уровне.

        Даже если где-то случайно вызовут:
            playNotifySound()

        звук не должен играть для замьюченного чата, если передали:
            playNotifySound("group", room_id)
            playNotifySound("dm", chat_id)
    */

    if (type && id && typeof isChatMuted === "function") {
        if (isChatMuted(type, id)) {
            return;
        }
    }

    const sound = notifySound || document.getElementById("notifySound");

    if (!sound) {
        return;
    }

    try {
        sound.currentTime = 0;
        sound.play().catch(() => {});
    } catch {}
}


function insertEmoji(emoji) {
    if (!input) {
        return;
    }

    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;

    input.value =
        input.value.substring(0, start) +
        emoji +
        input.value.substring(end);

    const pos = start + emoji.length;

    input.selectionStart = pos;
    input.selectionEnd = pos;

    input.focus();
}