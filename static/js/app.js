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
