document.addEventListener("DOMContentLoaded", () => {
  const savedTab = localStorage.getItem("activeTab");

  if (savedTab === "sumByCategory") {
    sumByCategory();
  } else {
    allEntries();
  }
});

function setCurrentTime() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  document.getElementById("tx_time").value = `${hours}:${minutes}`;
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("spendBtn").onclick = () => {
    document.getElementById("txModal").classList.remove("hidden");
    document.getElementById("txType").value = "expense";
    showOptions("expense");
    document.getElementsByClassName("saveBtn")[0].style.display = "none";
    document.getElementsByClassName("submitBtn")[0].style.display =
      "inline";
    const txForm = document.getElementById("txForm");
    txForm.reset();
    setCurrentTime();
  };

  document.getElementById("incomeBtn").onclick = () => {
    document.getElementById("txModal").classList.remove("hidden");
    document.getElementById("txType").value = "income";
    showOptions("income");
    document.getElementsByClassName("saveBtn")[0].style.display = "none";
    document.getElementsByClassName("submitBtn")[0].style.display =
      "inline";
    const txForm = document.getElementById("txForm");
    txForm.reset();
    setCurrentTime();
  };

  document.querySelector(".close-btn").onclick = () => {
    document.getElementById("txModal").classList.add("hidden");
    const txForm = document.getElementById("txForm");
    txForm.reset();
  };

  window.onclick = (event) => {
    const modal = document.getElementById("txModal");
    if (event.target === modal) {
      modal.classList.add("hidden");
      const txForm = document.getElementById("txForm");
      txForm.reset();
    }
  };
});

document.addEventListener("DOMContentLoaded", function () {
  flatpickr("#datePicker", {
    defaultDate: `${currentYear}-${currentMonth}-${currentDay}`,
    dateFormat: "Y-m-d",
    onChange: function (selectedDates, dateStr, instance) {
      const selectedDate = selectedDates[0];
      const year = selectedDate.getFullYear();
      const month = selectedDate.getMonth() + 1;
      const day = selectedDate.getDate();
      window.location.href = `/?year=${year}&month=${month}&day=${day}`;
    },
  });
});

function showOptions(type) {
  if (type == "income") {
    document.getElementById("income-options").style.display = "inline";
    document.getElementById("expense-options").style.display = "none";
  } else if (type == "expense") {
    document.getElementById("income-options").style.display = "none";
    document.getElementById("expense-options").style.display = "inline";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const editButtons = document.querySelectorAll(".edit-btn");
  const modal = document.getElementById("txModal");

  editButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const txId = button.getAttribute("data-tx-id");
      const txType = button.getAttribute("data-tx-type");
      const txPlace = button.getAttribute("data-tx-place");
      let txAmount = button.getAttribute("data-tx-amount");
      txAmount = Math.abs(txAmount);
      const txCategory = button.getAttribute("data-tx-category");
      const txTime = button.getAttribute("data-tx-time");

      const txForm = document.getElementById("txForm");
      txForm.action = "/update_tx";

      txForm.querySelector("input[name='tx_id']").value = txId;
      txForm.querySelector("input[name='type']").value = txType;
      txForm.querySelector("input[name='amount']").value = txAmount;
      txForm.querySelector("input[name='place']").value = txPlace;
      txForm.querySelector("input[name='tx_time']").value = txTime;

      if (txType === "expense") {
        document.getElementById("expense-options").style.display =
          "inline";
        document.getElementById("income-options").style.display = "none";
        txForm.querySelector("select[name='expense-category']").value =
          txCategory;
        document.getElementsByClassName("submitBtn")[0].style.display =
          "none";
        document.getElementsByClassName("saveBtn")[0].style.display =
          "inline";
      } else if (txType === "income") {
        document.getElementById("income-options").style.display =
          "inline";
        document.getElementById("expense-options").style.display = "none";
        txForm.querySelector("select[name='income-category']").value =
          txCategory;
        document.getElementsByClassName("submitBtn")[0].style.display =
          "none";
        document.getElementsByClassName("saveBtn")[0].style.display =
          "inline";
      }

      modal.classList.remove("hidden");
    });
  });

  document.querySelector(".close-btn").onclick = () => {
    modal.classList.add("hidden");
  };
});
window.onclick = (event) => {
  if (event.target === modal) {
    modal.classList.add("hidden");
  }
};

const centerTextPlugin = {
  id: "centerText",
  beforeDraw(chart) {
    const { width, height, ctx } = chart;
    ctx.save();

    const label = "Total";
    const value = totalSum ? totalSum : 0;

    ctx.font = "bold 14px Arial";
    ctx.fillStyle = "#333";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    ctx.fillText(label, width / 2, height / 2 - 10);

    ctx.font = "bold 16px Arial";
    ctx.fillText(value, width / 2, height / 2 + 10);

    ctx.restore();
  },
};

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

function loadExpenseChart() {
  fetch(
    `/expenses_by_category?year=${currentYear}&month=${currentMonth}&day=${currentDay}`
  )
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("expenseChart")
        .getContext("2d");

      const labels = data.categories;
      const backgroundColors = labels.map(
        (category) => categoryColors[category] || "#cccccc"
      );

      new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: data.categories,
          datasets: [
            {
              data: data.amounts,
              backgroundColor: backgroundColors,
              borderWidth: 1,
              realAmounts: data.real_amounts,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              display: false,
            },
            datalabels: {
              color: "#fff",
              font: {
                weight: "bold",
                size: 14,
              },
              formatter: (value, context) => {
                return value.toFixed(1) + "%";
              },
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  const realAmount =
                    context.dataset.realAmounts[context.dataIndex];
                  return `${realAmount.toFixed(2)} €`;
                },
              },
            },
          },
        },
        plugins: [centerTextPlugin, ChartDataLabels],
      });
    })
    .catch((error) => console.error("Error loading chart data:", error));
}
window.onload = loadExpenseChart;

function showReport() {
  window.location.href = "/report";
}

function sumByCategory() {
  const report = document.getElementsByClassName("report")[0];
  const table = document.getElementsByClassName("table")[0];
  const sumByCategory =
    document.getElementsByClassName("sumByCategory")[0];

  const calendar = document.getElementById("datePicker");
  const calendarRange = document.getElementById("rangeDatePicker");
  calendar.style.display = "inline";
  calendarRange.style.display = "none";

  const previousDayButton = document.getElementById("previousDay");
  previousDayButton.style.display = "flex";
  const nextDayButton = document.getElementById("nextDay");
  nextDayButton.style.display = "flex";

  report.style.display = "none";
  table.style.display = "none";
  sumByCategory.style.display = "block";

  localStorage.setItem("activeTab", "sumByCategory");
}

function allEntries() {
  const report = document.getElementsByClassName("report")[0];
  const table = document.getElementsByClassName("table")[0];
  const sumByCategory =
    document.getElementsByClassName("sumByCategory")[0];

  const calendar = document.getElementById("datePicker");
  const calendarRange = document.getElementById("rangeDatePicker");
  calendar.style.display = "inline";
  calendarRange.style.display = "none";

  const previousDayButton = document.getElementById("previousDay");
  previousDayButton.style.display = "flex";
  const nextDayButton = document.getElementById("nextDay");
  nextDayButton.style.display = "flex";

  report.style.display = "none";
  table.style.display = "block";
  sumByCategory.style.display = "none";

  localStorage.setItem("activeTab", "allEntries");
}