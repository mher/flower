import $ from "jquery";
import {
    addClickEventListenerToElementsWithClassNames,
    addClickEventListenerToElementWithId,
    addSubmitEventListenerToElementsWithClassNames,
    urlPrefix,
} from "../utils";
import { showDangerAlert, showSuccessAlert } from "../alert-box";
import { JSON_HTTP_HEADERS } from "../http";

const workerName = () => document.getElementById("workername").innerText;
const poolSize = () => document.getElementById("pool-size").value;

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

export function init() {
    addClickEventListenerToElementWithId("pool-grow", onPoolGrow);
    addClickEventListenerToElementWithId("pool-shrink", onPoolShrink);
    addClickEventListenerToElementWithId("autoscale", onPoolAutoscale);
    addClickEventListenerToElementWithId("add-consumer", onAddConsumer);
    addClickEventListenerToElementsWithClassNames(
        "btn-queue",
        onCancelConsumer
    );
    addSubmitEventListenerToElementsWithClassNames(
        "form-rate-limit",
        onTaskRateLimit
    );
    addSubmitEventListenerToElementsWithClassNames(
        "form-timeout",
        onTaskTimeout
    );
    addClickEventListenerToElementWithId("worker-refresh", onWorkerRefresh);
    addClickEventListenerToElementWithId("worker-shut-down", onWorkerShutdown);
    addClickEventListenerToElementWithId(
        "worker-pool-restart",
        onWorkerPoolRestart
    );
    addClickEventListenerToElementWithId("worker-refresh-all", onRefreshAll);
}
