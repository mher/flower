/**
 * @param {string} message the message to be displayed
 * @param {string} type "error", "success", something else
 */
const createAlertBox = (message, type) => {
    const alert = document.createElement("div");
    alert.classList.add(
        "alert",
        `alert-${type}`,
        "alert-dismissible",
        "fade",
        "show"
    );
    alert.setAttribute("role", "alert");

    const closeButton = document.createElement("button");
    closeButton.classList.add("btn-close");
    closeButton.setAttribute("type", "button");
    closeButton.setAttribute("data-bs-dismiss", "alert");
    closeButton.setAttribute("aria-label", "Close");

    closeButton.addEventListener("click", (event) =>
        event.target.parentNode.remove()
    );

    const title = document.createElement("strong");
    title.textContent = type.charAt(0).toUpperCase() + type.slice(1) + "!"; // Uppercase first letter of type

    const text = document.createElement("span");
    text.classList.add("d-inline-block", "ms-3");
    text.textContent = message;

    alert.appendChild(title);
    alert.appendChild(text);
    alert.appendChild(closeButton);

    return alert;
};

const showAlert = (message, type) => {
    const alertContainer = document.getElementById("alert-container");
    const alert = createAlertBox(message, type);
    alertContainer.appendChild(alert);
};

export const showDangerAlert = (message) => {
    showAlert(message, "danger");
};

export const showSuccessAlert = (message) => {
    showAlert(message, "success");
};
