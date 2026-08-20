(() => {
    'use strict';

    const kanjiMap = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
    const defaultAudio = 'https://actions.google.com/sounds/v1/water/waves_crashing_on_rock_beach.ogg';

    const body = document.body;
    const track = document.getElementById('track');
    const rail = document.getElementById('rail');
    const count = document.getElementById('haiku-count');
    const copyright = document.getElementById('copyright');
    const bgMusic = document.getElementById('bg-music');
    const musicToggle = document.getElementById('music-toggle');
    const loadStatus = document.getElementById('load-status');
    const sourcePath = body.dataset.haikuSource || 'content/haiku/generated/itsuki-haiku.json';

    let sections = [];
    let railButtons = [];
    let activeIndex = 0;
    const sectionRatios = new Map();

    function convertToKanji(numStr) {
        return String(numStr)
            .split('')
            .map(character => /[0-9]/.test(character) ? kanjiMap[parseInt(character, 10)] : character)
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

    function plainText(value) {
        return String(value || '').replace(/\{([^{}|]+)\|[^{}|]+\}/g, '$1');
    }

    function markKigoText(element, value) {
        const kigo = String(value || '').trim();
        if (!kigo) return false;

        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                if (!node.nodeValue || node.parentElement?.closest('rt')) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        const textNodes = [];
        let displayedText = '';
        let node;

        while ((node = walker.nextNode())) {
            textNodes.push({ node, start: displayedText.length });
            displayedText += node.nodeValue;
        }

        const matchStart = displayedText.indexOf(kigo);
        if (matchStart === -1) return false;
        const matchEnd = matchStart + kigo.length;

        textNodes.forEach(({ node: textNode, start }) => {
            const nodeEnd = start + textNode.nodeValue.length;
            const overlapStart = Math.max(matchStart, start);
            const overlapEnd = Math.min(matchEnd, nodeEnd);
            if (overlapStart >= overlapEnd) return;

            const range = document.createRange();
            range.setStart(textNode, overlapStart - start);
            range.setEnd(textNode, overlapEnd - start);
            const marker = document.createElement('span');
            marker.className = 'kigo-inline';
            range.surroundContents(marker);
        });

        return true;
    }

    function accentFor(background, theme) {
        if (theme === 'dark') return '#e0a25a';

        const match = String(background || '').match(/^#([0-9a-f]{6})$/i);
        if (!match) return '#7a6a44';
        const value = parseInt(match[1], 16);
        const channels = [value >> 16, (value >> 8) & 255, value & 255].map(channel => channel / 255);
        const max = Math.max(...channels);
        const min = Math.min(...channels);
        const delta = max - min;
        let hue = 0;

        if (delta !== 0) {
            if (max === channels[0]) hue = 60 * (((channels[1] - channels[2]) / delta) % 6);
            else if (max === channels[1]) hue = 60 * (((channels[2] - channels[0]) / delta) + 2);
            else hue = 60 * (((channels[0] - channels[1]) / delta) + 4);
        }

        if (hue < 0) hue += 360;
        const lightness = (max + min) / 2;
        const saturation = delta === 0 ? 0 : delta / (1 - Math.abs((2 * lightness) - 1));
        const accentSaturation = Math.max(32, Math.min(55, Math.round(saturation * 200)));
        return `hsl(${Math.round(hue)} ${accentSaturation}% 36%)`;
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
        source.slice(4, endIndex).split('\n').forEach(line => {
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
        const { meta, body: content } = parseFrontMatter(markdown);
        const poems = [];
        let current = null;

        content.split('\n').forEach(rawLine => {
            const line = rawLine.trim();
            if (!line || line === '---' || line.startsWith('<!--')) {
                return;
            }

            if (line.startsWith('# ') && !current) {
                return;
            }

            if (line.startsWith('## ')) {
                if (current) poems.push(current);
                current = {
                    ...parsePoemHeading(line.replace(/^##\s+/, '')),
                    keyword: '',
                    bgColor: '#fcfbf8',
                    theme: 'light',
                    lines: []
                };
                return;
            }

            if (!current) return;

            const fieldMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
            if (fieldMatch) {
                const key = fieldMatch[1];
                const value = parseValue(fieldMatch[2]);
                if (key === 'background') current.bgColor = value;
                else current[key] = value;
                return;
            }

            const bulletMatch = line.match(/^[-*]\s+(.*)$/);
            if (bulletMatch) current.lines.push(parseValue(bulletMatch[1]));
        });

        if (current) poems.push(current);
        return { meta, poems };
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

    function sourceDirectory(path) {
        const parts = path.split('/');
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

    async function fetchText(path) {
        const response = await fetch(path, { cache: 'no-cache' });
        if (!response.ok) {
            throw new Error(`Failed to load ${path}: ${response.status}`);
        }
        return response.text();
    }

    async function loadCollectionSource(path) {
        const sourceText = await fetchText(path);
        if (!path.endsWith('.json')) {
            return normalizeCollection(parseCollection(sourceText));
        }

        const parsed = JSON.parse(sourceText);
        if (!parsed.months) {
            return normalizeCollection(parsed);
        }

        const monthCollections = await Promise.all(parsed.months.map(async month => {
            const monthPath = resolveSourcePath(path, month.path);
            return normalizeCollection(JSON.parse(await fetchText(monthPath)));
        }));

        return normalizeCollection({
            meta: parsed.meta || {},
            poems: monthCollections.flatMap(collection => collection.poems)
        });
    }

    function formatDate(date) {
        const match = String(date || '').match(/^\d{4}-(\d{1,2})-(\d{1,2})$/);
        if (!match) return String(date || '');
        return `${convertToKanji(Number(match[1]))}月${convertToKanji(Number(match[2]))}日`;
    }

    function setMetaContent(selector, content) {
        const element = document.querySelector(selector);
        if (element && content) element.setAttribute('content', content);
    }

    function applyCollectionMeta(meta) {
        const title = meta.title || '樹の句帖';
        const subtitle = meta.subtitle || 'itsuki の俳句';
        document.getElementById('collection-title').textContent = title;
        document.querySelector('.wordmark').textContent = title;
        document.querySelector('.sub').textContent = subtitle;
        document.title = meta.pageTitle || `${title} | itsuki haiku`;

        if (meta.description) {
            setMetaContent('meta[name="description"]', meta.description);
            setMetaContent('meta[property="og:description"]', meta.description);
            setMetaContent('meta[name="twitter:description"]', meta.description);
        }
        if (meta.title) {
            setMetaContent('meta[property="og:title"]', meta.title);
            setMetaContent('meta[name="twitter:title"]', meta.title);
        }
        if (meta.author) setMetaContent('meta[name="author"]', meta.author);
        if (meta.cover) {
            setMetaContent('meta[property="og:image"]', meta.cover);
            setMetaContent('meta[name="twitter:image"]', meta.cover);
        }

        if (meta.copyright) copyright.textContent = meta.copyright;
        bgMusic.src = meta.audio || defaultAudio;

        const intro = document.getElementById('intro');
        intro.dataset.color = meta.background || '#fcfbf8';
        intro.dataset.theme = meta.theme || 'light';
        intro.dataset.accent = accentFor(intro.dataset.color, intro.dataset.theme);
    }

    function createPoemElement(poem, index) {
        const section = document.createElement('section');
        section.className = 'leaf track-item';
        section.id = `haiku-${index + 1}`;
        section.dataset.color = poem.bgColor || '#fcfbf8';
        section.dataset.theme = poem.theme || 'light';
        section.dataset.accent = accentFor(section.dataset.color, section.dataset.theme);
        section.setAttribute('aria-label', `${formatDate(poem.date)} ${plainText(poem.location)}`);

        const ghost = document.createElement('div');
        ghost.className = 'ghost';
        ghost.setAttribute('aria-hidden', 'true');
        ghost.textContent = poem.keyword || '';
        section.appendChild(ghost);

        const inner = document.createElement('div');
        inner.className = 'leaf-inner';

        const metaTop = document.createElement('div');
        metaTop.className = 'meta-top';

        const place = document.createElement('span');
        place.className = 'place';
        place.innerHTML = formatRubyLine(poem.location || '');
        metaTop.appendChild(place);

        const date = document.createElement('span');
        date.className = 'date-jp';
        date.textContent = formatDate(poem.date);
        metaTop.appendChild(date);
        inner.appendChild(metaTop);

        const poemBlock = document.createElement('div');
        poemBlock.className = 'poem';
        let kigoMarked = false;
        poem.lines.slice(0, 3).forEach((line, lineIndex) => {
            const lineElement = document.createElement('div');
            lineElement.className = `line l${lineIndex + 1}`;
            lineElement.innerHTML = formatRubyLine(line);
            if (!kigoMarked) {
                kigoMarked = markKigoText(lineElement, poem.kigo);
            }
            poemBlock.appendChild(lineElement);
        });
        inner.appendChild(poemBlock);

        const seasonalMeta = document.createElement('div');
        seasonalMeta.className = 'kigo';
        const hasKigo = typeof poem.kigo === 'string' && poem.kigo.trim();
        const metaValue = hasKigo ? poem.kigo : (poem.keyword || '');
        const metaLabel = hasKigo ? '季語' : 'けふの一字';
        seasonalMeta.innerHTML = `<span class="kigo-mark" aria-hidden="true"></span><span class="kw">${escapeHtml(metaValue)}</span><span class="kigo-label">${metaLabel}</span>`;
        inner.appendChild(seasonalMeta);

        section.appendChild(inner);
        return section;
    }

    function createRail() {
        rail.replaceChildren();
        sections.forEach((section, index) => {
            const button = document.createElement('button');
            button.className = 'rail-tick';
            button.type = 'button';
            button.dataset.index = String(index);
            button.setAttribute('aria-label', index === 0 ? '表紙' : `${index}句目へ`);
            button.innerHTML = `<span class="rail-num">${String(index + 1).padStart(2, '0')}</span><span class="bar" aria-hidden="true"></span>`;
            button.addEventListener('click', () => {
                sections[index].scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            rail.appendChild(button);
        });
        railButtons = [...rail.querySelectorAll('.rail-tick')];
    }

    function centerRailButton(button) {
        const top = button.offsetTop - ((rail.clientHeight - button.offsetHeight) / 2);
        rail.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }

    function setActiveSection(index) {
        if (!sections[index]) return;
        activeIndex = index;
        const section = sections[index];
        body.style.backgroundColor = section.dataset.color || '#fcfbf8';
        body.style.setProperty('--accent', section.dataset.accent || '#7a6a44');
        body.classList.toggle('dark-mode', section.dataset.theme === 'dark');

        railButtons.forEach((button, buttonIndex) => {
            const isActive = buttonIndex === index;
            button.classList.toggle('active', isActive);
            if (isActive) button.setAttribute('aria-current', 'true');
            else button.removeAttribute('aria-current');
        });

        if (railButtons[index]) centerRailButton(railButtons[index]);
    }

    function observeSections() {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                sectionRatios.set(entry.target, entry.intersectionRatio);
                if (entry.isIntersecting) entry.target.classList.add('in');
            });

            const mostVisible = sections.reduce((best, section, index) => {
                const ratio = sectionRatios.get(section) || 0;
                return ratio > best.ratio ? { index, ratio } : best;
            }, { index: activeIndex, ratio: -1 });

            if (mostVisible.ratio > 0) setActiveSection(mostVisible.index);
        }, { threshold: [0.2, 0.45, 0.65, 0.85] });

        sections.forEach(section => observer.observe(section));
    }

    function navigateBy(delta) {
        const nextIndex = Math.max(0, Math.min(sections.length - 1, activeIndex + delta));
        sections[nextIndex].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function bindKeyboardNavigation() {
        window.addEventListener('keydown', event => {
            const target = event.target;
            if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
                return;
            }

            if (['ArrowDown', 'PageDown', ' '].includes(event.key)) {
                event.preventDefault();
                navigateBy(1);
            } else if (['ArrowUp', 'PageUp'].includes(event.key)) {
                event.preventDefault();
                navigateBy(-1);
            } else if (event.key === 'Home') {
                event.preventDefault();
                sections[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (event.key === 'End') {
                event.preventDefault();
                sections[sections.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

    function bindMusicControl() {
        musicToggle.addEventListener('click', async () => {
            if (bgMusic.paused) {
                try {
                    await bgMusic.play();
                    musicToggle.classList.add('playing');
                    musicToggle.setAttribute('aria-label', '音楽を停止');
                } catch (error) {
                    loadStatus.textContent = '音楽を再生できませんでした';
                    loadStatus.classList.add('error');
                }
            } else {
                bgMusic.pause();
                musicToggle.classList.remove('playing');
                musicToggle.setAttribute('aria-label', '音楽を再生');
            }
        });
    }

    async function init() {
        try {
            const collection = await loadCollectionSource(sourcePath);
            applyCollectionMeta(collection.meta);
            collection.poems.forEach((poem, index) => {
                track.appendChild(createPoemElement(poem, index));
            });

            count.textContent = `${collection.poems.length} HAIKU · 一句ずつ、静かに`;
            sections = [...track.querySelectorAll('.track-item')];
            createRail();
            observeSections();
            bindKeyboardNavigation();
            bindMusicControl();
            setActiveSection(0);

            if (window.location.hash) {
                const target = document.querySelector(window.location.hash);
                if (target) requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
            }
        } catch (error) {
            console.error(error);
            loadStatus.textContent = '句帖を読み込めませんでした';
            loadStatus.classList.add('error');
        }
    }

    init();
})();
