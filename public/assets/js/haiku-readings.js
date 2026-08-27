(() => {
    'use strict';

    const storageKey = 'haiku-readings-visible';
    const root = document.documentElement;
    const toggles = [...document.querySelectorAll('[data-readings-toggle]')];

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function toHiragana(value) {
        return String(value).replace(/[\u30a1-\u30f6]/g, character =>
            String.fromCharCode(character.charCodeAt(0) - 0x60)
        );
    }

    function literalReadingCandidates(value) {
        const normalized = toHiragana(value);
        const modernized = normalized.replace(/ひ/g, 'い').replace(/ふ/g, 'う');
        return modernized === normalized ? [normalized] : [normalized, modernized];
    }

    function formatCompactRuby(base, reading) {
        const chunks = String(base).match(/[\p{Script=Han}ヶ]+|[^\p{Script=Han}ヶ]+/gu) || [];
        const normalizedReading = toHiragana(reading);
        if (!chunks.some(chunk => /^[\p{Script=Han}ヶ]+$/u.test(chunk))) {
            return escapeHtml(base);
        }

        function renderChunks(index, readingIndex) {
            if (index === chunks.length) {
                return readingIndex === normalizedReading.length ? '' : null;
            }

            const chunk = chunks[index];
            if (!/^[\p{Script=Han}ヶ]+$/u.test(chunk)) {
                for (const expected of literalReadingCandidates(chunk)) {
                    if (!normalizedReading.startsWith(expected, readingIndex)) continue;
                    const rest = renderChunks(index + 1, readingIndex + expected.length);
                    if (rest !== null) return `${escapeHtml(chunk)}${rest}`;
                }
                return null;
            }

            for (let end = readingIndex + 1; end <= normalizedReading.length; end += 1) {
                const rest = renderChunks(index + 1, end);
                if (rest !== null) {
                    const rubyReading = String(reading).slice(readingIndex, end);
                    return `<ruby class="reading-ruby">${escapeHtml(chunk)}<rt>${escapeHtml(rubyReading)}</rt></ruby>${rest}`;
                }
            }
            return null;
        }

        return renderChunks(0, 0) ?? `<ruby class="reading-ruby">${escapeHtml(base)}<rt>${escapeHtml(reading)}</rt></ruby>`;
    }

    function formatRubyValue(value) {
        const source = String(value || '');
        const match = source.match(/^\{([^{}|]+)\|([^{}|]+)\}$/);
        return match ? formatCompactRuby(match[1], match[2]) : escapeHtml(source);
    }

    function storedPreference() {
        try {
            return window.localStorage.getItem(storageKey);
        } catch {
            return null;
        }
    }

    function savePreference(visible) {
        try {
            window.localStorage.setItem(storageKey, String(visible));
        } catch {
            // The setting still works for this page when storage is unavailable.
        }
    }

    function applyPreference(visible, persist = false) {
        root.classList.toggle('readings-hidden', !visible);
        toggles.forEach(toggle => {
            toggle.setAttribute('aria-pressed', String(visible));
            toggle.setAttribute('aria-label', visible ? '漢字の読みを隠す' : '漢字の読みを表示');
            toggle.title = visible ? '漢字の読みを隠す' : '漢字の読みを表示';
        });
        if (persist) savePreference(visible);
    }

    const saved = storedPreference();
    let readingsVisible = saved !== 'false';
    applyPreference(readingsVisible);

    toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            readingsVisible = !readingsVisible;
            applyPreference(readingsVisible, true);
        });
    });

    window.HaikuReadings = Object.freeze({formatRubyValue});
})();
