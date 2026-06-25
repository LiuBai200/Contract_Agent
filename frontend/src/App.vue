<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  FileText,
  LogIn,
  LogOut,
  MessageSquare,
  Plus,
  RefreshCcw,
  Send,
  Trash2,
  UploadCloud,
  UserPlus,
} from "lucide-vue-next";
import {
  askContractStream,
  clearToken,
  deleteContract,
  deleteSession,
  getContracts,
  getCurrentUser,
  getReviewSettings,
  getSessionMessages,
  getSessions,
  getToken,
  login,
  register,
  saveReviewSettings,
  setToken,
  uploadContract,
} from "./api/client";

const user = ref(null);
const authMode = ref("login");
const username = ref("");
const password = ref("");
const authLoading = ref(false);
const sessions = ref([]);
const contracts = ref([]);
const activeContractId = ref(null);
const activeSessionId = ref(null);
const messages = ref([]);
const citations = ref([]);
const question = ref("");
const topK = ref(5);
const reviewRules = ref("");
const reviewRulesSaving = ref(false);
const file = ref(null);
const uploadResult = ref(null);
const busy = ref(false);
const error = ref("");
const notice = ref("");
let noticeTimer = null;

const isAuthed = computed(() => Boolean(user.value));
const activeContract = computed(() => {
  return contracts.value.find((item) => item.id === activeContractId.value) || null;
});
const activeSessionTitle = computed(() => {
  const session = sessions.value.find((item) => item.id === activeSessionId.value);
  return session?.title || "新会话";
});

watch(notice, (value) => {
  if (noticeTimer) {
    window.clearTimeout(noticeTimer);
    noticeTimer = null;
  }
  if (value) {
    noticeTimer = window.setTimeout(() => {
      notice.value = "";
      noticeTimer = null;
    }, 3000);
  }
});

onMounted(async () => {
  if (!getToken()) {
    return;
  }
  try {
    user.value = await getCurrentUser();
    await refreshData();
  } catch {
    clearToken();
  }
});

onBeforeUnmount(() => {
  if (noticeTimer) {
    window.clearTimeout(noticeTimer);
  }
});

async function submitAuth() {
  error.value = "";
  authLoading.value = true;
  try {
    const response = authMode.value === "login"
      ? await login(username.value, password.value)
      : await register(username.value, password.value);
    setToken(response.access_token);
    user.value = response.user;
    await refreshData();
  } catch (err) {
    error.value = err.message;
  } finally {
    authLoading.value = false;
  }
}

async function loadSessions() {
  sessions.value = await getSessions();
}

async function loadContracts() {
  contracts.value = await getContracts();
  if (!contracts.value.length) {
    activeContractId.value = null;
    return;
  }
  const exists = contracts.value.some((contract) => contract.id === activeContractId.value);
  if (!exists) {
    activeContractId.value = contracts.value[0].id;
  }
}

async function loadReviewSettings() {
  const settings = await getReviewSettings();
  reviewRules.value = settings.review_rules || "";
}

async function refreshData() {
  await Promise.all([loadSessions(), loadContracts(), loadReviewSettings()]);
}

async function selectSession(session) {
  error.value = "";
  activeSessionId.value = session.id;
  citations.value = [];
  try {
    messages.value = await getSessionMessages(session.id);
    syncCitationsFromMessages();
  } catch (err) {
    error.value = err.message;
  }
}

async function handleDeleteSession(session) {
  const title = session.title || "该会话";
  const confirmed = window.confirm(`确定删除聊天记录 "${title}" 吗？删除后无法恢复。`);
  if (!confirmed) {
    return;
  }

  error.value = "";
  notice.value = "";
  busy.value = true;
  try {
    const response = await deleteSession(session.id);
    notice.value = response.message || "聊天记录已删除";
    if (activeSessionId.value === session.id) {
      startNewChat();
    }
    await loadSessions();
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

function startNewChat() {
  activeSessionId.value = null;
  messages.value = [];
  citations.value = [];
  question.value = "";
}

function handleFileChange(event) {
  file.value = event.target.files?.[0] || null;
}

async function submitUpload() {
  if (!file.value) {
    error.value = "请选择文件";
    return;
  }
  error.value = "";
  notice.value = "";
  busy.value = true;
  try {
    uploadResult.value = await uploadContract(file.value);
    notice.value = uploadResult.value.message;
    await loadContracts();
    activeContractId.value = uploadResult.value.contract_id;
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function submitReviewRules() {
  error.value = "";
  notice.value = "";
  reviewRulesSaving.value = true;
  try {
    const response = await saveReviewSettings(reviewRules.value);
    reviewRules.value = response.review_rules || "";
    notice.value = "审查规则已保存";
  } catch (err) {
    error.value = err.message;
  } finally {
    reviewRulesSaving.value = false;
  }
}

async function submitQuestion() {
  const text = question.value.trim();
  if (!text) {
    return;
  }
  error.value = "";
  notice.value = "";
  busy.value = true;
  messages.value.push({ role: "user", content: text });
  const assistantIndex = messages.value.length;
  messages.value.push({ role: "assistant", content: "", citations: [], thinking: [], streaming: true });
  question.value = "";

  const updateAssistant = (patch) => {
    messages.value[assistantIndex] = {
      ...messages.value[assistantIndex],
      ...patch,
    };
  };
  const appendThinking = (content) => {
    if (!content) {
      return;
    }
    const current = messages.value[assistantIndex];
    updateAssistant({ thinking: [...(current.thinking || []), content] });
  };
  const appendAnswer = (content) => {
    if (!content) {
      return;
    }
    const current = messages.value[assistantIndex];
    updateAssistant({ content: `${current.content || ""}${content}` });
  };
  const setAssistantCitations = (items) => {
    const nextCitations = items || [];
    citations.value = nextCitations;
    updateAssistant({ citations: nextCitations });
  };

  try {
    await askContractStream(text, activeSessionId.value, topK.value, activeContractId.value, reviewRules.value, (event) => {
      if (event.type === "session") {
        activeSessionId.value = event.session_id || activeSessionId.value;
      } else if (event.type === "thinking") {
        appendThinking(event.content);
      } else if (event.type === "citations") {
        setAssistantCitations(event.citations);
      } else if (event.type === "answer_delta") {
        appendAnswer(event.content);
      } else if (event.type === "done") {
        activeSessionId.value = event.session_id || activeSessionId.value;
        setAssistantCitations(event.citations);
        updateAssistant({
          content: event.answer || messages.value[assistantIndex].content,
          streaming: false,
        });
      }
    });
    updateAssistant({ streaming: false });
    await loadSessions();
  } catch (err) {
    updateAssistant({ streaming: false });
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

function logout() {
  clearToken();
  user.value = null;
  sessions.value = [];
  contracts.value = [];
  activeContractId.value = null;
  messages.value = [];
  citations.value = [];
  reviewRules.value = "";
  activeSessionId.value = null;
}

function selectContract(contract) {
  activeContractId.value = contract.id;
  citations.value = [];
}

async function handleDeleteContract(contract) {
  const confirmed = window.confirm(`确定删除合同 "${contract.filename}" 吗？删除后会从知识库中移除，无法恢复。`);
  if (!confirmed) {
    return;
  }

  error.value = "";
  notice.value = "";
  busy.value = true;
  try {
    const response = await deleteContract(contract.id);
    notice.value = response.message || "合同已删除";
    if (activeContractId.value === contract.id) {
      activeContractId.value = null;
      citations.value = [];
    }
    await loadContracts();
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

function syncCitationsFromMessages() {
  const latest = [...messages.value]
    .reverse()
    .find((message) => message.role === "assistant" && message.citations?.length);
  citations.value = latest?.citations || [];
}
</script>

<template>
  <main v-if="!isAuthed" class="auth-shell">
    <section class="auth-panel">
      <div class="brand">
        <FileText :size="28" />
        <div>
          <h1>Contract RAG Agent</h1>
          <p>合同审查工作台</p>
        </div>
      </div>

      <form class="auth-form" @submit.prevent="submitAuth">
        <label>
          <span>用户名</span>
          <input v-model="username" autocomplete="username" />
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" autocomplete="current-password" />
        </label>
        <button class="primary-button" type="submit" :disabled="authLoading">
          <LogIn v-if="authMode === 'login'" :size="18" />
          <UserPlus v-else :size="18" />
          {{ authMode === "login" ? "登录" : "注册" }}
        </button>
      </form>

      <button class="text-button" type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'">
        {{ authMode === "login" ? "创建账号" : "使用已有账号" }}
      </button>

      <p v-if="error" class="error-text">{{ error }}</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="mini-brand">
          <FileText :size="22" />
          <span>Contract Agent</span>
        </div>
        <button class="icon-button" title="新会话" type="button" @click="startNewChat">
          <Plus :size="18" />
        </button>
      </div>

      <button class="new-chat" type="button" @click="startNewChat">
        <MessageSquare :size="18" />
        新会话
      </button>

      <nav class="session-list">
        <article
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === activeSessionId }"
        >
          <button class="session-select" type="button" @click="selectSession(session)">
            <MessageSquare :size="16" />
          <span>{{ session.title || "未命名会话" }}</span>
          </button>
          <button
            class="session-delete"
            type="button"
            title="删除聊天记录"
            :disabled="busy"
            @click="handleDeleteSession(session)"
          >
            <Trash2 :size="15" />
          </button>
        </article>
      </nav>

      <div class="sidebar-bottom">
        <span>{{ user.username }}</span>
        <button class="icon-button" title="退出登录" type="button" @click="logout">
          <LogOut :size="18" />
        </button>
      </div>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <h2>{{ activeSessionTitle }}</h2>
          <p>RAG 合同审查</p>
        </div>
        <button class="ghost-button" type="button" @click="refreshData">
          <RefreshCcw :size="17" />
          刷新
        </button>
      </header>

      <div class="content-grid">
        <section class="chat-column">
          <div class="messages">
            <div v-if="messages.length === 0" class="empty-state">
              <FileText :size="34" />
              <span>上传合同后开始提问</span>
            </div>

            <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
              <div class="avatar">{{ message.role === "user" ? "你" : "AI" }}</div>
              <div class="bubble">
                <div v-if="message.thinking?.length" class="thinking-box">
                  <div class="thinking-title">思考过程</div>
                  <ul>
                    <li v-for="(step, stepIndex) in message.thinking" :key="stepIndex">{{ step }}</li>
                  </ul>
                </div>
                <div v-if="message.content" class="answer-text">{{ message.content }}</div>
                <div v-else-if="message.streaming" class="stream-placeholder">正在生成回答...</div>
              </div>
            </article>
          </div>

          <form class="composer" @submit.prevent="submitQuestion">
            <input v-model="question" placeholder="输入合同审查问题" />
            <select v-model.number="topK" title="检索数量">
              <option v-for="count in 10" :key="count" :value="count">top {{ count }}</option>
            </select>
            <button class="send-button" type="submit" :disabled="busy || !question.trim()">
              <Send :size="18" />
            </button>
          </form>
        </section>

        <aside class="side-panel">
          <section class="panel-block review-rules">
            <h3>自定义审查规则</h3>
            <textarea
              v-model="reviewRules"
              placeholder="例如：站在乙方视角审查；不接受无限责任；付款周期超过 30 天需提示高风险；甲方单方解除权需要增加通知期。"
              rows="6"
            ></textarea>
            <button
              class="primary-button full"
              type="button"
              :disabled="reviewRulesSaving"
              @click="submitReviewRules"
            >
              保存审查规则
            </button>
          </section>

          <section class="panel-block">
            <h3>合同文件</h3>
            <label class="file-picker">
              <UploadCloud :size="20" />
              <span>{{ file?.name || "选择文件" }}</span>
              <input type="file" accept=".pdf,.docx,.pptx,.txt,.md" @change="handleFileChange" />
            </label>
            <button class="primary-button full" type="button" :disabled="busy || !file" @click="submitUpload">
              <UploadCloud :size="18" />
              上传入库
            </button>
            <div v-if="uploadResult" class="upload-stats">
              <span>Document {{ uploadResult.document_count }}</span>
              <span>Chunk {{ uploadResult.chunk_count }}</span>
              <span>Stored {{ uploadResult.stored_count }}</span>
            </div>
            <div v-if="activeContract" class="selected-contract">
              当前检索：{{ activeContract.filename }}
            </div>
            <div class="contract-list">
              <div v-if="contracts.length === 0" class="muted">暂无合同</div>
              <article
                v-for="contract in contracts"
                :key="contract.id"
                class="contract-item"
                :class="{ active: contract.id === activeContractId }"
              >
                <button class="contract-select" type="button" @click="selectContract(contract)">
                  <FileText :size="17" />
                <div>
                  <strong>{{ contract.filename }}</strong>
                  <span>Document {{ contract.document_count }} · Chunk {{ contract.chunk_count }}</span>
                </div>
                </button>
                <button
                  class="contract-delete"
                  type="button"
                  title="删除合同"
                  :disabled="busy"
                  @click="handleDeleteContract(contract)"
                >
                  <Trash2 :size="16" />
                </button>
              </article>
            </div>
          </section>

          <section class="panel-block citations">
            <h3>引用来源</h3>
            <div v-if="citations.length === 0" class="muted">暂无引用</div>
            <article v-for="(item, index) in citations" :key="index" class="citation-item">
              <div class="citation-title">
                <span>[{{ index + 1 }}]</span>
                <strong>{{ item.clause_title || item.filename || "合同片段" }}</strong>
              </div>
              <p>{{ item.content }}</p>
              <div class="citation-meta">
                <span>{{ item.filename }}</span>
                <span v-if="item.page">P{{ item.page }}</span>
                <span v-if="item.paragraph">段{{ item.paragraph }}</span>
                <span v-if="item.slide">Slide {{ item.slide }}</span>
                <span v-if="item.score">score {{ item.score }}</span>
              </div>
            </article>
          </section>
        </aside>
      </div>

      <div v-if="error" class="toast error">{{ error }}</div>
      <div v-else-if="notice" class="toast">{{ notice }}</div>
    </section>
  </main>
</template>
