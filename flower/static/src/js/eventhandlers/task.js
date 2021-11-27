import { addClickEventListenerToElementWithId, urlPrefix } from "../utils";
import { showDangerAlert, showSuccessAlert } from "../alert-box";
import { JSON_HTTP_HEADERS } from "../http";

const taskId = () => document.getElementById("taskid").innerText;

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

export function init() {
    addClickEventListenerToElementWithId("revoke-task", onTaskRevoke);
    addClickEventListenerToElementWithId("terminate-task", onTaskTerminate);
}
