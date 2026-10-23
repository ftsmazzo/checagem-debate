const CBN = "https://playerservices.streamtheworld.com/api/livestream-redirect/CBN_SPAAC.m3u8";
const labels = {
  pendente: "Checando",
  processando: "Checando",
  sustentado: "Verdadeiro",
  sustentado_ressalva: "Verdadeiro, mas...",
  nao_e_bem_assim: "Não é bem assim",
  contradito: "Falso",
  exagerado: "Exagerado",
  distorcido: "Distorcido",
  sem_prova: "Sem provas",
  sem_prova_publica: "Sem prova pública",
  versoes_em_disputa: "Versões em disputa",
  indicio: "Indício",
  dados_incompletos: "Dados incompletos",
  audio_confuso: "Áudio confuso",
  promessa: "Promessa",
  sem_evidencia: "Sem fonte suficiente",
  inconclusivo: "Em aberto",
  erro: "Erro na consulta",
};
const who = { lula: "Lula", flavio: "Flávio" };

const errorBox = document.querySelector("#error");
const debate = document.querySelector("#debate");
const statusLine = document.querySelector("#status");
let claims = [];
let installEvent = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[char]));
}

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "A consulta falhou.");
  return data;
}

function render(state) {
  const now = state.active_debate;
  debate.textContent = now ? now.title : "Nenhum debate ativo";
  const listening = state.browser
    ? "A aba está aberta no painel. Aqui a escuta é a rádio."
    : state.running
      ? (String(state.youtube_url || "").includes("CBN_SP") ? "Ouvindo a CBN" : "Ouvindo o canal")
      : "Escuta parada";
  statusLine.textContent = listening;
  const hearing = (state.hearing || "").trim();
  const live = hearing
    ? `<article class="chunk live"><p>${escapeHtml(hearing)}</p><p class="meta">entrando agora</p></article>`
    : "";
  const rows = (state.segments || []).slice(0, 6);
  const body = rows.length
    ? rows.map((row) => `<article class="chunk">
        <p>${escapeHtml(row.text)}</p>
        ${String(row.text || "").trim().length >= 12 ? `<div class="row"><button type="button" class="ghost" data-check="${row.id}">Checar</button></div>` : ""}
      </article>`).join("")
    : (hearing ? "" : `<p class="meta">A fala do debate ativo aparece aqui.</p>`);
  document.querySelector("#segments").innerHTML = live + body;
  claims = state.claims || [];
  document.querySelector("#claims").innerHTML = claims.length
    ? claims.slice(0, 12).map((claim) => {
        const person = who[claim.speaker] || "";
        return `<article class="claim">
          <p class="stamp ${escapeHtml(claim.status)}">${escapeHtml(labels[claim.status] || claim.status)}</p>
          ${person ? `<p class="who">${escapeHtml(person)}</p>` : ""}
          <p>${escapeHtml(claim.normalized || claim.quote || "")}</p>
          <p class="sum">${escapeHtml(claim.summary || "")}</p>
          <div class="row"><button type="button" class="zap" data-share="${claim.id}">WhatsApp</button></div>
        </article>`;
      }).join("")
    : `<p class="meta">As checagens deste debate entram aqui.</p>`;
}

async function refresh() {
  try {
    render(await api("/api/estado"));
    errorBox.textContent = "";
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

async function listen(url) {
  errorBox.textContent = "";
  if (/globo/i.test(url)) {
    errorBox.textContent = "O GloboPlay não abre por aqui. Use a CBN ou um canal de rádio.";
    return;
  }
  try {
    await api("/api/iniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ youtube_url: url, gravar: true }),
    });
    await refresh();
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

document.querySelector("#cbn").addEventListener("click", () => listen(CBN));
document.querySelector("#stop").addEventListener("click", async () => {
  try {
    await api("/api/parar", { method: "POST" });
    await refresh();
  } catch (error) {
    errorBox.textContent = error.message;
  }
});
document.querySelector("#channel").addEventListener("submit", (event) => {
  event.preventDefault();
  listen(document.querySelector("#url").value.trim());
});
document.querySelector("#segments").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-check]");
  if (!button) return;
  const row = document.querySelector(`#segments [data-check="${button.dataset.check}"]`)?.closest(".chunk");
  const text = row?.querySelector("p")?.textContent || "";
  try {
    await api("/api/checar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speaker: "avulsa" }),
    });
    await refresh();
  } catch (error) {
    errorBox.textContent = error.message;
  }
});
document.querySelector("#claims").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-share]");
  if (!button) return;
  const claim = claims.find((item) => item.id === Number(button.dataset.share));
  if (!claim) return;
  button.disabled = true;
  try {
    const result = await MentiroCard.share(claim, "feed");
    if (result === "saved") errorBox.textContent = "A imagem foi salva. No computador, o WhatsApp abre pelo arquivo.";
  } catch (error) {
    if (error?.name !== "AbortError") errorBox.textContent = error.message || "Não foi possível gerar a imagem.";
  } finally {
    button.disabled = false;
  }
});

const install = document.querySelector("#install");
window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installEvent = event;
  install.hidden = false;
});
install.addEventListener("click", async () => {
  if (!installEvent) return;
  installEvent.prompt();
  await installEvent.userChoice;
  install.hidden = true;
  installEvent = null;
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

refresh();
setInterval(refresh, 2000);
