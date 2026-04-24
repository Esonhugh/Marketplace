# Binary Analysis Reference

## codesign

```bash
codesign -dv binary                      # Basic signature info
codesign -dvv binary                     # Verbose (authority chain, TeamID, CDHash)
codesign -d --entitlements :- binary     # Show entitlements XML to stdout
codesign -d --entitlements - binary      # Same (older syntax)
codesign -s "Developer ID" binary        # Sign with identity
codesign -f -s "identity" binary         # Force re-sign
codesign --option=runtime -s "id" binary # Sign with hardened runtime
codesign --option=library -s "id" binary # Sign with library validation
codesign --option=0x800 -s "id" binary   # Sign with CS_RESTRICT
codesign -vv binary                      # Verify signature
```

### Key Entitlements

| Entitlement | Purpose |
|-------------|---------|
| `com.apple.security.get-task-allow` | Allow debugging (task_for_pid) |
| `com.apple.security.cs.allow-dyld-environment-variables` | Allow DYLD_INSERT |
| `com.apple.security.cs.disable-library-validation` | Allow unsigned dylibs |
| `com.apple.security.cs.allow-unsigned-executable-memory` | JIT/writable+executable |
| `com.apple.private.tcc.manager` | TCC database management |

## objdump

```bash
objdump -m --dylibs-used binary               # Loaded dylibs
objdump -m -h binary                          # Section headers
objdump -m --syms binary                      # Symbol table
objdump --full-contents --section=__cstring binary  # Raw section data
objdump -d binary                             # Disassemble all
objdump --disassemble-functions=_hello binary  # Disassemble specific function
objdump -x86-asm-syntax=intel -d binary       # Intel syntax
```

## jtool2

```bash
jtool2 -l binary                   # Load commands
jtool2 -L binary                   # Linked dylibs
jtool2 -S binary                   # Symbol table
jtool2 --sig binary                # Code signature details
jtool2 --ent binary                # Entitlements
ARCH=x86_64 jtool2 -l fat_binary  # Specify architecture
```

## Hopper Disassembler

### Views
- **ASM**: Assembly listing
- **CFG**: Control flow graph
- **Pseudocode**: Decompiled C-like output
- **Hex**: Raw hex editor

### Navigation
- **Proc tab**: Function/procedure list
- **Str tab**: String references (search for interesting strings)
- **Double-click**: Follow address/reference
- **References** (x key): Find cross-references to address
- **Inspector panel**: Call graph visualization

### External Function Resolution Chain

```
call _printf         ; in __text
  -> __stubs         ; stub jumps to address in __la_symbol_ptr
  -> __la_symbol_ptr ; lazy symbol pointer (initially points to __stub_helper)
  -> __stub_helper   ; calls dyld to resolve, patches __la_symbol_ptr
  -> resolved addr   ; subsequent calls go directly
```

## LLDB Debugger

### Configuration

```bash
# ~/.lldbinit
settings set target.x86-disassembly-flavor intel
```

### Debugging Access Rules

1. Binary has `get-task-allow` entitlement -> debug as regular user
2. SIP-protected binary -> needs debugger entitlement (com.apple.debugserver.applist)
3. Non-SIP, no entitlement -> need root or admin group membership

### Launching & Attaching

```
lldb ./binary                         # Launch with LLDB
lldb -p PID                           # Attach to running process
process launch -- arg1 arg2           # Launch with args
```

### Breakpoints

```
b main                                        # Break on main (any module)
breakpoint set -n main -s toolsdemo           # Break on main in specific module
breakpoint set -a 0x100003f00                 # Break at address
b toolsdemo`main                              # Module-qualified
breakpoint list                               # List all breakpoints
breakpoint delete 1                           # Delete breakpoint #1
```

### Disassembly

```
dis                          # Disassemble current function
dis -c 6                     # Disassemble 6 instructions from current
dis -n hello -b              # Disassemble function with bytecodes
dis -s 0xADDR -e 0xADDR     # Disassemble address range
dis -p -c 4                  # From current IP, 4 instructions
```

### Registers & Memory

```
register read                     # All registers
register read rip rax rdi rsi     # Specific registers
register write rax 42             # Modify register

memory read $rsi                  # Read memory at RSI
memory read -c 32 $rsp           # Read 32 bytes from stack
memory read -f s $rdi            # Read as C string
memory write -f s $rip+0x10 "new string"  # Write string to memory
x/16bx $rsp                     # Examine 16 bytes hex from stack
```

### Execution Control

```
s       # Source-level step into
si      # Instruction-level step into
n       # Source-level step over
ni      # Instruction-level step over
c       # Continue execution
finish  # Run until current function returns
```

### Useful Commands

```
parray 3 (char **)$rsi          # Print 3-element char** array
p (char *)$rdi                  # Print register as C string
po $rax                         # Print ObjC object description
image list                      # List loaded images/modules
expression -- (void)printf("x") # Evaluate expression in target
```

## DTrace

### D Language Syntax

```
probe_description /predicate/ { action; }
```

### Probe Format

```
provider:module:function:name
```

Common providers: `syscall`, `pid`, `fbt`, `objc`, `profile`, `proc`

### Practical Examples

```bash
# Trace all syscalls by process name
sudo dtrace -n 'syscall:::entry /execname == "targetapp"/ { printf("%s", probefunc); }'

# Trace file opens
sudo dtrace -n 'syscall::open*:entry /execname == "app"/ { printf("%s", copyinstr(arg0)); }'

# Count syscalls by function
sudo dtrace -n 'syscall:::entry /execname == "app"/ { @[probefunc] = count(); }'

# Trace with argument printing
sudo dtrace -n 'syscall::write:entry /execname == "app"/ {
    printf("fd=%d len=%d", arg0, arg2);
}'
```

### Built-in Variables

| Variable | Meaning |
|----------|---------|
| `execname` | Process name |
| `pid` | Process ID |
| `probefunc` | Current probe function |
| `arg0`-`arg9` | Syscall/function arguments |
| `timestamp` | Nanosecond timestamp |

### Aggregations

```
@[key] = count();      # Count occurrences
@[key] = sum(value);   # Sum values
@[key] = avg(value);   # Average
@[key] = quantize(v);  # Distribution histogram
```

### Utility Commands

```bash
dtrace -l                           # List all probes
dtrace -l -f "write*"              # List probes matching function
dtrace -l -n 'syscall:::entry'     # List syscall entry probes
man -k dtrace                       # Find DTrace-related man pages
sudo dtruss -n appname             # Trace syscalls (strace equivalent)
sudo dtruss -p PID                 # Trace running process
```

### String Handling

```
copyinstr(arg0)    # Copy user-space string (for char* syscall args)
stringof(addr)     # Kernel-space string
```
