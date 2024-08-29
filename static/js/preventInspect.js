document.addEventListener('keydown', function (event) {
    // Disable F12 key
    if (event.key === 'F12') {
        event.preventDefault();
        event.stopImmediatePropagation();
    }
    // Disable Ctrl+Shift+I and Ctrl+Shift+J
    if ((event.ctrlKey && event.shiftKey && (event.key === 'I' || event.key === 'J')) || 
        (event.metaKey && event.shiftKey && (event.key === 'I' || event.key === 'J'))) {
        event.preventDefault();
        event.stopImmediatePropagation();
    }
    // Disable Ctrl+U
    if (event.ctrlKey && event.key === 'U') {
        event.preventDefault();
        event.stopImmediatePropagation();
    }
});

// Prevent opening context menu with right-click
document.addEventListener('contextmenu', function (event) {
    event.preventDefault();
});

// Prevent opening developer tools by right-click and 'Inspect'
document.addEventListener('keydown', function (event) {
    if (event.ctrlKey && event.shiftKey && event.key === 'I') {
        event.preventDefault();
        event.stopImmediatePropagation();
    }
});

// Prevent copying content
document.addEventListener('copy', function (event) {
    event.preventDefault();
});

// Prevent pasting content
document.addEventListener('paste', function (event) {
    event.preventDefault();
});