const MentiroCard = (() => {
  const STAMP = {
    sustentado: ["VERDADEIRO", "#3dce8f"],
    sustentado_ressalva: ["VERDADEIRO, MAS...", "#b7d36a"],
    nao_e_bem_assim: ["NÃO É BEM ASSIM", "#e2b34a"],
    exagerado: ["EXAGERADO", "#f0a05a"],
    promessa: ["PROMESSA", "#f0a05a"],
    distorcido: ["DISTORCIDO", "#f3a0a8"],
    contradito: ["FALSO", "#ff6b6b"],
    sem_prova: ["SEM PROVAS", "#c8c2ba"],
    erro: ["ERRO", "#ff6b6b"],
    sem_prova_publica: ["SEM PROVA PÚBLICA", "#a9bdd4"],
    versoes_em_disputa: ["VERSÕES EM DISPUTA", "#a9bdd4"],
    indicio: ["INDÍCIO", "#a9bdd4"],
    dados_incompletos: ["DADOS INCOMPLETOS", "#a9bdd4"],
    audio_confuso: ["ÁUDIO CONFUSO", "#a9bdd4"],
    sem_evidencia: ["SEM FONTE", "#a9bdd4"],
    inconclusivo: ["EM ABERTO", "#a9bdd4"],
    pendente: ["CHECANDO", "#a9bdd4"],
    processando: ["CHECANDO", "#a9bdd4"],
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

  function montserrat() {
    return document.documentElement.dataset.face === "montserrat";
  }

  function face(weight, size, display) {
    if (montserrat()) return `${weight} ${size}px Montserrat, sans-serif`;
    return `400 ${size}px ${display ? "'Archivo Black', sans-serif" : "Literata, serif"}`;
  }

  function drawStamp(ctx, text, ink, x, y, maxW) {
    ctx.save();
    let size = 42;
    ctx.font = face(800, size, true);
    while (size > 26 && ctx.measureText(text).width > maxW - 56) {
      size -= 2;
      ctx.font = face(800, size, true);
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
    if (montserrat()) {
      await Promise.all([
        document.fonts.load("500 32px Montserrat"),
        document.fonts.load("700 28px Montserrat"),
        document.fonts.load("800 64px Montserrat"),
      ]);
      return;
    }
    if (document.fonts.check("16px 'Archivo Black'")) return;
    const black = new FontFace("Archivo Black", "url(/static/fonts/archivo-black.ttf)");
    const body = new FontFace("Literata", "url(/static/fonts/literata-500.ttf)", { weight: "500" });
    const bold = new FontFace("Literata", "url(/static/fonts/literata-700.ttf)", { weight: "700" });
    const loaded = await Promise.all([black.load(), body.load(), bold.load()]);
    loaded.forEach((item) => document.fonts.add(item));
  }

  async function draw(claim, format) {
    await faces();
    const story = format === "stories";
    const W = 1080;
    const H = story ? 1920 : 1350;
    const pad = 88;
    const [stamp, ink] = STAMP[claim.status] || ["CHECAGEM", "#f6f3ee"];
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0c0c0c";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#f15d5a";
    ctx.lineWidth = 12;
    ctx.strokeRect(18, 18, W - 36, H - 36);

    const logo = new Image();
    logo.src = "/static/logo-ie-mark.png";
    await logo.decode();
    const logoH = story ? 92 : 78;
    const logoW = logoH * (logo.width / logo.height);
    let top = story ? 120 : 72;
    ctx.drawImage(logo, pad, top, logoW, logoH);
    top += logoH + 28;

    ctx.fillStyle = "#f15d5a";
    ctx.font = face(800, 28, true);
    ctx.textBaseline = "top";
    ctx.fillText("MENTIRÔMETRO", pad, top);

    const who = WHO[claim.speaker] || "Checagem";
    ctx.fillStyle = "#f6f3ee";
    ctx.font = face(500, 32, false);
    ctx.fillText(who, pad, top + 48);

    const quote = `"${claim.normalized || claim.quote || ""}"`;
    ctx.font = face(800, 64, true);
    const quoteLines = wrap(ctx, quote, W - pad * 2).slice(0, story ? 8 : 5);
    let y = top + (story ? 140 : 120);
    quoteLines.forEach((line) => {
      ctx.fillText(line, pad, y);
      y += 74;
    });

    y += story ? 48 : 36;
    const stampH = drawStamp(ctx, stamp, ink, pad, y, W - pad * 2);
    ctx.textAlign = "left";
    ctx.textBaseline = "top";

    y += stampH + (story ? 48 : 36);
    ctx.fillStyle = "#f6f3ee";
    ctx.font = face(500, 36, false);
    wrap(ctx, claim.summary || "", W - pad * 2).slice(0, story ? 7 : 4)
      .forEach((line) => {
        ctx.fillText(line, pad, y);
        y += 48;
      });

    const source = (claim.sources || []).find((item) => item && item.url);
    const foot = H - (story ? 220 : 150);
    ctx.fillStyle = "#f15d5a";
    ctx.fillRect(pad, foot - 24, W - pad * 2, 3);
    ctx.fillStyle = "#f6f3ee";
    ctx.font = face(700, 28, false);
    const kind = source && source.kind ? `${source.kind} · ` : "";
    const sourceText = source ? `${kind}${source.title || source.url}` : "Sem página https";
    wrap(ctx, sourceText, W - pad * 2).slice(0, 2).forEach((line, index) => {
      ctx.fillText(line, pad, foot + index * 36);
    });
    if (claim.correction) {
      ctx.font = face(500, 26, false);
      wrap(ctx, `Correção: ${claim.correction}`, W - pad * 2).slice(0, 2).forEach((line, index) => {
        ctx.fillText(line, pad, foot + 84 + index * 34);
      });
    }

    return await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  }

  function filename(claim, format) {
    return `mentirometro-${claim.id || "checagem"}${format === "stories" ? "-stories" : ""}.png`;
  }

  function download(blob, name) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
  }

  async function png(claim, format) {
    const blob = await draw(claim, format);
    download(blob, filename(claim, format));
  }

  async function share(claim, format) {
    const blob = await draw(claim, format || "feed");
    const image = new File([blob], filename(claim, format || "feed"), { type: "image/png" });
    if (navigator.canShare && navigator.canShare({ files: [image] })) {
      await navigator.share({ files: [image], title: "Mentirômetro" });
      return "shared";
    }
    download(blob, image.name);
    return "saved";
  }

  return { png, share };
})();
