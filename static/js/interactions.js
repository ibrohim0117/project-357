// Server JSON qaytarmasa (masalan, sessiya tugab login sahifasiga yo'naltirsa) xato tashlaymiz,
// shunda chaqiruvchi forma oddiy usulda yuboriladi
async function sendForm(form, url) {
    const response = await fetch(url, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });
    if (!(response.headers.get("Content-Type") || "").includes("application/json")) {
        throw new Error(`Unexpected response: ${response.status}`);
    }
    return { ok: response.ok, data: await response.json() };
}

/* ---------- Likes ---------- */

function renderLike(post, form, liked, count) {
    const button = form.querySelector(".like-btn");
    button.setAttribute("aria-pressed", liked);
    button.setAttribute("aria-label", liked ? "Unlike" : "Like");
    form.action = liked ? form.dataset.unlikeUrl : form.dataset.likeUrl;

    post.querySelectorAll("[data-like-count]").forEach((el) => { el.textContent = count; });
    post.querySelectorAll("[data-like-plural]").forEach((el) => { el.textContent = count === 1 ? "" : "s"; });
}

function pop(element) {
    element.classList.remove("is-popping");
    void element.offsetWidth;
    element.classList.add("is-popping");
}

async function toggleLike(form, onlyLike = false) {
    if (form.dataset.busy) return;

    const post = form.closest("[data-post]");
    const button = form.querySelector(".like-btn");
    const wasLiked = button.getAttribute("aria-pressed") === "true";
    if (onlyLike && wasLiked) return;

    const oldCount = Number(post.querySelector("[data-like-count]")?.textContent || 0);
    const url = wasLiked ? form.dataset.unlikeUrl : form.dataset.likeUrl;

    form.dataset.busy = "1";
    renderLike(post, form, !wasLiked, Math.max(oldCount + (wasLiked ? -1 : 1), 0));
    if (!wasLiked) pop(button);

    try {
        const { ok, data } = await sendForm(form, url);
        if (!ok) throw new Error(data.error);
        renderLike(post, form, data.liked, data.like_count);
    } catch (error) {
        form.action = url;
        form.submit();
    } finally {
        delete form.dataset.busy;
    }
}

function showLikeBurst(media) {
    const burst = document.createElement("span");
    burst.className = "like-burst";
    burst.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-heart"/></svg>';
    burst.addEventListener("animationend", () => burst.remove());
    media.append(burst);
}

/* ---------- Comments ---------- */

function updateCommentCount(post, count) {
    post.querySelectorAll("[data-comment-count]").forEach((el) => { el.textContent = count; });

    const link = post.querySelector(".view-comments");
    const list = post.querySelector("[data-comment-list]");
    if (link && list) link.hidden = count <= list.children.length;
}

async function submitComment(form) {
    const input = form.querySelector(".comment-input");
    const button = form.querySelector(".comment-submit");
    if (!input.value.trim() || form.dataset.busy) return;

    const post = form.closest("[data-post]");
    form.dataset.busy = "1";
    button.disabled = true;

    try {
        const { ok, data } = await sendForm(form, form.action);
        if (!ok) {
            input.setCustomValidity(data.error || "Izoh yuborilmadi.");
            input.reportValidity();
            return;
        }

        const list = post.querySelector("[data-comment-list]");
        list.insertAdjacentHTML("beforeend", data.html);
        const comment = list.lastElementChild;
        comment.classList.add("is-new");
        comment.scrollIntoView({ block: "nearest", behavior: "smooth" });

        input.value = "";
        post.querySelector("[data-no-comments]")?.setAttribute("hidden", "");
        updateCommentCount(post, data.comment_count);
    } catch (error) {
        form.submit();
    } finally {
        delete form.dataset.busy;
        button.disabled = false;
    }
}

/* ---------- Events ---------- */

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (form.matches(".like-form")) {
        event.preventDefault();
        toggleLike(form);
    } else if (form.matches(".comment-form")) {
        event.preventDefault();
        submitComment(form);
    }
});

document.addEventListener("input", (event) => {
    if (event.target.matches(".comment-input")) event.target.setCustomValidity("");
});

let lastTap = { media: null, time: 0 };

document.addEventListener("click", (event) => {
    const focusTrigger = event.target.closest("[data-comment-focus]");
    const input = focusTrigger?.closest("[data-post]")?.querySelector(".comment-input");
    if (input) {
        event.preventDefault();
        input.focus();
        return;
    }

    // Videoda ikki marta bosish to'liq ekranga o'tkazadi, shuning uchun faqat rasmlarda ishlaydi
    const media = event.target.closest("[data-double-tap-like]");
    if (!media || event.target.tagName !== "IMG") return;

    const now = Date.now();
    if (lastTap.media === media && now - lastTap.time < 300) {
        lastTap = { media: null, time: 0 };
        showLikeBurst(media);
        const form = media.closest("[data-post]").querySelector(".like-form");
        if (form) toggleLike(form, true);
    } else {
        lastTap = { media, time: now };
    }
});

if (location.hash === "#comment") {
    document.querySelector(".comment-input")?.focus();
}
