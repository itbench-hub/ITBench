package check

default result = false

result {
    input.x11_forwarding == "X11Forwarding no"
}