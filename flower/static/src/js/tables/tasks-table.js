import $ from "jquery";

import {
    activePage,
    formatTime,
    htmlEscapeEntities,
    urlPrefix,
} from "../utils";

require("datatables.net-bs5")();
require("datatables.net-colreorder-bs5")();

export const initTasksTable = () => {
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

    return $(document).ready(function () {
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
                sSearch: $.urlParam("state")
                    ? `state:${$.urlParam("state")}`
                    : "",
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
};
