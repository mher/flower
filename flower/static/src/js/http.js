import { showDangerAlert, showSuccessAlert } from "./alert-box";
import { urlPrefix } from "./utils";

export const JSON_HTTP_HEADERS = {
    "Content-Type": "application/json",
};

export function performGetRequest(
    path,
    data = {},
    onSuccess = json => showSuccessAlert(json.message)
) {
    const url = new URL(window.location.href);
    url.pathname = `${urlPrefix()}/${path}`;
    Object.entries(data).forEach(item =>
        url.searchParams.append(item[0], item[1])
    );

    fetch(url.toString(), {
        method: "GET",
        headers: {
            Accept: "application/json, text/javascript, */*; q=0.01",
        },
    })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then(json => onSuccess(json))
        .catch(async response => {
            const text = await response.text();
            showDangerAlert(text);
        });
}

export function performPostRequest(
    url,
    data = {},
    onSuccess = json => showSuccessAlert(json.message)
) {
    const formData = new URLSearchParams();
    Object.entries(data).forEach(item => formData.append(item[0], item[1]));

    fetch(`${urlPrefix()}/${url}`, {
        method: "POST",
        mode: "cors",
        body: formData,
        headers: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            Accept: "application/json, text/javascript, */*; q=0.01",
        },
    })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            return Promise.reject(response);
        })
        .then(json => onSuccess(json))
        .catch(async response => {
            const text = await response.text();
            showDangerAlert(text);
        });
}
