document.querySelectorAll("[data-post]").forEach(function (post) {
    const track = post.querySelector(".media-track");
    if (!track || track.children.length < 2) return;

    const slides = [...track.children];
    const counter = post.querySelector(".media-counter");
    const prev = post.querySelector(".slide-btn.prev");
    const next = post.querySelector(".slide-btn.next");
    const dots = post.querySelectorAll(".media-dots span");

    function update() {
        const current = Math.round(track.scrollLeft / track.clientWidth);

        counter.textContent = `${current + 1} / ${slides.length}`;
        prev.hidden = current === 0;
        next.hidden = current === slides.length - 1;
        dots.forEach((dot, i) => dot.classList.toggle("active", i === current));

        // Boshqa slaydga o'tilganda video o'ynab qolmasin
        slides.forEach((slide, i) => {
            if (i !== current && slide.tagName === "VIDEO") slide.pause();
        });
    }

    track.addEventListener("scroll", update);
    prev.addEventListener("click", () => track.scrollBy({ left: -track.clientWidth }));
    next.addEventListener("click", () => track.scrollBy({ left: track.clientWidth }));
});
