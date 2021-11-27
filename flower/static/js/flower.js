import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import $ from "jquery";
import "@popperjs/core/dist/esm/popper";
import "bootstrap/js/dist/tab";
import "bootstrap/js/dist/dropdown";
import "../css/flower.scss";

require("datatables.net-bs5")();
require("datatables.net-colreorder-bs5")();

dayjs.extend(utc);
dayjs.extend(timezone);

const workerName = () => document.getElementById("workername").innerText;
const taskId = () => document.getElementById("taskid").innerText;
const poolSize = () => document.getElementById("pool-size").value;

function urlPrefix() {
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

const showDangerAlert = (message) => {
    showAlert(message, "danger");
};

const showSuccessAlert = (message) => {
    showAlert(message, "success");
};

const JSON_HTTP_HEADERS = {
    "Content-Type": "application/json",
};

function onTaskRevoke(event) {
    event.preventDefault();
    event.stopPropagation();

    fetch(`${urlPrefix()}/api/task/revoke/${taskId()}`, {
        method: "POST",
        body: JSON.stringify({
            terminate: false,
        }),
        headers: JSON_HTTP_HEADERS,
    })
        .then((response) => {
            if (response.status === 200) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then((json) => showSuccessAlert(json.message))
        .catch((response) => showDangerAlert(response.statusText));
}

const onTaskTerminate = (event) => {
    event.preventDefault();
    event.stopPropagation();

    fetch(`${urlPrefix()}/api/task/revoke/${taskId()}`, {
        method: "POST",
        body: JSON.stringify({
            terminate: true,
        }),
        headers: JSON_HTTP_HEADERS,
    })
        .then((response) => {
            if (response.ok) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then((json) => showSuccessAlert(json.message))
        .catch((response) => showDangerAlert(response.statusText));
};

const onPoolChange = (event, growOrShrink) => {
    event.preventDefault();
    event.stopPropagation();

    fetch(`${urlPrefix()}/api/worker/pool/${growOrShrink}/${workerName()}`, {
        method: "POST",
        body: JSON.stringify({
            workername: workerName(),
            n: poolSize(),
        }),
        headers: JSON_HTTP_HEADERS,
    })
        .then((response) => {
            if (response.ok) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then((json) => showSuccessAlert(json.message))
        .catch((response) => showDangerAlert(response.statusText));
};

const onPoolGrow = (event) => onPoolChange(event, "grow");

const onPoolShrink = (event) => onPoolChange(event, "shrink");

function onPoolAutoscale(event) {
    event.preventDefault();
    event.stopPropagation();

    const minAutoScale = document.getElementById("min-autoscale").value;
    const maxAutoScale = document.getElementById("max-autoscale").value;

    const data = JSON.stringify({
        workername: workerName(),
        min_value: minAutoScale,
        max_value: maxAutoScale,
    });

    console.log(data);

    fetch(`${urlPrefix()}/api/worker/pool/autoscale/${workerName()}`, {
        method: "POST",
        body: data,
        headers: JSON_HTTP_HEADERS,
    })
        .then((response) => {
            if (response.ok) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then((json) => showSuccessAlert(json.message))
        .catch((response) => showDangerAlert(response.statusText));
}

function onCancelConsumer(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/worker/queue/cancel-consumer/${workerName()}`,
        dataType: "json",
        data: {
            workername: workerName(),
            queue: event.target.value,
        },
        success: function (data) {
            showSuccessAlert(data.message);
            setTimeout(function () {
                $("#tab-queues")
                    .load(`/worker/${workerName()} #tab-queues`)
                    .fadeIn("show");
            }, 10000);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onAddConsumer(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/worker/queue/add-consumer/${workerName()}`,
        dataType: "json",
        data: {
            workername: workerName(),
            queue: document.getElementById("add-consumer-name").value,
        },
        success: function (data) {
            showSuccessAlert(data.message);
            setTimeout(function () {
                $("#tab-queues")
                    .load(`/worker/${workerName()} #tab-queues`)
                    .fadeIn("show");
            }, 10000);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

const taskName = (event) =>
    event.target.closest("tr").firstElementChild.textContent.split(" ")[0]; // removes [rate_limit=xxx]

function onTaskRateLimit(event) {
    event.preventDefault();
    event.stopPropagation();

    const rateLimit = event.target.firstElementChild.value;

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/task/rate-limit/${taskName(event)}`,
        dataType: "json",
        data: {
            workername: workerName(),
            ratelimit: rateLimit,
        },
        success: function (data) {
            showSuccessAlert(data.message);
            setTimeout(function () {
                $("#tab-limits")
                    .load(`/worker/${workerName()} #tab-limits`)
                    .fadeIn("show");
            }, 10000);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onTaskTimeout(event) {
    event.preventDefault();
    event.stopPropagation();

    const type = event.submitter.textContent.trim();
    const timeout = event.target.firstElementChild.value;

    const postData = {
        workername: workerName(),
    };

    postData[type] = timeout;

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/task/timeout/${taskName(event)}`,
        dataType: "json",
        data: postData,
        success: function (data) {
            showSuccessAlert(data.message);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onWorkerRefresh(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "GET",
        url: `${urlPrefix()}/api/workers`,
        dataType: "json",
        data: {
            workername: unescape(workerName()),
            refresh: 1,
        },
        success: function (data) {
            showSuccessAlert(data.message || "Refreshed");
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onRefreshAll(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "GET",
        url: `${urlPrefix()}/api/workers`,
        dataType: "json",
        data: {
            refresh: 1,
        },
        success: function (data) {
            showSuccessAlert(data.message || "Refreshed All Workers");
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onWorkerPoolRestart(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/worker/pool/restart/${workerName()}`,
        dataType: "json",
        data: {
            workername: workerName(),
        },
        success: function (data) {
            showSuccessAlert(data.message);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

function onWorkerShutdown(event) {
    event.preventDefault();
    event.stopPropagation();

    $.ajax({
        type: "POST",
        url: `${urlPrefix()}/api/worker/shutdown/${workerName()}`,
        dataType: "json",
        data: {
            workername: workerName(),
        },
        success: function (data) {
            showSuccessAlert(data.message);
        },
        error: function (data) {
            showDangerAlert(data.responseText);
        },
    });
}

document.getElementById("revoke-task")?.addEventListener("click", onTaskRevoke);
document
    .getElementById("terminate-task")
    ?.addEventListener("click", onTaskTerminate);
document.getElementById("pool-grow")?.addEventListener("click", onPoolGrow);
document.getElementById("pool-shrink")?.addEventListener("click", onPoolShrink);
document
    .getElementById("autoscale")
    ?.addEventListener("click", onPoolAutoscale);
document
    .getElementById("add-consumer")
    ?.addEventListener("click", onAddConsumer);
Array.from(document.getElementsByClassName("btn-queue")).forEach((btn) =>
    btn.addEventListener("click", onCancelConsumer)
);
Array.from(document.getElementsByClassName("form-rate-limit")).forEach((form) =>
    form.addEventListener("submit", onTaskRateLimit)
);
Array.from(document.getElementsByClassName("form-timeout")).forEach((form) =>
    form.addEventListener("submit", onTaskTimeout)
);
document
    .getElementById("worker-refresh")
    ?.addEventListener("click", onWorkerRefresh);
document
    .getElementById("worker-shut-down")
    ?.addEventListener("click", onWorkerShutdown);
document
    .getElementById("worker-pool-restart")
    ?.addEventListener("click", onWorkerPoolRestart);
document
    .getElementById("worker-refresh-all")
    ?.addEventListener("click", onRefreshAll);

function formatTime(timestamp) {
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
function htmlEscapeEntities(d) {
    return typeof d === "string"
        ? d.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        : d;
}

function activePage(name) {
    const pathname = $(location).attr("pathname");
    if (name === "/") {
        return pathname === urlPrefix() + name;
    } else {
        return pathname.startsWith(urlPrefix() + name);
    }
}

function isColumnVisible(name) {
    let columns = $("#columns").val();
    if (columns === "all") return true;
    if (columns) {
        columns = columns.split(",").map(function (e) {
            return e.trim();
        });
        return columns.indexOf(name) !== -1;
    }
    return true;
}

$.urlParam = function (name) {
    const results = new RegExp(`[\\?&]${name}=([^&#]*)`).exec(
        window.location.href
    );
    return (results && results[1]) || 0;
};

$(document).ready(function () {
    if (!activePage("/tasks")) {
        return;
    }

    $("#tasks-table").DataTable({
        rowId: "uuid",
        searching: true,
        paginate: true,
        scrollCollapse: true,
        processing: true,
        serverSide: true,
        colReorder: true,
        ajax: {
            type: "POST",
            url: `${urlPrefix()}/tasks/datatable`,
        },
        order: [[7, "desc"]],
        oSearch: {
            sSearch: $.urlParam("state") ? `state:${$.urlParam("state")}` : "",
        },
        columnDefs: [
            {
                targets: 0,
                data: "name",
                visible: isColumnVisible("name"),
                render: function (data, type, full, meta) {
                    return data;
                },
            },
            {
                targets: 1,
                data: "uuid",
                visible: isColumnVisible("uuid"),
                orderable: false,
                render: function (data, type, full, meta) {
                    return `<a href="${urlPrefix()}/task/${data}">${data}</a>`;
                },
            },
            {
                targets: 2,
                data: "state",
                visible: isColumnVisible("state"),
                render: function (data, type, full, meta) {
                    switch (data) {
                        case "SUCCESS":
                            return `<span class="badge bg-success">${data}</span>`;
                        case "FAILURE":
                            return `<span class="badge bg-danger">${data}</span>`;
                        default:
                            return `<span class="badge bg-primary">${data}</span>`;
                    }
                },
            },
            {
                targets: 3,
                data: "args",
                visible: isColumnVisible("args"),
                render: htmlEscapeEntities,
            },
            {
                targets: 4,
                data: "kwargs",
                visible: isColumnVisible("kwargs"),
                render: htmlEscapeEntities,
            },
            {
                targets: 5,
                data: "result",
                visible: isColumnVisible("result"),
                render: htmlEscapeEntities,
            },
            {
                targets: 6,
                data: "received",
                visible: isColumnVisible("received"),
                render: function (data, type, full, meta) {
                    if (data) {
                        return formatTime(data);
                    }
                    return data;
                },
            },
            {
                targets: 7,
                data: "started",
                visible: isColumnVisible("started"),
                render: function (data, type, full, meta) {
                    if (data) {
                        return formatTime(data);
                    }
                    return data;
                },
            },
            {
                targets: 8,
                data: "runtime",
                visible: isColumnVisible("runtime"),
                render: function (data, type, full, meta) {
                    return data ? data.toFixed(3) : data;
                },
            },
            {
                targets: 9,
                data: "worker",
                visible: isColumnVisible("worker"),
                render: function (data, type, full, meta) {
                    return `<a href="${urlPrefix()}/worker/${data}">${data}</a>`;
                },
            },
            {
                targets: 10,
                data: "exchange",
                visible: isColumnVisible("exchange"),
            },
            {
                targets: 11,
                data: "routing_key",
                visible: isColumnVisible("routing_key"),
            },
            {
                targets: 12,
                data: "retries",
                visible: isColumnVisible("retries"),
            },
            {
                targets: 13,
                data: "revoked",
                visible: isColumnVisible("revoked"),
            },
            {
                targets: 14,
                data: "exception",
                visible: isColumnVisible("exception"),
            },
            {
                targets: 15,
                data: "expires",
                visible: isColumnVisible("expires"),
            },
            {
                targets: 16,
                data: "eta",
                visible: isColumnVisible("eta"),
            },
        ],
    });
});

$(document).ready(function () {
    if (!activePage("/") && !activePage("/dashboard")) {
        return;
    }

    const workersTable = $("#workers-table").DataTable({
        rowId: "hostname",
        paginate: false,
        scrollY: true,
        scrollCollapse: true,
        ajax: `${urlPrefix()}/dashboard?json=1`,
        order: [[1, "asc"]],
        columnDefs: [
            {
                targets: 0,
                data: "hostname",
                type: "natural",
                render: function (data, type, full, meta) {
                    return `<a href="${urlPrefix()}/worker/${data}">${data}</a>`;
                },
            },
            {
                targets: 1,
                data: "status",
                render: function (data, type, full, meta) {
                    if (data) {
                        return '<span class="label label-success">Online</span>';
                    } else {
                        return '<span class="label label-important">Offline</span>';
                    }
                },
            },
            {
                targets: 2,
                data: "active",
                defaultContent: 0,
            },
            {
                targets: 3,
                data: "task-received",
                defaultContent: 0,
            },
            {
                targets: 4,
                data: "task-failed",
                defaultContent: 0,
            },
            {
                targets: 5,
                data: "task-succeeded",
                defaultContent: 0,
            },
            {
                targets: 6,
                data: "task-retried",
                defaultContent: 0,
            },
            {
                targets: 7,
                data: "loadavg",
                render: function (data, type, full, meta) {
                    if (Array.isArray(data)) {
                        return data.join(", ");
                    }
                    return data;
                },
            },
        ],
    });

    function columnSum(columnSelector) {
        const sum = (a, b) => a + b;
        return workersTable.column(columnSelector).data().reduce(sum, 0);
    }

    function setBtnText(columnSelector, btnName) {
        document.getElementById(
            `btn-${btnName.toLowerCase()}`
        ).innerText = `${btnName}: ${columnSum(columnSelector)}`;
    }

    function updateDashboardCounters() {
        setBtnText(2, "Active");
        setBtnText(3, "Processed");
        setBtnText(4, "Failed");
        setBtnText(5, "Succeeded");
        setBtnText(6, "Retried");
    }

    const autoRefreshInterval = $.urlParam("autorefresh") || 1;
    if (autorefresh !== 0) {
        setInterval(function () {
            workersTable.ajax.reload();
            updateDashboardCounters();
        }, autoRefreshInterval * 1000);
    }
});
