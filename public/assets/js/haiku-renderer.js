(() => {
    'use strict';

    const kanjiMap = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
    const defaultAudio = 'https://actions.google.com/sounds/v1/water/waves_crashing_on_rock_beach.ogg';

    let lastInteractionTime = Date.now();
    let isHoveringPoem = false;
    let isAutoPaused = false;
    let autoPauseEndTime = 0;
    let lastCenteredItemIndex = -1;
    let trackItems = [];
    let physicsItems = [];
    let currentX = 0;
    let targetX = 0;
    let activeColor = '#fcfbf8';
    let activeTheme = 'light';
    let smoothedVelocity = 0;
    let musicStarted = false;

    const ease = 0.08;
    const instruction = document.getElementById('instruction');
    const track = document.getElementById('track');
    const atmosphere = document.getElementById('atmosphere');
    const bgMusic = document.getElementById('bg-music');
    const musicToggle = document.getElementById('music-toggle');
    const copyright = document.getElementById('copyright');

    function convertToKanji(numStr) {
        return String(numStr)
            .split('')
            .map(char => /[0-9]/.test(char) ? kanjiMap[parseInt(char, 10)] : char)
            .join('');
    }

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
        const modernized = normalized
            .replace(/ひ/g, 'い')
            .replace(/ふ/g, 'う');

        return modernized === normalized ? [normalized] : [normalized, modernized];
    }

    function formatCompactRuby(base, reading) {
        const chunks = String(base).match(/[\p{Script=Han}ヶ]+|[^\p{Script=Han}ヶ]+/gu) || [];
        const normalizedReading = toHiragana(reading);
        const hasKanji = chunks.some(chunk => /^[\p{Script=Han}ヶ]+$/u.test(chunk));
        if (!hasKanji) {
            return escapeHtml(base);
        }

        function renderChunks(index, readingIndex) {
            if (index === chunks.length) {
                return readingIndex === normalizedReading.length ? '' : null;
            }

            const chunk = chunks[index];
            const isKanji = /^[\p{Script=Han}ヶ]+$/u.test(chunk);
            if (!isKanji) {
                for (const expected of literalReadingCandidates(chunk)) {
                    if (!normalizedReading.startsWith(expected, readingIndex)) {
                        continue;
                    }

                    const rest = renderChunks(index + 1, readingIndex + expected.length);
                    if (rest !== null) {
                        return `${escapeHtml(chunk)}${rest}`;
                    }
                }

                return null;
            }

            for (let end = readingIndex + 1; end <= normalizedReading.length; end += 1) {
                const rest = renderChunks(index + 1, end);
                if (rest !== null) {
                    const rubyReading = String(reading).slice(readingIndex, end);
                    return `<ruby>${escapeHtml(chunk)}<rt>${escapeHtml(rubyReading)}</rt></ruby>${rest}`;
                }
            }

            return null;
        }

        return renderChunks(0, 0) ?? `<ruby>${escapeHtml(base)}<rt>${escapeHtml(reading)}</rt></ruby>`;
    }

    function formatRubyLine(line) {
        const source = String(line || '');
        let html = '';
        let lastIndex = 0;
        const rubyPattern = /\{([^{}|]+)\|([^{}|]+)\}/g;
        let match;

        while ((match = rubyPattern.exec(source)) !== null) {
            html += escapeHtml(source.slice(lastIndex, match.index));
            html += formatCompactRuby(match[1], match[2]);
            lastIndex = match.index + match[0].length;
        }

        html += escapeHtml(source.slice(lastIndex));
        return html;
    }

    function parseValue(value) {
        return value.trim().replace(/^["']|["']$/g, '');
    }

    function parseFrontMatter(markdown) {
        const source = markdown.replace(/\r\n/g, '\n');
        if (!source.startsWith('---\n')) {
            return { meta: {}, body: source };
        }

        const endIndex = source.indexOf('\n---', 4);
        if (endIndex === -1) {
            return { meta: {}, body: source };
        }

        const meta = {};
        const frontMatter = source.slice(4, endIndex).split('\n');
        frontMatter.forEach(line => {
            const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
            if (match) {
                meta[match[1]] = parseValue(match[2]);
            }
        });

        return {
            meta,
            body: source.slice(endIndex + 4).trim()
        };
    }

    function parsePoemHeading(heading) {
        const [date = '', location = ''] = heading.split('|').map(part => part.trim());
        return { date, location };
    }

    function parseCollection(markdown) {
        const { meta, body } = parseFrontMatter(markdown);
        const poems = [];
        let current = null;

        body.split('\n').forEach(rawLine => {
            const line = rawLine.trim();

            if (!line || line === '---' || line.startsWith('<!--')) {
                return;
            }

            if (line.startsWith('# ') && !current) {
                return;
            }

            if (line.startsWith('## ')) {
                if (current) {
                    poems.push(current);
                }

                const heading = line.replace(/^##\s+/, '');
                current = {
                    ...parsePoemHeading(heading),
                    keyword: '',
                    bgColor: '#fcfbf8',
                    theme: 'light',
                    lines: []
                };
                return;
            }

            if (!current) {
                return;
            }

            const fieldMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
            if (fieldMatch) {
                const key = fieldMatch[1];
                const value = parseValue(fieldMatch[2]);
                if (key === 'background') current.bgColor = value;
                else if (key === 'theme') current.theme = value;
                else current[key] = value;
                return;
            }

            const bulletMatch = line.match(/^[-*]\s+(.*)$/);
            if (bulletMatch) {
                current.lines.push(parseValue(bulletMatch[1]));
            }
        });

        if (current) {
            poems.push(current);
        }

        return {
            meta,
            poems: poems.filter(poem => poem.lines.length > 0)
        };
    }

    function normalizeCollection(collection) {
        return {
            meta: collection.meta || {},
            poems: (collection.poems || []).map(poem => ({
                ...poem,
                bgColor: poem.bgColor || poem.background || '#fcfbf8',
                theme: poem.theme || 'light',
                lines: poem.lines || []
            })).filter(poem => poem.lines.length > 0)
        };
    }

    function parseCollectionSource(sourceText, sourcePath) {
        if (sourcePath.endsWith('.json')) {
            return normalizeCollection(JSON.parse(sourceText));
        }

        return normalizeCollection(parseCollection(sourceText));
    }

    function sourceDirectory(sourcePath) {
        const parts = sourcePath.split('/');
        parts.pop();
        return parts.join('/');
    }

    function resolveSourcePath(basePath, relativePath) {
        if (/^https?:\/\//.test(relativePath) || relativePath.startsWith('/')) {
            return relativePath;
        }

        const base = sourceDirectory(basePath);
        return base ? `${base}/${relativePath}` : relativePath;
    }

    async function fetchText(sourcePath) {
        const response = await fetch(sourcePath, { cache: 'no-cache' });
        if (!response.ok) {
            throw new Error(`Failed to load ${sourcePath}: ${response.status}`);
        }
        return response.text();
    }

    async function loadCollectionSource(sourcePath) {
        const sourceText = await fetchText(sourcePath);

        if (!sourcePath.endsWith('.json')) {
            return parseCollectionSource(sourceText, sourcePath);
        }

        const parsed = JSON.parse(sourceText);
        if (!parsed.months) {
            return normalizeCollection(parsed);
        }

        const monthCollections = await Promise.all(parsed.months.map(async month => {
            const monthPath = resolveSourcePath(sourcePath, month.path);
            const monthText = await fetchText(monthPath);
            return normalizeCollection(JSON.parse(monthText));
        }));

        return normalizeCollection({
            meta: parsed.meta || {},
            poems: monthCollections.flatMap(collection => collection.poems)
        });
    }

    function formatDate(date) {
        const value = String(date || '').trim();
        const isoMatch = value.match(/^\d{4}-(\d{1,2})-(\d{1,2})$/);
        const shortMatch = value.match(/^(\d{1,2})[./](\d{1,2})$/);

        if (isoMatch) {
            return `${convertToKanji(Number(isoMatch[1]))}月${convertToKanji(Number(isoMatch[2]))}日`;
        }

        if (shortMatch) {
            return `${convertToKanji(Number(shortMatch[1]))}月${convertToKanji(Number(shortMatch[2]))}日`;
        }

        return value;
    }

    function setMetaContent(selector, content) {
        const element = document.querySelector(selector);
        if (element && content) {
            element.setAttribute('content', content);
        }
    }

    function applyCollectionMeta(meta) {
        const intro = track.querySelector('.intro-title');
        const heading = intro.querySelector('h1');
        const subtitle = intro.querySelector('p');

        heading.textContent = meta.title || heading.textContent;
        subtitle.textContent = meta.subtitle || subtitle.textContent;
        intro.dataset.color = meta.background || intro.dataset.color || '#fcfbf8';
        intro.dataset.theme = meta.theme || intro.dataset.theme || 'light';
        document.title = meta.pageTitle || `${heading.textContent} | itsuki haiku`;

        if (meta.description) {
            setMetaContent('meta[name="description"]', meta.description);
            setMetaContent('meta[property="og:description"]', meta.description);
            setMetaContent('meta[name="twitter:description"]', meta.description);
        }

        if (meta.title) {
            setMetaContent('meta[property="og:title"]', meta.title);
            setMetaContent('meta[name="twitter:title"]', meta.title);
        }

        if (meta.author) {
            setMetaContent('meta[name="author"]', meta.author);
        }

        if (meta.cover) {
            setMetaContent('meta[property="og:image"]', meta.cover);
            setMetaContent('meta[name="twitter:image"]', meta.cover);
        }

        if (copyright && meta.copyright) {
            copyright.textContent = meta.copyright;
        }

        if (bgMusic) {
            bgMusic.src = meta.audio || defaultAudio;
        }
    }

    function recordInteraction() {
        lastInteractionTime = Date.now();
        isAutoPaused = false;
        if (instruction) instruction.style.opacity = '0.2';
    }

    function addRippleInteraction(content) {
        content.addEventListener('click', event => {
            recordInteraction();
            const ring = document.createElement('div');
            ring.className = 'click-ring';
            ring.style.left = `${event.clientX}px`;
            ring.style.top = `${event.clientY}px`;
            document.body.appendChild(ring);
            setTimeout(() => ring.remove(), 1000);

            content.querySelectorAll('.line').forEach(line => {
                const rect = line.getBoundingClientRect();
                const distance = Math.hypot(
                    (rect.left + rect.width / 2) - event.clientX,
                    (rect.top + rect.height / 2) - event.clientY
                );
                line.style.animationDelay = `${distance * 2.2}ms`;
                line.classList.remove('ripple-anim');
                void line.offsetWidth;
                line.classList.add('ripple-anim');
            });
        });

        content.addEventListener('mouseenter', () => {
            isHoveringPoem = true;
            recordInteraction();
        });

        content.addEventListener('mouseleave', () => {
            isHoveringPoem = false;
            recordInteraction();
        });
    }

    function createPoemElement(poem, index) {
        const item = document.createElement('article');
        item.className = 'haiku-item physics-item track-item';
        item.dataset.color = poem.bgColor || '#fcfbf8';
        item.dataset.theme = poem.theme || 'light';

        const giant = document.createElement('div');
        giant.className = 'giant-keyword';
        giant.textContent = poem.keyword || '';
        giant.style.animationDelay = `${index * -2.7}s`;
        item.appendChild(giant);

        const content = document.createElement('div');
        content.className = 'poem-content';
        content.setAttribute('role', 'button');
        content.setAttribute('tabindex', '0');
        content.setAttribute('aria-label', poem.lines.join(' / '));

        poem.lines.slice(0, 3).forEach((line, lineIndex) => {
            const div = document.createElement('div');
            div.className = `line l${lineIndex + 1}`;
            div.innerHTML = formatRubyLine(line);
            content.appendChild(div);
        });

        addRippleInteraction(content);
        item.appendChild(content);

        const meta = document.createElement('div');
        meta.className = 'meta';

        const dateDiv = document.createElement('div');
        dateDiv.className = 'date';
        dateDiv.textContent = formatDate(poem.date);

        const stamp = document.createElement('div');
        stamp.className = 'stamp';
        stamp.innerHTML = formatRubyLine(poem.location || '');

        meta.appendChild(dateDiv);
        meta.appendChild(stamp);
        item.appendChild(meta);

        return item;
    }

    function renderPoems(poems) {
        track.querySelectorAll('.haiku-item, .load-error').forEach(element => element.remove());
        poems.forEach((poem, index) => {
            track.appendChild(createPoemElement(poem, index));
        });
        trackItems = Array.from(document.querySelectorAll('.track-item'));
        physicsItems = Array.from(document.querySelectorAll('.physics-item'));
    }

    function showLoadError(error) {
        const message = document.createElement('div');
        message.className = 'load-error track-item';
        message.dataset.color = '#fcfbf8';
        message.dataset.theme = 'light';
        message.textContent = '俳句を読み込めませんでした';
        track.appendChild(message);
        trackItems = Array.from(document.querySelectorAll('.track-item'));
        console.error(error);
    }

    function getMaxScroll() {
        return Math.max(0, track.getBoundingClientRect().width - window.innerWidth);
    }

    function setupInput() {
        window.addEventListener('wheel', event => {
            recordInteraction();
            targetX += event.deltaY * 1.3;
            targetX = Math.max(0, Math.min(targetX, getMaxScroll()));
        }, { passive: true });

        window.addEventListener('mousemove', recordInteraction, { passive: true });

        let touchStartX = 0;
        window.addEventListener('touchstart', event => {
            recordInteraction();
            touchStartX = event.touches[0].clientX;
        }, { passive: true });

        window.addEventListener('touchmove', event => {
            recordInteraction();
            const touchX = event.touches[0].clientX;
            const diff = touchStartX - touchX;
            targetX += diff * 2.2;
            targetX = Math.max(0, Math.min(targetX, getMaxScroll()));
            touchStartX = touchX;
        }, { passive: true });

        window.addEventListener('resize', () => {
            targetX = Math.max(0, Math.min(targetX, getMaxScroll()));
        });
    }

    function setupMusic() {
        musicToggle.addEventListener('click', () => {
            if (bgMusic.paused) {
                const playPromise = bgMusic.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        musicToggle.classList.add('playing');
                        musicStarted = true;
                    }).catch(error => console.log(error));
                }
            } else {
                bgMusic.pause();
                musicToggle.classList.remove('playing');
            }
        });

        const startMusicOnInteraction = () => {
            if (!musicStarted) {
                bgMusic.volume = 0.5;
                const playPromise = bgMusic.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        musicToggle.classList.add('playing');
                        musicStarted = true;
                    }).catch(error => console.log('Waiting for audio permission', error));
                }
            }
            window.removeEventListener('click', startMusicOnInteraction);
            window.removeEventListener('wheel', startMusicOnInteraction);
            window.removeEventListener('touchstart', startMusicOnInteraction);
        };

        window.addEventListener('click', startMusicOnInteraction, { once: true });
        window.addEventListener('wheel', startMusicOnInteraction, { once: true });
        window.addEventListener('touchstart', startMusicOnInteraction, { once: true });
    }

    function renderFrame() {
        const idleTime = Date.now() - lastInteractionTime;
        const maxScroll = getMaxScroll();
        const screenCenter = window.innerWidth / 2;

        if (isAutoPaused && Date.now() > autoPauseEndTime) {
            isAutoPaused = false;
        }

        let isAutoScrolling = false;
        const baseScrollSpeed = Math.max(0.6, window.innerWidth * 0.0008);

        if ((idleTime > 2500 && !isHoveringPoem) || idleTime > 6000) {
            if (!isAutoPaused && targetX < maxScroll) {
                targetX += baseScrollSpeed;
                isAutoScrolling = true;
                if (instruction) instruction.style.opacity = '0.6';
            }
        }

        trackItems.forEach((item, index) => {
            const rect = item.getBoundingClientRect();
            const expectedItemCenter = rect.left + rect.width / 2 + (targetX - currentX);
            const distToCenter = screenCenter - expectedItemCenter;

            if (Math.abs(distToCenter) > 60 && lastCenteredItemIndex === index) {
                lastCenteredItemIndex = -1;
            }

            if (isAutoScrolling && Math.abs(distToCenter) <= baseScrollSpeed * 1.5 && lastCenteredItemIndex !== index) {
                targetX += distToCenter;
                isAutoPaused = true;
                autoPauseEndTime = Date.now() + 2000;
                lastCenteredItemIndex = index;
            }
        });

        currentX += (targetX - currentX) * ease;

        const instantVelocity = targetX - currentX;
        smoothedVelocity += (instantVelocity - smoothedVelocity) * 0.1;

        track.style.transform = `translateX(${currentX}px)`;

        physicsItems.forEach(item => {
            let skewY = smoothedVelocity * 0.035;
            skewY = Math.max(-15, Math.min(skewY, 15));
            item.style.transform = `skewY(${skewY}deg)`;
        });

        let closestItem = null;
        let minDistance = Infinity;

        trackItems.forEach(item => {
            const rect = item.getBoundingClientRect();
            const dist = Math.abs(screenCenter - (rect.left + rect.width / 2));
            if (dist < minDistance) {
                minDistance = dist;
                closestItem = item;
            }
        });

        if (closestItem) {
            const targetColor = closestItem.dataset.color;
            const targetTheme = closestItem.dataset.theme;

            if (targetColor && targetColor !== activeColor) {
                activeColor = targetColor;
                atmosphere.style.backgroundColor = activeColor;
            }

            if (targetTheme && targetTheme !== activeTheme) {
                activeTheme = targetTheme;
                document.body.classList.toggle('dark-mode', activeTheme === 'dark');
            }
        }

        requestAnimationFrame(renderFrame);
    }

    async function init() {
        setupInput();
        setupMusic();

        const source = document.body.dataset.haikuSource || 'content/haiku/generated/itsuki-haiku.json';
        try {
            const collection = await loadCollectionSource(source);
            applyCollectionMeta(collection.meta);
            renderPoems(collection.poems);
        } catch (error) {
            showLoadError(error);
        }

        renderFrame();
    }

    init();
})();
