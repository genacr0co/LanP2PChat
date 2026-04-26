async function loadEmojis() {
    try {
        const res = await fetch("/static/emojis.json");
        emojiCodes = await res.json();

        if (!Array.isArray(emojiCodes)) {
            emojiCodes = [];
        }
    } catch {
        emojiCodes = [];
    }
}


function renderEmojiPicker() {
    if (!emojiPicker) return;

    emojiPicker.innerHTML = "";

    emojiCodes.forEach((code) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.code = code;
        btn.textContent = `[${code}]`;

        btn.onclick = (e) => {
            e.stopPropagation();

            insertEmoji(`[${btn.dataset.code}]`);
            emojiPicker.classList.remove("show");

            input.dispatchEvent(new Event("input"));
        };

        emojiPicker.appendChild(btn);
    });

    if (typeof applySmileys === "function") {
        applySmileys(emojiPicker);
    }
}


emojiBtn.onclick = (e) => {
    e.stopPropagation();
    emojiPicker.classList.toggle("show");
};


document.addEventListener("click", (e) => {
    if (!emojiPicker) return;

    if (!emojiPicker.contains(e.target) && e.target !== emojiBtn) {
        emojiPicker.classList.remove("show");
    }
});