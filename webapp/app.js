const tg = window.Telegram.WebApp;
tg.ready();

const user = tg.initDataUnsafe?.user;
const userId = user?.id;
const username = user?.username ? `@${user.username}` : "Telegram user";
document.getElementById("user").textContent = username;

const panel = document.getElementById("panel");
const ADMIN_ID = 5815294733;

async function loadBalance() {
  const res = await fetch(`/api/balance/${userId}`);
  const data = await res.json();
  document.getElementById("b_usdt").textContent = data.usdt ?? 0;
  document.getElementById("b_rub").textContent  = data.rub ?? 0;
  document.getElementById("b_uzs").textContent  = data.uzs ?? 0;
}

function askCurrencyAmount() {
  const currency = (prompt("Valyuta: usdt / rub / uzs", "usdt") || "").toLowerCase().trim();
  const amountStr = prompt("Miqdor:", "10");
  const amount = Number(amountStr);
  if (!["usdt","rub","uzs"].includes(currency)) return null;
  if (!amount || amount <= 0) return null;
  return { currency, amount };
}

document.getElementById("btnDeposit").onclick = async () => {
  const v = askCurrencyAmount();
  if (!v) return tg.showAlert("❌ Noto‘g‘ri ma’lumot");
  const res = await fetch(`/api/deposit/request?user_id=${userId}&currency=${v.currency}&amount=${v.amount}`, { method:"POST" });
  tg.showAlert(res.ok ? "✅ Deposit so‘rovi yuborildi (pending)" : "❌ Xatolik");
};

document.getElementById("btnWithdraw").onclick = async () => {
  const v = askCurrencyAmount();
  if (!v) return tg.showAlert("❌ Noto‘g‘ri ma’lumot");
  const res = await fetch(`/api/withdraw/request?user_id=${userId}&currency=${v.currency}&amount=${v.amount}`, { method:"POST" });
  tg.showAlert(res.ok ? "✅ Withdraw so‘rovi yuborildi (pending)" : "❌ Xatolik (balans yetmasligi mumkin)");
};

document.getElementById("btnHistory").onclick = async () => {
  panel.style.display = "block";
  panel.innerHTML = "Yuklanmoqda...";
  const res = await fetch(`/api/history/${userId}`);
  const data = await res.json();
  const items = data.items || [];
  if (!items.length) {
    panel.innerHTML = "<b>Tarix bo‘sh</b>";
    return;
  }
  panel.innerHTML = "<b>Tarix</b><hr>" + items.map(it =>
    `<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06)">
      <div><b>${it.type.toUpperCase()}</b> • ${it.currency.toUpperCase()} • ${it.amount}</div>
      <div style="opacity:.8;font-size:12px">${it.status} • ${it.created_at}</div>
    </div>`
  ).join("");
};

// Admin ko‘rinsin
if (userId === ADMIN_ID) {
  document.getElementById("btnAdmin").style.display = "block";
}

document.getElementById("btnAdmin").onclick = async () => {
  panel.style.display = "block";
  panel.innerHTML = "Yuklanmoqda...";
  const res = await fetch(`/api/admin/pending?admin_id=${ADMIN_ID}`);
  const data = await res.json();
  const items = data.items || [];
  if (!items.length) {
    panel.innerHTML = "<b>Pending so‘rov yo‘q</b>";
    return;
  }
  panel.innerHTML = "<b>Admin: Pending</b><hr>" + items.map(it =>
    `<div style="padding:10px;border:1px solid rgba(255,255,255,.06);border-radius:12px;margin:10px 0">
      <div><b>${it.type.toUpperCase()}</b> • user: ${it.user_id}</div>
      <div>${it.currency.toUpperCase()} • ${it.amount}</div>
      <div style="opacity:.8;font-size:12px">${it.created_at}</div>
      <div style="margin-top:10px;display:flex;gap:8px">
        <button class="btn" onclick="decision('${it.type}', ${it.id}, 'approve')">✅ Approve</button>
        <button class="btn ghost" onclick="decision('${it.type}', ${it.id}, 'reject')">❌ Reject</button>
      </div>
    </div>`
  ).join("");
};

window.decision = async (type, id, action) => {
  const res = await fetch(`/api/admin/decision?admin_id=${ADMIN_ID}&req_type=${type}&req_id=${id}&action=${action}`, { method:"POST" });
  tg.showAlert(res.ok ? "✅ Bajarildi" : "❌ Xatolik");
  await loadBalance();
};

loadBalance();
