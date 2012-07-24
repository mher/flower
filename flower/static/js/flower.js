var flower = (function () {
    "use strict";
    /*jslint browser: true */
    /*global $, WebSocket, jQuery */

    function on_alert_close(event) {
        event.preventDefault();
        event.stopPropagation();
        $(event.target).parent().hide();
    }

    function show_error_alert(message) {
        $("#alert").removeClass("alert-success").addClass("alert-error");
        $("#alert-message").html("<strong>Error!</strong>    " + message);
        $("#alert").show();
    }

    function show_success_alert(message) {
        $("#alert").removeClass("alert-error").addClass("alert-success");
        $("#alert-message").html("<strong>Success!</strong>    " + message);
        $("#alert").show();
    }

    function _get_selected_workers(){
        return $('#workers-table tr').has('td.is_selected > input:checked');
    }

    function toggle_selected_workers(event){
        var $checkbox = $('#select-workers-toggler');

        $checkbox.is(':checked') ? select_all_workers()
                                 : select_none_workers();
    }

    function select_all_workers(){
        $('#workers-table td.is_selected > input').filter(':not(:checked)').click();
    }

    function select_none_workers(){
        $('#workers-table td.is_selected > input:checked').click();
    }

    function shutdown_selected(event) {
        var $selected_workes = _get_selected_workers();

        /* atomic would be better with list of ids (not-names) */
        $selected_workes.each(function(){
            var $worker = $(this),
                worker_name = $worker.attr('id');

            $.ajax({
                type: 'POST',
                url: '/shut-down-worker/' + worker_name,
                dataType: 'json',
                data: { workername: worker_name },
                success: function (data) {
                    show_success_alert(data.message);
                },
                error: function (data) {
                    show_error_alert(data.responseText);
                }
            });
        });
    }

    function restart_selected(event) {
        var $selected_workes = _get_selected_workers();

        /* atomic would be better with list of ids (not-names) */
        $selected_workes.each(function(){
            var $worker = $(this),
                worker_name = $worker.attr('id');

            $.ajax({
                type: 'POST',
                url: '/restart-pool-worker/' + worker_name,
                dataType: 'json',
                data: { workername: worker_name },
                success: function (data) {
                    show_success_alert(data.message);
                },
                error: function (data) {
                    show_error_alert(data.responseText);
                }
            });
        });
    }

    function on_pool_grow(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            grow_size = $('#pool-size option:selected').html();

        $.ajax({
            type: 'POST',
            url: '/worker-pool-grow/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': grow_size,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_pool_shrink(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            shrink_size = $('#pool-size option:selected').html();

        $.ajax({
            type: 'POST',
            url: '/worker-pool-shrink/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'n': shrink_size,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_pool_autoscale(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            min = $('#min-autoscale').val(),
            max = $('#max-autoscale').val();

        $.ajax({
            type: 'POST',
            url: '/worker-pool-autoscale/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'min': min,
                'max': max,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_add_consumer(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            queue = $('#add-consumer-name').val();

        $.ajax({
            type: 'POST',
            url: '/worker-queue-add-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout( function () {
                    $('#tab-queues').load('/worker/' + workername + ' #tab-queues').fadeIn('show');
                }, 10000)
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_cancel_consumer(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            queue = $(event.target).closest("tr").children("td:eq(0)").text();

        $.ajax({
            type: 'POST',
            url: '/worker-queue-cancel-consumer/' + workername,
            dataType: 'json',
            data: {
                'workername': workername,
                'queue': queue,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout( function () {
                    $('#tab-queues').load('/worker/' + workername + ' #tab-queues').fadeIn('show');
                }, 10000)
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_timeout(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
            type = $(event.target).html().toLowerCase(),
            timeout = $(event.target).siblings().closest("input").val();

        taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]

        $.ajax({
            type: 'POST',
            url: '/task-timeout/' + workername,
            dataType: 'json',
            data: {
                'taskname': taskname,
                type: timeout,
            },
            success: function (data) {
                show_success_alert(data.message);
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_task_rate_limit(event) {
        event.preventDefault();
        event.stopPropagation();

        var workername = $('#workername').text(),
            taskname = $(event.target).closest("tr").children("td:eq(0)").text(),
            ratelimit = $(event.target).prev().val();

        taskname = taskname.split(' ')[0]; // removes [rate_limit=xxx]

        $.ajax({
            type: 'POST',
            url: '/task-rate-limit/' + workername,
            dataType: 'json',
            data: {
                'taskname': taskname,
                'ratelimit': ratelimit,
            },
            success: function (data) {
                show_success_alert(data.message);
                setTimeout( function () {
                    $('#tab-limits').load('/worker/' + workername + ' #tab-limits').fadeIn('show');
                }, 10000)
            },
            error: function (data) {
                show_error_alert(data.responseText);
            }
        });
    }

    function on_workers_table_update(update) {
        $.each(update, function (name) {
            var id = name.replace(/(:|\.)/g, '\\$1'),
                tr = $('#' + id);

            if (tr.length === 0) {
                $('#workers-table-row').clone().removeClass('hidden').attr('id', name).appendTo('tbody');
                tr = $('#' + id);
                tr.children('td').children('a').attr('href', '/worker/' + id).text(name);
            }

            var stat = tr.children('td:eq(2)').children(),
                concurrency = tr.children('td:eq(3)'),
                completed_tasks = tr.children('td:eq(4)'),
                running_tasks = tr.children('td:eq(5)'),
                queues = tr.children('td:eq(6)');

            stat.text($(this).attr('status') ? "Online" : "Offline");
            stat.removeClass("label-success label-important");
            stat.addClass($(this).attr('status') ? "label-success" : "label-important");
            concurrency.text($(this).attr('concurrency'));
            completed_tasks.text($(this).attr('completed_tasks'));
            running_tasks.text($(this).attr('running_tasks'));
            queues.text($(this).attr('queues').toString().replace(/,/g, ', '));
        });
    }


    function on_cancel_task_filter(event) {
        event.preventDefault();
        event.stopPropagation();

        $('#task-filter-form').each(function () {
            $(this).find('INPUT:text').val('');
            $(this).find('SELECT').val('');
        });

        $('#task-filter-form').submit();
    }


    $(document).ready(function () {
        if ($.inArray($(location).attr('pathname'), ['', '/workers'])) {
            var host = $(location).attr('host'),
                ws = new WebSocket("ws://" + host + "/update-workers");
            ws.onmessage = function (event) {
                var update = $.parseJSON(event.data);
                on_workers_table_update(update);
            };
        }

        // Make bootstrap tabs persistent
        $(document).ready(function () {
            if (location.hash !== '') {
                $('a[href="' + location.hash + '"]').tab('show');
            }

            $('a[data-toggle="tab"]').on('shown', function (e) {
                location.hash = $(e.target).attr('href').substr(1);
            });
        });

    });

    return {
        toggle_selected_workers: toggle_selected_workers,
        select_all_workers: select_all_workers,
        select_none_workers: select_none_workers,
        shutdown_selected: shutdown_selected,
        restart_selected: restart_selected,
        on_alert_close: on_alert_close,
        on_pool_grow: on_pool_grow,
        on_pool_shrink: on_pool_shrink,
        on_pool_autoscale: on_pool_autoscale,
        on_add_consumer: on_add_consumer,
        on_cancel_consumer: on_cancel_consumer,
        on_task_timeout: on_task_timeout,
        on_task_rate_limit: on_task_rate_limit,
        on_cancel_task_filter: on_cancel_task_filter,
    }

}(jQuery));
