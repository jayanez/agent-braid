// SPDX-License-Identifier: AGPL-3.0-only
// Pure bounded host decoding. No VM, process, daemon or socket operations.
import Foundation
import CoreFoundation

// Foundation splits the LF byte even in CRLF. Swift Character splitting does
// not: CRLF is one extended grapheme, so split(separator: "\n") misses it.
// Always discard the final component: until LF arrives it is a partial record.
func engineConsoleLines(_ console: String) -> [String] {
    console.components(separatedBy: "\n").dropLast().map {
        $0.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

func enginePrerequisiteReady(_ console: String) -> Bool {
    engineConsoleLines(console).contains("FC2_ENGINE_EVENT prerequisiteReady eWVz")
}

func engineCompletionSeen(_ console: String) -> Bool {
    engineConsoleLines(console).contains("FC2_ENGINE_QUALIFICATION_DONE")
}

func uniqueJSON(_ data: Data) throws -> Any {
    guard data.count <= 1048576 else { throw NSError(domain: "budget", code: 1) }
    let bytes = [UInt8](data)
    struct Frame { var kind: UInt8; var keys = Set<String>(); var expectsKey: Bool }
    var frames = [Frame]()
    var index = 0
    while index < bytes.count {
        let byte = bytes[index]
        if byte == 123 || byte == 91 {
            guard frames.count < 128 else { throw NSError(domain: "depth", code: 1) }
            frames.append(Frame(kind: byte, expectsKey: byte == 123))
        } else if byte == 125 || byte == 93 {
            guard let frame = frames.last, frame.kind == (byte == 125 ? 123 : 91) else { throw NSError(domain: "framing", code: 1) }
            frames.removeLast()
        } else if byte == 44 {
            if !frames.isEmpty && frames[frames.count - 1].kind == 123 { frames[frames.count - 1].expectsKey = true }
        } else if byte == 34 {
            let begin = index
            index += 1
            while index < bytes.count {
                if bytes[index] == 92 { index += 2; continue }
                if bytes[index] == 34 { break }
                index += 1
            }
            guard index < bytes.count else { throw NSError(domain: "string", code: 1) }
            if !frames.isEmpty && frames[frames.count - 1].kind == 123 && frames[frames.count - 1].expectsKey {
                let raw = Data(bytes[begin...index])
                guard let key = try JSONSerialization.jsonObject(with: raw, options: .fragmentsAllowed) as? String else { throw NSError(domain: "key", code: 1) }
                guard frames[frames.count - 1].keys.insert(key).inserted else { throw NSError(domain: "duplicate", code: 1) }
                frames[frames.count - 1].expectsKey = false
            }
        }
        index += 1
    }
    guard frames.isEmpty else { throw NSError(domain: "framing", code: 1) }
    return try JSONSerialization.jsonObject(with: data, options: .fragmentsAllowed)
}

func engineHTTPJSON(_ raw: Data) throws -> Any {
    guard raw.count <= 1048576, let separator = raw.range(of: Data("\r\n\r\n".utf8)),
          let head = String(data: raw[..<separator.lowerBound], encoding: .utf8) else { throw NSError(domain: "HTTP", code: 1) }
    let lines = head.components(separatedBy: "\r\n")
    guard lines.first == "HTTP/1.0 200 OK" || lines.first == "HTTP/1.1 200 OK" else { throw NSError(domain: "HTTP", code: 2) }
    var headers = [String: String]()
    for line in lines.dropFirst() {
        guard let colon = line.firstIndex(of: ":") else { throw NSError(domain: "HTTP", code: 3) }
        let key = line[..<colon].trimmingCharacters(in: .whitespaces).lowercased()
        guard headers[key] == nil else { throw NSError(domain: "HTTP", code: 4) }
        headers[key] = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
    }
    let body = Data(raw[separator.upperBound...])
    guard headers["transfer-encoding"] == nil else { throw NSError(domain: "HTTP", code: 5) }
    if let size = headers["content-length"] { guard Int(size) == body.count else { throw NSError(domain: "HTTP", code: 6) } }
    return try uniqueJSON(body)
}

func nativeEnginePreflight(_ console: String) -> Bool {
    guard console.utf8.count <= 1048576 else { return false }
    var events = [String: Data]()
    for line in engineConsoleLines(console) {
        guard line.hasPrefix("FC2_ENGINE_EVENT ") else { continue }
        let parts = line.dropFirst("FC2_ENGINE_EVENT ".count).split(separator: " ", maxSplits: 1, omittingEmptySubsequences: false)
        guard parts.count == 2, events[String(parts[0])] == nil, events.count < 32, let value = Data(base64Encoded: String(parts[1])) else { return false }
        events[String(parts[0])] = value
    }
    guard events["daemonExecIdentity"] == Data("yes".utf8),
          events["runtimeSearchPath"] == Data("/usr/bin/runc".utf8),
          events["runtimeShimSearchPath"] == Data("/usr/bin/containerd-shim-runc-v2".utf8),
          events["prerequisiteReady"] == Data("yes".utf8), let infoRaw = events["infoHttp"],
          let imagesRaw = events["imagesHttp"], let containersRaw = events["containersHttp"],
          let statRaw = events["launchedStat"], let statText = String(data: statRaw, encoding: .utf8),
          let first = statText.range(of: " ("), let last = statText.range(of: ") ", options: .backwards),
          let pid = Int(statText[..<first.lowerBound]), pid > 1 else { return false }
    let fields = statText[last.upperBound...].split(separator: " ")
    guard fields.count >= 20, fields[0] != "Z", let birth = UInt64(fields[19]), birth > 0,
          UInt64(fields[11]) != nil, UInt64(fields[12]) != nil else { return false }
    do {
        guard let info = try engineHTTPJSON(infoRaw) as? [String: Any],
              info["DockerRootDir"] as? String == "/mnt/fc2-engine/docker",
              let identifier = info["ID"] as? String, !identifier.isEmpty,
              let live = info["LiveRestoreEnabled"] as? NSNumber,
              CFGetTypeID(live) == CFBooleanGetTypeID(), !live.boolValue,
              let count = info["Containers"] as? NSNumber, CFGetTypeID(count) != CFBooleanGetTypeID(),
              ["i", "s", "l", "q", "I", "S", "L", "Q"].contains(String(cString: count.objCType)), count.int64Value == 0,
              let images = try engineHTTPJSON(imagesRaw) as? [Any], images.isEmpty,
              let containers = try engineHTTPJSON(containersRaw) as? [Any], containers.isEmpty else { return false }
        return true
    } catch { return false }
}

let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let cases = try JSONSerialization.jsonObject(with: data) as! [[String: Any]]
var failures = 0
for row in cases {
    let result = nativeEnginePreflight(row["console"] as! String)
    if result != row["expected"] as! Bool { print("failed: \(row["name"]!)"); failures += 1 }
}
print("Native preflight cases: \(cases.count), failures: \(failures)")
exit(failures == 0 ? 0 : 2)
