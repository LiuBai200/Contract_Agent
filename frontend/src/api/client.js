const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";
const TOKEN_KEY = "contract_rag_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof data === "object" ? data.detail || JSON.stringify(data) : data;
    throw new Error(detail || `HTTP ${response.status}`);
  }

  return data;
}

export function register(username, password) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function login(username, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser() {
  return request("/auth/me");
}

export function getSessions() {
  return request("/sessions");
}

export function getContracts() {
  return request("/contracts");
}

export function getSessionMessages(sessionId) {
  return request(`/sessions/${sessionId}/messages`);
}

export function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export function uploadContract(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/contracts/upload", {
    method: "POST",
    body: formData,
  });
}

export function deleteContract(contractId) {
  return request(`/contracts/${contractId}`, {
    method: "DELETE",
  });
}

export function getReviewSettings() {
  return request("/review-settings");
}

export function saveReviewSettings(reviewRules) {
  return request("/review-settings", {
    method: "PUT",
    body: JSON.stringify({
      review_rules: reviewRules || "",
    }),
  });
}

export function askContract(question, sessionId, topK = 5, contractId = null, reviewRules = "") {
  return request("/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      session_id: sessionId || null,
      contract_id: contractId || null,
      top_k: topK,
      review_rules: reviewRules || "",
    }),
  });
}

export async function askContractStream(question, sessionId, topK = 5, contractId = null, reviewRules = "", onEvent) {
  const headers = new Headers();
  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}/ask/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      question,
      session_id: sessionId || null,
      contract_id: contractId || null,
      top_k: topK,
      review_rules: reviewRules || "",
    }),
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    const detail = typeof data === "object" ? data.detail || JSON.stringify(data) : data;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Current browser does not support streaming responses.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalEvent = null;

  const dispatchBlock = (block) => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) {
      return;
    }

    const event = JSON.parse(data);
    onEvent?.(event);
    if (event.type === "error") {
      throw new Error(event.message || "Stream request failed.");
    }
    if (event.type === "done") {
      finalEvent = event;
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";
    blocks.forEach(dispatchBlock);
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    dispatchBlock(buffer);
  }

  return finalEvent;
}
