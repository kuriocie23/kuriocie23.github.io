/**
 * Worker autopromo-live : totaux GA4 des 30 dernières minutes.
 * Aucune clé dans la page statique. La clé du compte de service est un secret Worker.
 * L'API Realtime ne permet pas les dimensions d'événement (jeu_source, etc.) :
 * https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema
 */
const ALLOWED_ORIGIN = "https://kuriocie23.github.io";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SCOPE = "https://www.googleapis.com/auth/analytics.readonly";
const VIEW = "cross_promo_view";
const CLICK = "cross_promo_click";
const CACHE_URL = "https://autopromo-live.internal/live";
const CACHE_MAX_AGE = 60;

function corsHeaders(origin, extra) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "public, max-age=" + CACHE_MAX_AGE,
    ...extra,
  };
  if (origin === ALLOWED_ORIGIN) {
    headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN;
    headers["Access-Control-Allow-Methods"] = "GET, OPTIONS";
    headers["Access-Control-Allow-Headers"] = "Content-Type";
    headers["Vary"] = "Origin";
  }
  return headers;
}

function json(origin, body, status) {
  return new Response(JSON.stringify(body), {
    status: status || 200,
    headers: corsHeaders(origin),
  });
}

function b64urlFromString(s) {
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function b64urlFromBytes(bytes) {
  let bin = "";
  const arr = new Uint8Array(bytes);
  for (let i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function importPrivateKey(pem) {
  const b64 = String(pem).replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const raw = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey(
    "pkcs8",
    raw.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
}

async function googleAccessToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = b64urlFromString(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = b64urlFromString(JSON.stringify({
    iss: sa.client_email,
    scope: SCOPE,
    aud: TOKEN_URL,
    iat: now,
    exp: now + 3600,
  }));
  const key = await importPrivateKey(sa.private_key);
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(header + "." + claim),
  );
  const jwt = header + "." + claim + "." + b64urlFromBytes(sig);
  const r = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  if (!r.ok) throw new Error("Jeton Google HTTP " + r.status);
  const data = await r.json();
  if (!data.access_token) throw new Error("Jeton Google manquant");
  return data.access_token;
}

function parseServiceAccount(raw) {
  if (!raw) throw new Error("Secret GA4_SERVICE_ACCOUNT_JSON manquant");
  const sa = typeof raw === "string" ? JSON.parse(raw) : raw;
  if (!sa.client_email || !sa.private_key) throw new Error("Compte de service incomplet");
  return sa;
}

async function runRealtime(token, propertyId) {
  const url = "https://analyticsdata.googleapis.com/v1beta/properties/" + propertyId + ":runRealtimeReport";
  const body = {
    dimensions: [{ name: "eventName" }],
    metrics: [{ name: "eventCount" }],
    dimensionFilter: {
      orGroup: {
        expressions: [VIEW, CLICK].map((ev) => ({
          filter: { fieldName: "eventName", stringFilter: { matchType: "EXACT", value: ev } },
        })),
      },
    },
    limit: "100",
  };
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  if (!r.ok) throw new Error("API GA4 temps réel HTTP " + r.status);
  return JSON.parse(text);
}

function maintenantParis() {
  const fmt = new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return fmt.format(new Date()) + " Europe/Paris";
}

function payloadFromReport(report) {
  let vues = 0;
  let clics = 0;
  for (const row of report.rows || []) {
    const nom = (row.dimensionValues && row.dimensionValues[0] && row.dimensionValues[0].value) || "";
    const n = Number((row.metricValues && row.metricValues[0] && row.metricValues[0].value) || 0);
    if (nom === VIEW) vues += n;
    else if (nom === CLICK) clics += n;
  }
  const vide = vues === 0 && clics === 0;
  return {
    periode: "30 dernières minutes",
    source: "API GA4 runRealtimeReport, propriété 563415076 (kuriocie-jeux)",
    evenements: [VIEW, CLICK],
    vues,
    clics,
    mis_a_jour: maintenantParis(),
    message: vide
      ? "Aucun affichage ni clic dans les 30 dernières minutes."
      : null,
    note: "Le temps réel ne donne que les totaux (l'API Realtime n'accepte pas les dimensions jeu_source, jeu_cible, langue, emplacement).",
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") {
      if (origin !== ALLOWED_ORIGIN) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "GET") {
      return json(origin, { erreur: "Méthode non autorisée" }, 405);
    }

    const cache = caches.default;
    const cacheKey = new Request(CACHE_URL, { method: "GET" });
    const hit = await cache.match(cacheKey);
    if (hit) {
      const cached = new Response(hit.body, hit);
      const headers = corsHeaders(origin);
      for (const [k, v] of Object.entries(headers)) cached.headers.set(k, v);
      cached.headers.set("X-Cache", "HIT");
      return cached;
    }

    try {
      const propertyId = String(env.GA4_PROPERTY_ID || "563415076").replace(/^properties\//, "");
      const sa = parseServiceAccount(env.GA4_SERVICE_ACCOUNT_JSON);
      const token = await googleAccessToken(sa);
      const report = await runRealtime(token, propertyId);
      const payload = payloadFromReport(report);
      const resp = json(origin, payload, 200);
      await cache.put(cacheKey, resp.clone());
      resp.headers.set("X-Cache", "MISS");
      return resp;
    } catch (err) {
      return json(origin, {
        erreur: "Temps réel indisponible pour le moment.",
        periode: "30 dernières minutes",
        vues: 0,
        clics: 0,
        mis_a_jour: maintenantParis(),
        message: "Impossible de lire les chiffres en direct. Réessayez dans une minute.",
      }, 200);
    }
  },
};
