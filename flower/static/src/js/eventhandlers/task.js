import { performPostRequest } from "../http";
import { addClickEventListenerToElementWithId } from "../utils";

const taskId = () => document.getElementById("taskid").innerText;

function onTaskRevoke(event) {
    event.preventDefault();
    event.stopPropagation();

    performPostRequest(`api/task/revoke/${taskId()}`, {
        terminate: false,
    });
}

const onTaskTerminate = event => {
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
