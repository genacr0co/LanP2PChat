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

const messageDrafts = new Map();

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

const profileAvatar = document.getElementById("profileAvatar");
const profileName = document.getElementById("profileName");
const editNameBtn = document.getElementById("editNameBtn");

const nameModal = document.getElementById("nameModal");
const nameModalTitle = document.getElementById("nameModalTitle");
const nameInput = document.getElementById("nameInput");
const saveNameBtn = document.getElementById("saveNameBtn");
const cancelNameBtn = document.getElementById("cancelNameBtn");

const roomModal = document.getElementById("roomModal");
const roomNameInput = document.getElementById("roomNameInput");
const roomPasswordInput = document.getElementById("roomPasswordInput");
const saveRoomBtn = document.getElementById("saveRoomBtn");
const cancelRoomBtn = document.getElementById("cancelRoomBtn");

const joinGroupModal = document.getElementById("joinGroupModal");
const joinGroupModalTitle = document.getElementById("joinGroupModalTitle");
const joinGroupModalText = document.getElementById("joinGroupModalText");
const joinGroupModalPasswordInput = document.getElementById("joinGroupModalPasswordInput");
const joinGroupModalError = document.getElementById("joinGroupModalError");
const joinGroupModalSaveBtn = document.getElementById("joinGroupModalSaveBtn");
const joinGroupModalCancelBtn = document.getElementById("joinGroupModalCancelBtn");
let pendingJoinRoomId = null;

const groupSettingsBtn = document.getElementById("groupSettingsBtn");
const groupSettingsModal = document.getElementById("groupSettingsModal");
const closeGroupSettingsBtn = document.getElementById("closeGroupSettingsBtn");
const groupSettingsTitle = document.getElementById("groupSettingsTitle");

const groupMuteBtn = document.getElementById("groupMuteBtn");
const groupLeaveBtn = document.getElementById("groupLeaveBtn");

const groupRenameBtn = document.getElementById("groupRenameBtn");

const groupPasswordBtn = document.getElementById("groupPasswordBtn");
const groupPasswordForm = document.getElementById("groupPasswordForm");
const groupPasswordInput = document.getElementById("groupPasswordInput");
const saveGroupPasswordBtn = document.getElementById("saveGroupPasswordBtn");
const cancelGroupPasswordBtn = document.getElementById("cancelGroupPasswordBtn");
const groupPasswordHint = document.getElementById("groupPasswordHint");
const groupRenameForm = document.getElementById("groupRenameForm");
const groupRenameInput = document.getElementById("groupRenameInput");
const saveGroupRenameBtn = document.getElementById("saveGroupRenameBtn");
const cancelGroupRenameBtn = document.getElementById("cancelGroupRenameBtn");

const groupDeleteBtn = document.getElementById("groupDeleteBtn");
const groupMembersList = document.getElementById("groupMembersList");

const directSettingsModal = document.getElementById("directSettingsModal");
const closeDirectSettingsBtn = document.getElementById("closeDirectSettingsBtn");
const directSettingsTitle = document.getElementById("directSettingsTitle");
const directMuteBtn = document.getElementById("directMuteBtn");
const directDeleteBtn = document.getElementById("directDeleteBtn");
const directInfoBox = document.getElementById("directInfoBox");

const emojiBtn = document.getElementById("emojiBtn");
const emojiPicker = document.getElementById("emojiPicker");

const notifySound = document.getElementById("notifySound");

let emojiCodes = [];