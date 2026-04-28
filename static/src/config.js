function getProfileLetter(name) {
    const value = (name || "").trim();

    if (!value) {
        return "?";
    }

    return value[0].toUpperCase();
}

function updateProfileUi() {
    if (profileName) {
        profileName.textContent = username || "Без имени";
    }

    if (profileAvatar) {
        profileAvatar.textContent = getProfileLetter(username);
    }
}

function openNameModal(mode = "first_start") {
    if (!nameModal) {
        return;
    }

    if (nameModalTitle) {
        nameModalTitle.textContent = mode === "edit"
            ? "Изменить имя"
            : "Ваше имя";
    }

    if (nameInput) {
        nameInput.value = username || "";
    }

    if (cancelNameBtn) {
        cancelNameBtn.style.display = mode === "edit" ? "inline-flex" : "none";
    }

    nameModal.classList.add("show");

    if (input) {
        input.disabled = true;
    }

    setTimeout(() => {
        if (nameInput) {
            nameInput.focus();
            nameInput.select();
        }
    }, 50);
}

function closeNameModal() {
    if (!username) {
        return;
    }

    if (nameModal) {
        nameModal.classList.remove("show");
    }

    if (input) {
        input.disabled = false;
        input.focus();
    }
}

async function loadConfig() {
    try {
        const res = await fetch("/api/config");
        const config = await res.json();

        username = config.username || "";
        myNodeId = config.node_id || null;

        updateProfileUi();

        if (!username) {
            openNameModal("first_start");
        } else {
            closeNameModal();
        }
    } catch {
        username = "";
        updateProfileUi();
        openNameModal("first_start");
    }
}

async function saveUsername() {
    const value = nameInput.value.trim();

    if (!value) {
        nameInput.focus();
        return;
    }

    try {
        const res = await fetch("/api/config", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                username: value,
            }),
        });

        const result = await res.json();

        if (!result.ok) {
            alert("Ошибка сохранения имени");
            return;
        }

        username = value;

        await loadConfig();

        updateProfileUi();
        closeNameModal();
    } catch {
        alert("Ошибка сохранения имени");
    }
}

if (saveNameBtn) {
    saveNameBtn.onclick = saveUsername;
}

if (cancelNameBtn) {
    cancelNameBtn.onclick = () => {
        closeNameModal();
    };
}

if (editNameBtn) {
    editNameBtn.onclick = () => {
        openNameModal("edit");
    };
}

if (nameInput) {
    nameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            saveUsername();
        }

        if (e.key === "Escape") {
            e.preventDefault();
            closeNameModal();
        }
    });
}