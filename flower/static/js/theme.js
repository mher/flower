(function () {
    "use strict";

    var storageKey = "flower-theme";
    var root = document.documentElement;
    var systemTheme = window.matchMedia("(prefers-color-scheme: dark)");

    function getStoredTheme() {
        try {
            return window.localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }

    function storeTheme(theme) {
        try {
            window.localStorage.setItem(storageKey, theme);
        } catch (error) {
            // The selected theme still applies when storage is unavailable.
        }
    }

    function preferredTheme() {
        return systemTheme.matches ? "dark" : "light";
    }

    function updateToggle(theme) {
        var toggle = document.getElementById("theme-toggle");
        var label = document.getElementById("theme-toggle-label");
        var nextTheme = theme === "dark" ? "light" : "dark";

        if (!toggle || !label) {
            return;
        }

        label.textContent = nextTheme === "dark" ? "Dark mode" : "Light mode";
        toggle.setAttribute("aria-label", "Switch to " + nextTheme + " mode");
    }

    function applyTheme(theme) {
        root.setAttribute("data-bs-theme", theme);
        updateToggle(theme);
    }

    applyTheme(getStoredTheme() || preferredTheme());

    document.addEventListener("DOMContentLoaded", function () {
        var toggle = document.getElementById("theme-toggle");

        updateToggle(root.getAttribute("data-bs-theme"));
        toggle.addEventListener("click", function () {
            var nextTheme = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            storeTheme(nextTheme);
            applyTheme(nextTheme);
        });
    });

    systemTheme.addEventListener("change", function () {
        if (!getStoredTheme()) {
            applyTheme(preferredTheme());
        }
    });
}());
