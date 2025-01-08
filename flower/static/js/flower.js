/*jslint browser: true */
/*global $, WebSocket, jQuery */

var flower = (function () {
    "use strict";
    /*jslint browser: true */
    /*jslint unparam: true, node: true */
    /*global $, WebSocket, jQuery, Rickshaw */

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

    function update_dashboard_counters() {
        var table = $('#workers-table').DataTable();
        $('a#btn-active').text('Active: ' + table.column(2).data().reduce(sum, 0));
        $('a#btn-processed').text('Processed: ' + table.column(3).data().reduce(sum, 0));
        $('a#btn-failed').text('Failed: ' + table.column(4).data().reduce(sum, 0));
        $('a#btn-succeeded').text('Succeeded: ' + table.column(5).data().reduce(sum, 0));
        $('a#btn-retried').text('Retried: ' + table.column(6).data().reduce(sum, 0));
    }

    function on_cancel_task_filter(event) {
        event.preventDefault();
        event.stopPropagation();

        $('#task-filter-form').each(function () {
            $(this).find('SELECT').val('');
            $(this).find('.datetimepicker').val('');
        });

        $('#task-filter-form').submit();
    }

    function create_graph(data, id, width, height, metric) {
        id = id || '';
        width = width || 500;
        height = height || 300;
        metric = metric || '';

        var name, seriesData = [],
            palette, graph, ticksTreatment, timeUnit, xAxis, yAxis, hoverDetail,
            legend, shelving, order, highlighter;
        for (name in data) {
            if (data.hasOwnProperty(name)) {
                seriesData.push({
                    name: name
                });
            }
        }

        palette = new Rickshaw.Color.Palette({
            scheme: 'colorwheel'
        });

        graph = new Rickshaw.Graph({
            element: document.getElementById("chart" + id),
            width: width,
            height: height,
            renderer: 'stack',
            series: new Rickshaw.Series(seriesData, palette),
            maxDataPoints: 10000,
            padding: {
                top: 0.1,
                left: 0.01,
                right: 0.01,
                bottom: 0.01
            },
        });

        ticksTreatment = 'glow';

        timeUnit = new Rickshaw.Fixtures.Time.Local();
        timeUnit.formatTime = function (d) {
            return moment(d).format("YYYY-MM-DD HH:mm:ss");
        };
        timeUnit.unit("minute");

        xAxis = new Rickshaw.Graph.Axis.Time({
            graph: graph,
            timeFixture: new Rickshaw.Fixtures.Time.Local(),
            ticksTreatment: ticksTreatment,
            timeUnit: timeUnit
        });

        xAxis.render();

        yAxis = new Rickshaw.Graph.Axis.Y({
            graph: graph,
            tickFormat: Rickshaw.Fixtures.Number.formatKMBT,
            ticksTreatment: ticksTreatment,
        });

        yAxis.render();

        hoverDetail = new Rickshaw.Graph.HoverDetail({
            graph: graph,
            yFormatter: function (y) {
                if (y % 1 === 0) {
                    return y + metric;
                } else {
                    return y.toFixed(2) + metric;
                }
            },
            xFormatter: function (x) {
                return moment(x * 1e3).format("YYYY-MM-DD HH:mm:ss");
            }
        });

        legend = new Rickshaw.Graph.Legend({
            graph: graph,
            element: document.getElementById('legend' + id)
        });

        shelving = new Rickshaw.Graph.Behavior.Series.Toggle({
            graph: graph,
            legend: legend
        });

        order = new Rickshaw.Graph.Behavior.Series.Order({
            graph: graph,
            legend: legend
        });

        highlighter = new Rickshaw.Graph.Behavior.Series.Highlight({
            graph: graph,
            legend: legend
        });

        legend.shelving = shelving;
        graph.series.legend = legend;

        graph.render();
        return graph;
    }

    function update_graph(graph, url, lastquery) {
        $.ajax({
            type: 'GET',
            url: url,
            data: {
                lastquery: lastquery
            },
            success: function (data) {
                graph.series.addData(data);
                graph.update();
            },
        });
    }

    function current_unix_time() {
        var now = new Date();
        return Date.UTC(now.getUTCFullYear(), now.getUTCMonth(),
            now.getUTCDate(), now.getUTCHours(),
            now.getUTCMinutes(), now.getUTCSeconds()) / 1000;
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

        if (active_page('/monitor')) {
            var sts = current_unix_time(),
                fts = current_unix_time(),
                tts = current_unix_time(),
                updateinterval = parseInt($.urlParam('updateInterval'), 10) || 1000,
                succeeded_graph = null,
                failed_graph = null,
                time_graph = null,
                broker_graph = null;

            $.ajax({
                type: 'GET',
                url: url_prefix() + '/monitor/succeeded-tasks',
                data: {
                    lastquery: current_unix_time()
                },
                success: function (data) {
                    succeeded_graph = create_graph(data, '-succeeded');
                    succeeded_graph.update();

                    succeeded_graph.series.setTimeInterval(updateinterval);
                    setInterval(function () {
                        update_graph(succeeded_graph,
                            url_prefix() + '/monitor/succeeded-tasks',
                            sts);
                        sts = current_unix_time();
                    }, updateinterval);

                },
            });

            $.ajax({
                type: 'GET',
                url: url_prefix() + '/monitor/completion-time',
                data: {
                    lastquery: current_unix_time()
                },
                success: function (data) {
                    time_graph = create_graph(data, '-time', null, null, 's');
                    time_graph.update();

                    time_graph.series.setTimeInterval(updateinterval);
                    setInterval(function () {
                        update_graph(time_graph,
                            url_prefix() + '/monitor/completion-time',
                            tts);
                        tts = current_unix_time();
                    }, updateinterval);

                },
            });

            $.ajax({
                type: 'GET',
                url: url_prefix() + '/monitor/failed-tasks',
                data: {
                    lastquery: current_unix_time()
                },
                success: function (data) {
                    failed_graph = create_graph(data, '-failed');
                    failed_graph.update();

                    failed_graph.series.setTimeInterval(updateinterval);
                    setInterval(function () {
                        update_graph(failed_graph,
                            url_prefix() + '/monitor/failed-tasks',
                            fts);
                        fts = current_unix_time();
                    }, updateinterval);

                },
            });

            $.ajax({
                type: 'GET',
                url: url_prefix() + '/monitor/broker',
                success: function (data) {
                    broker_graph = create_graph(data, '-broker');
                    broker_graph.update();

                    broker_graph.series.setTimeInterval(updateinterval);
                    setInterval(function () {
                        update_graph(broker_graph,
                            url_prefix() + '/monitor/broker');
                    }, updateinterval);

                },
            });

        }

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

        $('#tasks-table').DataTable({
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
                url: url_prefix() + '/tasks/datatable'
            },
            order: [
                [7, "desc"]
            ],
            oSearch: {
                "sSearch": $.urlParam('state') ? 'state:' + $.urlParam('state') : ''
            },
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

    });

}(jQuery));
