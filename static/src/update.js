(function () {
    const CHECK_DELAY_MS = 2500;

    let updateInfo = null;
    let isDownloading = false;

    function getBanner() {
        return document.getElementById("updateBanner");
    }

    function getTitle() {
        return document.getElementById("updateBannerTitle");
    }

    function getMessage() {
        return document.getElementById("updateBannerMessage");
    }

    function getButton() {
        return document.getElementById("updateInstallBtn");
    }

    function getCloseButton() {
        return document.getElementById("updateCloseBtn");
    }

    function showBanner(info) {
        const banner = getBanner();
        const title = getTitle();
        const message = getMessage();
        const button = getButton();
        const closeButton = getCloseButton();

        if (!banner || !title || !message || !button) {
            return;
        }

        updateInfo = info;

        title.textContent = info.title || "Доступна новая версия";
        message.textContent = info.message || `Можно обновиться до версии ${info.latest_version || "новее"}.`;

        button.disabled = false;
        button.textContent = "Обновить";

        if (closeButton) {
            closeButton.style.display = info.mandatory ? "none" : "inline-flex";
        }

        banner.classList.add("show");
    }

    function hideBanner() {
        const banner = getBanner();

        if (banner) {
            banner.classList.remove("show");
        }
    }

    function setButtonState(text, disabled) {
        const button = getButton();

        if (!button) {
            return;
        }

        button.textContent = text;
        button.disabled = !!disabled;
    }

    async function checkForUpdates() {
        try {
            const response = await fetch("/api/update/check", {
                cache: "no-store",
            });

            const data = await response.json();

            if (!data || !data.ok || !data.update_available) {
                return;
            }

            showBanner(data);

        } catch (error) {
            console.warn("Update check failed:", error);
        }
    }

    async function installUpdate() {
        if (isDownloading) {
            return;
        }

        isDownloading = true;
        setButtonState("Скачивание...", true);

        try {
            const response = await fetch("/api/update/download", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({}),
            });

            const data = await response.json();

            if (!data || !data.ok || !data.installer_path) {
                throw new Error((data && data.error) || "Не удалось скачать обновление");
            }

            setButtonState("Установка...", true);

            if (
                window.pywebview &&
                window.pywebview.api &&
                typeof window.pywebview.api.install_update === "function"
            ) {
                const result = await window.pywebview.api.install_update(data.installer_path);

                if (result && result.ok === false) {
                    throw new Error(result.error || "Не удалось запустить установщик");
                }

                return;
            }

            throw new Error("Обновление доступно только в desktop-версии приложения");

        } catch (error) {
            console.error("Install update failed:", error);
            alert("Не удалось обновить приложение: " + error.message);
            setButtonState("Обновить", false);
            isDownloading = false;
        }
    }

    function initUpdateUi() {
        const button = getButton();
        const closeButton = getCloseButton();

        if (button) {
            button.addEventListener("click", installUpdate);
        }

        if (closeButton) {
            closeButton.addEventListener("click", hideBanner);
        }

        setTimeout(checkForUpdates, CHECK_DELAY_MS);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initUpdateUi);
    } else {
        initUpdateUi();
    }
})();
