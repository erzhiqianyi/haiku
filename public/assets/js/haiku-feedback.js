(function () {
    "use strict";

    const form = document.querySelector("[data-feedback-form]");
    if (!form) {
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    const status = form.querySelector("[data-feedback-status]");
    const message = form.querySelector("textarea[name='message']");
    const count = form.querySelector("[data-feedback-count]");

    function setStatus(text, state) {
        status.textContent = text;
        status.dataset.state = state || "";
    }

    function updateCount() {
        count.textContent = `${message.value.length} / ${message.maxLength}`;
    }

    message.addEventListener("input", updateCount);
    updateCount();

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (submitButton.disabled) {
            return;
        }

        const formData = new FormData(form);
        const turnstileToken = formData.get("cf-turnstile-response");
        if (!turnstileToken) {
            setStatus("確認が終わるまで、少しお待ちください。", "error");
            return;
        }

        submitButton.disabled = true;
        submitButton.dataset.label = submitButton.textContent;
        submitButton.textContent = "送信中…";
        form.setAttribute("aria-busy", "true");
        setStatus("作者へ届けています。", "progress");

        const payload = Object.fromEntries(formData.entries());
        payload.turnstileToken = turnstileToken;

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify(payload),
            });
            const result = await response.json().catch(function () {
                return {};
            });

            if (!response.ok || !result.ok) {
                throw new Error(result.message || "送信できませんでした。時間をおいてお試しください。");
            }

            form.reset();
            updateCount();
            setStatus(result.message, "success");
        } catch (error) {
            setStatus(error.message || "送信できませんでした。時間をおいてお試しください。", "error");
        } finally {
            if (window.turnstile) {
                window.turnstile.reset();
            }
            submitButton.disabled = false;
            submitButton.textContent = submitButton.dataset.label || "作者へ送る";
            form.removeAttribute("aria-busy");
        }
    });
})();
