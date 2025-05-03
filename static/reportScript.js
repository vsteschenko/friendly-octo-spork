function index() {
    window.location.href = "/";
}

function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
  }
  
function loadReportChart() {
const year = getQueryParam("year") || new Date().getFullYear();
const month = getQueryParam("month") || new Date().getMonth() + 1;

    fetch(`/report_chart?year=${year}&month=${month}`)
        .then((response) => response.json())
        .then((data) => {
    const ctx = document.getElementById("reportChart").getContext("2d");
    const labels = data.categories;
    const categoryColors = {
        grocery: "#FF6384",
        rent: "#36A2EB",
        utilities: "#FFCE56",
        transport: "#4BC0C0",
        insurance: "#9966FF",
        dining: "#FF9F40",
        entertainment: "#C9CBCF",
        shopping: "#F67019",
        health: "#00A950",
        beauty: "#FF6B6B",
        loans: "#A0522D",
        credit_card: "#4682B4",
        savings: "#32CD32",
        education: "#8A2BE2",
        pets: "#DAA520",
        home_maintenance: "#708090",
        gifts: "#D2691E",
        travel: "#20B2AA",
        subscriptions: "#E9967A",
        other: "#B0C4DE",
        };
    const backgroundColors = labels.map((category) => categoryColors[category] || "#cccccc");
    new Chart(ctx, {
        type: "bar",
        data: {
        labels,
        datasets: [{
            label: "Expenses",
            data: data.amounts,
            backgroundColor: backgroundColors,
            borderWidth: 1,
        }],
        },
        options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            datalabels: {
            color: "#fff",
            font: { weight: "bold", size: 14 },
            },
        },
        scales: {
            y: {
            beginAtZero: true,
            ticks: {
                callback: (value) => value + " €",
            },
            },
        },
        },
        plugins: [ChartDataLabels],
    });
    })
    .catch((error) => console.error("Error loading chart data:", error));
}
window.onload = loadReportChart;

document.addEventListener("DOMContentLoaded", function () {
    flatpickr("#monthPicker", {
      dateFormat: "Y-m",
      plugins: [
        new monthSelectPlugin({
          shorthand: true,
          dateFormat: "Y-m",
          altFormat: "F Y",
        }),
      ],
      onChange: function (selectedDates, dateStr, instance) {
        const selectedDate = selectedDates[0];
        const year = selectedDate.getFullYear();
        const month = selectedDate.getMonth() + 1;
        window.location.href = `/report?year=${year}&month=${month}`;
      },
    });
  });  