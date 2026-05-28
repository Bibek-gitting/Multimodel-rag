console.log("JS loaded");

const API_BASE = "http://127.0.0.1:8000";
const messagesDiv = document.querySelector(".chat-main");
// const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("new-chat");
const fileInput = document.getElementById("doc");
const imgInput = document.getElementById("img");
const audInput = document.getElementById("aud");

let chats = [];
let activeChatId = null;
let pendingUploadMessages = [];
var flag = false;

function makeId() {
  return typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

function loadingIcon() {
  const loadingDiv = document.createElement("div");
  const chat = document.querySelector(".messages");
  loadingDiv.className = "loading";
  loadingDiv.innerHTML = `<div class="spinner-border text-primary" role="status">
      <span class="sr-only"></span>
      </div>`;
  chat.appendChild(loadingDiv);
  chat.scrollTop = chat.scrollHeight;
  chat.style.overflowY = "scroll";

  return loadingDiv;
}

function createNewChat() {
  const newChat = {
    id: makeId(),
    title: "New Chat",
    messages: [...pendingUploadMessages],
  };
  pendingUploadMessages = [];
  activeChatId = newChat.id;
  chats.push(newChat);
  // renderChatList();
  // renderMessages();
  // messageInput.focus();

  messagesDiv.querySelector(".messages-header").innerHTML =
    "<p style='font-weight: bold; margin-left: 10px;'>New Chat</p>";
  const messagesContainer = messagesDiv.querySelector(".messages-container");
  messagesContainer.innerHTML = "";
  Object.assign(messagesContainer.style, {
    height: "calc(100% - 71.2px)",
    display: "flex",
    padding: "0px",
    flexDirection: "column",
  });

  const messages = document.createElement("div");
  messages.className = "messages";
  messagesContainer.appendChild(messages);
  const inputarea = document.createElement("div");
  inputarea.className = "inputarea";
  messagesContainer.appendChild(inputarea);
  // }
  Object.assign(messages.style, {
    height: "calc(100% - 80px)",
    backgroundColor: "#716f6f",
  });
  Object.assign(inputarea.style, {
    backgroundColor: "#ffffff",
    height: "80px",
    marginBottom: "0px",
    display: "flex",
    gap: "15px",
    alignItems: "center",
  });
  messages.innerHTML =
    "<p style='display: flex; align-items: center; justify-content: center; height: 100%;'><i>Start the conversation by asking a question.</i></p>";

  const typebox = document.createElement("input");
  typebox.id = "typebox";
  typebox.placeholder = "Type your message here...";
  typebox.classList.add("typebox");
  inputarea.appendChild(typebox);

  const sendbtn = document.createElement("button");
  sendbtn.id = "sendBtn";
  sendbtn.innerHTML = "<i class='bi bi-send-fill'></i>";
  sendbtn.classList.add("sendBtn");
  inputarea.appendChild(sendbtn);
  sendbtn.disabled = true;

  const speakbtn = document.createElement("button");
  speakbtn.id = "speakBtn";
  speakbtn.innerHTML = "<i class='bi bi-mic'></i>";
  speakbtn.disabled = true;
  speakbtn.title = "Speech to text is currently unavailable.";
  speakbtn.classList.add("speakBtn");
  inputarea.appendChild(speakbtn);

  sendbtn.addEventListener("click", () => {
    sendMessage();
    sendbtn.disabled = true;
  });
  typebox.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendbtn.disabled = true;
      sendMessage();
    }
  });

  inputarea.style.alignItems = "center";
  typebox.addEventListener("input", () => {
    sendbtn.disabled = typebox.value.trim() === "";
  });
  // chats.push(newChat);
  renderMessages();
  renderChatList();
}

function renderMessages() {
  const activeChat = chats.find((chat) => chat.id === activeChatId);
  if (!activeChat) {
    return;
  }

  // messagesDiv.innerHTML = "";
  const chat = document.querySelector(".messages");
  chat.innerHTML = "";

  activeChat.messages.forEach((msg) => {
    const msgDiv = document.createElement("div");
    Object.assign(msgDiv.style, {
      padding: "10px",
      margin: "10px",
      borderRadius: "5px",
      textAlign: "left",
      maxWidth: "fit-content",
    });
    msgDiv.className = `message ${msg.type}`;
    const p = document.createElement("p");
    p.style.margin = "2px";
    p.textContent = msg.content;
    msgDiv.appendChild(p);
    chat.appendChild(msgDiv);
  });
  chat.scrollTop = chat.scrollHeight;
  chat.style.overflowY = "scroll";
}

function renderChatList() {
  const chatList = document.querySelector(".chat-list");
  chatList.innerHTML = "";
  chats.forEach((chat) => {
    const item = document.createElement("div");
    item.className = "chat-list-item";
    item.style.cssText = `
            display: flex; align-items: center;
            justify-content: space-between;
            padding: 8px 10px; cursor: pointer;
            border-radius: 5px; margin-bottom: 4px;
        `;
    if (chat.id === activeChatId) item.style.backgroundColor = "#3a3a3a";

    const title = document.createElement("span");
    title.textContent = chat.title;
    title.style.cssText =
      "flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
    title.addEventListener("click", () => {
      activeChatId = chat.id;
      renderMessages();
      renderChatList(); // re-render to update active highlight
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.innerHTML = "<i class='bi bi-trash-fill'></i>";
    deleteBtn.style.cssText = `
            background: none; border: none;
            color: #aaa; cursor: pointer;
            padding: 2px 5px; flex-shrink: 0;
        `;
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      chats = chats.filter((c) => c.id !== chat.id);
      if (activeChatId === chat.id) {
        activeChatId = chats.length > 0 ? chats[chats.length - 1].id : null;
        if (activeChatId == null) {
          const messagesContainer = messagesDiv.querySelector(
            ".messages-container",
          );
          messagesContainer.innerHTML =
            "<span><b>Select a chat or create a new one to start messaging.</b></span>";
          document.querySelector(".messages-header").innerHTML =
            "<p><i>Select or start a chat.</i></p>";
        }
      }
      renderChatList();
      renderMessages();
    });

    item.appendChild(title);
    item.appendChild(deleteBtn);
    chatList.appendChild(item);
  });
}

async function sendMessage() {
  if (!activeChatId) return;

  const question = document.getElementById("typebox").value.trim();
  if (!question) return;

  const activeChat = chats.find((chat) => chat.id === activeChatId);
  if (!activeChat) return;

  activeChat.messages.push({
    id: makeId(),
    type: "user",
    content: question,
  });
  if (activeChat.title === "New Chat") {
    activeChat.title =
      question.length > 20 ? question.slice(0, 20) + "..." : question;
    renderChatList();
  }
  document.getElementById("typebox").value = "";
  renderMessages();

  const loader = loadingIcon();

  if (!flag) {
    console.log("hi");
    await new Promise((r) => setTimeout(r, 500));
    loader.remove();
    activeChat.messages.push({
      id: makeId(),
      type: "bot",
      content: "Please upload a file before asking questions.",
    });
    renderMessages();
    return;
  }

  const userMessage = {
    id: makeId(),
    type: "user",
    content: question,
  };

  try {
    const response = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: question }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    loader.remove();
    const botMessage = {
      id: makeId(),
      type: "bot",
      content: data.answer || data.response || JSON.stringify(data),
    };

    activeChat.messages.push(botMessage);
  } catch (error) {
    loader.remove();
    const errorMessage = {
      id: makeId(),
      type: "bot",
      content: `Error: ${error.message || "Failed to get response. Please try again."}`,
    };

    activeChat.messages.push(errorMessage);
  }
  renderMessages();
}

async function fileUploadHandler(e) {
  e.preventDefault();
  const file = e.target.files[0];
  if (!file) return;
  console.log("hi");
  // Show uploading message
  // const uploadingMessage = {
  //   id: makeId(),
  //   type: "user",
  //   content: `Uploading ${file.name}...`,
  // };
  console.log("Uploading file:", file.name);
  const activeChat = chats.find((chat) => chat.id === activeChatId);
  let loader;
  const uploadAlertPass = document.createElement("div");
  uploadAlertPass.innerHTML = `Uploading the file <strong>${file.name}</strong>. Give it a click if you like to view it.`;
  uploadAlertPass.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    max-width: 350px;
    background: #d1e7dd;
    color: #0f5132;
    border: 1px solid #badbcc;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    font-family: Arial, sans-serif;
    line-height: 1.4;
  `;
  document.body.appendChild(uploadAlertPass);
  try {
    if (activeChat) {
      loader = loadingIcon();
    }
    await uploadFile(file);
    if (loader) {
      loader.remove();
    }
    uploadAlertPass.remove();
    fileLink_with_remove(".upload." + e.target.id);

    const successMessage = {
      id: makeId(),
      type: "bot",
      content: `✅ ${file.name} uploaded successfully! You can now ask questions about it.`,
    };
    console.log("Upload successful:", file.name);

    if (activeChat) {
      activeChat.messages.push(successMessage);
      renderMessages();
    } else {
      pendingUploadMessages.push(successMessage);
    }
  } catch (error) {
    // Replace uploading message with error
    uploadAlertPass.remove();
    const uploadAlertFail = document.createElement("div");
    uploadAlertFail.innerHTML = `<strong>Failed!</strong> to upload ${file.name}. Please try again.`;
    uploadAlertFail.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 350px;
      background: #f8d7da;
      color: #842029;
      border: 1px solid #f5c2c7;
      border-radius: 8px;
      padding: 12px 16px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.12);
      font-family: Arial, sans-serif;
      line-height: 1.4;
    `;
    document.body.appendChild(uploadAlertFail);
    setTimeout(() => uploadAlertFail.remove(), 4000);
    console.error("Upload failed:", error);
  }
  e.target.value = ""; // Reset file input
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    alert(`Failed to upload. Please try again.`);
    console.error("Upload failed:", error);
    throw error;
  }
}
async function fetchUploadedFile() {
  try {
    const response = await fetch(`${API_BASE}/uploaded_file`, {
      method: "GET",
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch uploaded files:", error);
    throw error;
  }
}

async function fileLink_with_remove(location) {
  const fileLink = document.createElement("a");
  const fileBtn = document.querySelector(location);
  try {
    const data = await fetchUploadedFile();
    fileLink.href = `${API_BASE}/files/${data.file}`;
  } catch (error) {
    console.error("Error fetching uploaded files:", error);
  }
  fileLink.className = "fileLink";
  fileLink.textContent = "Uploaded";
  fileLink.target = "_blank";
  fileBtn.appendChild(fileLink);

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "deleteBtn";
  deleteBtn.innerHTML = '<i class="bi bi-trash-fill"></i>';
  deleteBtn.style.display = "inline-flex";
  fileBtn.appendChild(deleteBtn);
  flag = true;

  deleteBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/delete_file`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Delete failed: ${response.status} ${errorText}`);
      }
      document.querySelectorAll(".fileLink").forEach((link) => link.remove());
      document.querySelectorAll(".deleteBtn").forEach((btn) => btn.remove());
      flag = false;
    } catch (error) {
      console.error("Error deleting file:", error);
    }
  });
}

async function handleInputChange(e) {
  if (flag) {
    await fetch(`${API_BASE}/delete_file`, {
      method: "DELETE",
    });
    document.querySelectorAll(".fileLink").forEach((link) => link.remove());
    document.querySelectorAll(".deleteBtn").forEach((btn) => btn.remove());
    flag = false;
  }
  await fileUploadHandler(e);
}

fileInput.addEventListener("change", handleInputChange);

imgInput.addEventListener("change", handleInputChange);

audInput.addEventListener("change", handleInputChange);

newChatBtn.addEventListener("click", createNewChat);

// Initialize with a new chat
// createNewChat();
