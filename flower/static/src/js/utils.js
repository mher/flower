import dayjs from "dayjs";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import $ from "jquery";

dayjs.extend(utc);
dayjs.extend(timezone);

export function urlPrefix() {
    let url_prefix = document.getElementById("url_prefix").value;
    if (url_prefix) {
        url_prefix = url_prefix.replace(/\/+$/, "");
        if (url_prefix.startsWith("/")) {
            return url_prefix;
        } else {
            return `/${url_prefix}`;
        }
    }
    return "";
}

export function formatTime(timestamp) {
    const time = $("#time").val(),
        prefix = time.startsWith("natural-time") ? "natural-time" : "time",
        tz = time.substr(prefix.length + 1) || "UTC";

    if (prefix === "natural-time") {
        dayjs(dayjs.unix(timestamp)).tz(tz).fromNow();
    }
    return dayjs(dayjs.unix(timestamp))
        .tz(tz)
        .format("YYYY-MM-DD HH:mm:ss.SSS");
}

//https://github.com/DataTables/DataTables/blob/1.10.11/media/js/jquery.dataTables.js#L14882
export function htmlEscapeEntities(d) {
    return typeof d === "string"
        ? d.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        : d;
}

export function activePage(name) {
    const pathname = $(location).attr("pathname");
    if (name === "/") {
        return pathname === urlPrefix() + name;
    } else {
        return pathname.startsWith(urlPrefix() + name);
    }
}

export function addClickEventListenerToElementWithId(elementId, listener) {
    document.getElementById(elementId)?.addEventListener("click", listener);
}

function addEventListenerToElementsWithClassNames(classNames, type, listener) {
    Array.from(document.getElementsByClassName(classNames)).forEach(element =>
        element.addEventListener(type, listener)
    );
}

export function addSubmitEventListenerToElementsWithClassNames(
    classNames,
    listener
) {
    addEventListenerToElementsWithClassNames(classNames, "submit", listener);
}

export function addClickEventListenerToElementsWithClassNames(
    classNames,
    listener
) {
    addEventListenerToElementsWithClassNames(classNames, "click", listener);
}
