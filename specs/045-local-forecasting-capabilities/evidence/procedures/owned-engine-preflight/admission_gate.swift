// SPDX-License-Identifier: AGPL-3.0-only
// Pure admission state machine. It never signals a daemon or starts a VM.
enum EngineAdmissionAction: Equatable {
    case sendCrashAdmissionToken
    case waitForFailureReceipt
    case stopAfterGuestReceipt
    case stopWithoutGuestReceipt
    case ignore
}

struct EngineAdmissionGate {
    static let failureReceiptGraceSeconds = 5

    private enum State {
        case awaitingPreflight
        case admitted
        case rejected
        case deliveryFailed
        case completed
        case expired
        case cancelled
    }

    private var state = State.awaitingPreflight
    private(set) var tokenAdmissionCount = 0

    mutating func cancel() {
        state = .cancelled
    }

    mutating func resolvePreflight(valid: Bool) -> EngineAdmissionAction {
        guard case .awaitingPreflight = state else { return .ignore }
        if valid {
            state = .admitted
            tokenAdmissionCount += 1
            return .sendCrashAdmissionToken
        }
        state = .rejected
        return .waitForFailureReceipt
    }

    mutating func guestCompleted() -> EngineAdmissionAction {
        switch state {
        case .rejected, .admitted, .deliveryFailed:
            state = .completed
            return .stopAfterGuestReceipt
        case .awaitingPreflight:
            state = .completed
            return .stopWithoutGuestReceipt
        case .completed, .expired, .cancelled:
            return .ignore
        }
    }

    mutating func tokenDeliveryFailed() -> EngineAdmissionAction {
        guard case .admitted = state else { return .ignore }
        state = .deliveryFailed
        return .waitForFailureReceipt
    }

    mutating func failureReceiptGraceExpired() -> EngineAdmissionAction {
        guard case .rejected = state else {
            guard case .deliveryFailed = state else { return .ignore }
            state = .expired
            return .stopWithoutGuestReceipt
        }
        state = .expired
        return .stopWithoutGuestReceipt
    }
}
