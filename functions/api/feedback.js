const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};

const MAX_BODY_BYTES = 16_384;
const MAX_MESSAGE_LENGTH = 1_000;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: JSON_HEADERS,
  });
}

function cleanLine(value, maxLength) {
  return String(value || "")
    .replace(/[\r\n\u2028\u2029]+/g, " ")
    .trim()
    .slice(0, maxLength);
}

function cleanMessage(value) {
  return String(value || "").replace(/\r\n?/g, "\n").trim();
}

function isEmail(value) {
  return !value || (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value.length <= 254);
}

function isFeedbackPath(value) {
  return value === "/feedback/" || /^\/haiku\/\d{4}-\d{2}-\d{2}-\d+\/$/.test(value);
}

async function readPayload(request) {
  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > MAX_BODY_BYTES) {
    throw new Error("payload_too_large");
  }

  const contentType = request.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const source = await request.text();
    if (new TextEncoder().encode(source).length > MAX_BODY_BYTES) {
      throw new Error("payload_too_large");
    }
    return JSON.parse(source);
  }

  if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
    return Object.fromEntries(await request.formData());
  }

  throw new Error("unsupported_media_type");
}

async function verifyTurnstile(token, request, secret) {
  const body = new FormData();
  body.set("secret", secret);
  body.set("response", token);

  const remoteIp = request.headers.get("CF-Connecting-IP");
  if (remoteIp) {
    body.set("remoteip", remoteIp);
  }

  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body,
  });
  if (!response.ok) {
    return false;
  }

  const result = await response.json();
  return result.success === true && (!result.action || result.action === "haiku_feedback");
}

function requestIsSameOrigin(request) {
  const origin = request.headers.get("origin");
  if (!origin) {
    return true;
  }

  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

async function handlePost(context) {
  const { request, env } = context;

  if (!requestIsSameOrigin(request)) {
    return jsonResponse({ ok: false, message: "送信元を確認できませんでした。" }, 403);
  }

  if (!env.RESEND_API_KEY || !env.FEEDBACK_FROM_EMAIL || !env.FEEDBACK_TO_EMAIL || !env.TURNSTILE_SECRET_KEY) {
    return jsonResponse({ ok: false, message: "ただいま送信機能を準備しています。" }, 503);
  }

  let payload;
  try {
    payload = await readPayload(request);
  } catch (error) {
    const status = error.message === "payload_too_large" ? 413 : 400;
    return jsonResponse({ ok: false, message: "入力内容を確認してください。" }, status);
  }

  const name = cleanLine(payload.name, 60);
  const email = cleanLine(payload.email, 254);
  const message = cleanMessage(payload.message);
  const poemPath = cleanLine(payload.poemPath, 80);
  const poemTitle = cleanLine(payload.poemTitle, 160);
  const honeypot = cleanLine(payload.website, 120);
  const turnstileToken = cleanLine(payload.turnstileToken || payload["cf-turnstile-response"], 2_048);

  if (honeypot) {
    return jsonResponse({ ok: true, message: "ありがとうございました。" });
  }

  if (!message || message.length > MAX_MESSAGE_LENGTH || !isEmail(email) || !isFeedbackPath(poemPath) || !poemTitle) {
    return jsonResponse({ ok: false, message: "入力内容を確認してください。" }, 400);
  }

  let verified = false;
  try {
    verified = Boolean(turnstileToken) && await verifyTurnstile(turnstileToken, request, env.TURNSTILE_SECRET_KEY);
  } catch {
    return jsonResponse({ ok: false, message: "確認サービスに接続できませんでした。" }, 502);
  }
  if (!verified) {
    return jsonResponse({ ok: false, message: "確認に失敗しました。もう一度お試しください。" }, 400);
  }

  const siteOrigin = new URL(request.url).origin;
  const poemUrl = new URL(poemPath, siteOrigin).toString();
  const senderName = name || "匿名";
  const isSiteFeedback = poemPath === "/feedback/";
  const targetLabel = isSiteFeedback ? "対象" : "句";
  const text = [
    "樹の句帖に、ひとことが届きました。",
    "",
    `${targetLabel}: ${poemTitle}`,
    `ページ: ${poemUrl}`,
    `お名前: ${senderName}`,
    `返信先: ${email || "記入なし"}`,
    "",
    "メッセージ:",
    message,
  ].join("\n");

  const emailPayload = {
    from: env.FEEDBACK_FROM_EMAIL,
    to: [env.FEEDBACK_TO_EMAIL],
    subject: isSiteFeedback
      ? "【樹の句帖】サイトへのひとこと"
      : `【樹の句帖】${poemTitle.slice(0, 48)}へのひとこと`,
    text,
  };
  if (email) {
    emailPayload.reply_to = email;
  }

  let resendResponse;
  try {
    resendResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(emailPayload),
    });
  } catch {
    return jsonResponse({ ok: false, message: "送信サービスに接続できませんでした。" }, 502);
  }

  if (!resendResponse.ok) {
    return jsonResponse({ ok: false, message: "送信できませんでした。時間をおいてお試しください。" }, 502);
  }

  return jsonResponse({ ok: true, message: "ありがとうございました。ひとことを受け取りました。" });
}

export async function onRequest(context) {
  if (context.request.method !== "POST") {
    return jsonResponse({ ok: false, message: "この操作には対応していません。" }, 405);
  }
  return handlePost(context);
}
