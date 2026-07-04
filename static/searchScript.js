
function moveToDate(year, month, day) {
    window.location.href = `/?year=${year}&month=${month}&day=${day}`;
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".search-result-row").forEach((row) => {
    row.addEventListener("click", () => {
        const timestamp = row.dataset.timestamp;
        const txDate = new Date(timestamp.replace(" ", "T"));

        if (Number.isNaN(txDate.getTime())) return;

        const year = txDate.getFullYear();
        const month = txDate.getMonth() + 1;
        const day = txDate.getDate();

        moveToDate(year, month, day);
    });

    row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        row.click();
        }
    });
    });
});