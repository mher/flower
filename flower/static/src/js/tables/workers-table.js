import $ from "jquery";
import { activePage, urlPrefix } from "../utils";

require("datatables.net-bs5")();
require("datatables.net-colreorder-bs5")();

export const initWorkersTable = () =>
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
