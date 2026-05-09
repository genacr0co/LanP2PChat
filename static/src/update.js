(function () {
    const STARTUP_CHECK_DELAYS_MS = [800, 2500, 7000, 15000, 30000, 60000];
    const CHECK_INTERVAL_MS = 5 * 60 * 1000;

    let updateInfo = null;
    let isChecking = false;
    let isDownloading = false;
    let checkTimer = null;
    let lastSuccessfulCheckAt = 0;
    let startupTimers = [];

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

        const latestVersion = info.latest_version || "новее";

        title.textContent = info.title || "Доступна новая версия";
        message.textContent = info.message || `Можно обновиться до версии ${latestVersion}.`;

        if (!isDownloading) {
            button.disabled = false;
            button.textContent = "Обновить";
        }

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
        if (isChecking || isDownloading) {
            return;
        }

        isChecking = true;

        try {
            const response = await fetch(`/api/update/check?t=${Date.now()}`, {
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            lastSuccessfulCheckAt = Date.now();

            if (!data || !data.ok || !data.update_available) {
                updateInfo = null;
                hideBanner();
                return;
            }

            showBanner(data);

        } catch (error) {
            console.warn("Update check failed:", error);
        } finally {
            isChecking = false;
        }
    }

    function clearStartupTimers() {
        for (const timer of startupTimers) {
            clearTimeout(timer);
        }

        startupTimers = [];
    }

    function runStartupUpdateChecks() {
        clearStartupTimers();

        for (const delay of STARTUP_CHECK_DELAYS_MS) {
            const timer = setTimeout(checkForUpdates, delay);
            startupTimers.push(timer);
        }
    }

    function startPeriodicUpdateChecks() {
        if (checkTimer) {
            clearInterval(checkTimer);
        }

        runStartupUpdateChecks();
        checkTimer = setInterval(checkForUpdates, CHECK_INTERVAL_MS);
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

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

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

            if (updateInfo) {
                showBanner(updateInfo);
            }
        }
    }

    function checkAfterWindowLoaded() {
        setTimeout(checkForUpdates, 500);
    }

    function checkAfterTabVisible() {
        if (document.visibilityState !== "visible") {
            return;
        }

        const now = Date.now();
        const minDelayBetweenVisibleChecks = 30 * 1000;

        if (now - lastSuccessfulCheckAt >= minDelayBetweenVisibleChecks) {
            checkForUpdates();
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

        startPeriodicUpdateChecks();

        window.addEventListener("load", checkAfterWindowLoaded);
        window.addEventListener("online", checkForUpdates);
        document.addEventListener("visibilitychange", checkAfterTabVisible);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initUpdateUi);
    } else {
        initUpdateUi();
    }
})();
