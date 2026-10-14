// SPDX-License-Identifier: AGPL-3.0-only
// Synthetic HTTP/event controls only. This test never starts a VM or opens a socket.
import Foundation

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fatalError(message) }
}

func http(_ status: Int, _ reason: String, _ body: String) -> Data {
    let bytes = Data(body.utf8)
    let header = Data("HTTP/1.0 \(status) \(reason)\r\nContent-Length: \(bytes.count)\r\n\r\n".utf8)
    return header + bytes
}

func processStat() -> Data {
    var fields = Array(repeating: "0", count: 20)
    fields[0] = "S"
    fields[11] = "1"
    fields[12] = "0"
    fields[19] = "123"
    return Data(("42 (dockerd) " + fields.joined(separator: " ")).utf8)
}

func syntheticConsole(info: Data, images: Data) -> String {
    let values: [(String, Data)] = [
        ("runtimeSearchPath", Data("/usr/bin/runc".utf8)),
        ("runtimeShimSearchPath", Data("/usr/bin/containerd-shim-runc-v2".utf8)),
        ("prerequisiteReady", Data("yes".utf8)),
        ("infoHttp", info),
        ("imagesHttp", images),
        ("containersHttp", http(200, "OK", "[]")),
        ("launchedStat", processStat()),
    ]
    return values.map { item in
        "FC2_ENGINE_EVENT \(item.0) \(item.1.base64EncodedString())"
    }.joined(separator: "\n") + "\n"
}

let validInfo = http(200, "OK", #"{"DockerRootDir":"/mnt/fc2-engine/docker","ID":"synthetic","LiveRestoreEnabled":false,"Containers":0}"#)
let emptyImages = http(200, "OK", "[]")
let acceptedConsole = syntheticConsole(info: validInfo, images: emptyImages)
var accepted = EngineAdmissionGate()
check(nativeEnginePreflight(acceptedConsole), "synthetic empty owned engine preflight should validate")
check(accepted.resolvePreflight(valid: nativeEnginePreflight(acceptedConsole)) == .sendCrashAdmissionToken,
      "valid preflight should admit exactly one crash token")
check(accepted.resolvePreflight(valid: true) == .ignore && accepted.tokenAdmissionCount == 1,
      "duplicate valid preflight must not admit a second token")

let rejectedCases: [(String, String, Data, Data)] = [
    ("info-null", "HTTP 200 with JSON null", http(200, "OK", "null"), emptyImages),
    ("images-499", "HTTP 499 response", validInfo, http(499, "Client Closed Request", "")),
]
for (name, _, info, images) in rejectedCases {
    let console = syntheticConsole(info: info, images: images)
    check(!nativeEnginePreflight(console), "\(name) must fail native preflight")
    var rejected = EngineAdmissionGate()
    check(rejected.resolvePreflight(valid: nativeEnginePreflight(console)) == .waitForFailureReceipt,
          "\(name) must wait for the bounded failure receipt")
    check(rejected.tokenAdmissionCount == 0, "\(name) must never admit a crash token")
    check(rejected.guestCompleted() == .stopAfterGuestReceipt && rejected.tokenAdmissionCount == 0,
          "\(name) may stop only after receipt completion")

    var missingReceipt = EngineAdmissionGate()
    check(missingReceipt.resolvePreflight(valid: nativeEnginePreflight(console)) == .waitForFailureReceipt,
          "\(name) starts the bounded receipt wait")
    check(missingReceipt.failureReceiptGraceExpired() == .stopWithoutGuestReceipt,
          "\(name) must stop if its receipt misses the deadline")
    check(missingReceipt.tokenAdmissionCount == 0, "receipt timeout must not admit a token")
}

check(EngineAdmissionGate.failureReceiptGraceSeconds == 5,
      "fallback stop must remain within the reviewed five-second grace")

var cancelledBeforePreflight = EngineAdmissionGate()
cancelledBeforePreflight.cancel()
check(cancelledBeforePreflight.resolvePreflight(valid: true) == .ignore,
      "a valid event queued after cancellation must not be admitted")
check(cancelledBeforePreflight.tokenAdmissionCount == 0,
      "cancellation before preflight must leave token admission count at zero")
check(cancelledBeforePreflight.guestCompleted() == .ignore,
      "cancellation is terminal and cannot be mistaken for a guest receipt")
check(cancelledBeforePreflight.failureReceiptGraceExpired() == .ignore,
      "cancellation is terminal and cannot schedule a late failure stop")
print("Owned-engine preflight: valid, null, 499, receipt, timeout, cancellation and no-token controls passed")
