const commandData = {
  run: {
    code: "lilo run claude --role reviewer",
    title: "Start a managed session.",
    copy:
      "The operator asks for work. Session mints the record, runtime launches the process, and the daemon keeps it visible.",
    output: "session 7f4a91d running\nrole reviewer\nworkspace ~/work/littleorgans",
  },
  get: {
    code: "lilo get session",
    title: "Inspect the live surface.",
    copy:
      "Session lists the operator view: roles, state, labels, and the short id needed for follow up commands.",
    output: "ID       ROLE       STATUS\n7f4a91d  reviewer   running\n91bc02a  general    waiting",
  },
  mail: {
    code: "lilo mail send 7f4a91d",
    title: "Leave durable instructions.",
    copy:
      "Mail is session scoped state. Nudge is just the wake cue. The body remains readable from the mailbox.",
    output: "message stored\nrecipient 7f4a91d\nnotify sent",
  },
  capture: {
    code: "lilo capture 7f4a91d",
    title: "Keep what happened.",
    copy:
      "Capture gives the operator evidence from the terminal surface while transport handles wire observation.",
    output: "captured pane output\nsaved under ~/.lilo\nlinked to session 7f4a91d",
  },
  doctor: {
    code: "lilo doctor",
    title: "Verify before done.",
    copy:
      "Health checks stay top level. The operator sees daemon, socket, database, and runtime readiness in one place.",
    output: "socket ok\ndatabase ok\nruntime ok\nlilod ready",
  },
};

const tabs = Array.from(document.querySelectorAll(".command-tab"));
const commandCode = document.querySelector("#command-code");
const commandTitle = document.querySelector("#command-title");
const commandCopy = document.querySelector("#command-copy");
const commandOutput = document.querySelector("#command-output");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const data = commandData[tab.dataset.command];
    tabs.forEach((button) => {
      button.setAttribute("aria-pressed", String(button === tab));
    });
    commandCode.textContent = data.code;
    commandTitle.textContent = data.title;
    commandCopy.textContent = data.copy;
    commandOutput.textContent = data.output;
  });
});

const copyButton = document.querySelector("[data-copy]");
const copyState = document.querySelector("#copy-state");

copyButton.addEventListener("click", async () => {
  const source = document.querySelector(`#${copyButton.dataset.copy}`);
  try {
    await navigator.clipboard.writeText(source.textContent.trim());
    copyState.textContent = "copied";
  } catch {
    copyState.textContent = "select manually";
  }
  window.setTimeout(() => {
    copyState.textContent = "ready";
  }, 1800);
});
