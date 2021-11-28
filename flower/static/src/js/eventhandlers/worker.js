import {
    addClickEventListenerToElementsWithClassNames,
    addClickEventListenerToElementWithId,
    addSubmitEventListenerToElementsWithClassNames,
    urlPrefix,
} from "../utils";
import { showSuccessAlert } from "../alert-box";
import { performGetRequest, performPostRequest } from "../http";

const workerName = () => document.getElementById("workername").innerText;
const poolSize = () => document.getElementById("pool-size").value;

const onPoolChange = (event, growOrShrink) => {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/worker/pool/${growOrShrink}/${workerName()}`, {
        workername: workerName(),
        n: poolSize(),
    });
};

const onPoolGrow = (event) => onPoolChange(event, "grow");
const onPoolShrink = (event) => onPoolChange(event, "shrink");

function onPoolAutoscale(event) {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/worker/pool/autoscale/${workerName()}`, {
        min: document.getElementById("min-autoscale").value,
        max: document.getElementById("max-autoscale").value,
    });
}

function onCancelConsumer(event) {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/worker/queue/cancel-consumer/${workerName()}`, {
        workername: workerName(),
        queue: event.target.value,
    });
}

function onAddConsumer(event) {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/worker/queue/add-consumer/${workerName()}`, {
        workername: workerName(),
        queue: document.getElementById("add-consumer-name").value,
    });
}

const taskName = (event) =>
    event.target.closest("tr").firstElementChild.textContent.split(" ")[0]; // removes [rate_limit=xxx]

function onTaskRateLimit(event) {
    event.preventDefault();
    event.stopPropagation();

    const rateLimit = event.target.firstElementChild.value;

    performPostRequest(`api/task/rate-limit/${taskName(event)}`, {
        workername: workerName(),
        ratelimit: rateLimit,
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

    performPostRequest(`api/task/timeout/${taskName(event)}`, postData);
}

function onWorkerRefresh(event) {
    event.preventDefault();

    performGetRequest(
        `api/workers`,
        {
            workername: unescape(workerName()),
            refresh: 1,
        },
        (json) => {
            showSuccessAlert(json.message || "Refreshed");
        }
    );
}

function onRefreshAll(event) {
    event.preventDefault();

    performGetRequest(
        `api/workers`,
        {
            refresh: 1,
        },
        (json) => {
            showSuccessAlert(json.message || "Refreshed All Workers");
        }
    );
}

function onWorkerPoolRestart(event) {
    event.preventDefault();

    performPostRequest(`api/worker/pool/restart/${workerName()}`);
}

function onWorkerShutdown(event) {
    event.preventDefault();

    performPostRequest(`api/worker/shutdown/${workerName()}`);
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
