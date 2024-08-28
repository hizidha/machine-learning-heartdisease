WebFont.load({
    google: { families: ["Public Sans:300,400,500,600,700"] },
    custom: {
        families: [
            "Font Awesome 5 Solid", "Font Awesome 5 Regular",
            "Font Awesome 5 Brands", "simple-line-icons",
        ],
        urls: ["../static/css/fonts.min.css"],
    },
    active: function () {
        sessionStorage.fonts = true;
    },
});

window.onload = function () {
    updateDateTime();
    setInterval(updateDateTime, 1000);
};

function updateDateTime() {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    const now = new Date();
    const day = days[now.getDay()];
    const date = now.getDate();
    const month = months[now.getMonth()];
    const year = now.getFullYear();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');

    const formattedDateTime = `${day}, ${date} ${month} ${year} | ${hours}:${minutes}:${seconds}`;
    document.getElementById('days').innerText = formattedDateTime;
}