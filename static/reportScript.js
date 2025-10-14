// Script responsible for loading and rendering the report charts as well as
// handling basic UI interactions.  This is largely based off of the
// original reportScript.js but has been extended to draw a second chart
// illustrating the proportional breakdown of spending by category.

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
      const ctx = document
        .getElementById("reportChart")
        .getContext("2d");
      const labels = data.categories;
      const categoryColors = {
        grocery: "#ff82a0",
        rent: "#bedaf1",
        utilities: "#f1d3b2",
        transport: "#ffe0e6",
        insurance: "#d9c6e5",
        dining: "#b9bfc6",
        entertainment: "#c1eccf",
        shopping: "#6eb5ff",
        health: "#fff5ba",
        beauty: "#ace7ff",
        loans: "#9ad4bc",
        credit_card: "#d98880",
        savings: "#b9bafd",
        education: "#fcf0e4",
        pets: "#fbcfea",
        home_maintenance: "#c2ecd6",
        gifts: "#ffa9f7",
        travel: "#ffffb5",
        subscriptions: "#ffd4b7",
        other: "#b7f2ff",
      };
      // Map each category to a colour.  Unknown categories default to grey.
      const backgroundColors = labels.map(
        (category) => categoryColors[category] || "#cccccc"
      );

      // Draw bar chart summarising the absolute amounts per category.  This
      // matches the original design but is encapsulated in a function for
      // clarity.
      new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Expenses",
              data: data.amounts,
              backgroundColor: backgroundColors,
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            datalabels: {
              color: "black",
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

      // Draw a doughnut chart showing the relative share of each category.  This
      // leverages the same labels, amounts and colours to ensure consistency
      // between charts.  Displaying the legend on the bottom improves
      // readability, especially on mobile devices.
      const ctxPie = document
        .getElementById("categoryChart")
        .getContext("2d");
      new Chart(ctxPie, {
        type: "doughnut",
        data: {
          labels,
          datasets: [
            {
              data: data.amounts,
              backgroundColor: backgroundColors,
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: true, position: "bottom" },
            datalabels: {
              color: "black",
              font: { weight: "bold", size: 14 },
              formatter: (value) => value + " €",
            },
          },
        },
        plugins: [ChartDataLabels],
      });
    })
    .catch((error) => console.error("Error loading chart data:", error));
}

// Ensure the chart is loaded on page load.  This replicates the original
// behaviour of assigning loadReportChart to window.onload.
window.onload = loadReportChart;

// Initialise the month picker and menu controls.  This block preserves
// existing interactive functionality such as navigation, menu toggling and
// account actions.
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

function menu() {
  const menuEl = document.getElementsByClassName("menu")[0];
  const currentDisplay = window.getComputedStyle(menuEl).display;
  if (currentDisplay == "none") {
    menuEl.style.display = "flex";
  } else {
    menuEl.style.display = "none";
  }
}

function changePassword() {
  window.location.href = "/change_password";
}

function deleteAccount() {
  window.location.href = "/delete_account";
}

function logout() {
  fetch("/logout", { method: "GET" })
    .then((response) => {
      if (response.ok) {
        window.location.href = "/login";
      } else {
        console.error("Error");
      }
    })
    .catch((error) => console.error("Error:", error));
}

document.addEventListener("DOMContentLoaded", () => {
  const indexFunc = document.getElementsByClassName("index")[0];
  if (indexFunc) {
    indexFunc.addEventListener("click", index);
  }
  const menuButtons = document.querySelectorAll(".menu-toggle");
  menuButtons.forEach((btn) => {
    btn.addEventListener("click", menu);
  });
  const changePasswordBtn = document.getElementById("change-password");
  if (changePasswordBtn) {
    changePasswordBtn.addEventListener("click", changePassword);
  }
  const deleteBtn = document.getElementById("delete-account");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", deleteAccount);
  }
  const logoutFunc = document.getElementById("logout");
  if (logoutFunc) {
    logoutFunc.addEventListener("click", logout);
  }
});