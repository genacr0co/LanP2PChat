let username = "";
let myNodeId = null;

let currentRoomId = "general";
let currentDirectChatId = null;
let activeTab = "group";

const onlineList = document.getElementById("onlineList");

const rendered = new Set();
const notified = new Set();

const rooms = new Map();
const directChats = new Map();

// Черновики сообщений по чатам
const messageDrafts = new Map();

// Mute чатов:
// group:<room_id>
// dm:<chat_id>
const mutedChats = new Set();

const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("messageInput");
const statusEl = document.getElementById("status");
const roomTitle = document.getElementById("roomTitle");

const roomsList = document.getElementById("roomsList");
const createRoomBtn = document.getElementById("createRoomBtn");

const groupsTab = document.getElementById("groupsTab");
const dmTab = document.getElementById("dmTab");

const nameModal = document.getElementById("nameModal");
const nameInput = document.getElementById("nameInput");
const saveNameBtn = document.getElementById("saveNameBtn");

const roomModal = document.getElementById("roomModal");
const roomNameInput = document.getElementById("roomNameInput");
const saveRoomBtn = document.getElementById("saveRoomBtn");
const cancelRoomBtn = document.getElementById("cancelRoomBtn");

const emojiBtn = document.getElementById("emojiBtn");
const emojiPicker = document.getElementById("emojiPicker");

const notifySound = document.getElementById("notifySound");

let emojiCodes = [];