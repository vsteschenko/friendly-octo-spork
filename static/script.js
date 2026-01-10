document.addEventListener("DOMContentLoaded", () => {

  const body = document.body;
  const currentYear = parseInt(body.dataset.year);
  const currentMonth = parseInt(body.dataset.month);
  const currentDay = parseInt(body.dataset.day);
  const totalSum = parseFloat(body.dataset.sum) || 0;

  const savedTab = localStorage.getItem("activeTab");

  if (savedTab === "sumByCategory") {
    sumByCategory();
  } else {
    allEntries();
  }

  function setCurrentTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    document.getElementById("tx_time").value = `${hours}:${minutes}`;
  }

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

  const modal = document.getElementById('txModal')
  const commentModal = document.getElementById("commentModal");
  const commentModalContent = document.getElementById("commentModalContent");
  const commentText = document.getElementById("commentText");

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
    } else if (event.target === commentModal) {
      commentModal.classList.add("hidden");
    }
  };

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

  function showOptions(type) {
    if (type == "income") {
      document.getElementById("income-options").style.display = "inline";
      document.getElementById("expense-options").style.display = "none";
    } else if (type == "expense") {
      document.getElementById("income-options").style.display = "none";
      document.getElementById("expense-options").style.display = "inline";
    }
  }

  const editButtons = document.querySelectorAll(".edit-btn");
  const commentButtons = document.querySelectorAll(".comment-btn");

  editButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const txId = button.getAttribute("data-tx-id");
      const txType = button.getAttribute("data-tx-type");
      const txPlace = button.getAttribute("data-tx-place");
      let txAmount = button.getAttribute("data-tx-amount");
      txAmount = Math.abs(txAmount);
      const txCategory = button.getAttribute("data-tx-category");
      const txTime = button.getAttribute("data-tx-time");
      const txComment = button.getAttribute("data-tx-comment")

      const txForm = document.getElementById("txForm");
      txForm.action = "/update_tx";

      txForm.querySelector("input[name='tx_id']").value = txId;
      txForm.querySelector("input[name='type']").value = txType;
      txForm.querySelector("input[name='amount']").value = txAmount;
      txForm.querySelector("input[name='place']").value = txPlace;
      txForm.querySelector("input[name='tx_time']").value = txTime;
      txForm.querySelector("input[name='comment']").value = txComment

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

  commentButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!commentModal.classList.contains("hidden")) {
        commentModal.classList.add("hidden");
        return;
      }
      const txComment = button.getAttribute("data-tx-comment") || "";
      commentText.textContent = txComment ? txComment : "No comment";
      commentModal.classList.remove("hidden");

      requestAnimationFrame(() => {
        const row = button.closest("tr");
        if (!row) {
          return;
        }
        const rowRect = row.getBoundingClientRect();
        const modalRect = commentModalContent.getBoundingClientRect();
        const offsetX = 20;
        const padding = 8;
        let top = rowRect.bottom;
        let left = rowRect.left + rowRect.width / 2 + offsetX;

        if (left + modalRect.width > window.innerWidth - padding) {
          left = window.innerWidth - modalRect.width - padding;
        }
        if (left < padding) {
          left = padding;
        }
        if (top + modalRect.height > window.innerHeight - padding) {
          top = window.innerHeight - modalRect.height - padding;
        }
        if (top < padding) {
          top = padding;
        }

        commentModalContent.style.top = `${top}px`;
        commentModalContent.style.left = `${left}px`;
      });
    });
  });

  // document.querySelector(".comment-close-btn").onclick = () => {
  //   commentModal.classList.add("hidden");
  // };

  document.querySelector(".close-btn").onclick = () => {
    modal.classList.add("hidden");
  }
})

const centerTextPlugin = {
  id: "centerText",
  beforeDraw(chart) {
    const { width, height, ctx } = chart;
    ctx.save();

    const label = "Expenses";
    
    let value = 0;
    if (chart.data.datasets[0] && chart.data.datasets[0].realAmounts) {
      value = chart.data.datasets[0].realAmounts.reduce((sum, amount) => sum + amount, 0);
    }
    const formattedValue = value.toFixed(2);

    ctx.font = "bold 14px Arial";
    ctx.fillStyle = "#333";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    ctx.fillText(label, width / 2, height / 2 - 10);

    ctx.font = "bold 16px Arial";
    ctx.fillText(`${formattedValue}€`, width / 2, height / 2 + 10);

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

let expenseChartInstance = null;

function loadExpenseChart() {
  const body = document.body;
  const currentYear = parseInt(body.dataset.year);
  const currentMonth = parseInt(body.dataset.month);
  const currentDay = parseInt(body.dataset.day);
  const totalSum = parseFloat(body.dataset.sum) || 0;

  fetch(
    `/expenses_by_category?year=${currentYear}&month=${currentMonth}&day=${currentDay}`
  )
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("expenseChart")
        .getContext("2d");

      if (expenseChartInstance) {
        expenseChartInstance.destroy();
      }

      const hasData = Array.isArray(data.amounts) && data.amounts.some((amount) => Number(amount) !== 0);
      const labels = hasData ? data.categories : ["No data"];
      const backgroundColors = hasData ? labels.map((category) => categoryColors[category] || "#cccccc"): ["#e0e0e0"];
      const amounts = hasData ? data.amounts : [1];
      const realAmounts = hasData ? data.real_amounts : [0];

      expenseChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [
            {
              data: amounts,
              backgroundColor: backgroundColors,
              borderWidth: 1,
              realAmounts: realAmounts,
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
              display: false
            },
            tooltip: {
              enabled: hasData,
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
function showAnnualReport(){
  window.location.href= "/annual_report"
}

function sumByCategory() {
  const report = document.getElementsByClassName("report")[0];
  const table = document.getElementsByClassName("table")[0];
  const sumByCategory = document.getElementsByClassName("sumByCategory")[0];

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
  const sumByCategory = document.getElementsByClassName("sumByCategory")[0];

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

function menu() {
  const menu = document.getElementsByClassName("menu")[0];
  const currentDisplay = window.getComputedStyle(menu).display;
  if (currentDisplay == "none") {
    menu.style.display = "flex";
  } else {
    menu.style.display = "none";
  }
}
function changePassword() {
  window.location.href = "/change_password"
}
function  deleteAccount() {
  window.location.href = "/delete_account"
}
document.addEventListener("DOMContentLoaded", () => {
  const menuButtons = document.querySelectorAll(".menu-toggle");
  menuButtons.forEach(btn => {
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
  const txs = document.getElementsByClassName('allEntries')[0];
  if (txs) {
    txs.addEventListener("click", allEntries)
  }
  const sumByCategoryFunc = document.getElementsByClassName('sumByCategoryFunc')[0]
  if (sumByCategoryFunc) {
    sumByCategoryFunc.addEventListener("click", sumByCategory)
  }
  const showReportFunc = document.getElementsByClassName('showReport')[0]
  if (showReportFunc) {
    showReportFunc.addEventListener("click", showReport)
  }
  const showAnnualReportFunc = document.getElementsByClassName('showAnnualReport')[0]
  if (showAnnualReportFunc) {
    showAnnualReportFunc.addEventListener("click", showAnnualReport)
  }
  const logoutFunc = document.getElementById("logout")
  if (logoutFunc) {
    logoutFunc.addEventListener("click", logout)
  }
});
// SLIDER
document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementsByClassName("chartBorder")[0];
  let touchStartX = null;
  const swipeThreshold = 50;

  canvas.addEventListener("touchstart", (evt) => {
    if (evt.touches.length === 1) {
      touchStartX = evt.touches[0].clientX;
    }
  });
  canvas.addEventListener("touchend", (evt) => {
    if (touchStartX === null) return;
    const touchEndX = evt.changedTouches[0].clientX;
    const deltaX = touchEndX - touchStartX;
    touchStartX = null;

    if (Math.abs(deltaX) < swipeThreshold) {
      return;
    }
    const body = document.body;
    let year = parseInt(body.dataset.year);
    let month = parseInt(body.dataset.month);
    let day = parseInt(body.dataset.day);

    if (deltaX > 0) {
      day = day - 1;
    } else {
      day = day + 1;
    }

    window.location.href = `/?year=${year}&month=${month}&day=${day}`;
  });
});
