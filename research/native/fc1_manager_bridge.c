// SPDX-License-Identifier: AGPL-3.0-only
/* Private source-only sd-bus bridge. Never compiled/loaded by Python import.
 * One outstanding request, six fixed units, fixed read-only properties and
 * StartUnit(...,"fail"). No shell, subprocess, generic D-Bus method or fallback.
 */
#define _GNU_SOURCE
#include <systemd/sd-bus.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>

struct fc1_result { int32_t kind, error; uint64_t number; char text[1024]; };
struct fc1_bus {
    sd_bus *bus; sd_bus_slot *slot;
    uint64_t deadline; int busy, state, property;
    char prefix[68]; struct fc1_result result;
};
static const char *roles[]={"-supervisor.service",".service","-operator.service",
                           "-prepare.service","-verify.service","-terminal.service"};
struct property { const char *interface, *name, *type; };
static const struct property properties[]={
    {"org.freedesktop.systemd1.Unit","ActiveState","s"},
    {"org.freedesktop.systemd1.Unit","SubState","s"},
    {"org.freedesktop.systemd1.Unit","ControlGroup","s"},
    {"org.freedesktop.systemd1.Unit","FragmentPath","s"},
    {"org.freedesktop.systemd1.Unit","CPUUsageNSec","t"},
    {"org.freedesktop.systemd1.Unit","MemoryCurrent","t"},
    {"org.freedesktop.systemd1.Unit","MemoryPeak","t"},
    {"org.freedesktop.systemd1.Unit","TasksCurrent","t"},
    {"org.freedesktop.systemd1.Service","MainPID","u"},
    {"org.freedesktop.systemd1.Service","ExecMainStatus","i"}
};
static uint64_t now_us(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)<0) return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000000+(uint64_t)t.tv_nsec/1000;
}
static int same_peer(struct fc1_bus *b) {
    struct ucred p; socklen_t n=sizeof p;
    int fd=sd_bus_get_fd(b->bus);
    if(fd<0) return fd;
    if(getsockopt(fd,SOL_SOCKET,SO_PEERCRED,&p,&n)<0) return -errno;
    return n==sizeof p && p.uid==0 && p.pid==1 ? 0 : -EPERM;
}
static int fail(struct fc1_bus *b,int error) {
    b->result.error=error<0?error:-EPROTO; b->busy=0;
    b->slot=sd_bus_slot_unref(b->slot); return b->result.error;
}
static int reply(sd_bus_message *,void *,sd_bus_error *);
static int enqueue(struct fc1_bus *b,sd_bus_message *m) {
    uint64_t n=now_us(); int r;
    if(n>=b->deadline) return fail(b,-ETIMEDOUT);
    r=sd_bus_call_async(b->bus,&b->slot,m,reply,b,b->deadline-n);
    return r<0?fail(b,r):0;
}
static int text_result(struct fc1_bus *b,const char *text) {
    size_t n=strnlen(text,sizeof b->result.text);
    if(n>=sizeof b->result.text) return fail(b,-E2BIG);
    memcpy(b->result.text,text,n+1);b->result.kind=1;return 0;
}
static int reply(sd_bus_message *m,void *data,sd_bus_error *error) {
    struct fc1_bus *b=data; sd_bus_message *next=NULL; int r;
    const char *text=NULL; (void)error;
    b->slot=sd_bus_slot_unref(b->slot);
    if(now_us()>=b->deadline || same_peer(b)<0) return fail(b,-ETIMEDOUT);
    if(sd_bus_message_is_method_error(m,NULL)>0) return fail(b,-EIO);
    if(b->state==1) { /* StartUnit acknowledgement is not launch evidence. */
        r=sd_bus_message_read(m,"o",&text);
        if(r<=0 || strncmp(text,"/org/freedesktop/systemd1/job/",sizeof("/org/freedesktop/systemd1/job/")-1)) return fail(b,-EPROTO);
        r=text_result(b,text); b->busy=0; return r<0?r:1;
    }
    if(b->state==2) { /* Resolve only the allowlisted unit before one property. */
        r=sd_bus_message_read(m,"o",&text);
        if(r<=0 || strncmp(text,"/org/freedesktop/systemd1/unit/",sizeof("/org/freedesktop/systemd1/unit/")-1) || strnlen(text,1024)>=1024)
            return fail(b,-EPROTO);
        r=sd_bus_message_new_method_call(b->bus,&next,NULL,text,
                                        "org.freedesktop.DBus.Properties","Get");
        if(r>=0) r=sd_bus_message_append(next,"ss",properties[b->property].interface,
                                                        properties[b->property].name);
        b->state=3;
        if(r>=0) r=enqueue(b,next);
        sd_bus_message_unref(next);return r<0?fail(b,r):1;
    }
    if(b->state!=3) return fail(b,-EPROTO);
    const char *type=properties[b->property].type;
    r=sd_bus_message_enter_container(m,'v',type);
    if(r<=0) return fail(b,-EPROTO);
    if(type[0]=='s') {
        r=sd_bus_message_read(m,"s",&text);
        if(r>0) r=text_result(b,text); else r=-EPROTO;
    } else if(type[0]=='u') {
        uint32_t value=0;r=sd_bus_message_read(m,"u",&value);
        b->result.number=value;b->result.kind=2;if(r==0) r=-EPROTO;
    } else if(type[0]=='i') {
        int32_t value=0;r=sd_bus_message_read(m,"i",&value);
        b->result.number=(uint64_t)(int64_t)value;b->result.kind=3;if(r==0) r=-EPROTO;
    } else {
        uint64_t value=0;r=sd_bus_message_read(m,"t",&value);
        b->result.number=value;b->result.kind=2;if(r==0) r=-EPROTO;
    }
    if(r<0) return fail(b,r);
    b->busy=0;return 1;
}
int fc1_manager_open(const char *identity,struct fc1_bus **out) {
    struct fc1_bus *b;int r;
    if(!out || !identity || getuid()!=0 || geteuid()!=0 || strlen(identity)!=64) return -EPERM;
    *out=NULL;
    for(size_t i=0;i<64;i++) if(!strchr("0123456789abcdef",identity[i])) return -EINVAL;
    b=calloc(1,sizeof *b);if(!b) return -ENOMEM;
    snprintf(b->prefix,sizeof b->prefix,"fc1%s",identity);
    r=sd_bus_new(&b->bus);
    if(r>=0) r=sd_bus_set_address(b->bus,"unix:path=/run/systemd/private");
    if(r>=0) r=sd_bus_start(b->bus);
    if(r>=0) r=same_peer(b);
    if(r<0) { sd_bus_unref(b->bus);free(b);return r; }
    *out=b;return 0;
}
static int begin(struct fc1_bus *b,int role,int property,uint64_t deadline,int start) {
    sd_bus_message *m=NULL;char unit[96];int r;
    if(!b || role<0 || role>=6 || b->busy || deadline<=now_us()) return -EINVAL;
    if(!start && (property<0 || property>=(int)(sizeof properties/sizeof *properties))) return -EINVAL;
    r=same_peer(b);if(r<0) return r;
    snprintf(unit,sizeof unit,"%s%s",b->prefix,roles[role]);
    memset(&b->result,0,sizeof b->result);b->deadline=deadline;b->property=property;
    b->busy=1;b->state=start?1:2;
    r=sd_bus_message_new_method_call(b->bus,&m,NULL,"/org/freedesktop/systemd1",
                 "org.freedesktop.systemd1.Manager",start?"StartUnit":"GetUnit");
    if(r>=0) r=start?sd_bus_message_append(m,"ss",unit,"fail"):sd_bus_message_append(m,"s",unit);
    if(r>=0) r=enqueue(b,m);
    sd_bus_message_unref(m);return r<0?fail(b,r):0;
}
int fc1_manager_start(struct fc1_bus *b,int role,uint64_t deadline) { return begin(b,role,0,deadline,1); }
int fc1_manager_property(struct fc1_bus *b,int role,int property,uint64_t deadline) {
    return begin(b,role,property,deadline,0);
}
int fc1_manager_step(struct fc1_bus *b,struct fc1_result *out) {
    int r;
    if(!b || !out) return -EINVAL;
    if(b->busy && now_us()>=b->deadline) fail(b,-ETIMEDOUT);
    for(int i=0;b->busy && i<16;i++) {
        r=sd_bus_process(b->bus,NULL);
        if(r<0) { fail(b,r);break; }
        if(!r) break;
    }
    if(b->busy) return 0;
    *out=b->result;return b->result.error?b->result.error:1;
}
int fc1_manager_fd(struct fc1_bus *b) { return b?sd_bus_get_fd(b->bus):-EINVAL; }
int fc1_manager_events(struct fc1_bus *b) { return b?sd_bus_get_events(b->bus):-EINVAL; }
void fc1_manager_close(struct fc1_bus *b) {
    if(!b) return;
    sd_bus_slot_unref(b->slot);sd_bus_close(b->bus);sd_bus_unref(b->bus);free(b);
}
