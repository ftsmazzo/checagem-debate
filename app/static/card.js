const MentiroCard = (() => {
  const STAMP = {
    sustentado: ["SUSTENTADO", "#3dce8f"],
    contradito: ["CONTRADITO", "#ff6b6b"],
    exagerado: ["EXAGERADO", "#e0a43a"],
    sem_evidencia: ["SEM FONTE", "#7b93ff"],
    inconclusivo: ["EM ABERTO", "#7b93ff"],
    sustentado_ressalva: ["COM RESSALVA", "#3dce8f"],
    nao_e_bem_assim: ["NÃO É BEM ASSIM", "#e0a43a"],
    distorcido: ["DISTORCIDO", "#ff6b6b"],
    sem_prova: ["SEM PROVA", "#ff6b6b"],
    sem_prova_publica: ["SEM PROVA PÚBLICA", "#7b93ff"],
    versoes_em_disputa: ["EM DISPUTA", "#7b93ff"],
    indicio: ["INDÍCIO", "#7b93ff"],
    dados_incompletos: ["DADOS INCOMPLETOS", "#7b93ff"],
    audio_confuso: ["ÁUDIO CONFUSO", "#7b93ff"],
    promessa: ["PROMESSA", "#e0a43a"],
    pendente: ["CHECANDO", "#9aa6b8"],
    processando: ["CHECANDO", "#9aa6b8"],
    erro: ["ERRO", "#ff6b6b"],
  };
  const WHO = { lula: "Lula", flavio: "Flávio", avulsa: "Checagem" };

  function wrap(ctx, text, maxW) {
    const words = String(text || "").split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const word of words) {
      const test = line ? `${line} ${word}` : word;
      if (ctx.measureText(test).width > maxW && line) {
        lines.push(line);
        line = word;
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  function round(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }

  async function png(claim, format) {
    await document.fonts.load('800 64px Montserrat').catch(() => {});
    const story = format === "stories";
    const W = 1080;
    const H = story ? 1920 : 1350;
    const pad = 84;
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0f141c";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#e8786a";
    ctx.fillRect(0, 0, W, 18);

    ctx.fillStyle = "#e8786a";
    ctx.font = "800 34px Montserrat, sans-serif";
    ctx.textBaseline = "top";
    ctx.fillText("MENTIRÔMETRO", pad, story ? 120 : 72);
    ctx.fillStyle = "#9aa6b8";
    ctx.font = "700 24px Montserrat, sans-serif";
    ctx.fillText("IEleitoral", pad, story ? 168 : 116);

    const who = WHO[claim.speaker] || "Checagem";
    ctx.fillStyle = "#f2f4f8";
    ctx.font = "800 36px Montserrat, sans-serif";
    ctx.fillText(who.toUpperCase(), pad, story ? 250 : 190);

    const quote = claim.normalized || claim.quote || "";
    ctx.font = "700 46px Montserrat, sans-serif";
    const quoteLines = wrap(ctx, quote, W - pad * 2 - 64).slice(0, story ? 8 : 5);
    const boxH = 72 + quoteLines.length * 62;
    const boxY = story ? 330 : 260;
    round(ctx, pad, boxY, W - pad * 2, boxH, 28);
    ctx.fillStyle = "#1a222f";
    ctx.fill();
    ctx.fillStyle = "#f2f4f8";
    quoteLines.forEach((line, i) => ctx.fillText(line, pad + 32, boxY + 36 + i * 62));

    const [stamp, color] = STAMP[claim.status] || [String(claim.status || "CHECAGEM").toUpperCase(), "#e8786a"];
    ctx.font = "800 64px Montserrat, sans-serif";
    const stampW = ctx.measureText(stamp).width + 72;
    const stampH = 118;
    const stampY = boxY + boxH + (story ? 90 : 64);
    ctx.save();
    ctx.translate(pad + stampW / 2 + 8, stampY + stampH / 2);
    ctx.rotate(-0.06);
    ctx.strokeStyle = color;
    ctx.lineWidth = 8;
    round(ctx, -stampW / 2, -stampH / 2, stampW, stampH, 18);
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(stamp, 0, 2);
    ctx.restore();

    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#d5dde8";
    ctx.font = "500 36px Montserrat, sans-serif";
    const summaryY = stampY + stampH + (story ? 70 : 48);
    wrap(ctx, claim.summary || "", W - pad * 2).slice(0, story ? 6 : 4)
      .forEach((line, i) => ctx.fillText(line, pad, summaryY + i * 50));

    const source = (claim.sources || []).find((item) => item && item.url);
    const foot = H - (story ? 180 : 110);
    ctx.fillStyle = "#2c3648";
    ctx.fillRect(pad, foot - 28, W - pad * 2, 3);
    ctx.fillStyle = "#9aa6b8";
    ctx.font = "700 24px Montserrat, sans-serif";
    const sourceLine = source ? String(source.title || source.url).slice(0, 70) : "Fontes no painel";
    ctx.fillText(sourceLine, pad, foot);
    ctx.fillStyle = "#f2f4f8";
    ctx.font = "800 28px Montserrat, sans-serif";
    const host = "mentirômetro";
    ctx.fillText(host, W - pad - ctx.measureText(host).width, foot);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `mentirometro-${claim.id || "checagem"}${story ? "-stories" : ""}.png`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
  }

  return { png };
})();
