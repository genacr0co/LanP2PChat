async function loadConfig() {
    try {
        const res = await fetch("/api/config");
        const config = await res.json();

        username = config.username || "";

        if (!username) {
            nameModal.classList.add("show");
            input.disabled = true;
            nameInput.focus();
        } else {
            nameModal.classList.remove("show");
            input.disabled = false;
        }
    } catch {
        // если сервер не ответил
        nameModal.classList.add("show");
        input.disabled = true;
    }
}


async function saveUsername() {
    const value = nameInput.value.trim();

    if (!value) {
        nameInput.focus();
        return;
    }

    try {
        await fetch("/api/config", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username: value}),
        });

        username = value;

        nameModal.classList.remove("show");
        input.disabled = false;
        input.focus();
    } catch {
        alert("Ошибка сохранения имени");
    }
}


saveNameBtn.onclick = saveUsername;

nameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        saveUsername();
    }
});