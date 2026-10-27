// SPDX-License-Identifier: AGPL-3.0-only
/* Source only. Never compiled/loaded/started by the repository's Python imports.
 * PID1 and executor use separate CLOEXEC channels to the same private escrow.
 * No channel FD is serialized or passed among params->fds to the target.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "fc1-systemd-gate.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/time.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FC1_MAGIC UINT32_C(0x31434641)
struct request { uint32_t magic, version, site, reserved; char unit[96], invocation[33], pad[7]; };
struct reply { uint32_t magic, version, site, allowed; uint64_t ticket, deadline; };
_Static_assert(sizeof(struct request)==152, "FC1 request ABI");
_Static_assert(sizeof(struct reply)==32, "FC1 reply ABI");
static const char *suffixes[]={"-supervisor.service",".service","-operator.service",
                              "-prepare.service","-verify.service","-terminal.service"};
static int hex(const char *s, size_t n) {
    if(!s) return 0;
    for(size_t i=0;i<n;i++) if(!s[i] || !strchr("0123456789abcdef",s[i])) return 0;
    return 1;
}
int fc1_unit_role(const char *unit) {
    if(!unit || strnlen(unit,96)>=96 || strncmp(unit,"fc1",3) || !hex(unit+3,64)) return -1;
    for(int i=0;i<6;i++) if(!strcmp(unit+67,suffixes[i])) return i;
    return -1;
}
int fc1_gate_open(const char *unit) {
    struct sockaddr_un address={.sun_family=AF_UNIX};
    struct ucred cred; socklen_t size=sizeof cred;
    if(fc1_unit_role(unit)<0) return -EINVAL;
    int n=snprintf(address.sun_path,sizeof address.sun_path,"/run/fc1/%.64s/manager-gate.sock",unit+3);
    if(n<0 || (size_t)n>=sizeof address.sun_path) return -E2BIG;
    int fd=socket(AF_UNIX,SOCK_SEQPACKET|SOCK_CLOEXEC,0);
    if(fd<0) return -errno;
    struct timeval timeout={.tv_sec=1};
    if(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof timeout)<0 ||
       setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof timeout)<0 ||
       connect(fd,(struct sockaddr*)&address,sizeof address)<0 ||
       getsockopt(fd,SOL_SOCKET,SO_PEERCRED,&cred,&size)<0 ||
       size!=sizeof cred || cred.uid!=0 || cred.pid<=1) {
        int error=errno?errno:EPERM;close(fd);return -error;
    }
    return fd;
}
int fc1_gate_authorize(int fd,unsigned site,const char *unit,const char *invocation) {
    struct request q={.magic=FC1_MAGIC,.version=1,.site=site};
    struct reply r={}; struct timespec now;
    if(fd<0 || site>1 || fc1_unit_role(unit)<0 || !invocation ||
       strnlen(invocation,33)!=32 || !hex(invocation,32)) return -EPERM;
    int flags=fcntl(fd,F_GETFD);
    if(flags<0 || !(flags&FD_CLOEXEC)) return -EPERM;
    memcpy(q.unit,unit,strlen(unit));memcpy(q.invocation,invocation,32);
    /* SO_PASSCRED at the receiver supplies this sender's CURRENT credentials,
     * including a target UID change; creator SO_PEERCRED is not that identity. */
    if(send(fd,&q,sizeof q,MSG_NOSIGNAL)!=(ssize_t)sizeof q) return -EIO;
    struct iovec iov={.iov_base=&r,.iov_len=sizeof r};
    struct msghdr message={.msg_iov=&iov,.msg_iovlen=1};
    if(recvmsg(fd,&message,0)!=(ssize_t)sizeof r || message.msg_flags&(MSG_TRUNC|MSG_CTRUNC)) return -EIO;
    if(clock_gettime(CLOCK_MONOTONIC,&now)<0) return -errno;
    uint64_t ns=(uint64_t)now.tv_sec*UINT64_C(1000000000)+(uint64_t)now.tv_nsec;
    if(r.magic!=FC1_MAGIC || r.version!=1 || r.site!=site || r.allowed!=1 || ns>=r.deadline) return -EPERM;
    return 0;
}
