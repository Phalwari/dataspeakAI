"""Bounded, cancellable CPU jobs. No estimator survives an expired request."""
import importlib
import multiprocessing
import threading
import time

_slots = threading.BoundedSemaphore(2)


def _execute(connection, module, function, arguments):
    try:
        operation = getattr(importlib.import_module(module), function)
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            result = operation(*arguments)
        connection.send(result)
    except Exception as exc:
        connection.send({"error": str(exc), "status": "failed", "best_model": None, "all_models": []})
    finally:
        connection.close()


def run_bounded(module, function, arguments, timeout):
    started = time.monotonic()
    if not _slots.acquire(blocking=False):
        return {"error": "Training capacity busy; retry later", "status": "busy", "best_model": None, "all_models": []}
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_execute, args=(sender, module, function, arguments), daemon=True)
    try:
        process.start()
        sender.close()
        remaining = max(0, timeout - (time.monotonic() - started))
        if receiver.poll(remaining):
            try:
                return receiver.recv()
            except EOFError:
                return {"error": "Training worker exited unexpectedly", "status": "failed", "best_model": None, "all_models": []}
        return {"error": f"Training timeout exceeded ({timeout}s)", "status": "timeout", "best_model": None, "all_models": []}
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=0.2)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.2)
            process.close()
        sender.close()
        receiver.close()
        _slots.release()
