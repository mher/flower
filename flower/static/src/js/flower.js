import "@popperjs/core/dist/esm/popper";
import "bootstrap/js/dist/tab";
import "bootstrap/js/dist/dropdown";
import "../css/flower.scss";
import { initTasksTable } from "./tables/tasks-table";
import { initWorkersTable } from "./tables/workers-table";
import { init as initTask } from "./eventhandlers/task";
import { init as initWorker } from "./eventhandlers/worker";

initTasksTable();
initWorkersTable();

initWorker();
initTask();
