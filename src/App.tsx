import React, {
  useState,
  useEffect,
  useRef,
  ChangeEvent,
  KeyboardEvent,
} from "react";
import {
  Mic,
  Send,
  FileText,
  Image as ImageIcon,
  AudioWaveform,
  Plus,
} from "lucide-react";

type MessageType = "user" | "bot";

interface Message {
  id: string;
  type: MessageType;
  content: string;
}

interface Chat {
  id: string;
  title: string;
  messages: Message[];
}

export default function App() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats, activeChatId]);

  const activeChat = chats.find((chat) => chat.id === activeChatId) || null;

  const createNewChat = () => {
    const newChat: Chat = {
      id: crypto.randomUUID(),
      title: "New Chat",
      messages: [],
    };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
    setInput("");
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeChatId) return;

    const newUserMessage: Message = {
      id: crypto.randomUUID(),
      type: "user",
      content: input.trim(),
    };

    setChats((prev) =>
      prev.map((chat) =>
        chat.id === activeChatId
          ? {
              ...chat,
              messages: [...chat.messages, newUserMessage],
              title:
                chat.title === "New Chat"
                  ? input.trim().slice(0, 20) + "..."
                  : chat.title,
            }
          : chat,
      ),
    );

    setInput("");
    setLoading(true);

    setTimeout(() => {
      const botReply: Message = {
        id: crypto.randomUUID(),
        type: "bot",
        content: `You asked: "${newUserMessage.content}". This is a mock reply from the assistant.`,
      };

      setChats((prev) =>
        prev.map((chat) =>
          chat.id === activeChatId
            ? { ...chat, messages: [...chat.messages, botReply] }
            : chat,
        ),
      );
      setLoading(false);
    }, 1000);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    formData.append("file", files[0]);

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("Server response:", data);
    } catch (err) {
      console.error("Upload failed:", err);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Top header */}
      <header className="w-full bg-gradient-to-r from-blue-800 to-blue-600 text-white shadow-md flex items-center px-6 py-4">
        <h1 className="text-3xl font-extrabold tracking-wide drop-shadow-md">
          Multimodal RAG Assistant
        </h1>
      </header>

      {/* Main layout: sidebar + chat */}
      <div className="flex flex-grow bg-gradient-to-tr from-blue-50 via-white to-blue-100">
        {/* Sidebar */}
        <aside className="w-64 bg-gradient-to-b from-blue-700 to-blue-900 text-white flex flex-col shadow-lg">
          <div className="p-5 border-b border-blue-800 flex items-center justify-between">
            <h2 className="font-bold text-xl tracking-wide">Chats</h2>
            <button
              onClick={createNewChat}
              className="p-1 rounded-md hover:bg-blue-600 transition-colors"
              title="New Chat"
              aria-label="New Chat"
            >
              <Plus className="w-6 h-6" />
            </button>
          </div>
          <nav className="flex-grow overflow-auto">
            {chats.length === 0 && (
              <p className="p-4 text-blue-200 text-sm italic">
                No chats yet. Start a new chat.
              </p>
            )}
            {chats.map((chat) => (
              <button
                key={chat.id}
                className={`w-full text-left px-4 py-3 border-l-4 transition-colors duration-150
                  ${
                    chat.id === activeChatId
                      ? "border-yellow-400 bg-yellow-50 text-blue-900 font-semibold shadow-inner"
                      : "border-transparent hover:bg-blue-800 hover:text-yellow-300"
                  }
                `}
                onClick={() => setActiveChatId(chat.id)}
              >
                {chat.title}
              </button>
            ))}
          </nav>
          <div className="p-4 border-t border-blue-800 space-y-2 bg-blue-800">
            <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 p-2 rounded-lg flex items-center space-x-2 transition-colors">
              <FileText className="w-5 h-5 text-yellow-300" />
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={handleFileUpload}
              />
              <span className="text-sm text-yellow-300 font-medium">Docs</span>
            </label>
            <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 p-2 rounded-lg flex items-center space-x-2 transition-colors">
              <ImageIcon className="w-5 h-5 text-yellow-300" />
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileUpload}
              />
              <span className=" text-sm text-yellow-300 font-medium">
                Images
              </span>
            </label>
            <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 p-2 rounded-lg flex items-center space-x-2 transition-colors">
              <AudioWaveform className="w-5 h-5 text-yellow-300" />
              <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={handleFileUpload}
              />
              <span className="text-sm text-yellow-300 font-medium">Audio</span>
            </label>
          </div>
        </aside>

        {/* Chat window */}
        <main className="flex flex-col flex-grow">
          {/* Chat header */}
          <header className="border-b border-blue-200 p-4 bg-white shadow-sm flex items-center justify-between">
            <h3 className="text-lg font-semibold text-blue-900">
              {activeChat ? activeChat.title : "Select or start a chat"}
            </h3>
          </header>
          {/* Messages container */}
          <div className="flex-grow overflow-auto p-6 bg-blue-50">
            {!activeChat && (
              <p className="text-blue-600 text-center mt-20 italic font-medium">
                Select a chat or create a new one to start messaging.
              </p>
            )}

            {activeChat && activeChat.messages.length === 0 && (
              <p className="text-blue-400 text-center mt-20 italic">
                No messages yet. Say hi!
              </p>
            )}

            {activeChat &&
              activeChat.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`max-w-xl mb-4 p-3 rounded-lg break-words
                    ${
                      msg.type === "user"
                        ? "bg-yellow-400 text-blue-900 self-end shadow-md"
                        : "bg-white text-blue-900 self-start shadow-sm"
                    }`}
                  style={{
                    alignSelf: msg.type === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  {msg.content}
                </div>
              ))}

            <div ref={messagesEndRef} />
          </div>

          {/* Input & send */}
          {activeChat && (
            <div className="p-4 bg-white border-t border-blue-200 flex items-center space-x-3 shadow-inner">
              <input
                type="text"
                placeholder="Type your message..."
                className="flex-grow border border-blue-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-yellow-400 outline-none"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />

              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="bg-yellow-400 text-blue-900 p-2 rounded-lg hover:bg-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>

              <button
                className="bg-blue-100 p-2 rounded-lg hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                disabled={loading}
              >
                <Mic className="w-5 h-5 text-blue-700" />
              </button>
            </div>
          )}

          {loading && (
            <div className="absolute bottom-20 right-10 bg-yellow-100 px-4 py-2 rounded shadow text-blue-900 text-sm font-semibold">
              Assistant is typing...
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
