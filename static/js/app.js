document.addEventListener(
    "DOMContentLoaded",
    function () {

        const flashes =
            document.querySelectorAll(".flash");

        flashes.forEach(function (flash) {

            setTimeout(function () {

                flash.style.opacity = "0";
                flash.style.transform =
                    "translateY(-10px)";

                setTimeout(function () {
                    flash.remove();
                }, 300);

            }, 3000);

        });


        document
            .querySelectorAll(".like-btn")

function formatFileSize(bytes) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showImagePreview(file, preview) {
    preview.innerHTML = "";

    if (!file || file.size > 15 * 1024 * 1024 || !file.type.startsWith("image/")) {
        return;
    }

    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = "Selected image preview";
    preview.appendChild(image);
}

function previewImage(event) {
    const file = event.target.files[0];
    const preview = document.getElementById("image-preview");
    const status = document.getElementById("upload-file-status");

    if (!file || !preview) return;

    showImagePreview(file, preview);
    if (status) {
        status.textContent = `${file.name} · ${formatFileSize(file.size)}`;
        status.classList.toggle("upload-file-error", file.size > 15 * 1024 * 1024);
    }
}

function previewProfileImage(event) {
    const file = event.target.files[0];
    const preview = document.getElementById("profile-image-preview");

    if (file && preview) showImagePreview(file, preview);
}
