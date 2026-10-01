import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// без globals Vitest Testing Library не размонтирует компоненты сама
afterEach(cleanup);

// jsdom не реализует модальный <dialog>: минимальный полифил открытия/закрытия
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
}
