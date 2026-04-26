let username = "";
let currentRoomId = "general";
let currentDirectChatId = null;
let activeTab = "group";

const onlineList = document.getElementById("onlineList");

const rendered = new Set();
const notified = new Set();

const rooms = new Map();
const directChats = new Map();

const unlockedRooms = new Set(["general"]);
const unreadCounts = new Map();
const directUnreadCounts = new Map();

const typingUsers = new Map();
let typingTimer = null;
let lastTypingSentAt = 0;

const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("messageInput");
const statusEl = document.getElementById("status");
const typingStatus = document.getElementById("typingStatus");
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
const roomUniqueInput = document.getElementById("roomUniqueInput");
const roomPasswordInput = document.getElementById("roomPasswordInput");
const saveRoomBtn = document.getElementById("saveRoomBtn");
const cancelRoomBtn = document.getElementById("cancelRoomBtn");

const groupSearchPanel = document.getElementById("groupSearchPanel");
const groupSearchInput = document.getElementById("groupSearchInput");
const groupSearchBtn = document.getElementById("groupSearchBtn");
const groupSearchStatus = document.getElementById("groupSearchStatus");
const groupSearchResults = document.getElementById("groupSearchResults");

let currentGroupSearchId = null;
let groupSearchTimer = null;

const emojiBtn = document.getElementById("emojiBtn");
const emojiPicker = document.getElementById("emojiPicker");

let emojiCodes = [];