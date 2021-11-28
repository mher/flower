import "@popperjs/core/dist/esm/popper";
import "bootstrap/js/dist/collapse";
import "bootstrap/js/dist/dropdown";
import "bootstrap/js/dist/tab";

import "../css/flower.scss";

import { init as initTask } from "./eventhandlers/task";
import { init as initWorker } from "./eventhandlers/worker";
import { initTasksTable } from "./tables/tasks-table";
import { initWorkersTable } from "./tables/workers-table";

initTasksTable();
initWorkersTable();

initWorker();
initTask();
