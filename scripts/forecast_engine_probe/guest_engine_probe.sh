# SPDX-License-Identifier: AGPL-3.0-only
# Bound shell-only diagnostic. No CPython, image, container or model.
set -Eeuo pipefail
umask 077
fc2_base=/run/fc2-engine
fc2_root=/mnt/fc2-engine/docker
fc2_diagnostics=/mnt/fc2-engine/diagnostics
fc2_daemon_log=$fc2_diagnostics/daemon.log
fc2_log_tail=$fc2_base/daemon-log-tail-bytes
fc2_log_pid=''
fc2_log_drain_complete=0
fc2_log_fifo=$fc2_base/daemon-output.fifo
fc2_socket=$fc2_base/docker.sock
fc2_status=incomplete
fc2_pid=''
fc2_signal=0
fc2_wait=0
fc2_begin=0
fc2_probes=0
fc2_emit() {
  printf '\nFC2_ENGINE_EVENT %s ' "$1"
  printf '%s' "$2" | /usr/bin/base64 -w0
  printf '\n'
}
fc2_file() {
  printf '\nFC2_ENGINE_EVENT %s ' "$1"
  /usr/bin/base64 -w0 < "$2"
  printf '\n'
}
fc2_now() {
  local fc2_u fc2_rest fc2_sec fc2_frac
  read -r fc2_u fc2_rest < /proc/uptime
  fc2_sec=${fc2_u%.*}; fc2_frac=${fc2_u#*.}000
  fc2_ms=$((10#$fc2_sec * 1000 + 10#${fc2_frac:0:3}))
}
fc2_guard() { fc2_now; (( fc2_ms - fc2_begin < 55000 )); }
# Keep at most 32 KiB on persistent scratch while draining all daemon output.
fc2_drain_daemon_output() {
  local fc2_fd=$1 fc2_path=$2 fc2_tail_path=$3
  {
    if ! /usr/bin/dd iflag=fullblock bs=32768 count=1 status=none > "$fc2_path"; then
      /usr/bin/wc -c >/dev/null
      return 1
    fi
    /usr/bin/wc -c > "$fc2_tail_path"
  } <&"$fc2_fd"
}
fc2_join_log_drain() {
  local fc2_j fc2_stat fc2_fields fc2_values
  for (( fc2_j=0; fc2_j<20; fc2_j++ )); do
    if [[ ! -r /proc/$fc2_log_pid/stat ]]; then break; fi
    read -r fc2_stat < "/proc/$fc2_log_pid/stat"
    fc2_fields=${fc2_stat##*) }; read -ra fc2_values <<< "$fc2_fields"
    [[ ${fc2_values[0]} == Z ]] && break
    /usr/bin/sleep .05
  done
  if [[ -r /proc/$fc2_log_pid/stat ]]; then
    read -r fc2_stat < "/proc/$fc2_log_pid/stat"
    fc2_fields=${fc2_stat##*) }; read -ra fc2_values <<< "$fc2_fields"
    if [[ ${fc2_values[0]} != Z ]]; then return 1; fi
  fi
  wait "$fc2_log_pid"; fc2_log_drain_status=$?
  fc2_log_pid=''
  exec 3<&-
  if (( fc2_log_drain_status == 0 )); then fc2_log_drain_complete=1; return 0; fi
  return 1
}
fc2_log_summary() {
  local fc2_log_stored=$1 fc2_counter_path=$2
  IFS= read -r fc2_log_tail_bytes < "$fc2_counter_path" || return 1
  [[ $fc2_log_tail_bytes =~ ^[0-9]+$ ]] || return 1
  fc2_log_bytes=$((fc2_log_stored + fc2_log_tail_bytes))
  (( fc2_log_stored <= 32768 && fc2_log_bytes >= fc2_log_stored )) || return 1
  if (( fc2_log_tail_bytes > 0 )); then fc2_log_truncated=yes; else fc2_log_truncated=no; fi
}
fc2_finish() {
  trap - EXIT
  set +e
  # On an incomplete path, stop only the verified owned daemon before joining
  # the bounded log drainer. Normal admitted SIGKILL already reaped it above.
  if [[ -n $fc2_pid && -e /proc/$fc2_pid/exe && /proc/$fc2_pid/exe -ef /usr/bin/dockerd ]]; then
    kill -TERM "$fc2_pid"
    for (( fc2_j=0; fc2_j<20; fc2_j++ )); do
      [[ ! -e /proc/$fc2_pid/exe ]] && break
      /usr/bin/sleep .05
    done
    if [[ -e /proc/$fc2_pid/exe && /proc/$fc2_pid/exe -ef /usr/bin/dockerd ]]; then kill -KILL "$fc2_pid"; fi
    wait "$fc2_pid" 2>/dev/null
  fi
  if [[ -n $fc2_log_pid ]]; then fc2_join_log_drain; fi
  if (( fc2_log_drain_complete == 1 )); then fc2_emit daemonLogDrainComplete yes; else fc2_emit daemonLogDrainComplete no; fi
  if [[ -f $fc2_daemon_log && ! -L $fc2_daemon_log && -f $fc2_log_tail && ! -L $fc2_log_tail ]]; then
    fc2_log_stored=$(/usr/bin/wc -c < "$fc2_daemon_log")
    if fc2_log_summary "$fc2_log_stored" "$fc2_log_tail"; then
      fc2_emit daemonLogAvailable yes
      fc2_emit daemonLogBytes "$fc2_log_bytes"
      fc2_emit daemonLogTruncated "$fc2_log_truncated"
      printf '\nFC2_ENGINE_EVENT daemonLogBase64 '
      /usr/bin/base64 -w0 < "$fc2_daemon_log"
      printf '\n'
    else
      fc2_status=incomplete
      fc2_emit daemonLogAvailable no
    fi
  else
    fc2_emit daemonLogAvailable no
  fi
  fc2_emit status "$fc2_status"
  fc2_emit signal "$fc2_signal"
  fc2_emit waitStatus "$fc2_wait"
  fc2_emit readinessProbes "$fc2_probes"
  if (( fc2_begin > 0 )); then fc2_now; fc2_emit wallNs "$(( (fc2_ms - fc2_begin) * 1000000 ))"; fi
  printf '\nFC2_ENGINE_QUALIFICATION_DONE\n'
  # Preserve PID1 until the independent VM supervisor stops the guest.
  while :; do /usr/bin/sleep 1; done
}
trap fc2_finish EXIT
/usr/bin/timeout -k1 3 /usr/bin/mount -t proc proc /proc
fc2_now; fc2_begin=$fc2_ms
# BEGIN PURE MOUNT-TABLE PARSER
fc2_mount_type() {
  local fc2_wanted=$1 fc2_table=$2 fc2_source fc2_target fc2_type fc2_options fc2_rest fc2_found=''
  while read -r fc2_source fc2_target fc2_type fc2_options fc2_rest; do
    [[ $fc2_target == "$fc2_wanted" ]] || continue
    [[ -z $fc2_found ]] || return 2
    fc2_found=$fc2_type
  done < "$fc2_table"
  printf '%s' "$fc2_found"
}
# END PURE MOUNT-TABLE PARSER
fc2_actual=$(/usr/bin/sha256sum /usr/bin/base64)
[[ ${fc2_actual%% *} == fddcdceb0e29dbd705b0be68df060754f41964e1cf5fd02563d978e43d92a13e ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/bash)
[[ ${fc2_actual%% *} == f5918390c5b15392ad8835e8368a79c1ee9937fbb19f2349cccf5d4524183299 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/containerd)
[[ ${fc2_actual%% *} == f1b2d857e25551d5c2e03287df8143d90e3289f46a46e71348bf806bead49643 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/dockerd)
[[ ${fc2_actual%% *} == fb8e4f78c21391f480ed2d2f6a89c5056ed7c5c931307fe701d51866cb6b6667 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/getconf)
[[ ${fc2_actual%% *} == ed69493e9116dde0f7e91d400193abb18d72f229d44d8669fe7912e5e85b1ac5 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/dd)
[[ ${fc2_actual%% *} == 57e766b90bd8c45b390da857893d13ef2d5af3c42fe95f2cadd31852220c9962 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/mkfifo)
[[ ${fc2_actual%% *} == db022d5e11018ab024ba9d2593281619bc07f6708c021faf019a8419b6316323 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/head)
[[ ${fc2_actual%% *} == d46405d797a24d1e9844039634f7ca28b62a995bd1529fd15ca1fddbd9cd3b73 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/mkdir)
[[ ${fc2_actual%% *} == 8fca34baba116e4e0b099db07b98b066314be0ceee7ae4c2eb2388cfa062c5b0 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/mount)
[[ ${fc2_actual%% *} == 4e3aa9cd2b207144bc3206a95019fcdeeac9114cb58d9b19850b948b2003c2ef ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/runc)
[[ ${fc2_actual%% *} == cb5ef5cf5b8b23d3a113cc5f9b6884fde921c52b75683f34855dd6e92e354b09 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/containerd-shim-runc-v2)
[[ ${fc2_actual%% *} == 709fa03b8b731c50ce3241247a4945b49c14e3ef0d8584c0159daf291fcb151f ]]
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
fc2_runc_path=$(command -v runc)
[[ $fc2_runc_path == /usr/bin/runc ]]
fc2_shim_path=$(command -v containerd-shim-runc-v2)
[[ $fc2_shim_path == /usr/bin/containerd-shim-runc-v2 ]]
fc2_emit runtimeSearchPath "$fc2_runc_path"
fc2_emit runtimeShimSearchPath "$fc2_shim_path"
fc2_actual=$(/usr/bin/sha256sum /usr/bin/sha256sum)
[[ ${fc2_actual%% *} == d72f4681a531bd27e3deaed5cbe4b1df0f87a4d69b9c12d5772712321405d709 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/sleep)
[[ ${fc2_actual%% *} == 17a623f303e2489770e64a9eab9420c66e576ec5ad215ea7c46ec392a2212f49 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/socat)
[[ ${fc2_actual%% *} == a77e9e102014dbf0f8a6d075a61d6dc5c1cf20d41da4ebc391a4827dd0009714 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/timeout)
[[ ${fc2_actual%% *} == 3629fa180f625d4de2e3fd3b15b12c5d42315e5733ecae6d1550b306abd7d482 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/bin/wc)
[[ ${fc2_actual%% *} == ce74356835b690f104f59f2917d58cfdfb7f01d4ac210df20df859e194738889 ]]
fc2_actual=$(/usr/bin/sha256sum /usr/sbin/mke2fs)
[[ ${fc2_actual%% *} == 92721c9a402ba8015ec6321acffaac187ce32fd2772a54690b46dfe94b8f6589 ]]
/usr/bin/timeout -k1 3 /usr/bin/mount -t sysfs sysfs /sys
fc2_dev_type=$(fc2_mount_type /dev /proc/mounts)
if [[ -z $fc2_dev_type ]]; then
  /usr/bin/timeout -k1 3 /usr/bin/mount -t devtmpfs devtmpfs /dev
else
  [[ $fc2_dev_type == devtmpfs ]]
fi
/usr/bin/timeout -k1 3 /usr/bin/mount -t tmpfs -o size=64m,nosuid,nodev tmpfs /run
/usr/bin/timeout -k1 3 /usr/bin/mount -t tmpfs -o size=64m,nosuid,nodev tmpfs /tmp
/usr/bin/timeout -k1 3 /usr/bin/mount -t cgroup2 none /sys/fs/cgroup
[[ -b /dev/vdb && -b /dev/vda && ! /dev/vdb -ef /dev/vda ]]
read -r fc2_sectors < /sys/class/block/vdb/size
[[ $fc2_sectors == 41943040 ]]
while read -r fc2_device fc2_rest; do [[ $fc2_device != /dev/vdb ]]; done < /proc/mounts
fc2_guard
/usr/bin/timeout -k1 10 /usr/sbin/mke2fs -q -t ext4 -F /dev/vdb
/usr/bin/timeout -k1 3 /usr/bin/mount -t ext4 -o nosuid,nodev /dev/vdb /mnt
/usr/bin/mkdir -m700 "$fc2_base"
/usr/bin/mkdir -p -m700 "$fc2_root"
/usr/bin/mkdir -p -m700 "$fc2_diagnostics"
printf '%s\n' '{"bridge":"none","ip-forward":false,"ip-masq":false,"ip6tables":false,"iptables":false,"live-restore":false,"log-level":"error","userland-proxy":false}' > "$fc2_base/daemon.json"
fc2_actual=$(/usr/bin/sha256sum "$fc2_base/daemon.json")
fc2_emit configurationSha256 "${fc2_actual%% *}"
fc2_guard
/usr/bin/timeout -k1 3 /usr/bin/dockerd --validate --config-file="$fc2_base/daemon.json" > "$fc2_base/daemon-validation.txt" 2>&1
IFS= read -r fc2_validation_result < "$fc2_base/daemon-validation.txt"
[[ $fc2_validation_result == 'configuration OK' ]]
fc2_emit daemonConfigValidated yes
fc2_guard
/usr/bin/timeout -k1 2 /usr/bin/mkfifo -m600 "$fc2_log_fifo"
( exec /usr/bin/dockerd --host="unix://$fc2_socket" --data-root="$fc2_root" --exec-root="$fc2_base/exec" --pidfile="$fc2_base/dockerd.pid" --config-file="$fc2_base/daemon.json" --containerd-namespace=fc2-engine-qualification --containerd-plugins-namespace=fc2-engine-qualification-plugins ) > "$fc2_log_fifo" 2>&1 &
fc2_pid=$!
exec 3< "$fc2_log_fifo"
fc2_drain_daemon_output 3 "$fc2_daemon_log" "$fc2_log_tail" &
fc2_log_pid=$!
fc2_exec_ready=0
for (( fc2_i=0; fc2_i<50; fc2_i++ )); do
  fc2_guard
  if [[ ! -e /proc/$fc2_pid/exe ]]; then break; fi
  if [[ /proc/$fc2_pid/exe -ef /usr/bin/dockerd ]]; then fc2_exec_ready=1; break; fi
  /usr/bin/sleep .02
done
if (( fc2_exec_ready != 1 )); then fc2_emit daemonExecIdentity no; exit 2; fi
fc2_emit daemonExecIdentity yes
read -r fc2_stat < "/proc/$fc2_pid/stat"
fc2_emit launchedStat "$fc2_stat"
fc2_fields=${fc2_stat##*) }; read -ra fc2_values <<< "$fc2_fields"; fc2_birth=${fc2_values[19]}
fc2_api() {
  fc2_guard || return 2
  printf 'GET %s HTTP/1.0\r\nHost: owned-guest\r\nConnection: close\r\n\r\n' "$1" | /usr/bin/timeout -k1 1 /usr/bin/socat -t0.05 -T0.8 STDIO,ignoreeof "UNIX-CONNECT:$fc2_socket" | /usr/bin/head -c1048577 > "$2" || return $?
  local fc2_bytes
  fc2_bytes=$(/usr/bin/wc -c < "$2"); (( fc2_bytes <= 1048576 ))
}
fc2_ready=0
for (( fc2_i=0; fc2_i<200; fc2_i++ )); do
  fc2_guard; (( fc2_probes+=1 )); kill -0 "$fc2_pid"
  if fc2_api /_ping "$fc2_base/ping"; then
    IFS= read -r fc2_line < "$fc2_base/ping"
    if [[ $fc2_line == $'HTTP/1.0 200 OK\r' || $fc2_line == $'HTTP/1.1 200 OK\r' ]]; then fc2_ready=1; break; fi
  fi
  /usr/bin/sleep .05
done
(( fc2_ready == 1 ))
fc2_api /info "$fc2_base/info"
fc2_api '/images/json?all=1' "$fc2_base/images"
fc2_api '/containers/json?all=1' "$fc2_base/containers"
fc2_file infoHttp "$fc2_base/info"
fc2_file imagesHttp "$fc2_base/images"
fc2_file containersHttp "$fc2_base/containers"
# The host independently parses these HTTP/JSON records before admitting the crash.
fc2_emit prerequisiteReady yes
IFS= read -r -t 3 fc2_token < /dev/hvc0
# BEGIN PURE ADMISSION CHECK
fc2_require_crash_admission() {
  if [[ $1 == FC2_ABORT_OWN_DAEMON_CRASH ]]; then
    fc2_emit hostPreflightRejected yes
    return 2
  fi
  [[ $1 == FC2_ADMIT_OWN_DAEMON_CRASH ]]
}
# END PURE ADMISSION CHECK
fc2_require_crash_admission "$fc2_token"
fc2_guard
read -r fc2_stat < "/proc/$fc2_pid/stat"
fc2_fields=${fc2_stat##*) }; read -ra fc2_values <<< "$fc2_fields"
[[ ${fc2_values[19]} == "$fc2_birth" && ${fc2_values[0]} != Z ]]
fc2_emit preCrashStat "$fc2_stat"
fc2_emit clockTicksPerSecond "$(/usr/bin/getconf CLK_TCK)"
read -r fc2_boot < /proc/sys/kernel/random/boot_id; fc2_emit bootId "$fc2_boot"
fc2_file cgroupControllers /sys/fs/cgroup/cgroup.controllers
kill -KILL "$fc2_pid"; fc2_signal=1
set +e
wait "$fc2_pid"; fc2_wait=$?
set -e
fc2_join_log_drain
(( fc2_log_drain_complete == 1 ))
(( fc2_wait == 137 ))
if fc2_api /_ping "$fc2_base/after-fault"; then exit 2; else fc2_client_status=$?; fi
fc2_guard
fc2_bytes=$(/usr/bin/wc -c < "$fc2_base/after-fault")
(( fc2_bytes == 0 ))
fc2_emit postFaultClientStatus "$fc2_client_status"
fc2_emit postFaultBytes "$fc2_bytes"
fc2_status=engine-ready-and-owned-daemon-crashed
exit 0
