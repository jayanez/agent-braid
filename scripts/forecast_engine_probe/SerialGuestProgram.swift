// SPDX-License-Identifier: AGPL-3.0-only
import Foundation

// Bash consumes the entire function definition before executing its invocation.
// A later read from the serial terminal therefore receives host admission data,
// not unread source lines. The pinned guest source is not caller-controlled.
func serialGuestProgram(_ script: Data) -> Data {
    var program = Data("fc2_run_probe() {\n".utf8)
    program.append(script)
    program.append(Data("\n}\nfc2_run_probe\n".utf8))
    return program
}
