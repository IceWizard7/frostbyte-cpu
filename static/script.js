const socket = io();

const MIN_INTERVAL = 50; // ms
let lastUpdateTime = 0;
let latestData = null;
let updateScheduled = false;

socket.on('simulation_update', (data) => {
    // console.log("data received", data);

    latestData = data;

    const now = Date.now()
    const timeSinceLast = now - lastUpdateTime;

    if (timeSinceLast >= MIN_INTERVAL) {
        performUIUpdate(latestData);
        lastUpdateTime = now;
        updateScheduled = false;
    } else if (!updateScheduled) {
        updateScheduled = true;
        setTimeout(() => {
            performUIUpdate(latestData);
            lastUpdateTime = Date.now();
            updateScheduled = false;
        }, MIN_INTERVAL - timeSinceLast);
    }
});


function performUIUpdate(data) {
    // console.log("Performing UI update", data);

    // Update Program Counter
    document.getElementById('pc-value').textContent = data.pc;

    // Update Registers
    document.querySelectorAll('.register-value').forEach(span => {
        const name = span.dataset.reg;
        if (data.registers[name]) span.textContent = data.registers[name];
    });

    // Update Read-Only Ports (ps)
    document.querySelectorAll('.port-ps-value').forEach(span => {
        const name = span.dataset.ps;
        if (data.ps[name]) span.textContent = data.ps[name];
    });

    // Update Write-Only Ports (pd)
    document.querySelectorAll('.port-pd-value').forEach(span => {
        const name = span.dataset.pd;
        if (data.pd[name]) span.textContent = data.pd[name];
    });

    // Update Data Memory
    document.querySelectorAll('.data-memory-value').forEach(span => {
        const name = span.dataset.mem;
        if (data.data_memory[name]) span.textContent = data.data_memory[name];
    });

    // Update Call Stack
    document.querySelectorAll('.callstack-value').forEach(span => {
        const name = span.dataset.call;
        if (data.call_stack[name]) span.textContent = data.call_stack[name];
    });

    // Update ALU Flags
    document.querySelectorAll('.alu-flag-value').forEach(span => {
        const name = span.dataset.flag;
        span.textContent = data.alu_flags[name];
    });

    // Update Letters and Number
    document.getElementById('letters-value').textContent = data.letters;
    document.getElementById('number-value').textContent = data.number;
    document.getElementById('big-number-value').textContent = data.big_number;

    // Update Screen Data
    const flatPixels = data.screen_data.flat();
    document.querySelectorAll('.lamp-pixel').forEach((img, i) => {
        img.src = flatPixels[i]
            ? "/static/redstone_lamp_on.png"
            : "/static/redstone_lamp_off.png";
    });

    // Update Assembly Code Display
    const assemblyContainer = document.getElementById('assembly-code');
    if (data.preprocessed_assembly) {
        assemblyContainer.innerHTML = ''; // Clear existing content
        data.preprocessed_assembly.forEach((line, index) => {
            const div = document.createElement('div');
            div.className = 'code-line';
            div.dataset.line = index;
            div.textContent = line;
            assemblyContainer.appendChild(div);
        });
    }

    // Highlight current line
    const currentLine = data.int_pc;
    const lineElement = document.querySelector(`.code-line[data-line="${currentLine}"]`);
    // console.log("Highlighting line:", currentLine);

    document.querySelectorAll('.code-line').forEach(line => {
        line.classList.remove('highlight');
    });

    if (lineElement) {
        lineElement.classList.add('highlight');
        const autoScrollEnabled = document.getElementById('auto-scroll-toggle')?.checked;
        if (autoScrollEnabled) {
            lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    } else {
        console.warn("No .code-line found for index:", currentLine);
    }
};


socket.on('error_message', data => {
    document.getElementById('error-message').textContent = data.message;
        setTimeout(() => {
            document.getElementById('error-message').textContent = '';
        }, 5000);
})

socket.on('generate_schematic_successful', data => {
    document.getElementById('gen-schem-status').textContent = 'Generated Schematic successfully!';
        setTimeout(() => {
            document.getElementById('gen-schem-status').textContent = '';
        }, 750);
})


document.getElementById('reset-btn').addEventListener('click', () => {
    socket.emit('reset_simulation');
});

document.getElementById('step-btn').addEventListener('click', () => {
    socket.emit('step_simulation');
});

document.getElementById('stop-btn').addEventListener('click', () => {
    socket.emit('stop_simulation');
});

document.getElementById('continue-btn').addEventListener('click', () => {
    socket.emit('continue_simulation');
});

document.getElementById('gen-schem-btn').addEventListener('click', () => {
    socket.emit('generate_schematic');
});

// On website Load, Request an Update
document.addEventListener('DOMContentLoaded', () => {
    socket.emit('request_update');
});

// Save the expanded/collapsed state
function saveCollapseState(buttonClass) {
    const states = {};
    document.querySelectorAll(buttonClass).forEach((btn, index) => {
        states[index] = btn.classList.contains("active");
    });
    localStorage.setItem(buttonClass, JSON.stringify(states));
}

// Restore the state and update visibility
function restoreCollapseState(buttonClass, contentClass) {
    const saved = localStorage.getItem(buttonClass);
    if (!saved) return;

    const states = JSON.parse(saved);
    const buttons = document.querySelectorAll(buttonClass);
    const contents = document.querySelectorAll(contentClass);

    buttons.forEach((btn, index) => {
        const content = contents[index];
        if (states[index]) {
            btn.classList.add("active");
            content.style.display = "grid"; // Changed to grid
        } else {
            btn.classList.remove("active");
            content.style.display = "none";
        }
    });
}

// Setup toggling logic
function setupToggle(buttonClass, contentClass) {
    const buttons = document.querySelectorAll(buttonClass);
    const contents = document.querySelectorAll(contentClass);

    buttons.forEach((btn, index) => {
        btn.addEventListener("click", () => {
            btn.classList.toggle("active");
            const content = contents[index];
            if (btn.classList.contains("active")) {
                content.style.display = "grid"; // Changed to grid
            } else {
                content.style.display = "none";
            }
            saveCollapseState(buttonClass);
        });
    });
}

// Initialize collapsibles and sub-collapsibles
document.addEventListener('DOMContentLoaded', restoreCollapseState(".collapsible", ".content"));
document.addEventListener('DOMContentLoaded', restoreCollapseState(".sub-collapsible", ".sub-content"));
setupToggle(".collapsible", ".content");
setupToggle(".sub-collapsible", ".sub-content");

// Drag & Drop logic
const dropArea = document.getElementById("drop-area");

["dragenter", "dragover"].forEach(eventName => {
    dropArea.addEventListener(eventName, e => {
        e.preventDefault();
        dropArea.style.backgroundColor = "#333";
    }, false);
});

["dragleave", "drop"].forEach(eventName => {
    dropArea.addEventListener(eventName, e => {
        e.preventDefault();
        dropArea.style.backgroundColor = "transparent";
    }, false);
});

// Speed Control Synchronization Logic
const speedSlider = document.getElementById('speed-slider');
const speedInput = document.getElementById('speed-input');
const speedOutput = document.getElementById('speed-output');
const incButton = document.getElementById('speed-increment');
const decButton = document.getElementById('speed-decrement');

const SPEED_STORAGE_KEY = 'speedValue'; // Key for localStorage

// Function to update all speed elements
function updateSpeed(value) {
    const clampedValue = Math.max(1, Math.min(2500, value)); // Enforce min/max
    speedSlider.value = clampedValue;
    speedInput.value = clampedValue;
    speedOutput.textContent = clampedValue;
    localStorage.setItem(SPEED_STORAGE_KEY, clampedValue); // Save the value

    socket.emit("update_speed", { speed: clampedValue });
}

// Function to restore speed from localStorage
function restoreSpeed() {
    const savedSpeed = localStorage.getItem(SPEED_STORAGE_KEY);
    if (savedSpeed !== null) {
        updateSpeed(parseInt(savedSpeed));
    } else {
        updateSpeed(parseInt(speedSlider.value)); // Use initial slider value if nothing saved
    }
}

const AUTO_SCROLL_KEY = 'autoScrollEnabled';
const autoScrollCheckbox = document.getElementById('auto-scroll-toggle');

// Restore saved auto-scroll setting on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedState = localStorage.getItem(AUTO_SCROLL_KEY);
    const enabled = savedState === 'true'; // Default to false if not set
    autoScrollCheckbox.checked = enabled;

});

// When checkbox is toggled, update storage and emit
autoScrollCheckbox.addEventListener('change', () => {
    const enabled = autoScrollCheckbox.checked;
    localStorage.setItem(AUTO_SCROLL_KEY, enabled.toString());
});

// Controller Input Handling
const keysPressed = new Set();

// Keyboard binds
document.addEventListener('keydown', (event) => {
    const activeElement = document.activeElement;
    const isTyping = activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA';
    if (isTyping) return;

    const key = event.key.toLowerCase();

    switch (key) {
        case 'w':
        case 'a':
        case 's':
        case 'd':
            if (!keysPressed.has(key)) { // Only trigger on first press
                keysPressed.add(key);
                updateVisualButton(key, true);
            }
            event.preventDefault(); // prevent scrolling
            break;

        case 'r':
            socket.emit('reset_simulation');
            visuallyPress('reset-btn');
            break;

        case 'c':
            socket.emit('continue_simulation');
            visuallyPress('continue-btn');
            break;

        case 't':
            socket.emit('step_simulation');
            visuallyPress('step-btn');
            break;

        case ' ':
            event.preventDefault(); // Prevent page scrolling
            socket.emit('stop_simulation');
            visuallyPress('stop-btn');
            break;

        case 'g':
            socket.emit('generate_schematic');
            visuallyPress('gen-schem-btn');
            break;
    }
});

document.addEventListener('keyup', (event) => {
    const key = event.key.toLowerCase();
    if (['w', 'a', 's', 'd'].includes(key)) {
        keysPressed.delete(key);
        updateVisualButton(key, false);
    }
});

function updateVisualButton(key, pressed) {
    const keyMap = { w: 'btn-up', a: 'btn-left', s: 'btn-down', d: 'btn-right' };
    const btn = document.getElementById(keyMap[key]);
    if (btn) {
        btn.classList.toggle('pressed', pressed);
        sendControllerUpdate();
    }
}

// Visual feedback for buttons
function visuallyPress(buttonId) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    btn.classList.add('pressed');
    setTimeout(() => btn.classList.remove('pressed'), 150);
}

document.addEventListener('DOMContentLoaded', restoreSpeed);

speedSlider.addEventListener('input', () => updateSpeed(speedSlider.value));
speedInput.addEventListener('input', () => updateSpeed(speedInput.value));

incButton.addEventListener('click', () => updateSpeed(parseInt(speedSlider.value) + 1));
decButton.addEventListener('click', () => updateSpeed(parseInt(speedSlider.value) - 1));

// When the user types a value and clicks away, re-validate
speedInput.addEventListener('change', () => updateSpeed(speedInput.value));

dropArea.addEventListener("drop", e => {
    const file = e.dataTransfer.files[0];
    if (!file || file.type !== "text/plain") {
        alert("Please drop a .txt file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => {
        if (response.ok) {
            location.reload(); // Reload to show updated code
        } else {
            alert("Upload failed.");
        }
    })
    .catch(err => {
        alert("Upload error.");
        console.error(err);
    });
});

function saveText() {
    const text = document.getElementById('codeInput').value;
    fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ codeInput: text }),
    }).then(() => {
        document.getElementById('save-status').textContent = 'Saved successfully!';
        setTimeout(() => {
            document.getElementById('save-status').textContent = '';
        }, 750);
    });

    socket.emit('request_update');
}

document.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('mousedown', () => {
        btn.classList.add('pressed');
        sendControllerUpdate();
    });
    btn.addEventListener('mouseup', () => {
        btn.classList.remove('pressed');
        sendControllerUpdate();
    });
    btn.addEventListener('mouseleave', () => {
        btn.classList.remove('pressed');
        sendControllerUpdate();
    });
    btn.addEventListener('touchstart', (e) => {
        e.preventDefault();
        btn.classList.add('pressed');
        sendControllerUpdate();
    });
    btn.addEventListener('touchend', (e) => {
        e.preventDefault();
        btn.classList.remove('pressed');
        sendControllerUpdate();
    });
});

function getControllerData() {
    return {
        UP:     isButtonPressed('btn-up'),
        RIGHT:  isButtonPressed('btn-right'),
        DOWN:   isButtonPressed('btn-down'),
        LEFT:   isButtonPressed('btn-left'),
        START:  isButtonPressed('btn-start'),
        SELECT: isButtonPressed('btn-select'),
        Y:      isButtonPressed('btn-y'),
        X:      isButtonPressed('btn-x')
    };
}

function isButtonPressed(id) {
    const btn = document.getElementById(id);
    return btn && btn.classList.contains('pressed') ? 1 : 0;
}

function sendControllerUpdate() {
    const controllerData = getControllerData();
    socket.emit('controller_update', { controller: controllerData });
}