const MentiroCard = (() => {
  const STAMP = {
    sustentado: ["VERDADEIRO", "#2f7a3e"],
    sustentado_ressalva: ["VERDADEIRO, MAS...", "#6d8f28"],
    nao_e_bem_assim: ["NÃO É BEM ASSIM", "#a67c1a"],
    exagerado: ["EXAGERADO", "#c56a2c"],
    promessa: ["PROMESSA", "#c56a2c"],
    distorcido: ["DISTORCIDO", "#c45c66"],
    contradito: ["FALSO", "#c43838"],
    sem_prova: ["SEM PROVAS", "#6f6f6f"],
    erro: ["ERRO", "#c43838"],
    sem_prova_publica: ["SEM PROVA PÚBLICA", "#5c6b7a"],
    versoes_em_disputa: ["VERSÕES EM DISPUTA", "#5c6b7a"],
    indicio: ["INDÍCIO", "#5c6b7a"],
    dados_incompletos: ["DADOS INCOMPLETOS", "#5c6b7a"],
    audio_confuso: ["ÁUDIO CONFUSO", "#5c6b7a"],
    sem_evidencia: ["SEM FONTE", "#5c6b7a"],
    inconclusivo: ["EM ABERTO", "#5c6b7a"],
    pendente: ["CHECANDO", "#5c6b7a"],
    processando: ["CHECANDO", "#5c6b7a"],
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

  function drawStamp(ctx, text, ink, x, y, maxW) {
    ctx.save();
    let size = 42;
    ctx.font = `400 ${size}px 'Archivo Black', sans-serif`;
    while (size > 26 && ctx.measureText(text).width > maxW - 56) {
      size -= 2;
      ctx.font = `400 ${size}px 'Archivo Black', sans-serif`;
    }
    const w = Math.min(ctx.measureText(text).width + 48, maxW);
    const h = size + 34;
    ctx.translate(x, y + h / 2);
    ctx.rotate(-0.045);
    ctx.translate(0, -h / 2);
    ctx.strokeStyle = ink;
    ctx.lineWidth = 6;
    ctx.strokeRect(3, 3, w - 6, h - 6);
    ctx.lineWidth = 2;
    ctx.strokeRect(10, 10, w - 20, h - 20);
    ctx.fillStyle = ink;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, w / 2, h / 2 + 1);
    ctx.restore();
    return h;
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
    const [stamp, ink] = STAMP[claim.status] || ["CHECAGEM", "#161616"];
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
    const stampH = drawStamp(ctx, stamp, ink, pad, y, W - pad * 2);
    ctx.textAlign = "left";
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
    const foot = H - (story ? 220 : 150);
    ctx.fillStyle = "#161616";
    ctx.fillRect(pad, foot - 24, W - pad * 2, 3);
    ctx.font = "700 28px Literata, serif";
    const kind = source && source.kind ? `${source.kind} · ` : "";
    const sourceText = source ? `${kind}${source.title || source.url}` : "Sem página https";
    wrap(ctx, sourceText, W - pad * 2).slice(0, 2).forEach((line, index) => {
      ctx.fillText(line, pad, foot + index * 36);
    });
    if (claim.correction) {
      ctx.font = "500 26px Literata, serif";
      wrap(ctx, `Correção: ${claim.correction}`, W - pad * 2).slice(0, 2).forEach((line, index) => {
        ctx.fillText(line, pad, foot + 84 + index * 34);
      });
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
