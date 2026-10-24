(() => {
const PEOPLE = [
  {
    speaker: "flavio",
    nome: "Flávio Bolsonaro",
    lines: ["Flávio", "Bolsonaro"],
    party: "PL · número 22",
    photo: "/static/portraits/flavio.jpg",
    alt: "Flávio Bolsonaro",
    pct: "47,03%",
    votos: "56,1 milhões de votos válidos — resultado oficial do TSE, 4 de outubro",
  },
  {
    speaker: "lula",
    nome: "Lula",
    lines: ["Lula"],
    party: "PT · número 13",
    photo: "/static/portraits/lula.jpg",
    alt: "Lula",
    pct: "45,16%",
    votos: "53,9 milhões de votos válidos — resultado oficial do TSE, 4 de outubro",
  },
];

const TILE = {
  sustentado: "#3dce8f",
  sustentado_ressalva: "#b7d36a",
  nao_e_bem_assim: "#e2b34a",
  exagerado: "#f0a05a",
  sem_prova: "#c8c2ba",
  distorcido: "#ff6b6b",
  contradito: "#ff6b6b",
};

const EMPTY = {
  verdadeiras: 0,
  ressalva: 0,
  parcial: 0,
  exageradas: 0,
  sem_provas: 0,
  falsas_ou_distorcidas: 0,
  classificadas: 0,
  sem_veredito: 0,
  promessas: 0,
  percentual: null,
};

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"]/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
  }[ch]));
}

function segments(resumo) {
  return [
    { n: resumo.falsas_ou_distorcidas, color: "#ff6b6b" },
    { n: resumo.exageradas, color: "#f0a05a" },
    { n: resumo.parcial, color: "#e2b34a" },
    { n: resumo.ressalva, color: "#b7d36a" },
    { n: resumo.sem_provas, color: "#c8c2ba" },
    { n: resumo.verdadeiras, color: "#3dce8f" },
  ];
}

function ring(resumo) {
  const parts = segments(resumo).filter((part) => part.n > 0);
  const total = parts.reduce((sum, part) => sum + part.n, 0);
  if (!total) return "conic-gradient(#2c2c2c 0 100%)";
  let cursor = 0;
  const stops = parts.map((part) => {
    const next = cursor + (part.n / total) * 100;
    const stop = `${part.color} ${cursor}% ${next}%`;
    cursor = next;
    return stop;
  });
  return `conic-gradient(from -90deg, ${stops.join(",")})`;
}

function legendItems(resumo) {
  const items = [
    ["#3dce8f", resumo.verdadeiras, "verdadeiras", false],
    ["#f0a05a", resumo.exageradas, "exageradas", false],
    ["#ff6b6b", resumo.falsas_ou_distorcidas, "falsas ou distorcidas", true],
  ];
  if (resumo.ressalva) items.push(["#b7d36a", resumo.ressalva, "verdadeiro, mas...", true]);
  if (resumo.parcial) items.push(["#e2b34a", resumo.parcial, "não é bem assim", true]);
  if (resumo.sem_provas) items.push(["#c8c2ba", resumo.sem_provas, "sem provas", true]);
  return items;
}

function tally(resumo) {
  if (!resumo.classificadas && !resumo.sem_veredito && !resumo.promessas) {
    return "Nenhuma checagem neste debate.";
  }
  const bits = [`${resumo.classificadas} checagens`, `${resumo.sem_veredito} sem veredito`];
  if (resumo.promessas) {
    const word = resumo.promessas === 1 ? "promessa" : "promessas";
    bits.push(`${resumo.promessas} ${word}, fora do percentual`);
  }
  return bits.join(" · ");
}

function phrase(person, item) {
  const resumo = (item && item.resumo) || EMPTY;
  if (resumo.percentual == null) return `${person.nome} ainda não tem carimbo fechado`;
  const checagens = resumo.classificadas === 1 ? "1 checagem" : `${resumo.classificadas} checagens`;
  return `${resumo.percentual}% das afirmações checadas de ${person.nome} foram classificadas como falsas ou distorcidas (${checagens})`;
}

function caption(title, bySpeaker) {
  const flavio = bySpeaker.flavio;
  const lula = bySpeaker.lula;
  const bothEmpty = [flavio, lula].every((item) => ((item && item.resumo) || EMPTY).percentual == null);
  if (bothEmpty) return "Este debate ainda não tem carimbo fechado.";
  const where = title ? `Em ${title}` : "No debate";
  return `${where}, ${phrase(PEOPLE[0], flavio)}. ${phrase(PEOPLE[1], lula)}.`;
}

function column(person, item) {
  const resumo = (item && item.resumo) || EMPTY;
  const tiles = (item && item.mosaico) || [];
  const pct = resumo.percentual == null ? "—" : `${resumo.percentual}%`;
  const legend = legendItems(resumo)
    .map(([color, count, label, wide]) => {
      return `<li class="${wide ? "wide" : ""}"><i style="background:${color}"></i><span><b>${count}</b> ${escapeHtml(label)}</span></li>`;
    })
    .join("");
  const density = tiles.length > 120 ? " tiny" : tiles.length > 48 ? " dense" : "";
  const squares = tiles
    .map((status) => `<i style="background:${TILE[status] || "#c8c2ba"}"></i>`)
    .join("");
  const vote = `<div class="vote"><span class="turn">1º turno</span><strong>${person.pct}</strong><p>${escapeHtml(person.votos)}</p></div>`;
  const photo = `<div class="photo"><img src="${person.photo}" alt="${escapeHtml(person.alt)}"><div class="mosaic${density}" aria-hidden="true">${squares}</div></div>`;
  const shot = person.speaker === "lula" ? photo + vote : vote + photo;
  return `<section class="col ${person.speaker}"><h2>${person.lines.map(escapeHtml).join("<br>")}</h2><p class="party">${escapeHtml(person.party)}</p><div class="meter"><div class="donut" style="background:${ring(resumo)}"><div class="hole"><strong>${pct}</strong><span>falsas ou distorcidas</span></div></div><ul class="legend">${legend}</ul></div><p class="tally">${escapeHtml(tally(resumo))}</p><div class="shot">${shot}</div></section>`;
}

function indexCandidates(candidates) {
  const by = {};
  for (const item of candidates || []) by[item.speaker] = item;
  return by;
}

function mount(board, captionEl, model) {
  const by = indexCandidates(model && model.candidates);
  board.innerHTML = PEOPLE.map((person) => column(person, by[person.speaker])).join("");
  captionEl.textContent = caption(model && model.debate && model.debate.title, by);
}

function wrap(ctx, text, width) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > width && line) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function cover(ctx, img, x, y, w, h, focusY) {
  const frame = w / h;
  const ratio = img.width / img.height;
  let sx = 0;
  let sy = 0;
  let sw = img.width;
  let sh = img.height;
  if (ratio > frame) {
    sw = img.height * frame;
    sx = (img.width - sw) / 2;
  } else {
    sh = img.width / frame;
    sy = Math.max(0, (img.height - sh) * focusY);
  }
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.filter = "grayscale(1) contrast(1.08)";
  ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
  ctx.filter = "none";
  const shade = ctx.createLinearGradient(0, y + h * 0.45, 0, y + h);
  shade.addColorStop(0, "rgba(0,0,0,0)");
  shade.addColorStop(1, "rgba(0,0,0,0.78)");
  ctx.fillStyle = shade;
  ctx.fillRect(x, y, w, h);
  ctx.restore();
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function drawDonut(ctx, cx, cy, outer, inner, resumo) {
  const parts = segments(resumo).filter((part) => part.n > 0);
  const total = parts.reduce((sum, part) => sum + part.n, 0);
  const mid = (outer + inner) / 2;
  ctx.lineWidth = outer - inner;
  ctx.lineCap = "butt";
  ctx.beginPath();
  ctx.strokeStyle = "#2c2c2c";
  ctx.arc(cx, cy, mid, 0, Math.PI * 2);
  ctx.stroke();
  let angle = -Math.PI / 2;
  for (const part of parts) {
    const sweep = (part.n / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.strokeStyle = part.color;
    ctx.arc(cx, cy, mid, angle, angle + sweep);
    ctx.stroke();
    angle += sweep;
  }
  ctx.fillStyle = "#141416";
  ctx.beginPath();
  ctx.arc(cx, cy, inner - 1, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#f6f3ee";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `400 34px "Archivo Black"`;
  const label = resumo.percentual == null ? "—" : `${resumo.percentual}%`;
  ctx.fillText(label, cx, cy - 8);
  ctx.font = `400 11px "Archivo Black"`;
  ctx.fillStyle = "#ddd6cc";
  ctx.fillText("FALSAS OU", cx, cy + 16);
  ctx.fillText("DISTORCIDAS", cx, cy + 30);
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
}

function cellSize(count) {
  if (count > 120) return 6;
  if (count > 48) return 8;
  return 11;
}

function mosaicBox(count, width) {
  const cell = cellSize(count);
  const gap = 3;
  const per = Math.max(1, Math.floor((width + gap) / (cell + gap)));
  const rows = Math.max(1, Math.ceil(count / per));
  return { cell, gap, height: rows * cell + (rows - 1) * gap };
}

function drawMosaic(ctx, tiles, x, y, width) {
  const cell = cellSize(tiles.length);
  const gap = 3;
  let cursor = 0;
  let row = 0;
  for (const status of tiles) {
    if (cursor + cell > width) {
      cursor = 0;
      row += 1;
    }
    ctx.fillStyle = TILE[status] || "#c8c2ba";
    ctx.fillRect(x + cursor, y + row * (cell + gap), cell, cell);
    cursor += cell + gap;
  }
}

async function draw(model) {
  const scale = 2;
  const width = 1200;
  const by = indexCandidates(model && model.candidates);
  const text = caption(model && model.debate && model.debate.title, by);
  const canvas = document.createElement("canvas");
  const probe = canvas.getContext("2d");
  probe.font = `500 22px Literata`;
  const captionLines = wrap(probe, text, width - 36);
  const height = 830 + captionLines.length * 30;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.fillStyle = "#0c0c0c";
  ctx.fillRect(0, 0, width, height);

  const images = {};
  await Promise.all(
    PEOPLE.map(async (person) => {
      images[person.speaker] = await loadImage(person.photo);
    })
  );

  const gap = 10;
  const panelW = (width - 36 - gap) / 2;
  PEOPLE.forEach((person, index) => {
    const item = by[person.speaker] || { resumo: EMPTY, mosaico: [] };
    const resumo = item.resumo || EMPTY;
    const x = 18 + index * (panelW + gap);
    const y = 18;
    const panelH = 700;
    ctx.fillStyle = "#141416";
    ctx.fillRect(x, y, panelW, panelH);

    ctx.fillStyle = "#f6f3ee";
    ctx.font = `400 58px "Archivo Black"`;
    ctx.textBaseline = "top";
    person.lines.forEach((line, lineIndex) => {
      ctx.fillText(line.toUpperCase(), x + 22, y + 26 + lineIndex * 60);
    });
    ctx.fillStyle = "#b7b0a6";
    ctx.font = `500 20px Literata`;
    ctx.fillText(person.party, x + 22, y + 158);

    drawDonut(ctx, x + 22 + 74, y + 196 + 74, 74, 52, resumo);

    ctx.textBaseline = "top";
    ctx.font = `500 18px Literata`;
    const legendX = x + 186;
    let legendY = y + 214;
    const left = legendItems(resumo).filter((row) => !row[3]);
    const rest = legendItems(resumo).filter((row) => row[3]);
    left.forEach((row, rowIndex) => {
      const col = rowIndex % 2;
      const rowY = legendY + Math.floor(rowIndex / 2) * 28;
      ctx.fillStyle = row[0];
      ctx.fillRect(legendX + col * 168, rowY + 4, 10, 10);
      ctx.fillStyle = "#f6f3ee";
      ctx.font = `400 18px "Archivo Black"`;
      const count = String(row[1]);
      const countW = ctx.measureText(count).width;
      ctx.fillText(count, legendX + 16 + col * 168, rowY);
      ctx.font = `500 18px Literata`;
      ctx.fillText(row[2], legendX + 16 + col * 168 + countW + 6, rowY);
    });
    legendY += 36;
    rest.forEach((row) => {
      ctx.fillStyle = row[0];
      ctx.fillRect(legendX, legendY + 4, 10, 10);
      ctx.fillStyle = "#f6f3ee";
      ctx.font = `400 18px "Archivo Black"`;
      const count = String(row[1]);
      const countW = ctx.measureText(count).width;
      ctx.fillText(count, legendX + 16, legendY);
      ctx.font = `500 18px Literata`;
      ctx.fillText(row[2], legendX + 16 + countW + 6, legendY);
      legendY += 28;
    });

    ctx.fillStyle = "#ddd6cc";
    ctx.font = `500 18px Literata`;
    ctx.fillText(tally(resumo), x + 22, y + 360);

    const shotY = y + 408;
    const shotH = 276;
    const voteW = 210;
    const photoX = person.speaker === "lula" ? x : x + voteW;
    const photoW = panelW - voteW;
    const voteX = person.speaker === "lula" ? x + photoW : x;
    ctx.fillStyle = "#0c0c0c";
    ctx.fillRect(x, shotY, panelW, shotH);
    const photo = images[person.speaker];
    if (photo) cover(ctx, photo, photoX, shotY, photoW, shotH, 0.08);
    ctx.fillStyle = "#b7b0a6";
    ctx.font = `400 13px "Archivo Black"`;
    ctx.fillText("1º TURNO", voteX + 16, shotY + shotH - 118);
    ctx.fillStyle = "#f6f3ee";
    ctx.font = `400 32px "Archivo Black"`;
    ctx.fillText(person.pct, voteX + 16, shotY + shotH - 96);
    ctx.fillStyle = "#ddd6cc";
    ctx.font = `500 15px Literata`;
    wrap(ctx, person.votos, voteW - 32).forEach((line, lineIndex) => {
      ctx.fillText(line, voteX + 16, shotY + shotH - 58 + lineIndex * 18);
    });
    const tiles = item.mosaico || [];
    if (tiles.length) {
      const box = mosaicBox(tiles.length, photoW - 20);
      ctx.save();
      ctx.beginPath();
      ctx.rect(photoX, shotY, photoW, shotH);
      ctx.clip();
      drawMosaic(ctx, tiles, photoX + 10, shotY + shotH - 10 - box.height, photoW - 20);
      ctx.restore();
    }
  });

  ctx.fillStyle = "#f15d5a";
  ctx.font = `400 16px "Archivo Black"`;
  ctx.textBaseline = "top";
  ctx.fillText("MENTIRÔMETRO", 18, 734);
  ctx.fillStyle = "#f6f3ee";
  ctx.font = `500 22px Literata`;
  captionLines.forEach((line, lineIndex) => {
    ctx.fillText(line, 18, 762 + lineIndex * 30);
  });
  const creditY = 762 + captionLines.length * 30 + 8;
  ctx.fillStyle = "#b7b0a6";
  ctx.font = `500 14px Literata`;
  ctx.fillText(
    "Retratos: Geraldo Magela/Agência Senado (CC BY-SA 4.0) e Ricardo Stuckert/PR (CC BY 2.0). 1º turno: TSE.",
    18,
    creditY
  );
  return await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

function download(blob, name) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1500);
}

async function share(model) {
  await document.fonts.load('400 58px "Archivo Black"');
  await document.fonts.load("500 22px Literata");
  await document.fonts.load("700 22px Literata");
  const blob = await draw(model);
  const slug = (model && model.debate && model.debate.slug) || "debate";
  const name = `placar-${slug}.png`;
  const image = new File([blob], name, { type: "image/png" });
  if (navigator.canShare && navigator.canShare({ files: [image] })) {
    await navigator.share({ files: [image], title: "Mentirômetro" });
    return "shared";
  }
  download(blob, name);
  return "saved";
}

window.Placar = { mount, share, caption, draw };
})();
