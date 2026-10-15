// Chatbot : widget flottant qui parle à la route Flask /api/chat
(function () {
    const box = document.getElementById("chat-box");
    const toggle = document.getElementById("chat-toggle");
    const closeBtn = document.getElementById("chat-close");
    const messages = document.getElementById("chat-messages");
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const chips = document.getElementById("chat-chips");
    let welcomed = false;

    function addMessage(text, who) {
        const div = document.createElement("div");
        div.className = "msg " + who;
        div.textContent = text;          // textContent : pas d'injection HTML
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    function addLinks(links) {
        if (!links || !links.length) return;
        const wrap = document.createElement("div");
        wrap.className = "msg-links";
        links.forEach(l => {
            const a = document.createElement("a");
            a.textContent = l.label;
            a.href = l.url;
            if (/^(https?:|mailto:)/.test(l.url)) { a.target = "_blank"; a.rel = "noopener"; }
            wrap.appendChild(a);
        });
        messages.appendChild(wrap);
        messages.scrollTop = messages.scrollHeight;
    }

    async function send(text) {
        text = text.trim();
        if (!text) return;
        addMessage(text, "user");
        const typing = addMessage("…", "bot");
        try {
            const r = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
            });
            const data = await r.json();
            typing.textContent = data.reply;
            addLinks(data.links);
        } catch (e) {
            typing.textContent = "Erreur de connexion au serveur";
        }
    }

    function open() {
        box.hidden = false;
        if (!welcomed) {
            addMessage("Salam / Bonjour ! Je réponds à tes questions sur les offres et les entreprises IA de Marrakech, en Darija ou en français.", "bot");
            welcomed = true;
        }
        input.focus();
    }

    toggle.addEventListener("click", () => (box.hidden ? open() : (box.hidden = true)));
    closeBtn.addEventListener("click", () => (box.hidden = true));
    form.addEventListener("submit", e => { e.preventDefault(); const t = input.value; input.value = ""; send(t); });
    chips.querySelectorAll("button").forEach(b => b.addEventListener("click", () => send(b.textContent)));
})();
