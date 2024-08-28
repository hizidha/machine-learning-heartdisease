const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const chooseFileButton = document.getElementById('chooseFileButton');
const dropzoneText = document.getElementById('dropzoneText');
const dropzoneText2 = document.getElementById('dropzoneText2');
const uploadForm = document.getElementById('btn-gets');
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
const loadingIndicator = document.getElementById('loadingIndicator');
const iframe = document.getElementById('notebookIframe');

document.addEventListener('DOMContentLoaded', function () {
    chooseFileButton.addEventListener('click', function () {
        fileInput.click();
    });

    // Handle drag events
    dropzone.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', function () {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', function (e) {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            dropzoneText.textContent = files[0].name;
            dropzoneText2.style.display = 'none';
        }
    });

    // Handle file input change
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            dropzoneText.textContent = fileInput.files[0].name;
            dropzoneText2.style.display = 'none';
        } else {
            dropzoneText.textContent = 'Drag and Drop the File Here or';
            dropzoneText2.style.display = 'block';
        }
    });

    uploadForm.addEventListener('click', function (e) {
        if (fileInput.files.length === 0) {
            e.preventDefault();
            $.notify({
                icon: 'fa fa-exclamation-triangle',
                title: 'Oh No!',
                message: 'Please select a file before submitting.',
            }, {
                type: 'danger',
                placement: {
                    from: 'top',
                    align: 'right',
                },
                time: 1000,
            });
        }
    });

    // Initialize Bootstrap tooltips
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Automatically click the first button when the modal is shown
    document.getElementById('imageModal2').addEventListener('shown.bs.modal', function () {
        document.querySelector('#btn1').click();
    });

    // Prevent interaction with the overlay
    const overlay = document.getElementById('overlays');
    overlay.addEventListener('mousedown', function (event) {
        event.preventDefault();
        event.stopPropagation();
    });
    overlay.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
    });
    overlay.addEventListener('contextmenu', function (event) {
        event.preventDefault();
        event.stopPropagation();
    });
});

function loadNotebook(notebookNumber) {
    let fileUrl = '';

    switch (notebookNumber) {
        case 1:
            fileUrl = 'https://nbviewer.jupyter.org/github/hizidha/machine-learning-heartdisease/blob/main/.preprocessing/1_eda.ipynb';
            break;
        case 2:
            fileUrl = 'https://nbviewer.jupyter.org/github/hizidha/machine-learning-heartdisease/blob/main/.preprocessing/2_preprocessing.ipynb';
            break;
        case 3:
            fileUrl = 'https://nbviewer.jupyter.org/github/hizidha/machine-learning-heartdisease/blob/main/.preprocessing/3_baseModel_rev.ipynb';
            break;
        default:
            fileUrl = 'https://nbviewer.jupyter.org/github/hizidha/machine-learning-heartdisease/blob/main/.preprocessing/1_eda.ipynb';
            break;
    }

    if (fileUrl !== '') {
        iframe.src = fileUrl;
        loadingIndicator.style.display = 'flex';

        iframe.addEventListener('load', function () {
            loadingIndicator.style.display = 'none';
        });
    }

    updateButtonStyles(notebookNumber);
}

function updateButtonStyles(activeNumber) {
    const buttons = document.querySelectorAll('#notebookButtons .btn');
    buttons.forEach(button => {
        const buttonNumber = button.onclick.toString().match(/\d+/)[0];
        if (parseInt(buttonNumber) === activeNumber) {
            button.classList.add('btn-secondary');
            button.classList.remove('btn-black');
        } else {
            button.classList.add('btn-black');
            button.classList.remove('btn-secondary');
        }
    });
}