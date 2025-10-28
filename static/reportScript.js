function index() {
  window.location.href = "/";
}

function getQueryParam(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

let reportChartInstance = null;

function loadReportChart() {
  const year = getQueryParam("year") || new Date().getFullYear();
  const month = getQueryParam("month") || new Date().getMonth() + 1;

  fetch(`/report_chart?year=${year}&month=${month}`)
    .then((response) => response.json())
    .then((data) => {
      const labels = data.categories.slice();
      const values = data.categories.slice();
      const expenseCategories = [
        { value: "beauty", label: "Beauty & Personal Care" },
        { value: "education", label: "Childcare & Education" },
        { value: "credit_card", label: "Credit Card Payments" },
        { value: "dining", label: "Dining Out" },
        { value: "entertainment", label: "Entertainment" },
        { value: "gifts", label: "Gifts & Donations" },
        { value: "grocery", label: "Grocery" },
        { value: "health", label: "Health & Fitness" },
        { value: "home_maintenance", label: "Home Maintenance" },
        { value: "insurance", label: "Insurance" },
        { value: "loans", label: "Loan Payments" },
        { value: "pets", label: "Pets" },
        { value: "rent", label: "Rent" },
        { value: "savings", label: "Savings & Investments" },
        { value: "shopping", label: "Shopping" },
        { value: "subscriptions", label: "Subscriptions & Memberships" },
        { value: "transport", label: "Transportation" },
        { value: "travel", label: "Travel" },
        { value: "utilities", label: "Utilities" },
        { value: "work", label: "Work" },
        { value: "taxes", label: "Taxes" },
        { value: "other", label: "Other" },
      ];
      labels.forEach((c, i) => {
        const found = expenseCategories.find(ec => ec.value === c);
        if (found) labels[i] = found.label;
      });

      const container = document.querySelector(".reportChart");
      const canvas = document.getElementById("reportChart");
      const PER_BAR = 60;
      const BAR_THICKNESS = 28;
      const CHART_HEIGHT = 320;

      const targetWidth = Math.max(PER_BAR * labels.length, container.clientWidth);
      canvas.width = targetWidth;
      canvas.height = CHART_HEIGHT;

      const ctx = canvas.getContext("2d");

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
        work: "#cfd8dc",   // добавлено
        taxes: "#ffd180"
      };
      const backgroundColors = values.map(v => categoryColors[v] || "#cccccc");

      if (reportChartInstance) {
        reportChartInstance.destroy();
      }

      // const shortLabels = labels.map(l => (l.length > 14 ? l.slice(0, 14) + "…" : l));

      reportChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "Expenses",
            data: data.amounts,
            backgroundColor: backgroundColors,
            borderWidth: 1,
            barThickness: BAR_THICKNESS,
            maxBarThickness: BAR_THICKNESS,
            categoryPercentage: 0.9,
            barPercentage: 0.9,
          }],
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            datalabels: {
              color: "black",
              font: { weight: "bold", size: 14 },
              clamp: true,
              clip: true,
              anchor: 'end',
              align: 'end',
              offset: 4,
              formatter: (v) => `${v} €`,
            },
            tooltip: { enabled: true },
          },
          scales: {
            x: {
              ticks: {
                maxRotation: 45,
                minRotation: 45,
              },
              grid: { display: false },
            },
            y: {
              beginAtZero: true,
              ticks: { callback: (value) => value + " €" },
              grid: { drawBorder: false },
            },
          },
          layout: { padding: { right: 8 } },
        },
        plugins: [ChartDataLabels],
      });
    })
    .catch((error) => console.error("Error loading chart data:", error));
}

window.onload = loadReportChart;

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