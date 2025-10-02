/*jslint browser: true */
/*global $, WebSocket, jQuery */

var flower = (function () {
    "use strict";

    var alertContainer = document.getElementById('alert-container');
    function show_alert(message, type) {
        var wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible" role="alert">
                <div>${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
        alertContainer.appendChild(wrapper);
    }

    function url_prefix() {
        var prefix = $('#url_prefix').val();
        if (prefix) {
            prefix = prefix.replace(/\/+$/, '');
            if (prefix.startsWith('/')) {
                return prefix;
            } else {
                return '/' + prefix;
            }
        }
        return '';
    }

    //https://github.com/DataTables/DataTables/blob/1.10.11/media/js/jquery.dataTables.js#L14882
    function htmlEscapeEntities(d) {
        return typeof d === 'string' ?
            d.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') :
            d;
    }

    function active_page(name) {
        var pathname = $(location).attr('pathname');
        if (name === '/') {
            return pathname === (url_prefix() + name);
        }
        else {
            return pathname.startsWith(url_prefix() + name);
        }
    }

    function applyTheme(theme) {
        var htmlEl = document.documentElement;
        var resolved = theme;
        if (!resolved || resolved === 'system') {
            var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            resolved = prefersDark ? 'dark' : 'light';
        }
        htmlEl.setAttribute('data-bs-theme', resolved);
        localStorage.setItem('flower-theme', theme || 'system');
    }

    function initTheme() {
        var stored = localStorage.getItem('flower-theme') || 'system';
        applyTheme(stored);
        if (window.matchMedia) {
            var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            if (mediaQuery) {
                var syncSystemTheme = function () {
                    var current = localStorage.getItem('flower-theme') || 'system';
                    if (current === 'system') {
                        applyTheme('system');
                    }
                };
                if (typeof mediaQuery.addEventListener === 'function') {
                    mediaQuery.addEventListener('change', syncSystemTheme);
                } else if (typeof mediaQuery.addListener === 'function') {
                    mediaQuery.addListener(syncSystemTheme);
                }
            }
        }
    }

    $('#worker-refresh').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        $('.dropdown-toggle').dropdown('hide');

        var workername = $('#workername').text();

        $.ajax({
            type: 'GET',
            url: url_prefix() + '/api/workers',
            dataType: 'json',
            data: {
                workername: unescape(workername),
                refresh: 1
            },
            success: function (data) {
                show_alert(data.message || 'Successfully refreshed', 'success');
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-refresh-all').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        $('.dropdown-toggle').dropdown('hide');

        $.ajax({
            type: 'GET',
            url: url_prefix() + '/api/workers',
            dataType: 'json',
            data: {
                refresh: 1
            },
            success: function (data) {
                show_alert(data.message || 'Refreshed All Workers', 'success');
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-pool-restart').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        $('.dropdown-toggle').dropdown('hide');

        var workername = $('#workername').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/restart/' + workername,
            dataType: 'json',
            data: {
                workername: workername
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-shutdown').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        $('.dropdown-toggle').dropdown('hide');

        var workername = $('#workername').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/shutdown/' + workername,
            dataType: 'json',
            data: {
                workername: workername
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-pool-grow').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            grow_size = $('#pool-size').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/grow/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': grow_size,
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-pool-shrink').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            shrink_size = $('#pool-size').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/shrink/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': shrink_size,
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-pool-autoscale').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            min = $('#min-autoscale').val(),
            max = $('#max-autoscale').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/pool/autoscale/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'min': min,
                'max': max,
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-add-consumer').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            queue = $('#add-consumer-name').val();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/queue/add-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#worker-queues').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        if (!event.target.id.startsWith("worker-cancel-consumer")) {
            return;
        }

        var workername = $('#workername').text(),
            queue = $(event.target).closest("tr").children("td:eq(0)").text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/worker/queue/cancel-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_alert(data.message, "success");
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#limits-table').on('click', function (event) {
        if (event.target.id.startsWith("task-timeout-")) {
            var timeout = parseInt($(event.target).siblings().closest("input").val()),
                type = $(event.target).text().toLowerCase(),
                taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
                post_data = {'workername': $('#workername').text()};

            taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]
            post_data[type] = timeout;

            if (!Number.isInteger(timeout)) {
                show_alert("Invalid timeout value", "danger");
                return;
            }

            $.ajax({
                type: 'POST',
                url: url_prefix() + '/api/task/timeout/' + taskname,
                dataType: 'json',
                data: post_data,
                success: function (data) {
                    show_alert(data.message, "success");
                },
                error: function (data) {
                    show_alert($(data.responseText).text(), "danger");
                }
            });
        } else if (event.target.id.startsWith("task-rate-limit-")) {
            var taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
                workername = $('#workername').text(),
                ratelimit = parseInt($(event.target).prev().val());

            taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]

            $.ajax({
                type: 'POST',
                url: url_prefix() + '/api/task/rate-limit/' + taskname,
                dataType: 'json',
                data: {
                    'workername': workername,
                    'ratelimit': ratelimit,
                },
                success: function (data) {
                    show_alert(data.message, "success");
                },
                error: function (data) {
                    show_alert(data.responseText, "danger");
                }
            });
        }
    });

    $('#task-revoke').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var taskid = $('#taskid').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/revoke/' + taskid,
            dataType: 'json',
            data: {
                'terminate': false,
            },
            success: function (data) {
                show_alert(data.message, "success");
                document.getElementById("task-revoke").disabled = true;
                setTimeout(function() {location.reload();}, 5000);
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    $('#task-terminate').on('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        var taskid = $('#taskid').text();

        $.ajax({
            type: 'POST',
            url: url_prefix() + '/api/task/revoke/' + taskid,
            dataType: 'json',
            data: {
                'terminate': true,
            },
            success: function (data) {
                show_alert(data.message, "success");
                document.getElementById("task-terminate").disabled = true;
                setTimeout(function() {location.reload();}, 5000);
            },
            error: function (data) {
                show_alert(data.responseText, "danger");
            }
        });
    });

    function sum(a, b) {
        return parseInt(a, 10) + parseInt(b, 10);
    }

    function format_time(timestamp) {
        var time = $('#time').val(),
            prefix = time.startsWith('natural-time') ? 'natural-time' : 'time',
            tz = time.substr(prefix.length + 1) || 'UTC';

        if (prefix === 'natural-time') {
            return moment.unix(timestamp).tz(tz).fromNow();
        }
        return moment.unix(timestamp).tz(tz).format('YYYY-MM-DD HH:mm:ss.SSS');
    }

    function isColumnVisible(name) {
        var columns = $('#columns').val();
        if (columns === "all")
            return true;
        if (columns) {
            columns = columns.split(',').map(function (e) {
                return e.trim();
            });
            return columns.indexOf(name) !== -1;
        }
        return true;
    }

    $.urlParam = function (name) {
        var results = new RegExp('[\\?&]' + name + '=([^&#]*)').exec(window.location.href);
        return (results && results[1]) || 0;
    };

    $(document).ready(function () {
        //https://github.com/twitter/bootstrap/issues/1768
        var shiftWindow = function () {
            scrollBy(0, -50);
        };
        if (location.hash) {
            shiftWindow();
        }
        window.addEventListener("hashchange", shiftWindow);

        // Make bootstrap tabs persistent
        $(document).ready(function () {
            initTheme();
            $(document).on('click', '.theme-choice', function (e) {
                e.preventDefault();
                var choice = $(this).data('theme');
                applyTheme(choice);
            });
            if (location.hash !== '') {
                $('a[href="' + location.hash + '"]').tab('show');
            }

            // Listen for tab shown events and update the URL hash fragment accordingly
            $('.nav-tabs a[data-bs-toggle="tab"]').on('shown.bs.tab', function (event) {
                const tabPaneId = $(event.target).attr('href').substr(1);
                if (tabPaneId) {
                    window.location.hash = tabPaneId;
                }
            });
        });
    });

    $(document).ready(function () {
        if (!active_page('/') && !active_page('/workers')) {
            return;
        }

        $('#workers-table').DataTable({
            rowId: 'name',
            searching: true,
            select: false,
            paging: true,
            scrollCollapse: true,
            lengthMenu: [15, 30, 50, 100],
            pageLength: 15,
            language: {
                lengthMenu: 'Show _MENU_ workers',
                info: 'Showing _START_ to _END_ of _TOTAL_ workers',
                infoFiltered: '(filtered from _MAX_ total workers)'
            },
            ajax: url_prefix() + '/workers?json=1',
            order: [
                [1, "des"]
            ],
            footerCallback: function( tfoot, data, start, end, display ) {
                var api = this.api();
                var columns = {2:"STARTED", 3:"", 4:"FAILURE", 5:"SUCCESS", 6:"RETRY"};
                for (const [column, state] of Object.entries(columns)) {
                    var total = api.column(column).data().reduce(sum, 0);
                    var footer = total;
                    if (total !== 0) {
                        let queryParams = (state !== '' ? `?state=${state}` : '');
                        footer = '<a href="' + url_prefix() + '/tasks' + queryParams + '">' + total + '</a>';
                    }
                    $(api.column(column).footer()).html(footer);
                }
            },
            columnDefs: [{
                targets: 0,
                data: 'hostname',
                type: 'natural',
                render: function (data, type, full, meta) {
                    return '<a href="' + url_prefix() + '/worker/' + encodeURIComponent(data) + '">' + data + '</a>';
                }
            }, {
                targets: 1,
                data: 'status',
                className: "text-center",
                width: "10%",
                render: function (data, type, full, meta) {
                    if (data) {
                        return '<span class="badge bg-success">Online</span>';
                    } else {
                        return '<span class="badge bg-secondary">Offline</span>';
                    }
                }
            }, {
                targets: 2,
                data: 'active',
                className: "text-center",
                width: "10%",
                defaultContent: 0
            }, {
                targets: 3,
                data: 'task-received',
                className: "text-center",
                width: "10%",
                defaultContent: 0
            }, {
                targets: 4,
                data: 'task-failed',
                className: "text-center",
                width: "10%",
                defaultContent: 0
            }, {
                targets: 5,
                data: 'task-succeeded',
                className: "text-center",
                width: "10%",
                defaultContent: 0
            }, {
                targets: 6,
                data: 'task-retried',
                className: "text-center",
                width: "10%",
                defaultContent: 0
            }, {
                targets: 7,
                data: 'loadavg',
                width: "10%",
                className: "text-center text-nowrap",
                render: function (data, type, full, meta) {
                    if (!full.status) {
                        return 'N/A';
                    }
                    if (Array.isArray(data)) {
                        return data.join(', ');
                    }
                    return data;
                }
            }, ],
        });

        var autorefresh_interval = $.urlParam('autorefresh') || 1;
        if (autorefresh !== 0) {
            setInterval( function () {
                $('#workers-table').DataTable().ajax.reload(null, false);
            }, autorefresh_interval * 1000);
        }

    });

    $(document).ready(function () {
        if (!active_page('/tasks')) {
            return;
        }

        var stateFilterControl = $('#state-filter-control');
        var statusToggleButton = stateFilterControl.find('#status-filter-toggle');
        var statusOptionsContainer = stateFilterControl.find('#status-filter-options');
        var statusDropdownElement = statusToggleButton.length ? statusToggleButton[0] : null;
        var statusDropdownInstance = null;
        stateFilterControl = stateFilterControl.detach();
        var statusIdCounter = 0;
        var selectionLockedFromUrl = false;

        var defaultStates = [
            'FAILURE', 'IGNORED', 'PENDING', 'QUEUED', 'RECEIVED',
            'REJECTED', 'RETRY', 'REVOKED', 'SCHEDULED', 'SENT',
            'STARTED', 'SUCCESS', 'UNKNOWN'
        ];

        var knownStates = defaultStates.slice();
        var selectedStates = new Set(knownStates);

        function normalizeState(value) {
            if (!value) {
                return 'UNKNOWN';
            }
            return value.toString().trim().toUpperCase();
        }

        function updateStatusSummary() {
            var label;
            if (selectedStates.size === 0) {
                label = 'None';
            } else if (selectedStates.size === knownStates.length) {
                label = 'All';
            } else if (selectedStates.size === 1) {
                label = Array.from(selectedStates)[0];
            } else {
                label = selectedStates.size + ' selected';
            }
            statusToggleButton.text(label);
            statusToggleButton.attr('aria-label', 'Filter task states. Currently: ' + label + '.');
        }

        function buildOption(state) {
            var safeState = normalizeState(state);
            var optionId = 'status-filter-' + (safeState.replace(/[^a-z0-9_-]/gi, '').toLowerCase() || ('state-' + statusIdCounter));
            statusIdCounter += 1;

            var option = $('<div>', {
                'class': 'status-filter-option d-flex align-items-center',
                'data-state': safeState
            });

            var checkbox = $('<input>', {
                type: 'checkbox',
                'class': 'form-check-input status-filter-checkbox me-2',
                id: optionId,
                value: safeState
            }).prop('checked', selectedStates.has(safeState));

            var label = $('<label>', {
                'class': 'status-filter-option-label flex-grow-1 mb-0',
                for: optionId,
                text: safeState
            });

            var onlyButton = $('<button>', {
                type: 'button',
                'class': 'btn btn-link btn-sm p-0 status-only',
                'data-state': safeState,
                text: 'Only'
            });

            option.append(checkbox, label, onlyButton);
            statusOptionsContainer.append(option);
        }

        function rebuildStatusOptions() {
            statusOptionsContainer.empty();
            statusIdCounter = 0;
            knownStates.forEach(function (state) {
                buildOption(state);
            });
            updateStatusSummary();
        }

        function ensureKnownStates(states) {
            var addedStates = [];
            states.forEach(function (raw) {
                var state = normalizeState(raw);
                if (knownStates.indexOf(state) === -1) {
                    knownStates.push(state);
                    addedStates.push(state);
                }
            });
            if (addedStates.length) {
                knownStates.sort();
                rebuildStatusOptions();
            }
            return addedStates;
        }

        function setSelectedStates(values) {
            selectedStates = new Set(Array.from(values));
            statusOptionsContainer.find('.status-filter-checkbox').each(function () {
                this.checked = selectedStates.has(this.value);
            });
            updateStatusSummary();
        }

        function getSelectedStates() {
            return Array.from(selectedStates);
        }

        var rawStateParam = $.urlParam('state');
        if (typeof rawStateParam === 'string' && rawStateParam !== '') {
            var initialState = normalizeState(rawStateParam);
            var addedInitialStates = ensureKnownStates([initialState]);
            var initialSelection = new Set([initialState]);
            addedInitialStates.forEach(function (state) {
                initialSelection.add(state);
            });
            setSelectedStates(initialSelection);
            selectionLockedFromUrl = true;
        }
        rebuildStatusOptions();

        function extractStatesFromSearch(rawSearch) {
            if (!rawSearch) {
                return null;
            }
            var pattern = /(\s*)(?:state|status):(?:"([^"]+)"|([^\s]+))/gi;
            var cleaned = rawSearch;
            var states = [];
            var match;
            while ((match = pattern.exec(rawSearch)) !== null) {
                var value = match[2] || match[3];
                if (value) {
                    states.push(normalizeState(value));
                }
                cleaned = cleaned.replace(match[0], ' ');
            }
            cleaned = cleaned.replace(/\s+/g, ' ').trim();
            if (!states.length) {
                return null;
            }
            return {
                states: states,
                cleaned: cleaned
            };
        }

        statusOptionsContainer.on('change', '.status-filter-checkbox', function () {
            var value = normalizeState(this.value);
            if (this.checked) {
                selectedStates.add(value);
            } else {
                selectedStates.delete(value);
            }
            updateStatusSummary();
            dt.ajax.reload();
        });

        stateFilterControl.on('click', '.status-filter-dropdown', function (event) {
            event.stopPropagation();
        });

        stateFilterControl.on('click', '.status-filter-dropdown .dropdown-menu', function (event) {
            event.stopPropagation();
        });

        statusToggleButton.on('click', function (event) {
            event.stopPropagation();
        });

        statusOptionsContainer.on('click', function (event) {
            event.stopPropagation();
        });

        stateFilterControl.on('click', '.status-select-all', function (event) {
            event.preventDefault();
            setSelectedStates(knownStates);
            dt.ajax.reload();
            if (statusDropdownInstance) {
                statusDropdownInstance.hide();
            }
        });

        stateFilterControl.on('click', '.status-select-none', function (event) {
            event.preventDefault();
            setSelectedStates([]);
            dt.ajax.reload();
            if (statusDropdownInstance) {
                statusDropdownInstance.hide();
            }
        });

        statusOptionsContainer.on('click', '.status-only', function (event) {
            event.preventDefault();
            var value = normalizeState($(this).data('state'));
            setSelectedStates([value]);
            if (statusDropdownInstance) {
                statusDropdownInstance.hide();
            }
            dt.ajax.reload();
        });

        var dt = $('#tasks-table').DataTable({
            rowId: 'uuid',
            searching: true,
            scrollX: true,
            scrollCollapse: true,
            processing: true,
            serverSide: true,
            colReorder: true,
            lengthMenu: [15, 30, 50, 100],
            pageLength: 15,
            stateSave: true,
            language: {
                lengthMenu: 'Show _MENU_ tasks',
                info: 'Showing _START_ to _END_ of _TOTAL_ tasks',
                infoFiltered: '(filtered from _MAX_ total tasks)'
            },
            ajax: {
                type: 'POST',
                url: url_prefix() + '/tasks/datatable',
                data: function(d) {
                    var states = getSelectedStates();
                    if (states.length === 0) {
                        d.include_states = '__none__';
                    } else if (states.length === knownStates.length) {
                        d.include_states = '';
                    } else {
                        d.include_states = states.join(',');
                    }
                }
            },
            order: [
                [7, "desc"]
            ],
            oSearch: { "sSearch": '' },
            columnDefs: [{
                targets: 0,
                data: 'name',
                visible: isColumnVisible('name'),
                render: function (data, type, full, meta) {
                    return data;
                }
            }, {
                targets: 1,
                data: 'uuid',
                visible: isColumnVisible('uuid'),
                orderable: false,
                className: "text-nowrap",
                render: function (data, type, full, meta) {
                    return '<a href="' + url_prefix() + '/task/' + encodeURIComponent(data) + '">' + data + '</a>';
                }
            }, {
                targets: 2,
                data: 'state',
                visible: isColumnVisible('state'),
                className: "text-center",
                render: function (data, type, full, meta) {
                    switch (data) {
                    case 'SUCCESS':
                        return '<span class="badge bg-success">' + data + '</span>';
                    case 'FAILURE':
                        return '<span class="badge bg-danger">' + data + '</span>';
                    default:
                        return '<span class="badge bg-secondary">' + data + '</span>';
                    }
                }
            }, {
                targets: 3,
                data: 'args',
                className: "text-nowrap overflow-auto",
                visible: isColumnVisible('args'),
                render: htmlEscapeEntities
            }, {
                targets: 4,
                data: 'kwargs',
                className: "text-nowrap overflow-auto",
                visible: isColumnVisible('kwargs'),
                render: htmlEscapeEntities
            }, {
                targets: 5,
                data: 'result',
                visible: isColumnVisible('result'),
                className: "text-nowrap overflow-auto",
                render: htmlEscapeEntities
            }, {
                targets: 6,
                data: 'received',
                className: "text-nowrap",
                visible: isColumnVisible('received'),
                render: function (data, type, full, meta) {
                    if (data) {
                        return format_time(data);
                    }
                    return data;
                }
            }, {
                targets: 7,
                data: 'started',
                className: "text-nowrap",
                visible: isColumnVisible('started'),
                render: function (data, type, full, meta) {
                    if (data) {
                        return format_time(data);
                    }
                    return data;
                }
            }, {
                targets: 8,
                data: 'runtime',
                className: "text-center",
                visible: isColumnVisible('runtime'),
                render: function (data, type, full, meta) {
                    return data ? data.toFixed(2) : data;
                }
            }, {
                targets: 9,
                data: 'worker',
                visible: isColumnVisible('worker'),
                render: function (data, type, full, meta) {
                    return '<a href="' + url_prefix() + '/worker/' + encodeURIComponent(data) + '">' + data + '</a>';
                }
            }, {
                targets: 10,
                data: 'exchange',
                visible: isColumnVisible('exchange')
            }, {
                targets: 11,
                data: 'routing_key',
                visible: isColumnVisible('routing_key')
            }, {
                targets: 12,
                data: 'retries',
                className: "text-center",
                visible: isColumnVisible('retries')
            }, {
                targets: 13,
                data: 'revoked',
                className: "text-nowrap",
                visible: isColumnVisible('revoked'),
                render: function (data, type, full, meta) {
                    if (data) {
                        return format_time(data);
                    }
                    return data;
                }
            }, {
                targets: 14,
                data: 'exception',
                className: "text-nowrap",
                visible: isColumnVisible('exception')
            }, {
                targets: 15,
                data: 'expires',
                visible: isColumnVisible('expires')
            }, {
                targets: 16,
                data: 'eta',
                visible: isColumnVisible('eta')
            }, ],
        });

        var filterContainer = $('#tasks-table_filter');
        if (filterContainer.length && stateFilterControl.length) {
            filterContainer.prepend(stateFilterControl.removeClass('d-none'));
        }

        if (statusDropdownElement && window.bootstrap && window.bootstrap.Dropdown) {
            statusDropdownInstance = window.bootstrap.Dropdown.getOrCreateInstance(
                statusDropdownElement,
                { autoClose: 'outside' }
            );
        }

        // Improve search placeholder to hint advanced usage
        var searchInput = $('#tasks-table_filter input');
        searchInput.attr('placeholder', 'Search tasks...');

        if (!selectionLockedFromUrl) {
            var savedState = dt.state.loaded && dt.state.loaded();
            if (savedState && savedState.search && typeof savedState.search.search === 'string') {
                var extraction = extractStatesFromSearch(savedState.search.search);
                if (extraction) {
                    ensureKnownStates(extraction.states);
                    setSelectedStates(extraction.states);
                    if (extraction.cleaned !== savedState.search.search) {
                        dt.search(extraction.cleaned);
                        if (searchInput.length) {
                            searchInput.val(extraction.cleaned);
                        }
                    }
                }
            }
        }

        function triggerFilterReload() {
            dt.ajax.reload();
        }

        dt.on('xhr', function (event, settings, json) {
            if (!json || !Array.isArray(json.data)) {
                return;
            }
            var observedStates = [];
            json.data.forEach(function (task) {
                if (task && task.state) {
                    observedStates.push(task.state);
                }
            });
            if (observedStates.length) {
                var previousSelection = new Set(selectedStates);
                var newStates = ensureKnownStates(observedStates);
                newStates.forEach(function (state) {
                    previousSelection.add(normalizeState(state));
                });
                setSelectedStates(previousSelection);
            }
        });

        triggerFilterReload();

    });

}(jQuery));
