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


        document.querySelectorAll(".like-btn").forEach(function (button) {
            button.addEventListener("click", async function () {
                const response = await fetch(button.dataset.url, {
                    method: "POST"
                });
                const result = await response.json();

                if (result.success) {
                    button.classList.toggle("liked", result.liked);
                    const count = document.getElementById(`likes-${button.closest(".post-card").dataset.postId}`);
                    if (count) count.textContent = result.like_count;
                    const label = count && count.parentElement;
                    if (label) label.lastChild.textContent = result.like_count === 1 ? " like" : " likes";
                }
            });
        });
    }
);

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

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".share-btn").forEach(function (button) {
        button.addEventListener("click", async function () {
            const shareUrl = button.dataset.shareUrl;
            if (navigator.share) {
                await navigator.share({ title: "PiskeGram", url: shareUrl });
            } else {
                await navigator.clipboard.writeText(shareUrl);
                button.classList.add("shared");
                button.title = "Link copied";
            }
        });
    });

    document.querySelectorAll(".save-btn").forEach(function (button) {
        const key = `piskegram-saved-${button.dataset.saveId}`;
        button.classList.toggle("saved", localStorage.getItem(key) === "true");
        button.addEventListener("click", function () {
            const saved = !button.classList.contains("saved");
            button.classList.toggle("saved", saved);
            localStorage.setItem(key, saved);
        });
    });

    document.querySelectorAll("form[enctype='multipart/form-data']").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const fileInput = form.querySelector("input[type='file']");
            const file = fileInput && fileInput.files[0];

            if (file && file.size > 15 * 1024 * 1024) {
                event.preventDefault();
                window.alert("Please choose an image that is 15 MB or smaller.");
            }
        });
    });
});

function focusComment(postId) {
    const input = document.querySelector(`#comment-${postId} input[name='comment']`);
    if (input) input.focus();
}
