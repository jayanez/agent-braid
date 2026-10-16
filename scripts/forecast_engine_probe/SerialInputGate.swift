// SPDX-License-Identifier: AGPL-3.0-only
import Foundation

// One linearization order for cancellation and whole bounded serial writes.
// A write already holding the lock precedes cancellation; after cancel returns
// no sender can start. Callers keep the original absolute cleanup deadline.
final class SerialInputGate {
    private let lock = NSLock()
    private var cancelled = false

    func cancel() {
        lock.lock()
        defer { lock.unlock() }
        cancelled = true
    }

    func sendIfActive(_ sender: () -> Bool) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard !cancelled else { return false }
        return sender()
    }
}
