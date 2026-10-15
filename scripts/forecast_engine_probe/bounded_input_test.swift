import Foundation
import Darwin
func sendBoundedInput(_ data: Data, to handle: FileHandle, budgetNs: UInt64, closeAfter: Bool = true) -> Bool {
    let fd = handle.fileDescriptor
    let flags = fcntl(fd, F_GETFL)
    guard flags >= 0 && fcntl(fd, F_SETFL, flags | O_NONBLOCK) >= 0 else { return false }
    let deadline = DispatchTime.now().uptimeNanoseconds + budgetNs
    var offset = 0
    data.withUnsafeBytes { bytes in
        while offset < data.count && DispatchTime.now().uptimeNanoseconds < deadline {
            let count = Darwin.write(fd, bytes.baseAddress!.advanced(by: offset), data.count - offset)
            if count > 0 { offset += count }
            else if count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK) { usleep(10000) }
            else if count < 0 && errno == EINTR { continue }
            else { break }
        }
    }
    if closeAfter { try? handle.close() }
    return offset == data.count
}

signal(SIGPIPE, SIG_IGN)
let pipe = Pipe()
let started = DispatchTime.now().uptimeNanoseconds
var responsive = false
DispatchQueue.main.asyncAfter(deadline: .now() + 0.02) { responsive = true }
DispatchQueue.global(qos: .utility).async {
    let delivered = sendBoundedInput(Data(repeating: 120, count: 2097152), to: pipe.fileHandleForWriting, budgetNs: 200000000)
    DispatchQueue.main.async {
        let elapsed = DispatchTime.now().uptimeNanoseconds - started
        print("{\"delivered\":\(delivered),\"mainResponsive\":\(responsive),\"wallNs\":\(elapsed)}")
        exit(!delivered && responsive && elapsed < 1000000000 ? 0 : 2)
    }
}
DispatchQueue.main.asyncAfter(deadline: .now() + 2) { exit(3) }
dispatchMain()
