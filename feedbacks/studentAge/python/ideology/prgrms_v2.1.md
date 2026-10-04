```assenbly
mov STATE 10, 6
mov STATE A, 9
mov STATE 1010, 10
add STATE 10, STATE A
sub STATE 10, STATE 1010
```

```assenbly
section .data
    msg db "Hello, World!", 10
    len equ $ - msg

section .text
    global _start

_start:
    mov rax, 1
    mov rdi, 1
    mov rsi, msg
    mov rdx, len
    syscall

    mov rax, 60
    mov rdi, 0
    syscall
```

```assenbly
STATE ENTRY

message := "Hello, World!"

output.STATE(message)

STATE EXIT
```
