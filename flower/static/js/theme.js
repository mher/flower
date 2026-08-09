(function () {
    "use strict";

    var storageKey = "flower-theme";
    var root = document.documentElement;
    var systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    var selectedTheme;

    function getStoredTheme() {
        var theme;

        try {
            theme = window.localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }

        return theme === "light" || theme === "dark" ? theme : null;
    }

    function storeTheme(theme) {
        try {
            if (theme === "system") {
                window.localStorage.removeItem(storageKey);
            } else {
                window.localStorage.setItem(storageKey, theme);
            }
        } catch (error) {
            // The selected theme still applies when storage is unavailable.
        }
    }

    function preferredTheme() {
        return systemTheme.matches ? "dark" : "light";
    }

    function resolvedTheme(theme) {
        return theme === "system" ? preferredTheme() : theme;
    }

    function updateThemeMenu(theme) {
        var toggle = document.getElementById("theme-toggle");
        var label = document.getElementById("theme-toggle-label");
        var icon = document.getElementById("theme-toggle-icon");
        var themeName = theme.charAt(0).toUpperCase() + theme.slice(1);

        if (!toggle || !label || !icon) {
            return;
        }

        label.textContent = "Select theme: " + themeName;
        toggle.setAttribute("aria-label", "Select theme, current setting: " + themeName);
        icon.setAttribute("href", "#theme-icon-" + theme);

        document.querySelectorAll("[data-bs-theme-value]").forEach(function (option) {
            var selected = option.getAttribute("data-bs-theme-value") === theme;
            option.classList.toggle("active", selected);
            option.setAttribute("aria-pressed", selected ? "true" : "false");
        });
    }

    function applyTheme(theme) {
        root.setAttribute("data-bs-theme", resolvedTheme(theme));
        updateThemeMenu(theme);
    }

    selectedTheme = getStoredTheme() || "system";
    applyTheme(selectedTheme);

    document.addEventListener("DOMContentLoaded", function () {
        updateThemeMenu(selectedTheme);
        document.querySelectorAll("[data-bs-theme-value]").forEach(function (option) {
            option.addEventListener("click", function () {
                selectedTheme = option.getAttribute("data-bs-theme-value");
                storeTheme(selectedTheme);
                applyTheme(selectedTheme);
            });
        });
    });

    systemTheme.addEventListener("change", function () {
        if (selectedTheme === "system") {
            applyTheme(selectedTheme);
        }
    });
}());
