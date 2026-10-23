const MentiroCard = (() => {
  const STAMP = {
    sustentado: ["SUSTENTADO", "#0b6b3a", "#d9f3e4"],
    sustentado_ressalva: ["COM RESSALVA", "#0b6b3a", "#d9f3e4"],
    nao_e_bem_assim: ["NÃO É BEM ASSIM", "#8a4b08", "#ffe7c2"],
    exagerado: ["EXAGERADO", "#8a4b08", "#ffe7c2"],
    promessa: ["PROMESSA", "#8a4b08", "#ffe7c2"],
    distorcido: ["DISTORCIDO", "#a4161a", "#ffd6d4"],
    contradito: ["CONTRADITO", "#a4161a", "#ffd6d4"],
    sem_prova: ["SEM PROVA", "#a4161a", "#ffd6d4"],
    erro: ["ERRO", "#a4161a", "#ffd6d4"],
    sem_prova_publica: ["SEM PROVA PÚBLICA", "#1d4e89", "#d9e6f5"],
    versoes_em_disputa: ["EM DISPUTA", "#1d4e89", "#d9e6f5"],
    indicio: ["INDÍCIO", "#1d4e89", "#d9e6f5"],
    dados_incompletos: ["DADOS INCOMPLETOS", "#1d4e89", "#d9e6f5"],
    audio_confuso: ["ÁUDIO CONFUSO", "#1d4e89", "#d9e6f5"],
    sem_evidencia: ["SEM FONTE", "#1d4e89", "#d9e6f5"],
    inconclusivo: ["EM ABERTO", "#1d4e89", "#d9e6f5"],
    pendente: ["CHECANDO", "#1d4e89", "#d9e6f5"],
    processando: ["CHECANDO", "#1d4e89", "#d9e6f5"],
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

  async function faces() {
    if (document.fonts.check("16px 'Archivo Black'")) return;
    const black = new FontFace("Archivo Black", "url(/static/fonts/archivo-black.ttf)");
    const body = new FontFace("Literata", "url(/static/fonts/literata-500.ttf)", { weight: "500" });
    const bold = new FontFace("Literata", "url(/static/fonts/literata-700.ttf)", { weight: "700" });
    const loaded = await Promise.all([black.load(), body.load(), bold.load()]);
    loaded.forEach((face) => document.fonts.add(face));
  }

  async function png(claim, format) {
    await faces();
    const story = format === "stories";
    const W = 1080;
    const H = story ? 1920 : 1350;
    const pad = 88;
    const [stamp, ink, wash] = STAMP[claim.status] || ["CHECAGEM", "#161616", "#f3f1ec"];
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#f3f1ec";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = ink;
    ctx.fillRect(0, 0, 36, H);

    ctx.fillStyle = "#161616";
    ctx.font = "400 34px 'Archivo Black', sans-serif";
    ctx.textBaseline = "top";
    ctx.fillText("MENTIRÔMETRO", pad, story ? 120 : 78);

    const who = WHO[claim.speaker] || "Checagem";
    ctx.font = "500 32px Literata, serif";
    ctx.fillText(who, pad, story ? 180 : 132);

    const quote = `"${claim.normalized || claim.quote || ""}"`;
    ctx.font = "400 64px 'Archivo Black', sans-serif";
    const quoteLines = wrap(ctx, quote, W - pad * 2).slice(0, story ? 8 : 5);
    let y = story ? 280 : 220;
    quoteLines.forEach((line) => {
      ctx.fillText(line, pad, y);
      y += 74;
    });

    y += story ? 48 : 36;
    ctx.font = "400 42px 'Archivo Black', sans-serif";
    const stampW = Math.min(ctx.measureText(stamp).width + 48, W - pad * 2);
    const stampH = 78;
    ctx.fillStyle = wash;
    ctx.fillRect(pad, y, stampW, stampH);
    ctx.fillStyle = ink;
    ctx.textBaseline = "middle";
    ctx.fillText(stamp, pad + 24, y + stampH / 2 + 2);
    ctx.textBaseline = "top";

    y += stampH + (story ? 48 : 36);
    ctx.fillStyle = "#161616";
    ctx.font = "500 36px Literata, serif";
    wrap(ctx, claim.summary || "", W - pad * 2).slice(0, story ? 7 : 4)
      .forEach((line) => {
        ctx.fillText(line, pad, y);
        y += 48;
      });

    const source = (claim.sources || []).find((item) => item && item.url);
    const foot = H - (story ? 160 : 96);
    ctx.fillStyle = "#161616";
    ctx.fillRect(pad, foot - 24, W - pad * 2, 3);
    ctx.font = "700 28px Literata, serif";
    const kind = source && source.kind ? `${source.kind} · ` : "";
    const sourceLine = source ? `${kind}${String(source.title || source.url)}`.slice(0, 72) : "Sem página https";
    ctx.fillText(sourceLine, pad, foot);
    if (claim.correction) {
      ctx.font = "500 26px Literata, serif";
      ctx.fillText(`Correção: ${String(claim.correction).slice(0, 90)}`, pad, foot + 42);
    }

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `mentirometro-${claim.id || "checagem"}${story ? "-stories" : ""}.png`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
  }

  return { png };
})();
