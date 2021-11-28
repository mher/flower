import { addClickEventListenerToElementWithId, urlPrefix } from "../utils";
import { showDangerAlert, showSuccessAlert } from "../alert-box";
import { JSON_HTTP_HEADERS, performPostRequest } from "../http";

const taskId = () => document.getElementById("taskid").innerText;

function onTaskRevoke(event) {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/task/revoke/${taskId()}`, {
        terminate: false,
    });
}

const onTaskTerminate = (event) => {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/task/revoke/${taskId()}`, {
        terminate: true,
    });
};

export function init() {
    addClickEventListenerToElementWithId("revoke-task", onTaskRevoke);
    addClickEventListenerToElementWithId("terminate-task", onTaskTerminate);
}
