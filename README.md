# Automacro

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

Automacro is a powerful and flexible Python library for creating macros and automation workflows. It combines low-level input control (keyboard and mouse) with a sophisticated workflow engine, allowing you to build complex, interruptible, and maintainable automation scripts with ease.

## Key Features

- **Workflow Engine:** Compose automation logic using a tree of nodes.
- **Mouse & Keyboard Control:** Intuitive API for simulating inputs and listening to events.
- **Computer Vision & OCR:** Built-in support for screen capture, color detection, and OCR.
- **Advanced Execution Control:** Start, stop, pause, resume, and even step-through your workflows just like you would with a debugger.
- **Thread-Safe:** Designed for multi-threaded environments, allowing you to easily control workflows from other threads.

## Installation

Automacro is currently not available on PyPI, but you can install it by cloning the repository and installing it manually:

```bash
git clone https://github.com/junkaizhang8/automacro.git
pip install ./automacro
```

### Optional Dependencies

For computer vision and OCR support:

```bash
# For OpenCV (image processing)
pip install ./automacro[cv]

# For Tesseract OCR
pip install ./automacro[ocr-tesseract]
```

_Note: For OCR, you must also have [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system._

## Quick Start

### Creating a Workflow

Structure your automation into reusable and controllable components using nodes.

```python
import time

from automacro import ExecutionContext, Sleep, Task, Workflow, if_, while_

class IterateTask(Task):
    def __init__(self, count: int):
        super().__init__()
        self._count = count

    def on_enter(self) -> None:
        self._current = 0

    def step(self, ctx: ExecutionContext) -> bool:
        if self._current < self._count:
            print(f"Iteration {self._current + 1}/{self._count}")
            self._current += 1
            # Wait for a short time before the next iteration
            ctx.wait(0.5)
            # Return False to indicate that the task is not yet complete
            return False
        # Return True to indicate that the task is complete
        return True

counter = 0

def increment_counter():
    global counter
    counter += 1

def check_counter():
    return counter < 4

def check_ready():
    return counter % 2 == 0

# Define a node chain by chaining nodes together with the | operator
chain = while_(check_counter).do_(
    (lambda: print("Checking if ready..."))
    | if_(check_ready)
    .then_((lambda: print("Ready!")) | IterateTask(5))
    .else_((lambda: print("Not ready. Sleeping for 3 seconds...")) | Sleep(3.0))
    | increment_counter
)

workflow = Workflow(chain)
# Run in a new thread
workflow.start()

time.sleep(2)
workflow.pause()
print("Workflow paused!")
time.sleep(1)
workflow.resume()
print("Workflow resumed!")
time.sleep(2)
workflow.stop(block=True)
print("Workflow stopped!")
```

### Basic Input Control

Simulate mouse and keyboard actions with simple, intuitive commands.

```python
from automacro.mouse import MouseButton, MouseController
from automacro.keyboard import KeyController, KeySequence, ModifierKey
from automacro.animate import easing

mouse = MouseController()
keyboard = KeyController()

# Move mouse with easing
mouse.move_to(100, 100, duration=1.0, easing_fn=easing.ease_in_out_quad)
mouse.click(MouseButton.LEFT)

# Type text
keyboard.type("Hello, World!")

# Use key sequences (e.g., Ctrl+C)
keyboard.tap(KeySequence("c", {ModifierKey.CTRL}))
```

### Event Listeners

Listen and respond to keyboard and mouse events in real-time.

```python
import time

from automacro.keyboard import Key, KeyListener, KeySequence, ModifierKey
from automacro.mouse import MouseButton, MouseListener

def on_ctrl_c():
    print("Ctrl+C detected!")

def on_f1():
    print("F1 pressed!")

def on_move(x, y):
    print(f"Mouse moved to ({x}, {y})")

def on_click(x, y, button, pressed):
    if pressed:
        if button == MouseButton.LEFT:
            print(f"Left button pressed at ({x}, {y})")
        elif button == MouseButton.RIGHT:
            print(f"Right button pressed at ({x}, {y})")

def on_scroll(x, y, dx, dy):
    print(f"Scrolled at ({x}, {y}) with horizontal delta {dx} and vertical delta {dy}")

# Create a mapping of KeySequences to callables
callbacks = {
    KeySequence("c", {ModifierKey.CTRL}): on_ctrl_c,
    KeySequence(Key.F1): on_f1,
}

# Start the key listener
with KeyListener(callbacks):
    # Start the mouse listener
    with MouseListener(on_move=on_move, on_click=on_click, on_scroll=on_scroll):
        # Keep the listeners running for 10 seconds
        time.sleep(10)
```

## Advanced Usage

### Vision & OCR

Make your workflows respond to what's on the screen.

```python
from automacro.screen import is_pixel
from automacro.screen.ocr import (
    contains_text,
    set_backend,
)
from automacro.screen.ocr.tesseract import TesseractOCR

# Setup global OCR back-end
set_backend(TesseractOCR())

# Check for text in a specific region (left, top, width, height)
if contains_text("Login", region=(0, 0, 500, 500)):
    print("Login screen detected!")

# Check pixel color
if is_pixel(100, 100, (255, 255, 255), tolerance=8):
    print("Pixel at (100, 100) is approximately white!")

```

### Debugging with Stepping

Debugger-like stepping capabilities for workflows, which is perfect for complex automation development.

```python
workflow = Workflow(my_node_chain)
workflow.start(start_paused=True)

# Step-by-step execution
workflow.step_in()   # Enter a node
workflow.step_over() # Execute the current node completely
workflow.step_out()  # Finish the current scope and return to parent
```

## License

Automacro is released under the [BSD 3-Clause License](LICENSE).
